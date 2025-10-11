#!/usr/bin/env python3
"""
Lightweight Data Extractor for FSRA OCF-23 Forms
Uses Qwen for fast, efficient data extraction
"""

import os
import json
import re
from datetime import datetime
from typing import Dict, Any, Optional
from model_manager import model_manager


class OCF23DataExtractor:
    def __init__(self, model_type="qwen3-4b"):
        self.model_type = model_type
        self.field_map = None
        self.checkbox_groups = None
        
        # Load field mappings
        self._load_field_mappings()
        
    def _load_field_mappings(self):
        """Load OCF-23 field mappings and checkbox groups"""
        try:
            with open("config/field_map_ocf23_simplified.json", "r") as f:
                self.field_map = json.load(f)
            
            with open("config/ocf23_checkbox_groups_simplified.json", "r") as f:
                self.checkbox_groups = json.load(f)
                
            print("Field mappings loaded successfully")
        except Exception as e:
            print(f"Warning: Could not load field mappings: {e}")
            self.field_map = {}
            self.checkbox_groups = {}
    
    def cleanup(self):
        """Clean up resources - no longer needed with ModelManager"""
        # The ModelManager handles cleanup centrally
        print(f"OCF23DataExtractor cleanup completed (using shared ModelManager)")

    def _create_ocf23_prompt(self, transcript_text: str):
        """Create a structured prompt for OCF-23 field extraction"""
        
        prompt = f"""Extract OCF-23 form data from this physiotherapy assessment transcript. You are a specialized medical data analyst. Carefully read the entire transcript and extract the required fields as described below.

CRITICAL RULES:
- Return ONLY a single JSON object. Do not repeat the JSON. Do not add explanations. Do not add markdown formatting.
- For any field, only extract information if it is explicitly stated or can be directly and unambiguously inferred from the transcript context. If there is any doubt or the information is missing, set the field to null.
- For single-choice (radio) and yes/no (boolean) fields, select a value only if the transcript gives clear and direct evidence; avoid inferring or guessing. Otherwise, set the field to null.
- When extracting dates, convert any natural language date (e.g. 'August 4th, 2025') to exactly 'YYYY-MM-DD' format.
- For categorical fields, the extracted value must match one of the allowed options exactly (case-sensitive). Never invent new option strings.

The output must be a single JSON object that contains every field listed below, even if set to null. Do not omit keys. The JSON must be formatted with two-space indentation.:
REQUIRED JSON OUTPUT:
{{
  "injury_sequelae_1_diagnosis": "Primary injury diagnosis or condition",
  "injury_sequelae_2_diagnosis": "Secondary injury diagnosis or condition (if mentioned)",
  "injury_sequelae_3_diagnosis": "Third injury diagnosis or condition (if mentioned)",
  "injury_sequelae_4_diagnosis": "Fourth injury diagnosis or condition (if mentioned)",
  "part6_employed_at_accident": "Was the applicant employed at the time of the accident? (yes/no)",
  "part6_prior_conditions": "Prior to the accident, did the applicant have any disease, condition or injury that could affect his/her response to treatment? (no/unknown/yes)",
  "part6_prior_conditions_explanation": "Detailed explanation of prior conditions and their impact on treatment (only if part6_prior_conditions is 'yes')",
  "part6_past_year_treatment": "Did the applicant undergo investigation or receive treatment for this prior disease, condition or injury in the past year? (no/unknown/yes)",
  "part6_past_year_treatment_explanation": "Detailed explanation of past year investigations or treatment (only if part6_past_year_treatment is 'yes')",
  "part7_barriers_to_recovery": "Have you identified any barriers to recovery that may affect the success of this treatment? (no/yes)",
  "part7_barriers_explanation": "Detailed explanation of barriers to recovery (only if part7_barriers_to_recovery is 'yes')",
  "accident_date": "Date of the motor vehicle accident (YYYY-MM-DD format)",
  "minor_injury_guideline": "Description of the minor injury.",
  "supplementary_services_description": "Description of the supplementary services.",
  "other_preapproved_services_description": "Description of the other pre-approved services.",
}}


TRANSCRIPT: 
{transcript_text}

CRITICAL: Return ONLY a single JSON object. Do not repeat the JSON. Do not add explanations. Do not add markdown formatting. Stop after the closing brace.

Extract transcript data and return ONLY the JSON object:"""

        return prompt

    def _extract_with_model(self, transcript_text: str) -> dict:
        """Extract data using the shared ModelManager with robust JSON recovery"""
        try:
            prompt = self._create_ocf23_prompt(transcript_text)
            print(f"Extracting OCF-23 data with {self.model_type} using shared ModelManager...")

            # Optimize parameters based on model type
            if self.model_type in ["qwen3-1.7b", "qwen3-4b"]:
                # Optimized parameters for Qwen models to prevent repetition
                result = model_manager.process_prompt(
                    prompt=prompt,
                    model_type=self.model_type,
                    max_tokens=2048,  # Increased for complete JSON
                    temperature=0.0,  # More deterministic output
                    stop_sequences=["Transcript:", "Rules:", "```", "```json", "}\n```", "}\n\n", "}\n\n```"]
                )
            else:
                # Standard parameters for other models
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
                if '"injury_sequelae_1_diagnosis"' in response_text or '"part6_employed_at_accident"' in response_text:
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
                        data: dict = {}
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
            print(f"Warning: OCF-23 extraction failed: {e}")
            return {}

    def extract_data(self, transcript_path: str, appointment_id: str, output_path: str = None) -> dict:
        """Extract OCF-23 data from transcript and persist to JSON"""
        try:
            with open(transcript_path, 'r', encoding='utf-8') as f:
                transcript_text = f.read()

            print(f"Processing transcript for OCF-23: {transcript_path}")
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

            print(f"OCF-23 extraction saved to: {output_path}")
            return extracted
        except Exception as e:
            print(f"Error extracting OCF-23 data: {e}")
            return {}

    def get_extraction(self, extraction_path: str) -> Optional[Dict[str, Any]]:
        """Get an existing OCF-23 extraction from a specific path"""
        if os.path.exists(extraction_path):
            with open(extraction_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None


if __name__ == "__main__":
    # Test the lightweight extractor
    extractor = OCF23DataExtractor(model_type="qwen3-4b")
    
    # Test with a sample transcript if available
    test_transcript = "transcripts/Nishu_20250805_201257.txt"
    if os.path.exists(test_transcript):
        print("Testing lightweight extractor...")
        result = extractor.extract_data(test_transcript, "test_appointment")
        print(f"Extraction result: {json.dumps(result, indent=2)}")
    else:
        print("No test transcript found")


