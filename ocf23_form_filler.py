#!/usr/bin/env python3
"""
OCF-23 Form Filler using PyPDFForm
Separate filler to avoid impacting WSIB flow during development
"""

import os
import json
import warnings
from typing import Dict, Any, List, Optional
from PyPDFForm import PdfWrapper

# Suppress pypdf warnings about undefined objects
warnings.filterwarnings("ignore", message="Object 0 0 not defined")


class OCF23FormFiller:
    def __init__(self, config_dir: Optional[str] = None):
        # Use proper resource path for config files (read-only from bundle)
        if config_dir is None:
            try:
                from app_paths import get_resource_path
                self.config_dir = str(get_resource_path("config"))
            except ImportError:
                import sys
                from pathlib import Path
                if getattr(sys, '_MEIPASS', None):
                    self.config_dir = str(Path(sys._MEIPASS) / "config")
                else:
                    self.config_dir = "config"
        else:
            self.config_dir = config_dir
        self.field_map = self._load_field_map()
        self.checkbox_groups = self._load_checkbox_groups()
        self.field_types = self._load_field_types()
        self.stored_data = self._load_stored_data()

    def _load_field_map(self) -> Dict[str, str]:
        with open(os.path.join(self.config_dir, "field_map_ocf23_simplified.json"), 'r') as f:
            return json.load(f)

    def _load_checkbox_groups(self) -> Dict[str, Any]:
        with open(os.path.join(self.config_dir, "ocf23_checkbox_groups_simplified.json"), 'r') as f:
            return json.load(f)

    def _load_field_types(self) -> Dict[str, str]:
        with open(os.path.join(self.config_dir, "ocf23_field_types_simplified.json"), 'r') as f:
            return json.load(f)["field_types"]

    def _load_stored_data(self) -> Dict[str, Any]:
        path = os.path.join(self.config_dir, "ocf23_stored_data.json")
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                print(f"📋 Loaded OCF-23 stored data from: {path}")
                return data
            except Exception as e:
                print(f"⚠️  Could not load OCF-23 stored data: {e}")
                return {}
        print(f"⚠️  OCF-23 stored data file not found: {path}")
        return {}

    def _merge_extraction_with_stored_data(self, extraction_data: Dict[str, Any]) -> Dict[str, Any]:
        merged = extraction_data.copy()
        flat: Dict[str, Any] = {}
        for section in ("health_professional_info", "clinic_info", "cover_page"):
            if section in self.stored_data and isinstance(self.stored_data[section], dict):
                for k, v in self.stored_data[section].items():
                    flat[k] = v
        for k, v in flat.items():
            if k not in merged:
                merged[k] = v
                print(f"  ✅ Added stored field: {k} = {v}")
        return merged

    def fill_ocf23_form(self, template_path: str, extraction_data: Dict[str, Any], output_path: str) -> bool:
        try:
            print(f"Loading OCF-23 PDF template: {template_path}")
            merged = self._merge_extraction_with_stored_data(extraction_data)
            form = PdfWrapper(template_path)
            available = form.data

            processed = 0
            # Text fields
            text_payload: Dict[str, Any] = {}
            for key, value in merged.items():
                if key in self.field_map and self.field_types.get(key, "text") == "text":
                    pdf_key = self.field_map[key].strip('()')
                    if pdf_key in available:
                        text_payload[pdf_key] = "" if value is None else str(value)
                        processed += 1
            if text_payload:
                form.fill(text_payload)

            # Yes/No checkboxes
            yes_no = set(self.checkbox_groups.get("yes_no_fields", []))
            for key, value in merged.items():
                if key in self.field_map and (self.field_types.get(key) == "checkbox" or key in yes_no):
                    pdf_key = self.field_map[key].strip('()')
                    if pdf_key in available:
                        form.fill({pdf_key: bool(value) if value is not None else False})
                        processed += 1

            # Radio button groups (by field membership)
            radio_groups = self.checkbox_groups.get("radio_button_groups", {})
            for key, value in merged.items():
                group = None
                for gname, fields in radio_groups.items():
                    if key in fields:
                        group = gname
                        break
                if group and value:
                    pdf_key = self.field_map.get(key)
                    if pdf_key:
                        clean = pdf_key.strip('()')
                        if clean in available:
                            form.fill({clean: True})
                            processed += 1
                            # Uncheck others in the same group
                            for other in radio_groups[group]:
                                if other != key:
                                    other_pdf = self.field_map.get(other)
                                    if other_pdf:
                                        other_clean = other_pdf.strip('()')
                                        if other_clean in available:
                                            form.fill({other_clean: False})

            # Multiple choice fields
            mc_all = self.checkbox_groups.get("multiple_choice_fields", {})
            for key, value in merged.items():
                if key in mc_all:
                    mc = mc_all[key]
                    pdf_name = mc["field_name"]
                    options: List[str] = mc["options"]
                    # Normalize boolean if needed
                    if options == ["yes", "no"] and isinstance(value, bool):
                        selected = "yes" if value else "no"
                    else:
                        selected = None
                        for opt in options:
                            if opt.lower() == str(value).lower():
                                selected = opt
                                break
                    if selected is not None and pdf_name in available:
                        # Use widgets index if radio
                        widget = form.widgets.get(pdf_name)
                        if widget and hasattr(widget, 'number_of_options') and widget.number_of_options >= 2:
                            try:
                                idx = options.index(selected)
                            except ValueError:
                                idx = None
                            if idx is not None:
                                form.fill({pdf_name: idx})
                                processed += 1
                        else:
                            form.fill({pdf_name: selected})
                            processed += 1

            form.write(output_path)
            print(f"📊 OCF-23 fields processed: {processed}")
            print(f"💾 OCF-23 form saved to: {output_path}")
            return True
        except Exception as e:
            print(f"Error filling OCF-23 form: {e}")
            import traceback
            traceback.print_exc()
            return False


