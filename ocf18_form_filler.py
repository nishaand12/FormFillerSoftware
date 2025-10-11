#!/usr/bin/env python3
"""
OCF-18 Form Filler using PyPDFForm
Fills OCF-18 Treatment and Assessment Plan forms with extracted data
"""

import os
import json
import warnings
from typing import Dict, Any, List
from PyPDFForm import PdfWrapper

# Suppress pypdf warnings about undefined objects
warnings.filterwarnings("ignore", message="Object 0 0 not defined")


class OCF18FormFiller:
    def __init__(self, config_dir: str = "config"):
        self.config_dir = config_dir
        self.field_map = self._load_field_map()
        self.checkbox_groups = self._load_checkbox_groups()
        self.field_types = self._load_field_types()
        self.stored_data = self._load_stored_data()

    def _load_field_map(self) -> Dict[str, str]:
        with open(os.path.join(self.config_dir, "field_map_ocf18.json"), 'r') as f:
            return json.load(f)

    def _load_checkbox_groups(self) -> Dict[str, Any]:
        with open(os.path.join(self.config_dir, "ocf18_checkbox_groups.json"), 'r') as f:
            return json.load(f)

    def _load_field_types(self) -> Dict[str, str]:
        with open(os.path.join(self.config_dir, "ocf18_field_types.json"), 'r') as f:
            return json.load(f)["field_types"]

    def _load_stored_data(self) -> Dict[str, Any]:
        path = os.path.join(self.config_dir, "ocf18_stored_data.json")
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                print(f"📋 Loaded OCF-18 stored data from: {path}")
                return data
            except Exception as e:
                print(f"⚠️  Could not load OCF-18 stored data: {e}")
                return {}
        print(f"⚠️  OCF-18 stored data file not found: {path}")
        return {}

    def _merge_extraction_with_stored_data(self, extraction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Merge extracted data with stored clinic/professional data"""
        merged = extraction_data.copy()
        
        # Flatten stored data sections
        flat: Dict[str, Any] = {}
        for section in ("clinic_info", "health_provider_info", "professional_info", "form_defaults"):
            if section in self.stored_data and isinstance(self.stored_data[section], dict):
                for k, v in self.stored_data[section].items():
                    flat[k] = v
        
        # Add stored data to merged data
        for k, v in flat.items():
            if k not in merged:
                merged[k] = v
                print(f"  ✅ Added stored field: {k} = {v}")
        
        return merged

    def _process_conditional_fields(self, merged_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process conditional logic for dependent fields"""
        conditional_logic = self.checkbox_groups.get("conditional_logic", {})
        
        for field, conditions in conditional_logic.items():
            if field in merged_data:
                field_value = merged_data[field]
                
                # Process if_true conditions
                if_true_fields = conditions.get("if_true", [])
                if field_value and if_true_fields:
                    for dependent_field in if_true_fields:
                        if dependent_field not in merged_data or merged_data[dependent_field] is None:
                            # Set default value for dependent field
                            if "explain" in dependent_field.lower() or "specify" in dependent_field.lower():
                                merged_data[dependent_field] = ""
                            else:
                                merged_data[dependent_field] = False
                
                # Process if_false conditions
                if_false_fields = conditions.get("if_false", [])
                if not field_value and if_false_fields:
                    for dependent_field in if_false_fields:
                        if dependent_field not in merged_data or merged_data[dependent_field] is None:
                            merged_data[dependent_field] = ""
                
                # Process if_yes conditions
                if_yes_fields = conditions.get("if_yes", [])
                if field_value == "yes" and if_yes_fields:
                    for dependent_field in if_yes_fields:
                        if dependent_field not in merged_data or merged_data[dependent_field] is None:
                            merged_data[dependent_field] = ""
                
                # Process if_no conditions
                if_no_fields = conditions.get("if_no", [])
                if field_value == "no" and if_no_fields:
                    for dependent_field in if_no_fields:
                        if dependent_field not in merged_data or merged_data[dependent_field] is None:
                            merged_data[dependent_field] = ""
                
                # Process if_other conditions
                if_other_fields = conditions.get("if_other", [])
                if field_value == "other" and if_other_fields:
                    for dependent_field in if_other_fields:
                        if dependent_field not in merged_data or merged_data[dependent_field] is None:
                            merged_data[dependent_field] = ""
                
                # Process if_not_other conditions (custom logic for part9i_goals)
                if_not_other_fields = conditions.get("if_not_other", [])
                if field_value != "other" and field_value is not None and field_value != "" and if_not_other_fields:
                    for dependent_field in if_not_other_fields:
                        # For part9i_goals -> part9_a2_please_specify mapping
                        if field == "part9i_goals" and dependent_field == "part9_a2_please_specify":
                            merged_data[dependent_field] = str(field_value)
                            print(f"  ✅ Set {dependent_field} = {field_value} (from {field})")
                        else:
                            # Default behavior for other if_not_other conditions
                            if dependent_field not in merged_data or merged_data[dependent_field] is None:
                                merged_data[dependent_field] = ""
        
        return merged_data

    def _map_checkbox_values(self, value: Any, field_name: str) -> bool:
        """Map various value types to boolean for checkboxes"""
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ['yes', 'true', '1', 'y']
        if isinstance(value, (int, float)):
            return bool(value)
        return False

    def _map_radio_values(self, value: Any, field_name: str) -> str:
        """Map values to radio button options"""
        if value is None:
            return ""
        
        # Map common values to radio options
        value_str = str(value).lower()
        
        if field_name == "patient_gender":
            if value_str in ['male', 'm']:
                return "male"
            elif value_str in ['female', 'f']:
                return "female"
        
        return value_str

    def _map_three_option_values(self, value: Any, field_name: str) -> int:
        """Map values to three-option fields (no/unknown/yes) - return index for radio buttons"""
        if value is None:
            return 0  # Default to "no" (index 0)
        
        value_str = str(value).lower()
        
        # Map common variations to standard options
        # Options are: [0: no, 1: unknown, 2: yes]
        if value_str in ['no', 'n', 'false', '0']:
            return 0
        elif value_str in ['unknown', 'unclear', 'uncertain', 'unsure']:
            return 1
        elif value_str in ['yes', 'y', 'true', '1']:
            return 2
        
        return 0  # Default to "no" for unrecognized values

    def _map_four_option_values(self, value: Any, field_name: str) -> int:
        """Map values to four-option fields - return index for radio buttons"""
        if value is None:
            return 0  # Default to first option (index 0)
        
        value_str = str(value).lower()
        
        if field_name == "part8_task_checkbox":
            # Options are: [0: not_employed, 1: no, 2: unknown, 3: yes]
            if value_str in ['not_employed', 'not employed', 'unemployed', 'not working']:
                return 0
            elif value_str in ['no', 'n', 'false', '0']:
                return 1
            elif value_str in ['unknown', 'unclear', 'uncertain', 'unsure']:
                return 2
            elif value_str in ['yes', 'y', 'true', '1']:
                return 3
        elif field_name == "part8_c_checkbox":
            # Options are: [0: not_employed, 1: yes, 2: unknown, 3: no]
            if value_str in ['not_employed', 'not employed', 'unemployed', 'not working']:
                return 0
            elif value_str in ['yes', 'y', 'true', '1']:
                return 1
            elif value_str in ['unknown', 'unclear', 'uncertain', 'unsure']:
                return 2
            elif value_str in ['no', 'n', 'false', '0']:
                return 3
        
        return 0  # Default to first option for unrecognized values

    def _map_two_option_values(self, value: Any, field_name: str) -> int:
        """Map values to two-option fields (no/yes) - return index for radio buttons"""
        if value is None:
            return 0  # Default to "no" (index 0)
        
        value_str = str(value).lower()
        
        # Options are: [0: no, 1: yes]
        if value_str in ['no', 'n', 'false', '0']:
            return 0
        elif value_str in ['yes', 'y', 'true', '1']:
            return 1
        
        return 0  # Default to "no" for unrecognized values

    def fill_ocf18_form(self, template_path: str, extraction_data: Dict[str, Any], output_path: str) -> bool:
        """Fill OCF-18 form with extracted and stored data"""
        try:
            print(f"Loading OCF-18 PDF template: {template_path}")
            
            # Merge with stored data
            merged = self._merge_extraction_with_stored_data(extraction_data)
            
            # Process conditional fields
            merged = self._process_conditional_fields(merged)
            
            form = PdfWrapper(template_path)
            available = form.data
            print(f"Available PDF fields: {len(available)}")

            processed = 0
            
            # Process text fields - only for fields that exist in merged data
            text_payload: Dict[str, Any] = {}
            for key, value in merged.items():
                if key in self.field_map and self.field_types.get(key, "text") == "text":
                    pdf_key = self.field_map[key].strip('()')
                    if pdf_key in available:
                        text_value = "" if value is None else str(value)
                        text_payload[pdf_key] = text_value
                        processed += 1
                        print(f"  📝 Text field: {key} -> {pdf_key} = {text_value}")
            
            if text_payload:
                form.fill(text_payload)

            # Process checkboxes (yes/no fields) - only for fields that exist in merged data
            yes_no_fields = set(self.checkbox_groups.get("yes_no_fields", []))
            for key, value in merged.items():
                if key in self.field_map and (self.field_types.get(key) == "checkbox" or key in yes_no_fields):
                    pdf_key = self.field_map[key].strip('()')
                    if pdf_key in available:
                        checkbox_value = self._map_checkbox_values(value, key)
                        form.fill({pdf_key: checkbox_value})
                        processed += 1
                        print(f"  ☑️  Checkbox: {key} -> {pdf_key} = {checkbox_value}")

            # Process three-option fields - only for fields that exist in merged data
            three_option_fields = self.checkbox_groups.get("three_option_fields", {})
            for key, value in merged.items():
                if key in three_option_fields and key in self.field_map:
                    pdf_key = self.field_map[key].strip('()')
                    if pdf_key in available:
                        mapped_value = self._map_three_option_values(value, key)
                        # For three-option fields, we need to handle them as radio buttons
                        # This is a simplified approach - in practice, you might need to map to specific PDF field names
                        form.fill({pdf_key: mapped_value})
                        processed += 1
                        print(f"  🔘 Three-option: {key} -> {pdf_key} = {mapped_value}")

            # Process four-option fields - only for fields that exist in merged data
            four_option_fields = self.checkbox_groups.get("four_option_fields", {})
            for key, value in merged.items():
                if key in four_option_fields and key in self.field_map:
                    pdf_key = self.field_map[key].strip('()')
                    if pdf_key in available:
                        mapped_value = self._map_four_option_values(value, key)
                        form.fill({pdf_key: mapped_value})
                        processed += 1
                        print(f"  🔘 Four-option: {key} -> {pdf_key} = {mapped_value}")

            # Process two-option fields (Part9_c1, Part9_c2, Part9_d) - only for fields that exist in merged data
            two_option_fields = ["part9_c1_checkbox", "part9_c2_checkbox", "part9_d_checkbox"]
            for key, value in merged.items():
                if key in two_option_fields and key in self.field_map:
                    pdf_key = self.field_map[key].strip('()')
                    if pdf_key in available:
                        mapped_value = self._map_two_option_values(value, key)
                        form.fill({pdf_key: mapped_value})
                        processed += 1
                        print(f"  🔘 Two-option: {key} -> {pdf_key} = {mapped_value}")

            # Process goals fields - fill as text values for now (workaround for PyPDFForm limitation)
            goals_field_mapping = {
                "part9i_goals": "Part9_a1",
                "part9ii_function_goals": "Part9_a2"
            }
            
            for goal_field, goal_value in merged.items():
                if goal_field in goals_field_mapping and goal_value:
                    pdf_key = goals_field_mapping[goal_field]
                    if pdf_key in available:
                        # Fill as text value (workaround)
                        form.fill({pdf_key: str(goal_value)})
                        processed += 1
                        print(f"  📝 Goal field (text): {goal_field} -> {pdf_key} = {goal_value}")
                    else:
                        print(f"  ⚠️  Goal field not found: {pdf_key}")

            # Process radio button groups - only for fields that exist in merged data
            radio_groups = self.checkbox_groups.get("radio_button_groups", {})
            for key, value in merged.items():
                # Check if this field belongs to a radio button group
                group = None
                for group_name, group_config in radio_groups.items():
                    if isinstance(group_config, list) and key in group_config:
                        group = group_name
                        break
                    elif isinstance(group_config, dict) and key == group_name:
                        group = group_name
                        break
                
                if group and value and key in self.field_map:
                    pdf_key = self.field_map[key].strip('()')
                    if pdf_key in available:
                        if group == "patient_gender":
                            # Handle gender as simple radio button
                            form.fill({pdf_key: True})
                            processed += 1
                            print(f"  🔘 Radio: {key} -> {pdf_key} = True")
                        else:
                            # Handle other radio groups (goals) as text values
                            form.fill({pdf_key: str(value)})
                            processed += 1
                            print(f"  🔘 Radio: {key} -> {pdf_key} = {value}")
                        
                        # Uncheck others in the same group (for gender only)
                        if group == "patient_gender" and isinstance(radio_groups[group], list):
                            for other_field in radio_groups[group]:
                                if other_field != key:
                                    other_pdf = self.field_map.get(other_field)
                                    if other_pdf:
                                        other_clean = other_pdf.strip('()')
                                        if other_clean in available:
                                            form.fill({other_clean: False})

            # Process multiple choice fields - only for fields that exist in merged data
            mc_fields = self.checkbox_groups.get("multiple_choice_fields", {})
            for key, value in merged.items():
                if key in mc_fields:
                    mc_config = mc_fields[key]
                    pdf_name = mc_config["field_name"]
                    options = mc_config["options"]
                    
                    if pdf_name in available and value is not None:
                        # Find matching option
                        selected_option = None
                        value_str = str(value).lower()
                        
                        for option in options:
                            if option.lower() == value_str:
                                selected_option = option
                                break
                        
                        if selected_option is not None:
                            # Try to fill as radio button group
                            try:
                                widget = form.widgets.get(pdf_name)
                                if widget and hasattr(widget, 'number_of_options') and widget.number_of_options >= 2:
                                    idx = options.index(selected_option)
                                    form.fill({pdf_name: idx})
                                    processed += 1
                                    print(f"  📋 Multiple choice: {key} -> {pdf_name} = {selected_option} (index {idx})")
                                else:
                                    form.fill({pdf_name: selected_option})
                                    processed += 1
                                    print(f"  📋 Multiple choice: {key} -> {pdf_name} = {selected_option}")
                            except Exception as e:
                                print(f"  ⚠️  Could not fill multiple choice field {key}: {e}")

            # Save the filled form
            form.write(output_path)
            print(f"📊 OCF-18 fields processed: {processed}")
            print(f"💾 OCF-18 form saved to: {output_path}")
            return True
            
        except Exception as e:
            print(f"Error filling OCF-18 form: {e}")
            import traceback
            traceback.print_exc()
            return False

    def fill_from_extraction_file(self, template_path: str, extraction_file: str, output_path: str) -> bool:
        """Fill OCF-18 form from an extraction JSON file"""
        try:
            with open(extraction_file, 'r', encoding='utf-8') as f:
                extraction_data = json.load(f)
            
            return self.fill_ocf18_form(template_path, extraction_data, output_path)
        except Exception as e:
            print(f"Error loading extraction file {extraction_file}: {e}")
            return False

    def get_field_summary(self, extraction_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get a summary of how fields will be processed
        
        Args:
            extraction_data: The data extracted by the Qwen model
            
        Returns:
            Dict containing field processing summary
        """
        # Merge with stored data for complete picture
        merged_data = self._merge_extraction_with_stored_data(extraction_data)
        
        summary = {
            "text_fields": [],
            "checkbox_fields": [],
            "three_option_fields": [],
            "four_option_fields": [],
            "radio_group_fields": [],
            "multiple_choice_fields": [],
            "unmapped_fields": [],
            "stored_fields_added": [],
            "total_fields": len(merged_data),
            "extraction_fields": len(extraction_data),
            "stored_fields": len(merged_data) - len(extraction_data)
        }
        
        for field_name, field_value in merged_data.items():
            # Check if this field came from stored data
            is_stored_field = field_name not in extraction_data
            
            # Check if this field is mapped to a PDF field
            if field_name in self.field_map:
                field_type = self.field_types.get(field_name, "unknown")
                pdf_field_name = self.field_map[field_name]
                
                field_info = {
                    "field_name": field_name,
                    "pdf_field_name": pdf_field_name,
                    "field_type": field_type,
                    "value": field_value,
                    "source": "stored" if is_stored_field else "extraction"
                }
                
                if field_name in self.checkbox_groups.get("multiple_choice_fields", {}):
                    summary["multiple_choice_fields"].append(field_info)
                elif field_type == "text":
                    summary["text_fields"].append(field_info)
                elif field_type == "checkbox" or field_name in self.checkbox_groups.get("yes_no_fields", []):
                    summary["checkbox_fields"].append(field_info)
                elif field_type == "three_option" or field_name in self.checkbox_groups.get("three_option_fields", {}):
                    summary["three_option_fields"].append(field_info)
                elif field_type == "four_option" or field_name in self.checkbox_groups.get("four_option_fields", {}):
                    summary["four_option_fields"].append(field_info)
                elif field_type == "radio_group":
                    summary["radio_group_fields"].append(field_info)
                else:
                    summary["unmapped_fields"].append(field_info)
                
                if is_stored_field:
                    summary["stored_fields_added"].append(field_name)
            else:
                summary["unmapped_fields"].append({
                    "field_name": field_name,
                    "pdf_field_name": "NOT_FOUND",
                    "field_type": "unmapped",
                    "value": field_value,
                    "source": "stored" if is_stored_field else "extraction"
                })
                if is_stored_field:
                    summary["stored_fields_added"].append(field_name)
        
        return summary


if __name__ == "__main__":
    # Test the form filler
    template_path = "forms/templates/fsra_ocf18_template.pdf"
    extraction_file = "extractions/test_ocf18_extraction.json"
    output_path = "output_forms/test_ocf18_filled.pdf"
    
    if os.path.exists(template_path):
        filler = OCF18FormFiller()
        if os.path.exists(extraction_file):
            success = filler.fill_from_extraction_file(template_path, extraction_file, output_path)
            print(f"Form filling {'successful' if success else 'failed'}")
        else:
            print(f"Extraction file not found: {extraction_file}")
    else:
        print(f"Template file not found: {template_path}")
