#!/usr/bin/env python3
"""
Lightweight Data Extractor for WSIB Forms
Uses Qwen for fast, efficient data extraction
"""

import os
import json
import re
from datetime import datetime
from model_manager import model_manager


class WSIBDataExtractor:
    def __init__(self, model_type="qwen3-4b"):
        self.model_type = model_type
        self.field_map = None
        self.checkbox_groups = None
        
        # Load field mappings
        self._load_field_mappings()
        
    def _load_field_mappings(self):
        """Load WSIB field mappings and checkbox groups"""
        try:
            with open("config/field_map_wsib.json", "r") as f:
                self.field_map = json.load(f)
            
            with open("config/wsib_checkbox_groups.json", "r") as f:
                self.checkbox_groups = json.load(f)
                
            print("Field mappings loaded successfully")
        except Exception as e:
            print(f"Warning: Could not load field mappings: {e}")
            self.field_map = {}
            self.checkbox_groups = {}
    
    def cleanup(self):
        """Clean up resources - no longer needed with ModelManager"""
        # The ModelManager handles cleanup centrally
        print(f"WSIBDataExtractor cleanup completed (using shared ModelManager)")
    
    def _extract_with_regex(self, text):
        """Extract basic data using regex patterns"""
        extracted_data = {}
        
        # Date patterns
        date_patterns = [
            r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b',
            r'\b(\d{4})[/-](\d{1,2})[/-](\d{1,2})\b',
            r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})\b'
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                extracted_data['dates'] = matches
                break
        
        # Name patterns
        name_patterns = [
            r'\b(name|patient|client)\s*[:\-]?\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',
            r'\b([A-Z][a-z]+\s+[A-Z][a-z]+)\s+(is|was|has)\b'
        ]
        
        for pattern in name_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                extracted_data['patient_name'] = matches[0][1] if len(matches[0]) > 1 else matches[0][0]
                break
        
        return extracted_data
    
    def _create_wsib_prompt(self, text):
        """Create a structured prompt for WSIB field extraction"""
        
        prompt = f"""Extract WSIB form data from this physiotherapy assessment transcript. You are a specialized medical data analyst. Carefully read the entire transcript and extract the required fields as described below.

CRITICAL RULES:
- Return ONLY a single JSON object. Do not repeat the JSON. Do not add explanations. Do not add markdown formatting.
- For any field, only extract information if it is explicitly stated or can be directly and unambiguously inferred from the transcript context. If there is any doubt or the information is missing, set the field to null.
- For single-choice (radio) and yes/no (boolean) fields, select a value only if the transcript gives clear and direct evidence; avoid inferring or guessing. Otherwise, set the field to null.
- When extracting dates, convert any natural language date (e.g. 'August 4th, 2025') to exactly 'YYYY-MM-DD' format.
- For categorical fields, the extracted value must match one of the allowed options exactly (case-sensitive). Never invent new option strings.

The output must be a single JSON object that contains every field listed below, even if set to null. Do not omit keys. The JSON must be formatted with two-space indentation.:
REQUIRED JSON OUTPUT:
{{
    "date_of_assessment": "Assessment date (DD-MM-YYYY format)",
    "return_to_work_capability": "RTWNORESTRICTION", "RTWWITHRESTRICTION", or "NORTW",
    "walking_ability": "walking_ability_full", "walking_ability_<100_meters", "walking_ability_100_to_200_meters", or "walking_ability_other",
    "standing_ability": "standing_ability_full", "standing_ability_<14_minutes", "standing_ability_15_to_30_minutes", or "standing_ability_other",
    "sitting_ability": "sitting_ability_full", "sitting_ability_<30_minutes", "sitting_ability_30_to_60_minutes", or "sitting_ability_other",
    "lifting_floor_to_waist_ability": "lifting_floor_to_waist_full_ability", "lifting_floor_to_waist_<5kg", "lifting_floor_to_waist_5_to_10kg", or "lifting_floor_to_waist_other",
    "lifting_waist_to_shoulder_ability": "lifting_waist_to_shoulder_full_ability", "lifting_waist_to_shoulder_<5kg", "lifting_waist_to_shoulder_5_to_10kg", or "lifting_waist_to_shoulder_other",
    "stair_climbing_ability": "stair_climbing_ability_full", "stair_climbing_ability_<5_steps", "stair_climbing_ability_5_to_10_steps", or "stair_climbing_ability_other",
    "ladder_climbing_ability": "ladder_climbing_full_ability", "ladder_climbing_1_to_3_steps", "ladder_climbing_4_to_6_steps", or "ladder_climbing_other",
    "ability_to_use_public_transit": true/false,
    "ability_to_drive_a_car": true/false,
    "restricted_work_above_shoulder": true/false,
    "restricted_operating_motorized_equipment": true/false,
    "restricted_use_of_hands": true/false,
    "restricted_gripping_left_hand": true/false,
    "restricted_gripping_right_hand": true/false,
    "restricted_pinching_left_hand": true/false,
    "restricted_pinching_right_hand": true/false,
    "other_restriction_left_hand": true/false,
    "other_restriction_right_hand": true/false,
    "restricted_bending_twisting": true/false,
    "restricted_work_above_shoulder": true/false,
    "restricted_chemical_exposure": true/false,
    "restricted_environmental_exposure": true/false,
    "restricted_pulling_pushing": true/false,
    "restricted_pulling_pushing_left_arm": true/false,
    "restricted_pulling_pushing_right_arm": true/false,
    "restricted_pulling_pushing_other": true/false,
    "restricted_operating_motorized_equipment": true/false,
    "potential_side_effects": true/false,
    "restricted_exposure_to_vibration": true/false,
    "restricted_exposure_to_vibration_whole_body": true/false,
    "restricted_exposure_to_vibration_hand_arm": true/false,
    "restriction_duration": "1-2 days", "3-7 days", "8-14 days", or "14 + days",
    "discussed_return_to_work_with_worker": true/false,
    "discussed_return_to_work_with_employer": true/false,
    "recommendation_for_work_hours": "reg full time hours", "modified hours", or "graduated hours",
    "work_hours_start_date": "Start date for work hours (DD-MM-YYYY format)",
    "date_of_next_appointment": "Next appointment date (DD-MM-YYYY format)",
    "additional_comments_explanation": "Any additional comments or explanations"
}}

TRANSCRIPT: 
{text}

CRITICAL: Return ONLY a single JSON object. Do not repeat the JSON. Do not add explanations. Do not add markdown formatting. Stop after the closing brace.

Extract transcript data and return ONLY the JSON object:"""

        return prompt
    
    def _extract_with_llama(self, text):
        """Extract data using the shared model manager"""
        try:
            # Create structured prompt for WSIB extraction
            prompt = self._create_wsib_prompt(text)
            
            print(f"Extracting data with {self.model_type} using shared ModelManager...")
            
            # Use the ModelManager's thread-safe process_prompt method
            # Optimize parameters based on model type
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
                    max_tokens=1024,
                    temperature=0.1,
                    stop_sequences=["Transcript:", "Rules:"]
                )
            
            if not result['success']:
                print(f"Warning: Model inference failed: {result['error']}")
                return {}
            
            response_text = result['text']
            print(f"Model response length: {len(response_text)} characters")
            print(f"Model response preview: {response_text[:300]}...")
            
            # Try to find JSON in the response - look for the start of JSON
            json_start = response_text.find('{')
            if json_start == -1:
                # Try to find JSON-like content that might be missing the opening brace
                if '"workers_first_name"' in response_text or '"workers_last_name"' in response_text:
                    print("Found JSON-like content without opening brace, attempting to fix...")
                    # Add opening brace and try to parse
                    json_str = "{" + response_text.strip()
                else:
                    print(f"Warning: No JSON start found in response")
                    print(f"Response: {response_text[:500]}...")
                    return {}
            else:
                # Find the end of JSON by counting braces
                brace_count = 0
                json_end = json_start
                for i, char in enumerate(response_text[json_start:], json_start):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_end = i + 1
                            break
                
                json_str = response_text[json_start:json_end]
            print(f"Extracted JSON string: {json_str[:200]}...")
            
            try:
                extracted_data = json.loads(json_str)
                print(f"Successfully extracted {len(extracted_data)} fields")
                return extracted_data
            except json.JSONDecodeError as e:
                print(f"Warning: Invalid JSON in response: {e}")
                print(f"Raw JSON: {json_str}")
                
                # Try to fix common JSON issues
                try:
                    # Remove any trailing commas
                    json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
                    # Fix double quotes at the end of string values
                    json_str = re.sub(r'""(\s*[,}])', r'"\1', json_str)
                    # Fix any unescaped quotes in strings
                    json_str = re.sub(r'([^\\])"([^"]*)"([^\\])"', r'\1"\2\\"\3"', json_str)
                    # Remove any newlines within string values
                    json_str = re.sub(r'\n', ' ', json_str)
                    # Remove any extra quotes at the end of values
                    json_str = re.sub(r'""(\s*[,}])', r'"\1', json_str)
                    
                    extracted_data = json.loads(json_str)
                    print(f"Successfully extracted {len(extracted_data)} fields after JSON fix")
                    return extracted_data
                except json.JSONDecodeError as e2:
                    print(f"Warning: Still invalid JSON after fix: {e2}")
                    print(f"Attempted to parse: {json_str[:500]}...")
                    
                    # Try manual parsing as last resort
                    try:
                        print("Attempting manual JSON parsing...")
                        extracted_data = {}
                        
                        # Extract string key-value pairs
                        string_pairs = re.findall(r'"([^"]+)"\s*:\s*"([^"]*)"', json_str)
                        for key, value in string_pairs:
                            extracted_data[key] = value
                        
                        # Extract boolean key-value pairs
                        bool_pairs = re.findall(r'"([^"]+)"\s*:\s*(true|false)', json_str)
                        for key, value in bool_pairs:
                            extracted_data[key] = value.lower() == 'true'
                        
                        # Extract null values
                        null_pairs = re.findall(r'"([^"]+)"\s*:\s*null', json_str)
                        for key in null_pairs:
                            extracted_data[key] = None
                        
                        if extracted_data:
                            print(f"Successfully extracted {len(extracted_data)} fields using manual parsing")
                            return extracted_data
                        else:
                            print("No fields extracted with manual parsing")
                            return {}
                    except Exception as e3:
                        print(f"Manual parsing also failed: {e3}")
                        return {}
            
        except Exception as e:
            print("Warning: Llama extraction failed:", str(e))
            
            # Try to extract data from the error message itself (as a fallback)
            try:
                error_str = str(e)
                if '"workers_first_name"' in error_str or '"workers_last_name"' in error_str:
                    print("Attempting to extract data from error message...")
                    
                    # Extract key-value pairs using regex
                    extracted_data = {}
                    
                    # Extract string values
                    string_pairs = re.findall(r'"([^"]+)"\s*:\s*"([^"]*)"', error_str)
                    for key, value in string_pairs:
                        extracted_data[key] = value
                    
                    # Extract boolean values
                    bool_pairs = re.findall(r'"([^"]+)"\s*:\s*(true|false)', error_str)
                    for key, value in bool_pairs:
                        extracted_data[key] = value.lower() == 'true'
                    
                    if extracted_data:
                        print(f"Successfully extracted {len(extracted_data)} fields from error message")
                        return extracted_data
            except Exception as fallback_error:
                print("Fallback extraction also failed:", str(fallback_error))
            
            return {}
    
    def extract_data(self, transcript_path, appointment_id, output_path=None):
        """Extract data from transcript and save to JSON"""
        try:
            # Read transcript
            with open(transcript_path, 'r', encoding='utf-8') as f:
                transcript_text = f.read()
            
            print(f"Processing transcript: {transcript_path}")
            print(f"Transcript length: {len(transcript_text)} characters")
            
            # Extract data using model
            extracted_data = self._extract_with_llama(transcript_text)
            
            # Add metadata
            extracted_data['appointment_id'] = appointment_id
            extracted_data['extraction_timestamp'] = datetime.now().isoformat()
            extracted_data['model_used'] = self.model_type
            extracted_data['transcript_path'] = transcript_path
            
            # Save extraction
            if output_path is None:
                raise ValueError("output_path is required for data extraction")
            else:
                # Ensure output directory exists
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(extracted_data, f, indent=2, ensure_ascii=False)
            
            print(f"Extraction saved to: {output_path}")
            return extracted_data
            
        except Exception as e:
            print(f"Error extracting data: {e}")
            return {}
    
    def get_extraction(self, extraction_path):
        """Get existing extraction from a specific path"""
        if os.path.exists(extraction_path):
            with open(extraction_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None


if __name__ == "__main__":
    # Test the lightweight extractor
    extractor = WSIBDataExtractor(model_type="qwen3-4b")
    
    # Test with a sample transcript if available
    test_transcript = "transcripts/Nishu_20250805_201257.txt"
    if os.path.exists(test_transcript):
        print("Testing lightweight extractor...")
        result = extractor.extract_data(test_transcript, "test_appointment")
        print(f"Extraction result: {json.dumps(result, indent=2)}")
    else:
        print("No test transcript found")
