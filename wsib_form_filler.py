#!/usr/bin/env python3
"""
Complete Form Filler using PyPDFForm for all field types
Handles text fields, checkboxes, radio button groups, multiple choice fields, and yes/no fields
Automatically incorporates stored data from wsib_stored_data.json
"""

import os
import json
import shutil
import warnings
from typing import Dict, Any, List, Optional
from PyPDFForm import PdfWrapper
from pdfrw import PdfReader, PdfWriter, objects
from pdfrw.objects.pdfname import BasePdfName

# Suppress pypdf warnings about undefined objects
warnings.filterwarnings("ignore", message="Object 0 0 not defined")


class WSIBFormFiller:
    """
    Complete form filler that uses PyPDFForm for all field types
    """
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = config_dir
        self.field_map = self._load_field_map()
        self.checkbox_groups = self._load_checkbox_groups()
        self.field_types = self._load_field_types()
        self.stored_data = self._load_stored_data()
        
    def _load_field_map(self) -> Dict[str, str]:
        """Load the field mapping from field_map_wsib.json"""
        field_map_path = os.path.join(self.config_dir, "field_map_wsib.json")
        with open(field_map_path, 'r') as f:
            data = json.load(f)
        return data
    
    def _load_checkbox_groups(self) -> Dict[str, Any]:
        """Load checkbox groups and radio button configurations"""
        checkbox_path = os.path.join(self.config_dir, "wsib_checkbox_groups.json")
        with open(checkbox_path, 'r') as f:
            data = json.load(f)
        return data
    
    def _load_field_types(self) -> Dict[str, str]:
        """Load field types configuration"""
        types_path = os.path.join(self.config_dir, "wsib_field_types.json")
        with open(types_path, 'r') as f:
            data = json.load(f)
        return data["field_types"]
    
    def _load_stored_data(self) -> Dict[str, Any]:
        """Load stored data from wsib_stored_data.json"""
        stored_data_path = os.path.join(self.config_dir, "wsib_stored_data.json")
        if os.path.exists(stored_data_path):
            try:
                with open(stored_data_path, 'r') as f:
                    data = json.load(f)
                print(f"📋 Loaded stored data from: {stored_data_path}")
                return data
            except Exception as e:
                print(f"⚠️  Could not load stored data: {e}")
                return {}
        else:
            print(f"⚠️  Stored data file not found: {stored_data_path}")
            return {}
    
    def _merge_extraction_with_stored_data(self, extraction_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge extraction data with stored data, giving priority to extraction data
        """
        merged_data = extraction_data.copy()
        
        if self.stored_data:
            print("🔄 Merging extraction data with stored data...")
            
            # Flatten the stored data structure
            stored_fields = {}
            
            # Add health professional info
            if "health_professional_info" in self.stored_data:
                for key, value in self.stored_data["health_professional_info"].items():
                    stored_fields[key] = value
            
            # Add clinic info
            if "clinic_info" in self.stored_data:
                for key, value in self.stored_data["clinic_info"].items():
                    stored_fields[key] = value
            
            # Merge stored fields into extraction data (extraction data takes priority)
            for field_name, field_value in stored_fields.items():
                if field_name not in merged_data:
                    merged_data[field_name] = field_value
                    print(f"  ✅ Added stored field: {field_name} = {field_value}")
                else:
                    print(f"  ⚠️  Skipped stored field (extraction data exists): {field_name}")
        
        return merged_data
    
    def fill_wsib_form(self, template_path: str, extraction_data: Dict[str, Any], 
                       output_path: str) -> bool:
        """
        Fill the WSIB form using PyPDFForm for all field types
        Automatically incorporates stored data from wsib_stored_data.json
        """
        try:
            print(f"Loading PDF template: {template_path}")
            
            # Merge extraction data with stored data
            merged_data = self._merge_extraction_with_stored_data(extraction_data)
            
            # Load the form with PyPDFForm
            form = PdfWrapper(template_path)
            
            # Get available fields
            available_fields = form.data
            print(f"📋 Available fields: {len(available_fields)}")
            
            # Process all field types
            fields_processed = 0
            
            # Step 1: Process text fields
            text_fields_processed = self._process_text_fields(form, merged_data, available_fields)
            fields_processed += text_fields_processed
            
            # Step 2: Process yes/no fields (checkboxes)
            yes_no_fields_processed = self._process_yes_no_fields(form, merged_data, available_fields)
            fields_processed += yes_no_fields_processed
            
            # Step 3: Process radio button groups
            radio_fields_processed = self._process_radio_button_groups(form, merged_data, available_fields)
            fields_processed += radio_fields_processed
            
            # Step 4: Process multiple choice fields
            multiple_choice_fields_processed = self._process_multiple_choice_fields(form, merged_data, available_fields)
            fields_processed += multiple_choice_fields_processed
            
            # Step 5: Process aggregated radio group fields
            aggregated_fields_processed = self._process_aggregated_radio_groups(form, merged_data, available_fields)
            fields_processed += aggregated_fields_processed
            
            # Save the filled form
            form.write(output_path)
            
            print(f"\n📊 Total fields processed: {fields_processed}")
            print(f"💾 Form saved to: {output_path}")
            
            return True
            
        except Exception as e:
            print(f"Error filling form: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _process_text_fields(self, form: PdfWrapper, extraction_data: Dict[str, Any], 
                           available_fields: Dict[str, Any]) -> int:
        """Process text fields"""
        
        print("\n📝 Processing text fields...")
        text_fields_to_fill = {}
        text_fields_processed = 0
        
        for field_name, field_value in extraction_data.items():
            if field_name in self.field_map:
                pdf_field_name = self.field_map[field_name]
                field_type = self.field_types.get(field_name, "text")
                
                if field_type == "text":
                    # Remove parentheses for PyPDFForm
                    clean_field_name = pdf_field_name.strip('()')
                    
                    if clean_field_name in available_fields:
                        text_fields_to_fill[clean_field_name] = str(field_value)
                        print(f"  ✅ Text field: {field_name} -> {clean_field_name} = {field_value}")
                        text_fields_processed += 1
                    else:
                        print(f"  ⚠️  Text field {clean_field_name} not found in PDF")
        
        # Fill the text fields
        if text_fields_to_fill:
            form.fill(text_fields_to_fill)
            print(f"📝 Text fields filled: {text_fields_processed}")
        
        return text_fields_processed
    
    def _process_yes_no_fields(self, form: PdfWrapper, extraction_data: Dict[str, Any], 
                              available_fields: Dict[str, Any]) -> int:
        """Process yes/no fields (checkboxes)"""
        
        print("\n✅ Processing yes/no fields...")
        yes_no_fields_processed = 0
        
        for field_name, field_value in extraction_data.items():
            if field_name in self.field_map:
                pdf_field_name = self.field_map[field_name]
                field_type = self.field_types.get(field_name, "text")
                
                # Check if it's a yes/no field
                is_yes_no_field = (
                    field_type == "checkbox" or 
                    field_name in self.checkbox_groups.get("yes_no_fields", [])
                )
                
                if is_yes_no_field:
                    # Remove parentheses for PyPDFForm
                    clean_field_name = pdf_field_name.strip('()')
                    
                    if clean_field_name in available_fields:
                        # Convert value to boolean
                        is_checked = bool(field_value) if field_value is not None else False
                        
                        # Set checkbox value (True = checked, False = unchecked)
                        form.fill({clean_field_name: is_checked})
                        print(f"  ✅ Yes/No field: {field_name} -> {clean_field_name} = {is_checked}")
                        yes_no_fields_processed += 1
                    else:
                        print(f"  ⚠️  Yes/No field {clean_field_name} not found in PDF")
        
        return yes_no_fields_processed
    
    def _process_radio_button_groups(self, form: PdfWrapper, extraction_data: Dict[str, Any], 
                                   available_fields: Dict[str, Any]) -> int:
        """Process radio button groups"""
        
        print("\n📻 Processing radio button groups...")
        radio_fields_processed = 0
        
        for field_name, field_value in extraction_data.items():
            # Check if this field belongs to a radio button group
            radio_group = None
            for group_name, fields in self.checkbox_groups["radio_button_groups"].items():
                if field_name in fields:
                    radio_group = group_name
                    break
            
            if radio_group and field_value:  # Only process if field has a truthy value
                print(f"  📻 Radio group {radio_group}: {field_name} = {field_value}")
                
                # Get the PDF field name for this field
                pdf_field_name = self.field_map.get(field_name)
                if pdf_field_name:
                    clean_field_name = pdf_field_name.strip('()')
                    
                    if clean_field_name in available_fields:
                        # Set this field to checked
                        form.fill({clean_field_name: True})
                        print(f"    ✅ Set {clean_field_name} = True")
                        radio_fields_processed += 1
                        
                        # Set other fields in the same group to unchecked
                        for other_field in self.checkbox_groups["radio_button_groups"][radio_group]:
                            if other_field != field_name:
                                other_pdf_field = self.field_map.get(other_field)
                                if other_pdf_field:
                                    other_clean_field = other_pdf_field.strip('()')
                                    if other_clean_field in available_fields:
                                        form.fill({other_clean_field: False})
                                        print(f"    ✅ Set {other_clean_field} = False")
                    else:
                        print(f"    ⚠️  Field {clean_field_name} not found in PDF")
                else:
                    print(f"    ⚠️  No PDF field mapping for {field_name}")
        
        return radio_fields_processed
    
    def _process_multiple_choice_fields(self, form: PdfWrapper, extraction_data: Dict[str, Any], 
                                      available_fields: Dict[str, Any]) -> int:
        """Process multiple choice fields"""
        
        print("\n🔘 Processing multiple choice fields...")
        multiple_choice_fields_processed = 0
        
        for field_name, field_value in extraction_data.items():
            if field_name in self.checkbox_groups.get("multiple_choice_fields", {}):
                mc_config = self.checkbox_groups["multiple_choice_fields"][field_name]
                pdf_field_name = mc_config["field_name"]
                options = mc_config["options"]
                
                print(f"  🔘 Multiple choice field: {field_name} -> {pdf_field_name}")
                
                # Handle boolean values for dual-checkbox yes/no fields
                if options == ["yes", "no"] and isinstance(field_value, bool):
                    selected_option = "yes" if field_value else "no"
                    print(f"    🔄 Converted boolean {field_value} to option: {selected_option}")
                else:
                    # Find the matching option for other field types
                    selected_option = None
                    for option in options:
                        if option.lower() in str(field_value).lower():
                            selected_option = option
                            break
                
                if selected_option:
                    print(f"    ✅ Selected option: {selected_option}")
                    
                    # For multiple choice fields, we need to handle them as radio buttons
                    # where only one option can be selected
                    success = self._fill_multiple_choice_field(form, pdf_field_name, selected_option, options, available_fields)
                    if success:
                        multiple_choice_fields_processed += 1
                else:
                    print(f"    ⚠️  No matching option found for value: {field_value}")
                    print(f"    Available options: {options}")
        
        return multiple_choice_fields_processed
    
    def _fill_multiple_choice_field(self, form: PdfWrapper, pdf_field_name: str, selected_option: str, 
                                  all_options: List[str], available_fields: Dict[str, Any]) -> bool:
        """Fill a multiple choice field by setting the correct option"""
        
        try:
            print(f"    🔧 Filling multiple choice field {pdf_field_name} with option: {selected_option}")
            
            # Check if this is a radio button field (dual-checkbox yes/no field)
            if pdf_field_name in available_fields:
                # Use form.widgets to get the actual widget object, not available_fields which contains None values
                field_widget = form.widgets.get(pdf_field_name)
                
                # For radio button fields with exactly 2 options (yes/no), convert to integer indices
                if field_widget and hasattr(field_widget, 'number_of_options') and field_widget.number_of_options >= 2:
                    if all_options == ["yes", "no"]:
                        # Convert yes/no to integer indices: yes=0, no=1
                        radio_value = 0 if selected_option == "yes" else 1
                        print(f"    🔄 Converting {selected_option} to radio button index: {radio_value}")
                        form.fill({pdf_field_name: radio_value})
                        print(f"    ✅ Set {pdf_field_name} = {radio_value} (radio button index)")
                        return True
                    else:
                        # For other radio button fields, use the option index
                        try:
                            radio_value = all_options.index(selected_option)
                            print(f"    🔄 Converting {selected_option} to radio button index: {radio_value}")
                            form.fill({pdf_field_name: radio_value})
                            print(f"    ✅ Set {pdf_field_name} = {radio_value} (radio button index)")
                            return True
                        except ValueError:
                            print(f"    ⚠️  Option {selected_option} not found in {all_options}")
                            return False
                else:
                    # For non-radio fields, use the option value directly
                    form.fill({pdf_field_name: selected_option})
                    print(f"    ✅ Set {pdf_field_name} = {selected_option}")
                    return True
            else:
                print(f"    ⚠️  Field {pdf_field_name} not found in PDF")
                return False
                
        except Exception as e:
            print(f"    ❌ Error filling multiple choice field: {e}")
            return False
    
    def _process_aggregated_radio_groups(self, form: PdfWrapper, extraction_data: Dict[str, Any], 
                                       available_fields: Dict[str, Any]) -> int:
        """Process aggregated radio group fields"""
        
        print("\n📻 Processing aggregated radio groups...")
        aggregated_fields_processed = 0
        
        for field_name, field_value in extraction_data.items():
            # Check if this is an aggregated radio group field
            radio_group = None
            for group_name, fields in self.checkbox_groups["radio_button_groups"].items():
                if field_value in fields:
                    radio_group = group_name
                    break
            
            if radio_group:
                print(f"  📻 Aggregated radio group {radio_group}: {field_name} -> {field_value}")
                
                # Get the PDF field name for the specific sub-field
                pdf_field_name = self.field_map.get(field_value)
                if pdf_field_name:
                    clean_field_name = pdf_field_name.strip('()')
                    
                    if clean_field_name in available_fields:
                        # Set this field to checked
                        form.fill({clean_field_name: True})
                        print(f"    ✅ Set {clean_field_name} = True")
                        aggregated_fields_processed += 1
                        
                        # Set other fields in the same group to unchecked
                        for other_field in self.checkbox_groups["radio_button_groups"][radio_group]:
                            if other_field != field_value:
                                other_pdf_field = self.field_map.get(other_field)
                                if other_pdf_field:
                                    other_clean_field = other_pdf_field.strip('()')
                                    if other_clean_field in available_fields:
                                        form.fill({other_clean_field: False})
                                        print(f"    ✅ Set {other_clean_field} = False")
                    else:
                        print(f"    ⚠️  Field {clean_field_name} not found in PDF")
                else:
                    print(f"    ⚠️  No PDF field mapping for sub-field {field_value}")
        
        return aggregated_fields_processed
    
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
            "yes_no_fields": [],
            "radio_group_fields": [],
            "multiple_choice_fields": [],
            "aggregated_radio_group_fields": [],
            "unmapped_fields": [],
            "stored_fields_added": [],
            "total_fields": len(merged_data),
            "extraction_fields": len(extraction_data),
            "stored_fields": len(merged_data) - len(extraction_data)
        }
        
        for field_name, field_value in merged_data.items():
            # Check if this field came from stored data
            is_stored_field = field_name not in extraction_data
            
            # Check if this is an aggregated radio group field first
            radio_group = None
            for group_name, fields in self.checkbox_groups["radio_button_groups"].items():
                if field_value in fields:
                    radio_group = group_name
                    break
            
            if radio_group:
                field_info = {
                    "field_name": field_name,
                    "pdf_field_name": f"AGGREGATED->{field_value}",
                    "field_type": "aggregated_radio_group",
                    "value": field_value,
                    "source": "stored" if is_stored_field else "extraction"
                }
                summary["aggregated_radio_group_fields"].append(field_info)
                if is_stored_field:
                    summary["stored_fields_added"].append(field_name)
            # Check if this field is directly mapped
            elif field_name in self.field_map:
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
                    summary["yes_no_fields"].append(field_info)
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


def test_complete_form_filler():
    """Test the complete PyPDFForm form filler with stored data"""
    
    print("🧪 Testing Complete PyPDFForm Form Filler with Stored Data")
    print("=" * 80)
    
    # Load test extraction data
    extraction_path = "extractions/test_appointment_extraction.json"
    with open(extraction_path, 'r') as f:
        extraction_data = json.load(f)
    
    # Initialize form filler
    filler = WSIBFormFiller()
    
    # Get field summary
    summary = filler.get_field_summary(extraction_data)
    
    print(f"📊 Field Processing Summary:")
    print(f"  Total fields: {summary['total_fields']}")
    print(f"  Extraction fields: {summary['extraction_fields']}")
    print(f"  Stored fields: {summary['stored_fields']}")
    print(f"  Text fields: {len(summary['text_fields'])}")
    print(f"  Yes/No fields: {len(summary['yes_no_fields'])}")
    print(f"  Radio group fields: {len(summary['radio_group_fields'])}")
    print(f"  Multiple choice fields: {len(summary['multiple_choice_fields'])}")
    print(f"  Aggregated radio groups: {len(summary['aggregated_radio_group_fields'])}")
    print(f"  Unmapped fields: {len(summary['unmapped_fields'])}")
    
    if summary['stored_fields_added']:
        print(f"\n📋 Stored fields added:")
        for field in summary['stored_fields_added']:
            print(f"  ✅ {field}")
    
    # Test form filling
    template_path = "forms/templates/wsib_faf_template.pdf"
    output_path = "output_forms/complete_pypdfform_with_stored_data_test.pdf"
    
    print(f"\n📄 Template: {template_path}")
    print(f"📄 Output: {output_path}")
    
    # Fill the form
    success = filler.fill_wsib_form(template_path, extraction_data, output_path)
    
    if success:
        print(f"\n✅ Form filling completed successfully!")
        
        # Check output file
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"📊 Output file size: {file_size} bytes")
            
            if file_size > 1000:
                print(f"✅ Output file appears to have content")
                
                # Try to verify the filled form
                try:
                    # Check with PyPDFForm
                    form = PdfWrapper(output_path)
                    filled_data = form.data
                    
                    print(f"\n🔍 Verifying filled form:")
                    
                    # Check some key fields from each category
                    key_fields = [
                        # Text fields (including stored data)
                        'txtD1dateofassessment',
                        'txtE6workhoursstarted', 
                        'txtFdateofnextappointment',
                        'txtE3additionalcomments',
                        'txtChealthprofessionalname',  # Stored data
                        'txtChealthprofessionaladdress',  # Stored data
                        'txtChealthprofessionalcitytown',  # Stored data
                        # Yes/No fields
                        'cbE2restrictionsaboveshoulder',
                        'cbE2restrictionsoperatingequipment',
                        'cbcareyouregistered1',  # Stored data
                        # Multiple choice fields
                        'CBQ21',  # return_to_work_capability
                        'cbE4howlong'  # restriction_duration
                    ]
                    
                    for field_name in key_fields:
                        if field_name in filled_data:
                            value = filled_data[field_name]
                            print(f"  {field_name}: {value}")
                        else:
                            print(f"  {field_name}: NOT_FOUND")
                    
                    print(f"✅ Form verification successful!")
                    
                except Exception as e:
                    print(f"❌ Cannot verify filled form: {e}")
            else:
                print(f"⚠️  Output file seems small")
        else:
            print(f"❌ Output file was not created")
    else:
        print(f"❌ Form filling failed")


if __name__ == "__main__":
    test_complete_form_filler()
