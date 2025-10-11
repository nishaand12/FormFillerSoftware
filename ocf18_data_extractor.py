#!/usr/bin/env python3
"""
Data Extractor for FSRA OCF-18 Forms
Uses Qwen via the shared ModelManager for structured data extraction
Focuses on Parts 6-9: Injury descriptions, prior conditions, activity limitations, and treatment goals
"""

import os
import json
import re
from datetime import datetime
from typing import Dict, Any, Optional
from model_manager import model_manager


class OCF18DataExtractor:
    def __init__(self, model_type: str = "qwen3-4b"):
        self.model_type = model_type
        self.field_map: Dict[str, str] = {}
        self.checkbox_groups: Dict[str, Any] = {}
        self.field_types: Dict[str, str] = {}
        self._load_configs()

    def _load_configs(self):
        """Load OCF-18 field map, checkbox groups, and field types"""
        try:
            # Use proper resource path for config files
            try:
                from app_paths import get_resource_path
                field_map_path = get_resource_path("config/field_map_ocf18.json")
                checkbox_path = get_resource_path("config/ocf18_checkbox_groups.json")
                field_types_path = get_resource_path("config/ocf18_field_types.json")
            except ImportError:
                # Fallback for development
                import sys
                if getattr(sys, '_MEIPASS', None):
                    from pathlib import Path
                    field_map_path = Path(sys._MEIPASS) / "config/field_map_ocf18.json"
                    checkbox_path = Path(sys._MEIPASS) / "config/ocf18_checkbox_groups.json"
                    field_types_path = Path(sys._MEIPASS) / "config/ocf18_field_types.json"
                else:
                    field_map_path = "config/field_map_ocf18.json"
                    checkbox_path = "config/ocf18_checkbox_groups.json"
                    field_types_path = "config/ocf18_field_types.json"

            with open(field_map_path, "r") as f:
                self.field_map = json.load(f)

            with open(checkbox_path, "r") as f:
                self.checkbox_groups = json.load(f)

            with open(field_types_path, "r") as f:
                self.field_types = json.load(f).get("field_types", {})

            print("OCF-18 configs loaded successfully")
        except Exception as e:
            print(f"Warning: Could not load OCF-18 configs: {e}")
            self.field_map = {}
            self.checkbox_groups = {}
            self.field_types = {}

    def cleanup(self):
        """Cleanup hook to mirror other extractors (ModelManager handles actual cleanup)"""
        print("OCF18DataExtractor cleanup completed (using shared ModelManager)")

    def _date_rule(self) -> str:
        return "DD-MM-YYYY"

    def _create_ocf18_prompt(self, transcript_text: str) -> str:
        """Create a focused prompt for OCF-18 extraction"""

        # Build comprehensive prompt
        prompt = f"""Extract form data from this physiotherapy assessment transcript. You are a specialized medical data analyst. Carefully read the entire transcript and extract the required fields as described below.

CRITICAL RULES:
- Return ONLY a single JSON object. Do not repeat the JSON. Do not add explanations. Do not add markdown formatting.
- For any field, only extract information if it is explicitly stated or can be directly and unambiguously inferred from the transcript context. If there is any doubt or the information is missing, set the field to null.
- For single-choice (radio) and yes/no (boolean) fields, select a value only if the transcript gives clear and direct evidence; avoid inferring or guessing. Otherwise, set the field to null.
- When extracting dates, convert any natural language date (e.g. 'August 4th, 2025') to exactly 'YYYY-MM-DD' format.
- For categorical fields, the extracted value must match one of the allowed options exactly (case-sensitive). Never invent new option strings.

The output must be a single JSON object that contains every field listed below, even if set to null. Do not omit keys. The JSON must be formatted with two-space indentation.:
REQUIRED JSON OUTPUT:
{{
  "diagnosis_description_1": "Primary injury description (most significant)",
  "diagnosis_description_2": "Secondary injury description (if applicable)",
  "diagnosis_description_3": "Third injury description (if applicable)", 
  "diagnosis_description_4": "Fourth injury description (if applicable)",
  "part7_a_checkbox": "Prior to the accident, did the applicant have any disease, condition or injury that could affect his/her response to treatment for the injuries identified? (no/unknown/yes)",
  "part7_a_please_explain": "Please explain the prior conditions affecting treatment. (if yes to part7_a_checkbox)",
  "part7_a2_checkbox": "Did the applicant undergo investigation or receive treatment for this disease, condition or injury in the past year? (no/unknown/yes)",
  "part7_a1_please_explain": "Explain past year treatment for prior conditions. (if yes to part7_a2_checkbox)",
  "part7_b_checkbox": "Has the applicant developed any other disease, condition or injury not related to the automobile accident that could affect their response to treatment? (no/unknown/yes)",
  "part7_b_please_explain": "Explain concurrent conditions since accident. (if yes to part7_b_checkbox)",
  "part8_task_checkbox": "Does the impairment affect the applicant's ability to perform their employment tasks? (not_employed/no/unknown/yes)",
  "part8_act_checkbox": "Does the impairment affect the applicant's ability to perform their daily activities? (no/unknown/yes)",
  "part8_b_please_explain": "Description of activity limitations. (if yes to part8_task_checkbox or part8_act_checkbox)",
  "part8_c_checkbox": "Is the employer able to provide suitable modified employment to the applicant? (not_employed/yes/unknown/no)",
  "part8_c_please_explain": "Please explain the reason for the employer's inability to provide suitable modified employment. (if no to part8_c_checkbox)",
  "part9i_goals": "Goals in regard to impairment, symptom, or pathology that this Treatment and Assessment Plan seeks to achieve. (pain_reduction/increased_range_of_motion/increase_in_strength/other)",
  "part9i_other_please_specify": "Please specify the other goals. (if part9i_goals is 'other')",
  "part9ii_function_goals": "Functional goals that this Treatment and Assessment Plan seeks to achieve. (return_to_activities_of_normal_living/return_to_pre_accident_work_activities/return_to_modified_work_activities/other)",
  "part9_a2_please_specify": "Please specify the other functional goals. (if part9ii_function_goals is 'other')",
  "part9_b1": "How will progress on the goal(s) specified be evaluated?",
  "part9_b2": "If this is a subsequent Treatment and Assessment Plan, what was the applicants improvement at the end of the previous plan based on your evaluation method?",
  "part9_c1_checkbox": "Are there any barriers to recovery? (no/yes)",
  "part9_c1_please_explain": "Explain the barriers to recovery. (if yes to part9_c1_checkbox)",
  "part9_c2_checkbox": "Recommendations and/or strategies to overcome these barriers? (no/yes)",
  "part9_c2_please_explain": "Please explain the recommendations and/or strategies to overcome these barriers. (if yes to part9_c2_checkbox)",
  "part9_d_checkbox": "Is there any concurrent treatment that will be porvided by any other provider/facility? (no/yes)",
  "part9_d_please_explain": "Please explain the concurrent treatment. (if yes to part9_d_checkbox)"
}}

TRANSCRIPT: 
{transcript_text}

CRITICAL: Return ONLY a single JSON object. Do not repeat the JSON. Do not add explanations. Do not add markdown formatting. Stop after the closing brace.

Extract transcript data and return ONLY the JSON object:"""

        return prompt

    def _extract_with_model(self, text: str) -> Dict[str, Any]:
        """Extract data using the shared ModelManager with robust JSON recovery"""
        try:
            prompt = self._create_ocf18_prompt(text)
            print(f"Extracting OCF-18 data with {self.model_type} using shared ModelManager...")

            # Optimize parameters for Qwen models to prevent repetition
            if self.model_type in ["qwen3-1.7b", "qwen3-4b"]:
                result = model_manager.process_prompt(
                    prompt=prompt,
                    model_type=self.model_type,
                    max_tokens=2048,  # Increased for complete JSON
                    temperature=0.0,  # More deterministic output
                    stop_sequences=["Transcript:", "Rules:", "```", "```json", "}\n```", "}\n\n", "}\n\n```"]
                )
            else:
                result = model_manager.process_prompt(
                    prompt=prompt,
                    model_type=self.model_type,
                    max_tokens=1536,
                    temperature=0.1,
                    stop_sequences=["Transcript:", "Rules:"]
                )

            if not result.get('success'):
                print(f"Warning: Model inference failed: {result.get('error')}")
                return {}

            response_text = result.get('text', '')
            print(f"Model response length: {len(response_text)}")
            print(f"Model response preview: {response_text[:300]}...")

            # Try to locate JSON by brace counting
            json_start = response_text.find('{')
            if json_start == -1:
                # Try recovering if it starts directly with keys
                if '"diagnosis_description_1"' in response_text or '"part7_a_please_explain"' in response_text:
                    json_str = "{" + response_text.strip()
                else:
                    print("Warning: No JSON start found in response")
                    return {}
            else:
                brace_count = 0
                json_end = json_start
                for i, ch in enumerate(response_text[json_start:], json_start):
                    if ch == '{':
                        brace_count += 1
                    elif ch == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_end = i + 1
                            break
                json_str = response_text[json_start:json_end]

            print(f"Extracted JSON string preview: {json_str[:200]}...")

            try:
                data = json.loads(json_str)
                print(f"Successfully parsed JSON with {len(data)} keys")
                return data
            except json.JSONDecodeError as e:
                print(f"Warning: JSON decode error: {e}")
                print("Attempting common fixes...")

                # Common recovery steps
                json_fixed = json_str
                # Remove trailing commas
                json_fixed = re.sub(r',\s*([}\]])', r'\1', json_fixed)
                # Normalize newlines in values
                json_fixed = re.sub(r'\n', ' ', json_fixed)
                # Fix accidental double quotes before delimiters
                json_fixed = re.sub(r'""(\s*[,}])', r'"\1', json_fixed)

                try:
                    data = json.loads(json_fixed)
                    print(f"Successfully parsed JSON after fixes with {len(data)} keys")
                    return data
                except json.JSONDecodeError as e2:
                    print(f"Warning: Still invalid JSON after fixes: {e2}")

                    # Last-resort manual parsing for strings/bools/nulls
                    try:
                        data: Dict[str, Any] = {}
                        str_pairs = re.findall(r'"([^"]+)"\s*:\s*"([^"]*)"', json_fixed)
                        for k, v in str_pairs:
                            data[k] = v
                        bool_pairs = re.findall(r'"([^"]+)"\s*:\s*(true|false)', json_fixed)
                        for k, v in bool_pairs:
                            data[k] = v.lower() == 'true'
                        null_pairs = re.findall(r'"([^"]+)"\s*:\s*null', json_fixed)
                        for k in null_pairs:
                            data[k] = None
                        if data:
                            print(f"Manual parse recovered {len(data)} fields")
                            return data
                    except Exception as e3:
                        print(f"Manual parsing failed: {e3}")

            return {}
        except Exception as e:
            print(f"Warning: OCF-18 extraction failed: {e}")
            return {}

    def extract_data(self, transcript_path: str, appointment_id: str, output_path: Optional[str] = None) -> Dict[str, Any]:
        """Extract OCF-18 data from transcript and persist to JSON"""
        try:
            with open(transcript_path, 'r', encoding='utf-8') as f:
                transcript_text = f.read()

            print(f"Processing transcript for OCF-18: {transcript_path}")
            print(f"Transcript length: {len(transcript_text)} characters")

            extracted = self._extract_with_model(transcript_text)

            # Add metadata
            extracted['appointment_id'] = appointment_id
            extracted['extraction_timestamp'] = datetime.now().isoformat()
            extracted['model_used'] = self.model_type
            extracted['transcript_path'] = transcript_path

            # Save
            if output_path is None:
                raise ValueError("output_path is required for data extraction")
            else:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(extracted, f, indent=2, ensure_ascii=False)

            print(f"OCF-18 extraction saved to: {output_path}")
            return extracted
        except Exception as e:
            print(f"Error extracting OCF-18 data: {e}")
            return {}

    def get_extraction(self, extraction_path: str) -> Optional[Dict[str, Any]]:
        """Get an existing OCF-18 extraction from a specific path"""
        if os.path.exists(extraction_path):
            with open(extraction_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None


if __name__ == "__main__":
    # Optional: lightweight smoke test if a transcript exists
    test_transcript = "transcripts/test_123.txt"
    if os.path.exists(test_transcript):
        extractor = OCF18DataExtractor(model_type="qwen3-4b")
        res = extractor.extract_data(test_transcript, "test_ocf18")
        print(json.dumps(res, indent=2))
    else:
        print("No test transcript found; skipping")
