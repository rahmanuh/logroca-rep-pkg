#!/usr/bin/env python3
"""
Generate HTML survey files for LogRoca output evaluation.
Creates ZIP packages containing survey HTML and required log files.
"""

import pandas as pd
import json
from pathlib import Path
from datetime import datetime
import zipfile
import shutil
import numpy as np


def format_json_for_html(json_str):
    """Parse and format JSON string for HTML display, handling truncated JSON"""
    if pd.isna(json_str) or json_str == '':
        return ''

    try:
        if isinstance(json_str, str):
            data = json.loads(json_str)
        else:
            data = json_str
        return json.dumps(data, indent=2, ensure_ascii=False)
    except json.JSONDecodeError:
        # If JSON is invalid/truncated, try to format it nicely anyway
        return format_truncated_json(json_str)
    except Exception:
        return str(json_str)


def format_truncated_json(json_str):
    """Format potentially truncated JSON for better readability"""
    if not isinstance(json_str, str):
        return str(json_str)

    # Basic formatting: add proper indentation
    formatted = []
    indent_level = 0
    in_string = False
    escape_next = False
    i = 0

    while i < len(json_str):
        char = json_str[i]

        # Handle string escaping
        if escape_next:
            formatted.append(char)
            escape_next = False
            i += 1
            continue

        if char == '\\':
            formatted.append(char)
            escape_next = True
            i += 1
            continue

        # Track if we're inside a string
        if char == '"':
            in_string = not in_string
            formatted.append(char)
            i += 1
            continue

        # Only process structure characters outside strings
        if not in_string:
            if char in '{[':
                formatted.append(char)
                indent_level += 1
                formatted.append('\n' + '  ' * indent_level)
            elif char in '}]':
                indent_level = max(0, indent_level - 1)
                formatted.append('\n' + '  ' * indent_level)
                formatted.append(char)
            elif char == ',':
                formatted.append(char)
                formatted.append('\n' + '  ' * indent_level)
            elif char == ':':
                formatted.append(char)
                formatted.append(' ')
            elif char == '\n':
                # Skip existing newlines, we'll add our own
                i += 1
                continue
            else:
                formatted.append(char)
        else:
            formatted.append(char)

        i += 1

    result = ''.join(formatted)

    # Clean up multiple consecutive spaces (but preserve indentation)
    lines = result.split('\n')
    cleaned_lines = []
    for line in lines:
        # Get leading whitespace
        stripped = line.lstrip()
        if stripped:
            leading_spaces = len(line) - len(stripped)
            # Remove extra spaces in content but keep indentation
            cleaned_content = ' '.join(stripped.split())
            cleaned_lines.append('  ' * (leading_spaces // 2) + cleaned_content)
        elif line.strip():  # Line with only spaces
            cleaned_lines.append(line)

    result = '\n'.join(cleaned_lines)

    # Add a note if the JSON appears truncated
    if result.rstrip().endswith(',') or (not result.rstrip().endswith(('}', ']', '"')) and len(result) > 100):
        result += '\n\n[Note: This JSON excerpt appears to be truncated]'

    return result


def wrap_text(text, width):
    """Wrap text at word boundaries to fit within specified width"""
    if not text or len(text) <= width:
        return [text] if text else ['']

    words = text.split()
    lines = []
    current_line = []
    current_length = 0

    for word in words:
        word_len = len(word)
        # +1 for space between words
        if current_length + word_len + (1 if current_line else 0) <= width:
            current_line.append(word)
            current_length += word_len + (1 if len(current_line) > 1 else 0)
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]
            current_length = word_len

    if current_line:
        lines.append(' '.join(current_line))

    return lines if lines else ['']


def format_test_case(test_case_str):
    """Format test case JSON string into a readable format with 2-column categories"""
    if not test_case_str:
        return ''

    import re

    # Since the JSON might be truncated, use regex-based extraction
    formatted_parts = []

    # Extract test_case_id
    tc_id_match = re.search(r'"test_case_id":\s*"([^"]+)"', test_case_str)
    if tc_id_match:
        formatted_parts.append(f"Test Case ID: {tc_id_match.group(1)}")

    # Extract name
    name_match = re.search(r'"name":\s*"([^"]+)"', test_case_str)
    if name_match:
        formatted_parts.append(f"Name: {name_match.group(1)}")

    # Extract State
    state_match = re.search(r'"State":\s*"([^"]+)"', test_case_str)
    if state_match:
        formatted_parts.append(f"State: {state_match.group(1)}")

    formatted_parts.append("")  # Empty line

    # Extract Description
    desc_match = re.search(r'"Description":\s*"([^"]+)"', test_case_str)
    if desc_match:
        formatted_parts.append("Description:")
        formatted_parts.append(f"  {desc_match.group(1)}")
        formatted_parts.append("")

    # Extract Categories - 2 COLUMN LAYOUT
    # Find the Categories array: "Categories": [[...], [...], ...]
    cat_match = re.search(r'"Categories":\s*\[(.*?)\](?=\s*,\s*"|\s*\})', test_case_str, re.DOTALL)
    if cat_match:
        cat_content = cat_match.group(1)
        # Extract individual category pairs: ["key", "value"]
        cat_pairs = re.findall(r'\[\s*"([^"]+)"\s*,\s*"([^"]*)"', cat_content)

        if cat_pairs:
            formatted_parts.append("Categories:")

            # Format in 2 columns
            col_width = 45  # Width for each column
            for i in range(0, len(cat_pairs), 2):
                left_key, left_val = cat_pairs[i]
                left_text = f"{left_key}: {left_val}"

                if i + 1 < len(cat_pairs):
                    right_key, right_val = cat_pairs[i + 1]
                    right_text = f"{right_key}: {right_val}"
                    formatted_parts.append(f"  {left_text:<{col_width}} {right_text}")
                else:
                    formatted_parts.append(f"  {left_text}")

            formatted_parts.append("")

    # Extract Validated Requirements
    val_req_match = re.search(r'"Validated Requirements":\s*\[(.*?)\](?=\s*,\s*"|\s*\})', test_case_str, re.DOTALL)
    if val_req_match:
        val_req_content = val_req_match.group(1)
        # Extract individual requirements
        val_reqs = re.findall(r'"([^"]+(?:\|[^"]+)*)"', val_req_content)

        if val_reqs:
            formatted_parts.append("Validated Requirements:")
            for req in val_reqs:
                formatted_parts.append(f"  - {req}")
            formatted_parts.append("")

    # Extract Pre-Condition
    pre_cond_match = re.search(r'"Pre-Condition":\s*\[(.*?)\](?=\s*,\s*"|\s*\})', test_case_str, re.DOTALL)
    if pre_cond_match:
        pre_cond_content = pre_cond_match.group(1)
        # Extract individual steps
        pre_steps = re.findall(r'"([^"]+)"', pre_cond_content)

        if pre_steps:
            formatted_parts.append("Pre-Condition:")
            for i, step in enumerate(pre_steps, 1):
                formatted_parts.append(f"  {i}. {step}")
            formatted_parts.append("")

    # Extract Test Case Design - Format with each step on new line
    design_match = re.search(r'"Test Case Design":\s*\[(.*?)(?:\](?=\s*,\s*")|$)', test_case_str, re.DOTALL)
    if design_match:
        design_content = design_match.group(1)
        formatted_parts.append("Test Case Design:")

        # Extract individual test steps using regex (handles truncated JSON)
        # Find string literals (like "System test")
        string_items = re.findall(r'^\s*"([^"]+)"(?=\s*,)', design_content)
        for item in string_items:
            formatted_parts.append(f"\n  {item}")

        # Find array items with 3 elements [No, Action, Expected]
        # Pattern: ["something", "something", "something"]
        step_pattern = r'\[\s*"([^"]+)"\s*,\s*"([^"]+)"\s*,\s*"([^"]+)"\s*\]'
        steps = re.findall(step_pattern, design_content)

        for step_no, action, expected in steps:
            formatted_parts.append(f"\n  Step {step_no}:")
            formatted_parts.append(f"    Action: {action}")
            formatted_parts.append(f"    Expected Result: {expected}")

        # Find array items with 2 elements (like header row)
        header_pattern = r'\[\s*"([^"]+)"\s*,\s*"([^"]+)"\s*\]'
        headers = re.findall(header_pattern, design_content)

        # Filter out 3-element arrays (already processed)
        for header in headers:
            if header not in [(s[0], s[1]) for s in steps]:
                formatted_parts.append(f"\n  {header[0]} | {header[1]}")

        # Check if content appears to be truncated
        # Content is truncated if it contains truncation markers or doesn't end properly
        content_end = design_content.rstrip()
        is_truncated = (
            '[truncated]' in content_end or
            '...[truncated' in content_end or
            content_end.endswith('...') or
            content_end.endswith(',') or
            (not content_end.endswith(']') and len(content_end) > 100)
        )

        if is_truncated:
            formatted_parts.append("\n  [Note: Test Case Design content appears to be truncated]")

        formatted_parts.append("")

    # Extract Post-Condition
    post_cond_match = re.search(r'"Post-Condition":\s*\[(.*?)\](?=\s*\}|$)', test_case_str, re.DOTALL)
    if post_cond_match:
        post_cond_content = post_cond_match.group(1)
        # Extract individual steps
        post_steps = re.findall(r'"([^"]+)"', post_cond_content)

        if post_steps:
            formatted_parts.append("Post-Condition:")
            for i, step in enumerate(post_steps, 1):
                formatted_parts.append(f"  {i}. {step}")

    return "\n".join(formatted_parts)


def get_html_log_path(log_file_name):
    """
    Get the relative path to the HTML log file for iframe src.

    Args:
        log_file_name: Name from CSV (e.g., 'log_0007.json')

    Returns:
        str: Relative path to HTML log file (e.g., 'logs/log_0007.html')
    """
    # Handle file name mapping: CSV has .json, but HTML files are .html
    html_file_name = log_file_name.replace('.json', '.html')
    html_path = Path(__file__).parent / "logs" / html_file_name

    # Check if HTML file exists
    if not html_path.exists():
        print(f"Warning: HTML log file not found: {html_file_name}")
        return ''

    # Return relative path for iframe src
    return f'logs/{html_file_name}'


def escape_js_string(s):
    """Escape string for safe embedding in JavaScript"""
    if pd.isna(s):
        return ''
    s = str(s)
    s = s.replace('\\', '\\\\')
    s = s.replace('`', '\\`')
    s = s.replace('$', '\\$')
    return s


def format_requirements(requirements_str):
    """Format requirements JSON string into a readable format with 2-column layout"""
    if not requirements_str:
        return ''

    import re

    # Find all requirement objects
    req_pattern = r'\{"ID":[^}]+\}'
    requirements = re.findall(req_pattern, requirements_str)

    if not requirements:
        return requirements_str

    formatted_parts = []
    col_width = 45  # Width for left column

    for i, req_json in enumerate(requirements, 1):
        try:
            req_obj = json.loads(req_json)

            # Format each requirement with 2-column layout for metadata
            formatted = f"Requirement {i}:\n"

            # Row 1: ID and SIL
            left = f"ID: {req_obj.get('ID', 'N/A')}"
            right = f"SIL: {req_obj.get('SIL', 'N/A')}"
            formatted += f"  {left:<{col_width}} {right}\n"

            # Row 2: Name and Status
            left = f"Name: {req_obj.get('Name', 'N/A')}"
            right = f"Status: {req_obj.get('Status', 'N/A')}"
            formatted += f"  {left:<{col_width}} {right}\n"

            # Row 3: Type (single column)
            formatted += f"  Type: {req_obj.get('Type', 'N/A')}\n"

            formatted += "\n"  # Empty line before full-width fields

            # Full-width fields
            if req_obj.get('Description'):
                formatted += f"  Description:\n    {req_obj.get('Description')}\n"

            # Add optional fields if they exist and are not empty
            if req_obj.get('Requires'):
                formatted += f"  Requires: {req_obj.get('Requires')}\n"
            if req_obj.get('Provides'):
                formatted += f"  Provides: {req_obj.get('Provides')}\n"
            if req_obj.get('Derived from'):
                formatted += f"  Derived from: {req_obj.get('Derived from')}\n"
            if req_obj.get('Rationale'):
                formatted += f"  Rationale: {req_obj.get('Rationale')}\n"

            formatted_parts.append(formatted)
        except:
            # If parsing fails, add raw JSON
            formatted_parts.append(f"Requirement {i} (raw):\n{req_json}\n")

    return "\n".join(formatted_parts)


def split_kb_context(kb_context_str):
    """Split KB context into test case and requirements using simple string matching"""
    if pd.isna(kb_context_str) or kb_context_str == '':
        return '', ''

    kb_str = str(kb_context_str)

    # Split by looking for requirement markers (objects with "ID" field)
    # Strategy: Split on patterns like {"ID": "
    import re

    # Find all positions where requirements start (indicated by {"ID": ")
    req_pattern = r'\{"ID":\s*"'
    matches = list(re.finditer(req_pattern, kb_str))

    if not matches:
        # No requirements found, treat entire content as test case
        # Format the test case for better display
        formatted_test_case = format_truncated_json(kb_str)
        return formatted_test_case, ''

    # First requirement starts at the first match
    first_req_pos = matches[0].start()

    # Everything before first requirement is test case
    test_case_part = kb_str[:first_req_pos].strip()

    # Everything from first requirement onwards is requirements
    requirements_part = kb_str[first_req_pos:].strip()

    # Clean up test case part - remove trailing separators
    test_case_part = test_case_part.rstrip(',').rstrip()

    # Format test case for better readability
    test_case_part = format_test_case(test_case_part)

    # Format requirements for better readability
    requirements_part = format_requirements(requirements_part)

    return test_case_part, requirements_part


def generate_html_survey(data_rows, rater_name, output_file):
    """Generate a self-contained HTML survey file"""

    # Reset index to ensure sequential numbering from 0
    data_rows = data_rows.reset_index(drop=True)

    # Load INFO.md content
    info_file = Path(__file__).parent / "INFO.md"
    info_content = ""
    if info_file.exists():
        with open(info_file, 'r', encoding='utf-8') as f:
            info_content = f.read()

    # Convert dataframe rows to JavaScript array
    survey_data = []
    for idx, row in data_rows.iterrows():
        # Split KB context into test case and requirements
        test_case_json, requirements_json = split_kb_context(row['truncated_kb_context'])

        # Get HTML log path for iframe
        html_log_path = get_html_log_path(row['log_file_name'])

        survey_data.append({
            'experiment_id': escape_js_string(row['experiment_id']),
            'log_file_name': escape_js_string(row['log_file_name']),
            'root_cause_output': escape_js_string(row['root_cause_output']),
            'root_cause_origin_output': escape_js_string(row['root_cause_origin_output']),
            'action_suggestions_output': escape_js_string(row['action_suggestions_output']),
            'rationale_output': escape_js_string(row['rationale_output']),
            'truncated_log_content': escape_js_string(format_json_for_html(row['truncated_log_content'])),
            'kb_test_case': escape_js_string(test_case_json),
            'kb_requirements': escape_js_string(requirements_json),
            'full_html_log_path': escape_js_string(html_log_path)
        })

    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LogRoca Survey - {rater_name}</title>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}

        .header {{
            border-bottom: 3px solid #007bff;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}

        .header h1 {{
            color: #007bff;
            font-size: 28px;
            margin-bottom: 10px;
        }}

        .progress-bar {{
            width: 100%;
            height: 30px;
            background: #e9ecef;
            border-radius: 15px;
            overflow: hidden;
            margin-top: 15px;
        }}

        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #007bff, #0056b3);
            transition: width 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 12px;
        }}

        .content-section {{
            margin-bottom: 30px;
        }}

        .logroca-output-section {{
            background: #e8f4f8;
            padding: 25px;
            border-radius: 8px;
            border: 2px solid #17a2b8;
            margin-bottom: 25px;
        }}

        .logroca-output-section h3 {{
            color: #17a2b8;
            margin-bottom: 20px;
            margin-top: 0;
            font-size: 20px;
            border-bottom: 2px solid #17a2b8;
            padding-bottom: 10px;
        }}

        .context-section {{
            background: #f0f4f8;
            padding: 25px;
            border-radius: 8px;
            border: 2px solid #6c757d;
            margin-bottom: 25px;
        }}

        .context-section h3 {{
            color: #495057;
            margin-bottom: 20px;
            margin-top: 0;
            font-size: 20px;
            border-bottom: 2px solid #6c757d;
            padding-bottom: 10px;
        }}

        .field {{
            margin-bottom: 20px;
        }}

        .field-label {{
            font-weight: 600;
            color: #555;
            margin-bottom: 8px;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .field-value {{
            background: #ffffff;
            padding: 12px 15px;
            border-radius: 5px;
            border-left: 4px solid #007bff;
            font-size: 15px;
        }}

        .field-value.list {{
            white-space: pre-wrap;
        }}

        .collapsible {{
            background: #007bff;
            color: white;
            cursor: pointer;
            padding: 12px 15px;
            border: none;
            text-align: left;
            width: 100%;
            border-radius: 5px;
            font-size: 15px;
            font-weight: 600;
            margin-bottom: 10px;
            transition: background 0.3s;
        }}

        .collapsible:hover {{
            background: #0056b3;
        }}

        .collapsible:after {{
            content: '\\25BC';
            float: right;
            margin-left: 5px;
            transition: transform 0.3s;
        }}

        .collapsible.active:after {{
            transform: rotate(-180deg);
        }}

        .json-content {{
            display: none;
            background: #ffffff;
            padding: 15px;
            border-radius: 0 0 5px 5px;
            margin-top: -10px;
            margin-bottom: 15px;
            overflow-x: auto;
            border-left: 4px solid #007bff;
        }}

        .json-content pre {{
            color: #212529;
            font-family: 'Courier New', Courier, monospace;
            font-size: 15px;
            margin: 0;
            white-space: pre;
            overflow-x: auto;
            line-height: 1.8;
            tab-size: 12;
        }}

        .rating-section {{
            background: #fff3cd;
            border: 2px solid #ffc107;
            border-radius: 8px;
            padding: 25px;
            margin: 30px 0;
        }}

        .rating-section h3 {{
            color: #856404;
            margin-bottom: 20px;
        }}

        .radio-group {{
            margin: 20px 0;
        }}

        .radio-option {{
            display: inline-block;
            margin-right: 30px;
        }}

        .radio-option input[type="radio"] {{
            margin-right: 8px;
            width: 18px;
            height: 18px;
            vertical-align: middle;
        }}

        .radio-option label {{
            font-size: 16px;
            vertical-align: middle;
            cursor: pointer;
        }}

        textarea {{
            width: 100%;
            min-height: 100px;
            padding: 12px;
            border: 1px solid #ced4da;
            border-radius: 5px;
            font-size: 14px;
            font-family: inherit;
            resize: vertical;
        }}

        .navigation {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 2px solid #e9ecef;
        }}

        .btn {{
            padding: 12px 24px;
            border: none;
            border-radius: 5px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }}

        .btn-primary {{
            background: #007bff;
            color: white;
        }}

        .btn-primary:hover:not(:disabled) {{
            background: #0056b3;
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,123,255,0.3);
        }}

        .btn-secondary {{
            background: #6c757d;
            color: white;
        }}

        .btn-secondary:hover:not(:disabled) {{
            background: #545b62;
        }}

        .btn-success {{
            background: #28a745;
            color: white;
        }}

        .btn-success:hover:not(:disabled) {{
            background: #218838;
        }}

        .btn:disabled {{
            opacity: 0.5;
            cursor: not-allowed;
        }}

        .action-buttons {{
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            padding: 15px;
            background: #e7f3ff;
            border-radius: 5px;
        }}

        .auto-save-indicator {{
            position: fixed;
            top: 20px;
            right: 20px;
            background: #28a745;
            color: white;
            padding: 10px 15px;
            border-radius: 5px;
            font-size: 14px;
            opacity: 0;
            transition: opacity 0.3s;
        }}

        .auto-save-indicator.show {{
            opacity: 1;
        }}

        .hidden {{
            display: none;
        }}

        .validation-error {{
            background: #f8d7da;
            border: 1px solid #f5c6cb;
            color: #721c24;
            padding: 12px;
            border-radius: 5px;
            margin: 15px 0;
        }}

        .info-section {{
            background: #e7f3ff;
            border-left: 4px solid #007bff;
            padding: 20px;
            margin-bottom: 25px;
            border-radius: 5px;
            line-height: 1.8;
        }}

        .info-section h2 {{
            color: #007bff;
            margin-top: 0;
            margin-bottom: 15px;
        }}

        .info-section h1 {{
            color: #007bff;
            margin-top: 20px;
            margin-bottom: 10px;
            font-size: 24px;
        }}

        .info-section h3 {{
            color: #0056b3;
            margin-top: 15px;
            margin-bottom: 8px;
        }}

        .info-section p {{
            margin-bottom: 10px;
        }}

        .info-section ul, .info-section ol {{
            margin-left: 25px;
            margin-bottom: 10px;
        }}

        .info-section li {{
            margin-bottom: 5px;
        }}

        .info-section strong {{
            color: #0056b3;
        }}

        .info-section code {{
            background: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }}

        /* Likert Scale Styles */
        .likert-group {{
            margin: 25px 0;
            padding: 20px;
            background: #fff;
            border-radius: 8px;
            border: 1px solid #dee2e6;
        }}

        .likert-question {{
            font-weight: 600;
            color: #495057;
            margin-bottom: 15px;
            font-size: 15px;
        }}

        .likert-field-name {{
            color: #007bff;
            font-weight: 700;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 10px;
        }}

        .likert-scale {{
            display: flex;
            justify-content: space-between;
            align-items: stretch;
            gap: 10px;
            margin-top: 10px;
        }}

        .likert-option {{
            flex: 1;
            display: flex;
            flex-direction: column;
            align-items: center;
        }}

        .likert-option input[type="radio"] {{
            margin-bottom: 8px;
            width: 20px;
            height: 20px;
            cursor: pointer;
        }}

        .likert-label {{
            font-size: 13px;
            text-align: center;
            color: #495057;
            line-height: 1.3;
            max-width: 120px;
        }}

        .likert-option input[type="radio"]:checked + .likert-label {{
            color: #007bff;
            font-weight: 600;
        }}

        /* Full XML Log Section Styles */
        .full-log-section {{
            background: #fff8e1;
            padding: 25px;
            border-radius: 8px;
            border: 2px solid #ffc107;
            margin-bottom: 25px;
        }}

        .full-log-section h3 {{
            color: #f57c00;
            margin-bottom: 20px;
            margin-top: 0;
            font-size: 20px;
            border-bottom: 2px solid #ffc107;
            padding-bottom: 10px;
        }}

        .xml-content {{
            display: none;
            background: #f5f5f5;
            padding: 15px;
            border-radius: 0 0 5px 5px;
            margin-top: -10px;
            margin-bottom: 15px;
            overflow-x: auto;
            max-height: 600px;
            overflow-y: auto;
        }}

        .xml-content iframe {{
            width: 100%;
            height: 500px;
            border: none;
            background: white;
        }}

        .error-message {{
            background: #fff3cd;
            border: 1px solid #ffc107;
            color: #856404;
            padding: 12px;
            border-radius: 5px;
            margin: 10px 0;
        }}

        /* Mobile Responsive */
        @media (max-width: 768px) {{
            .likert-scale {{
                flex-direction: column;
                gap: 15px;
            }}

            .likert-option {{
                flex-direction: row;
                justify-content: flex-start;
            }}

            .likert-option input[type="radio"] {{
                margin-right: 10px;
                margin-bottom: 0;
            }}

            .likert-label {{
                text-align: left;
            }}
        }}
    </style>
</head>
<body>
    <div class="auto-save-indicator" id="autoSaveIndicator">Auto-saved</div>

    <div class="container">
        <div class="header">
            <h1>LogRoca Output Evaluation Survey</h1>
            <p><strong>Rater:</strong> {rater_name}</p>
            <p><strong>Total Questions:</strong> <span id="totalQuestions">{len(survey_data)}</span></p>
            <div class="progress-bar">
                <div class="progress-fill" id="progressBar">0%</div>
            </div>
        </div>

        <div class="info-section" id="infoSection"></div>

        <div class="action-buttons">
            <button class="btn btn-secondary" onclick="downloadProgress()" title="Download your progress as a JSON file to resume later">💾 Save Progress</button>
            <button class="btn btn-secondary" onclick="document.getElementById('loadFile').click()" title="Load a previously saved progress file">📂 Load Progress</button>
            <input type="file" id="loadFile" class="hidden" accept=".json" onchange="loadProgress(event)">
            <button class="btn btn-success" onclick="submitSurvey()" id="submitBtn" title="Export all responses to a CSV file for submission">✓ Save Final Responses as CSV</button>
        </div>

        <div id="questionContent"></div>

        <div class="navigation">
            <button class="btn btn-secondary" id="prevBtn" onclick="previousQuestion()" title="Go to the previous question">← Previous</button>
            <span id="questionNumber">Question 1 of {len(survey_data)}</span>
            <button class="btn btn-primary" id="nextBtn" onclick="nextQuestion()" title="Go to the next question">Next →</button>
        </div>
    </div>

    <script>
        // Survey data embedded in JavaScript
        const surveyData = {json.dumps(survey_data, ensure_ascii=False)};
        const raterName = "{rater_name}";
        const storageKey = `logroca_survey_${{raterName}}`;

        // Markdown content for info section
        const infoMarkdown = `{escape_js_string(info_content)}`;

        let currentQuestion = 0;
        let responses = {{}};
        let demographicData = {{}};
        let conclusionData = {{}};
        let showingDemographic = true;
        let showingConclusion = false;

        // Initialize on page load
        window.onload = function() {{
            // Render markdown info section
            const infoSection = document.getElementById('infoSection');
            if (infoSection && typeof marked !== 'undefined') {{
                infoSection.innerHTML = marked.parse(infoMarkdown);
            }} else {{
                infoSection.textContent = infoMarkdown;
            }}

            loadFromLocalStorage();
            if (demographicData.role && demographicData.experience && demographicData.department && demographicData.tcms_experience) {{
                showingDemographic = false;
            }}
            renderContent();
            updateProgress();
        }};

        function renderContent() {{
            if (showingDemographic) {{
                renderDemographic();
            }} else if (showingConclusion) {{
                renderConclusion();
            }} else {{
                renderQuestion();
            }}
        }}

        function renderDemographic() {{
            const html = `
                <div class="rating-section">
                    <h3>Demographic Information</h3>
                    <p style="margin-bottom: 20px;">Please answer these questions before starting the survey:</p>

                    <div class="radio-group">
                        <strong>What is your primary role?</strong><br><br>
                        <div class="radio-option">
                            <input type="radio" id="role_dev" name="role" value="software developer"
                                ${{demographicData.role === 'software developer' ? 'checked' : ''}}
                                onchange="saveDemographic()">
                            <label for="role_dev">Software Developer</label>
                        </div>
                        <div class="radio-option">
                            <input type="radio" id="role_tester" name="role" value="software tester"
                                ${{demographicData.role === 'software tester' ? 'checked' : ''}}
                                onchange="saveDemographic()">
                            <label for="role_tester">Software Tester</label>
                        </div>
                        <div class="radio-option">
                            <input type="radio" id="role_qa" name="role" value="software QA"
                                ${{demographicData.role === 'software QA' ? 'checked' : ''}}
                                onchange="saveDemographic()">
                            <label for="role_qa">Software QA</label>
                        </div>
                        <div class="radio-option">
                            <input type="radio" id="role_others" name="role" value="others"
                                ${{(demographicData.role && demographicData.role !== 'software developer' && demographicData.role !== 'software tester' && demographicData.role !== 'software QA') ? 'checked' : ''}}
                                onchange="saveDemographic()">
                            <label for="role_others">Others</label>
                        </div>
                        <div id="role_others_text" style="margin-top: 15px; display: ${{(demographicData.role && demographicData.role !== 'software developer' && demographicData.role !== 'software tester' && demographicData.role !== 'software QA') ? 'block' : 'none'}};">
                            <input type="text" id="role_others_input" placeholder="Please specify your role"
                                   style="width: 100%; padding: 10px; border: 1px solid #ced4da; border-radius: 5px; font-size: 14px;"
                                   value="${{demographicData.role && demographicData.role !== 'software developer' && demographicData.role !== 'software tester' && demographicData.role !== 'software QA' ? demographicData.role : ''}}"
                                   oninput="saveDemographic()">
                        </div>
                    </div>

                    <div class="radio-group" style="margin-top: 30px;">
                        <strong>How many years of experience do you have in software development/testing?</strong><br><br>
                        <div class="radio-option">
                            <input type="radio" id="exp_lt2" name="experience" value="<2 yoe"
                                ${{demographicData.experience === '<2 yoe' ? 'checked' : ''}}
                                onchange="saveDemographic()">
                            <label for="exp_lt2">&lt;2 years</label>
                        </div>
                        <div class="radio-option">
                            <input type="radio" id="exp_2to5" name="experience" value="2-5 yoe"
                                ${{demographicData.experience === '2-5 yoe' ? 'checked' : ''}}
                                onchange="saveDemographic()">
                            <label for="exp_2to5">2-5 years</label>
                        </div>
                        <div class="radio-option">
                            <input type="radio" id="exp_gt5" name="experience" value=">5 yoe"
                                ${{demographicData.experience === '>5 yoe' ? 'checked' : ''}}
                                onchange="saveDemographic()">
                            <label for="exp_gt5">&gt;5 years</label>
                        </div>
                    </div>

                    <div class="radio-group" style="margin-top: 30px;">
                        <strong>What department are you working in?</strong><br><br>
                        <div class="radio-option">
                            <input type="text" id="department_input" placeholder="Please specify your department"
                                   style="width: 100%; padding: 10px; border: 1px solid #ced4da; border-radius: 5px; font-size: 14px;"
                                   value="${{demographicData.department || ''}}"
                                   oninput="saveDemographic()">
                        </div>
                    </div>

                    <div class="radio-group" style="margin-top: 30px;">
                        <strong>Have you worked with TCMS?</strong><br><br>
                        <div class="radio-option">
                            <input type="radio" id="tcms_yes" name="tcms_experience" value="yes"
                                ${{demographicData.tcms_experience === 'yes' ? 'checked' : ''}}
                                onchange="saveDemographic()">
                            <label for="tcms_yes">Yes</label>
                        </div>
                        <div class="radio-option">
                            <input type="radio" id="tcms_no" name="tcms_experience" value="no"
                                ${{demographicData.tcms_experience === 'no' ? 'checked' : ''}}
                                onchange="saveDemographic()">
                            <label for="tcms_no">No</label>
                        </div>
                    </div>
                </div>
            `;

            document.getElementById('questionContent').innerHTML = html;
            document.getElementById('questionNumber').textContent = 'Demographic Information';

            // Update navigation buttons
            document.getElementById('prevBtn').style.visibility = 'hidden';
            document.getElementById('nextBtn').textContent = 'Start Survey →';
            document.getElementById('nextBtn').disabled = false;
        }}

        function saveDemographic() {{
            const role = document.querySelector('input[name="role"]:checked');
            const experience = document.querySelector('input[name="experience"]:checked');
            const department = document.getElementById('department_input');
            const tcms_experience = document.querySelector('input[name="tcms_experience"]:checked');
            const roleOthersText = document.getElementById('role_others_input');
            const roleOthersDiv = document.getElementById('role_others_text');

            // Toggle visibility of "others" text box
            if (role && role.value === 'others') {{
                if (roleOthersDiv) roleOthersDiv.style.display = 'block';
            }} else {{
                if (roleOthersDiv) roleOthersDiv.style.display = 'none';
            }}

            // Save role - use custom text if "others" is selected
            let roleValue = '';
            if (role) {{
                if (role.value === 'others' && roleOthersText && roleOthersText.value.trim()) {{
                    roleValue = roleOthersText.value.trim();
                }} else if (role.value !== 'others') {{
                    roleValue = role.value;
                }} else {{
                    roleValue = 'others';
                }}
            }}

            demographicData = {{
                role: roleValue,
                experience: experience ? experience.value : '',
                department: department ? department.value : '',
                tcms_experience: tcms_experience ? tcms_experience.value : ''
            }};

            saveToLocalStorage();
            showAutoSaveIndicator();
        }}

        function renderConclusion() {{
            const html = `
                <div class="rating-section">
                    <h3>Conclusion Questions</h3>
                    <p style="margin-bottom: 20px;">Please answer these final questions about your overall experience:</p>

                    <!-- Question 1 -->
                    <div class="likert-group">
                        <div class="likert-question">I trust the tool output.</div>
                        <div class="likert-scale">
                            <div class="likert-option">
                                <input type="radio" id="conclusion_q2_1" name="conclusion_q2" value="1"
                                    ${{conclusionData.q2 === '1' ? 'checked' : ''}}
                                    onchange="saveConclusion()">
                                <label class="likert-label" for="conclusion_q2_1">1<br>Strongly Disagree</label>
                            </div>
                            <div class="likert-option">
                                <input type="radio" id="conclusion_q2_2" name="conclusion_q2" value="2"
                                    ${{conclusionData.q2 === '2' ? 'checked' : ''}}
                                    onchange="saveConclusion()">
                                <label class="likert-label" for="conclusion_q2_2">2<br>Disagree</label>
                            </div>
                            <div class="likert-option">
                                <input type="radio" id="conclusion_q2_3" name="conclusion_q2" value="3"
                                    ${{conclusionData.q2 === '3' ? 'checked' : ''}}
                                    onchange="saveConclusion()">
                                <label class="likert-label" for="conclusion_q2_3">3<br>Neutral</label>
                            </div>
                            <div class="likert-option">
                                <input type="radio" id="conclusion_q2_4" name="conclusion_q2" value="4"
                                    ${{conclusionData.q2 === '4' ? 'checked' : ''}}
                                    onchange="saveConclusion()">
                                <label class="likert-label" for="conclusion_q2_4">4<br>Agree</label>
                            </div>
                            <div class="likert-option">
                                <input type="radio" id="conclusion_q2_5" name="conclusion_q2" value="5"
                                    ${{conclusionData.q2 === '5' ? 'checked' : ''}}
                                    onchange="saveConclusion()">
                                <label class="likert-label" for="conclusion_q2_5">5<br>Strongly Agree</label>
                            </div>
                        </div>
                    </div>

                    <!-- Question 3 -->
                    <div class="likert-group">
                        <div class="likert-question">I would recommend the tool to my colleagues.</div>
                        <div class="likert-scale">
                            <div class="likert-option">
                                <input type="radio" id="conclusion_q3_1" name="conclusion_q3" value="1"
                                    ${{conclusionData.q3 === '1' ? 'checked' : ''}}
                                    onchange="saveConclusion()">
                                <label class="likert-label" for="conclusion_q3_1">1<br>Strongly Disagree</label>
                            </div>
                            <div class="likert-option">
                                <input type="radio" id="conclusion_q3_2" name="conclusion_q3" value="2"
                                    ${{conclusionData.q3 === '2' ? 'checked' : ''}}
                                    onchange="saveConclusion()">
                                <label class="likert-label" for="conclusion_q3_2">2<br>Disagree</label>
                            </div>
                            <div class="likert-option">
                                <input type="radio" id="conclusion_q3_3" name="conclusion_q3" value="3"
                                    ${{conclusionData.q3 === '3' ? 'checked' : ''}}
                                    onchange="saveConclusion()">
                                <label class="likert-label" for="conclusion_q3_3">3<br>Neutral</label>
                            </div>
                            <div class="likert-option">
                                <input type="radio" id="conclusion_q3_4" name="conclusion_q3" value="4"
                                    ${{conclusionData.q3 === '4' ? 'checked' : ''}}
                                    onchange="saveConclusion()">
                                <label class="likert-label" for="conclusion_q3_4">4<br>Agree</label>
                            </div>
                            <div class="likert-option">
                                <input type="radio" id="conclusion_q3_5" name="conclusion_q3" value="5"
                                    ${{conclusionData.q3 === '5' ? 'checked' : ''}}
                                    onchange="saveConclusion()">
                                <label class="likert-label" for="conclusion_q3_5">5<br>Strongly Agree</label>
                            </div>
                        </div>
                    </div>

                    <!-- Question 4 - Free Text -->
                    <div class="likert-group">
                        <div class="likert-question">What improvements/features would you suggest for the tool? (Optional)</div>
                        <textarea id="conclusion_q4"
                                  placeholder="Please share your suggestions here..."
                                  style="width: 100%; min-height: 100px; padding: 12px; border: 1px solid #ced4da; border-radius: 5px; font-size: 14px; font-family: inherit; resize: vertical; margin-top: 10px;"
                                  oninput="saveConclusion()">${{conclusionData.q4 || ''}}</textarea>
                    </div>

                    <!-- Question 5 - Contact Permission -->
                    <div class="likert-group">
                        <div class="likert-question">Is it OK to contact you for follow-up questions?</div>
                        <div class="radio-group" style="margin-top: 15px;">
                            <div class="radio-option">
                                <input type="radio" id="contact_yes" name="conclusion_q5_contact" value="yes"
                                    ${{conclusionData.q5_contact === 'yes' ? 'checked' : ''}}
                                    onchange="saveConclusion()">
                                <label for="contact_yes">Yes</label>
                            </div>
                            <div class="radio-option">
                                <input type="radio" id="contact_no" name="conclusion_q5_contact" value="no"
                                    ${{conclusionData.q5_contact === 'no' ? 'checked' : ''}}
                                    onchange="saveConclusion()">
                                <label for="contact_no">No</label>
                            </div>
                        </div>
                        <div id="email_field" style="margin-top: 15px; display: ${{conclusionData.q5_contact === 'yes' ? 'block' : 'none'}};">
                            <label for="conclusion_q5_email" style="display: block; margin-bottom: 8px; font-weight: 600; color: #495057;">Please provide your email address:</label>
                            <input type="email" id="conclusion_q5_email"
                                   placeholder="your.email@example.com"
                                   style="width: 100%; padding: 10px; border: 1px solid #ced4da; border-radius: 5px; font-size: 14px;"
                                   value="${{conclusionData.q5_email || ''}}"
                                   oninput="saveConclusion()">
                        </div>
                    </div>
                </div>
            `;

            document.getElementById('questionContent').innerHTML = html;
            document.getElementById('questionNumber').textContent = 'Conclusion Questions';

            // Update navigation buttons
            document.getElementById('prevBtn').style.visibility = 'visible';
            document.getElementById('prevBtn').textContent = '← Back to Questions';
            document.getElementById('prevBtn').disabled = false;
            document.getElementById('nextBtn').textContent = 'Complete Survey →';
            document.getElementById('nextBtn').disabled = false;
        }}

        function saveConclusion() {{
            const q2 = document.querySelector('input[name="conclusion_q2"]:checked');
            const q3 = document.querySelector('input[name="conclusion_q3"]:checked');
            const q4 = document.getElementById('conclusion_q4');
            const q5_contact = document.querySelector('input[name="conclusion_q5_contact"]:checked');
            const q5_email = document.getElementById('conclusion_q5_email');

            // Toggle email field visibility
            const emailField = document.getElementById('email_field');
            if (emailField && q5_contact) {{
                emailField.style.display = q5_contact.value === 'yes' ? 'block' : 'none';
            }}

            conclusionData = {{
                q2: q2 ? q2.value : '',
                q3: q3 ? q3.value : '',
                q4: q4 ? q4.value : '',
                q5_contact: q5_contact ? q5_contact.value : '',
                q5_email: q5_email ? q5_email.value : ''
            }};

            saveToLocalStorage();
            showAutoSaveIndicator();
        }}

        function renderQuestion() {{
            const data = surveyData[currentQuestion];
            const response = responses[currentQuestion] || {{}};

            const html = `
                <div class="content-section">
                    <div class="field">
                        <div class="field-label">Experiment ID</div>
                        <div class="field-value">${{data.experiment_id}}</div>
                    </div>

                    <div class="field">
                        <div class="field-label">Log File Name</div>
                        <div class="field-value">${{data.log_file_name}}</div>
                    </div>
                </div>

                <div class="logroca-output-section">
                    <h3>LogRoca Output</h3>

                    <!-- Root Cause Output with Likert Scale -->
                    <div class="field">
                        <div class="field-label">Root Cause Output</div>
                        <div class="field-value">${{data.root_cause_output}}</div>
                    </div>
                    <div class="likert-group">
                        <div class="likert-question">The root cause prediction is correct.</div>
                        <div class="likert-scale">
                            <div class="likert-option">
                                <input type="radio" id="rc_1_${{currentQuestion}}" name="root_cause_rating" value="1"
                                    ${{response.root_cause_rating === '1' ? 'checked' : ''}}
                                    onchange="saveResponse()">
                                <label class="likert-label" for="rc_1_${{currentQuestion}}">1<br>Strongly Disagree</label>
                            </div>
                            <div class="likert-option">
                                <input type="radio" id="rc_2_${{currentQuestion}}" name="root_cause_rating" value="2"
                                    ${{response.root_cause_rating === '2' ? 'checked' : ''}}
                                    onchange="saveResponse()">
                                <label class="likert-label" for="rc_2_${{currentQuestion}}">2<br>Disagree</label>
                            </div>
                            <div class="likert-option">
                                <input type="radio" id="rc_3_${{currentQuestion}}" name="root_cause_rating" value="3"
                                    ${{response.root_cause_rating === '3' ? 'checked' : ''}}
                                    onchange="saveResponse()">
                                <label class="likert-label" for="rc_3_${{currentQuestion}}">3<br>Neutral</label>
                            </div>
                            <div class="likert-option">
                                <input type="radio" id="rc_4_${{currentQuestion}}" name="root_cause_rating" value="4"
                                    ${{response.root_cause_rating === '4' ? 'checked' : ''}}
                                    onchange="saveResponse()">
                                <label class="likert-label" for="rc_4_${{currentQuestion}}">4<br>Agree</label>
                            </div>
                            <div class="likert-option">
                                <input type="radio" id="rc_5_${{currentQuestion}}" name="root_cause_rating" value="5"
                                    ${{response.root_cause_rating === '5' ? 'checked' : ''}}
                                    onchange="saveResponse()">
                                <label class="likert-label" for="rc_5_${{currentQuestion}}">5<br>Strongly Agree</label>
                            </div>
                        </div>
                    </div>

                    <!-- Root Cause Origin Output with Likert Scale -->
                    <div class="field">
                        <div class="field-label">Root Cause Origin Output</div>
                        <div class="field-value">${{data.root_cause_origin_output}}</div>
                    </div>
                    <div class="likert-group">
                        <div class="likert-question">The root cause origin prediction points to the correct source document.</div>
                        <div class="likert-scale">
                            <div class="likert-option">
                                <input type="radio" id="rco_1_${{currentQuestion}}" name="root_cause_origin_rating" value="1"
                                    ${{response.root_cause_origin_rating === '1' ? 'checked' : ''}}
                                    onchange="saveResponse()">
                                <label class="likert-label" for="rco_1_${{currentQuestion}}">1<br>Strongly Disagree</label>
                            </div>
                            <div class="likert-option">
                                <input type="radio" id="rco_2_${{currentQuestion}}" name="root_cause_origin_rating" value="2"
                                    ${{response.root_cause_origin_rating === '2' ? 'checked' : ''}}
                                    onchange="saveResponse()">
                                <label class="likert-label" for="rco_2_${{currentQuestion}}">2<br>Disagree</label>
                            </div>
                            <div class="likert-option">
                                <input type="radio" id="rco_3_${{currentQuestion}}" name="root_cause_origin_rating" value="3"
                                    ${{response.root_cause_origin_rating === '3' ? 'checked' : ''}}
                                    onchange="saveResponse()">
                                <label class="likert-label" for="rco_3_${{currentQuestion}}">3<br>Neutral</label>
                            </div>
                            <div class="likert-option">
                                <input type="radio" id="rco_4_${{currentQuestion}}" name="root_cause_origin_rating" value="4"
                                    ${{response.root_cause_origin_rating === '4' ? 'checked' : ''}}
                                    onchange="saveResponse()">
                                <label class="likert-label" for="rco_4_${{currentQuestion}}">4<br>Agree</label>
                            </div>
                            <div class="likert-option">
                                <input type="radio" id="rco_5_${{currentQuestion}}" name="root_cause_origin_rating" value="5"
                                    ${{response.root_cause_origin_rating === '5' ? 'checked' : ''}}
                                    onchange="saveResponse()">
                                <label class="likert-label" for="rco_5_${{currentQuestion}}">5<br>Strongly Agree</label>
                            </div>
                        </div>
                    </div>

                    <!-- Action Suggestions Output with Likert Scale -->
                    <div class="field">
                        <div class="field-label">Action Suggestions Output</div>
                        <div class="field-value list">${{data.action_suggestions_output}}</div>
                    </div>
                    <div class="likert-group">
                        <div class="likert-question">The action suggestions are useful and relevant to the root cause and root cause origin.</div>
                        <div class="likert-scale">
                            <div class="likert-option">
                                <input type="radio" id="as_1_${{currentQuestion}}" name="action_suggestions_rating" value="1"
                                    ${{response.action_suggestions_rating === '1' ? 'checked' : ''}}
                                    onchange="saveResponse()">
                                <label class="likert-label" for="as_1_${{currentQuestion}}">1<br>Strongly Disagree</label>
                            </div>
                            <div class="likert-option">
                                <input type="radio" id="as_2_${{currentQuestion}}" name="action_suggestions_rating" value="2"
                                    ${{response.action_suggestions_rating === '2' ? 'checked' : ''}}
                                    onchange="saveResponse()">
                                <label class="likert-label" for="as_2_${{currentQuestion}}">2<br>Disagree</label>
                            </div>
                            <div class="likert-option">
                                <input type="radio" id="as_3_${{currentQuestion}}" name="action_suggestions_rating" value="3"
                                    ${{response.action_suggestions_rating === '3' ? 'checked' : ''}}
                                    onchange="saveResponse()">
                                <label class="likert-label" for="as_3_${{currentQuestion}}">3<br>Neutral</label>
                            </div>
                            <div class="likert-option">
                                <input type="radio" id="as_4_${{currentQuestion}}" name="action_suggestions_rating" value="4"
                                    ${{response.action_suggestions_rating === '4' ? 'checked' : ''}}
                                    onchange="saveResponse()">
                                <label class="likert-label" for="as_4_${{currentQuestion}}">4<br>Agree</label>
                            </div>
                            <div class="likert-option">
                                <input type="radio" id="as_5_${{currentQuestion}}" name="action_suggestions_rating" value="5"
                                    ${{response.action_suggestions_rating === '5' ? 'checked' : ''}}
                                    onchange="saveResponse()">
                                <label class="likert-label" for="as_5_${{currentQuestion}}">5<br>Strongly Agree</label>
                            </div>
                        </div>
                    </div>

                    <!-- Rationale Output with Likert Scale -->
                    <div class="field">
                        <div class="field-label">Rationale Output</div>
                        <div class="field-value">${{data.rationale_output}}</div>
                    </div>
                    <div class="likert-group">
                        <div class="likert-question">The rationale is understandable, clear, and related to the root cause, root cause origin, and the action suggestion.</div>
                        <div class="likert-scale">
                            <div class="likert-option">
                                <input type="radio" id="rat_1_${{currentQuestion}}" name="rationale_rating" value="1"
                                    ${{response.rationale_rating === '1' ? 'checked' : ''}}
                                    onchange="saveResponse()">
                                <label class="likert-label" for="rat_1_${{currentQuestion}}">1<br>Strongly Disagree</label>
                            </div>
                            <div class="likert-option">
                                <input type="radio" id="rat_2_${{currentQuestion}}" name="rationale_rating" value="2"
                                    ${{response.rationale_rating === '2' ? 'checked' : ''}}
                                    onchange="saveResponse()">
                                <label class="likert-label" for="rat_2_${{currentQuestion}}">2<br>Disagree</label>
                            </div>
                            <div class="likert-option">
                                <input type="radio" id="rat_3_${{currentQuestion}}" name="rationale_rating" value="3"
                                    ${{response.rationale_rating === '3' ? 'checked' : ''}}
                                    onchange="saveResponse()">
                                <label class="likert-label" for="rat_3_${{currentQuestion}}">3<br>Neutral</label>
                            </div>
                            <div class="likert-option">
                                <input type="radio" id="rat_4_${{currentQuestion}}" name="rationale_rating" value="4"
                                    ${{response.rationale_rating === '4' ? 'checked' : ''}}
                                    onchange="saveResponse()">
                                <label class="likert-label" for="rat_4_${{currentQuestion}}">4<br>Agree</label>
                            </div>
                            <div class="likert-option">
                                <input type="radio" id="rat_5_${{currentQuestion}}" name="rationale_rating" value="5"
                                    ${{response.rationale_rating === '5' ? 'checked' : ''}}
                                    onchange="saveResponse()">
                                <label class="likert-label" for="rat_5_${{currentQuestion}}">5<br>Strongly Agree</label>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="context-section">
                    <h3>Context Information</h3>

                    <div class="field">
                        <button class="collapsible" onclick="toggleCollapsible(event)">
                            Excerpt of Test Log (Click to expand)
                        </button>
                        <div class="json-content">
                            <pre>${{data.truncated_log_content}}</pre>
                        </div>
                    </div>

                    <div class="field">
                        <button class="collapsible" onclick="toggleCollapsible(event)">
                            Excerpt of Test Case (Click to expand)
                        </button>
                        <div class="json-content">
                            <pre>${{data.kb_test_case}}</pre>
                        </div>
                    </div>

                    <div class="field">
                        <button class="collapsible" onclick="toggleCollapsible(event)">
                            Excerpt of Requirements (Click to expand)
                        </button>
                        <div class="json-content">
                            <pre>${{data.kb_requirements}}</pre>
                        </div>
                    </div>
                </div>

                <div class="full-log-section">
                    <h3>Full Test Log</h3>

                    <div class="field">
                        <button class="collapsible" onclick="toggleLogCollapsible(event, ${{currentQuestion}})">
                            Full HTML Test Log (Click to expand)
                        </button>
                        <div class="xml-content" id="log_content_${{currentQuestion}}">
                            <iframe id="log_iframe_${{currentQuestion}}" style="width: 100%; height: 500px; border: none; background: white;"></iframe>
                        </div>
                    </div>
                </div>

                <div class="rating-section">
                    <h3>Additional Comments</h3>

                    <div style="margin-top: 20px;">
                        <strong>Comments (optional):</strong><br><br>
                        <textarea id="comments_${{currentQuestion}}"
                                  placeholder="Add any comments about the LogRoca output..."
                                  onchange="saveResponse()">${{response.comments || ''}}</textarea>
                    </div>
                </div>
            `;

            document.getElementById('questionContent').innerHTML = html;
            document.getElementById('questionNumber').textContent = `Question ${{currentQuestion + 1}} of ${{surveyData.length}}`;

            // Update navigation buttons
            document.getElementById('prevBtn').style.visibility = 'visible';
            document.getElementById('prevBtn').disabled = false; // Always enable to allow going back to demographics
            document.getElementById('prevBtn').textContent = currentQuestion === 0 ? '← Back to Demographics' : '← Previous';
            // Change Next button text on last question
            document.getElementById('nextBtn').textContent = currentQuestion === surveyData.length - 1 ? 'Continue to Conclusion →' : 'Next →';
            document.getElementById('nextBtn').disabled = false; // Never disable - last question goes to conclusion
        }}

        function toggleCollapsible(event) {{
            event.target.classList.toggle('active');
            const content = event.target.nextElementSibling;
            if (content.style.display === 'block') {{
                content.style.display = 'none';
            }} else {{
                content.style.display = 'block';
            }}
        }}

        function toggleLogCollapsible(event, questionIndex) {{
            event.target.classList.toggle('active');
            const content = event.target.nextElementSibling;

            if (content.style.display === 'block') {{
                content.style.display = 'none';
            }} else {{
                content.style.display = 'block';

                // Load HTML log file into iframe if not already loaded
                const iframe = document.getElementById(`log_iframe_${{questionIndex}}`);
                if (!iframe.src || iframe.src === 'about:blank') {{
                    const htmlLogPath = surveyData[questionIndex].full_html_log_path;
                    if (htmlLogPath) {{
                        iframe.src = htmlLogPath;
                    }}
                }}
            }}
        }}

        function saveResponse() {{
            const rootCauseRating = document.querySelector('input[name="root_cause_rating"]:checked');
            const rootCauseOriginRating = document.querySelector('input[name="root_cause_origin_rating"]:checked');
            const actionSuggestionsRating = document.querySelector('input[name="action_suggestions_rating"]:checked');
            const rationaleRating = document.querySelector('input[name="rationale_rating"]:checked');
            const comments = document.getElementById(`comments_${{currentQuestion}}`);

            responses[currentQuestion] = {{
                experiment_id: surveyData[currentQuestion].experiment_id,
                log_file_name: surveyData[currentQuestion].log_file_name,
                root_cause_rating: rootCauseRating ? rootCauseRating.value : '',
                root_cause_origin_rating: rootCauseOriginRating ? rootCauseOriginRating.value : '',
                action_suggestions_rating: actionSuggestionsRating ? actionSuggestionsRating.value : '',
                rationale_rating: rationaleRating ? rationaleRating.value : '',
                comments: comments ? comments.value : ''
            }};

            saveToLocalStorage();
            showAutoSaveIndicator();
            updateProgress();
        }}

        function nextQuestion() {{
            if (showingDemographic) {{
                const role = document.querySelector('input[name="role"]:checked');
                const experience = document.querySelector('input[name="experience"]:checked');
                const roleOthersText = document.getElementById('role_others_input');

                if (!role || !experience) {{
                    alert('Please answer both demographic questions before proceeding.');
                    return;
                }}

                // Validate "others" text field
                if (role.value === 'others' && (!roleOthersText || !roleOthersText.value.trim())) {{
                    alert('Please specify your role in the text field.');
                    return;
                }}

                showingDemographic = false;
                saveToLocalStorage();
                renderContent();
                window.scrollTo(0, 0);
                return;
            }}

            if (showingConclusion) {{
                // Validate required conclusion questions (q2-q3, q5 contact choice)
                const q2 = document.querySelector('input[name="conclusion_q2"]:checked');
                const q3 = document.querySelector('input[name="conclusion_q3"]:checked');
                const q5_contact = document.querySelector('input[name="conclusion_q5_contact"]:checked');
                const q5_email = document.getElementById('conclusion_q5_email');

                const missingQuestions = [];
                if (!q2) missingQuestions.push('Question 1: I trust the tool output');
                if (!q3) missingQuestions.push('Question 2: I would recommend the tool to my colleagues');
                if (!q5_contact) missingQuestions.push('Question 4: Contact permission (Yes/No)');

                // Validate email if "yes" was selected
                if (q5_contact && q5_contact.value === 'yes') {{
                    if (!q5_email || !q5_email.value.trim()) {{
                        missingQuestions.push('Question 4: Email address (required when you select "Yes")');
                    }}
                }}

                if (missingQuestions.length > 0) {{
                    alert('Please answer all required conclusion questions before completing the survey.\\n\\nMissing answers for:\\n- ' + missingQuestions.join('\\n- '));
                    return;
                }}

                // All required conclusion questions answered, allow submission
                alert('Thank you for completing all questions! You can now use the "Save Final Responses as CSV" button to export your responses.');
                return;
            }}

            // Check if all 4 Likert scales are answered
            const rootCauseRating = document.querySelector('input[name="root_cause_rating"]:checked');
            const rootCauseOriginRating = document.querySelector('input[name="root_cause_origin_rating"]:checked');
            const actionSuggestionsRating = document.querySelector('input[name="action_suggestions_rating"]:checked');
            const rationaleRating = document.querySelector('input[name="rationale_rating"]:checked');

            const missingRatings = [];
            if (!rootCauseRating) missingRatings.push('Root Cause');
            if (!rootCauseOriginRating) missingRatings.push('Root Cause Origin');
            if (!actionSuggestionsRating) missingRatings.push('Action Suggestions');
            if (!rationaleRating) missingRatings.push('Rationale');

            if (missingRatings.length > 0) {{
                alert('Please rate all LogRoca output fields before proceeding.\\n\\nMissing ratings for:\\n- ' + missingRatings.join('\\n- '));
                return;
            }}

            if (currentQuestion < surveyData.length - 1) {{
                currentQuestion++;
                renderQuestion();
                updateProgress();
                window.scrollTo(0, 0);
            }} else if (currentQuestion === surveyData.length - 1) {{
                // Last question completed, move to conclusion
                showingConclusion = true;
                saveToLocalStorage();
                renderContent();
                window.scrollTo(0, 0);
            }}
        }}

        function previousQuestion() {{
            if (showingConclusion) {{
                // Go back from conclusion to last question
                showingConclusion = false;
                currentQuestion = surveyData.length - 1;
                saveToLocalStorage();
                renderContent();
                updateProgress();
                window.scrollTo(0, 0);
                return;
            }}

            if (currentQuestion > 0) {{
                currentQuestion--;
                renderQuestion();
                updateProgress();
                window.scrollTo(0, 0);
            }} else if (currentQuestion === 0 && !showingDemographic) {{
                // Allow going back to demographic questions from first survey question
                showingDemographic = true;
                renderContent();
                updateProgress();
                window.scrollTo(0, 0);
            }}
        }}

        function updateProgress() {{
            const completed = Object.keys(responses).filter(k => {{
                const r = responses[k];
                return r.root_cause_rating && r.root_cause_origin_rating &&
                       r.action_suggestions_rating && r.rationale_rating;
            }}).length;
            const percentage = Math.round((completed / surveyData.length) * 100);

            const progressBar = document.getElementById('progressBar');
            progressBar.style.width = percentage + '%';
            progressBar.textContent = `${{completed}} / ${{surveyData.length}} (${{percentage}}%)`;
        }}

        function saveToLocalStorage() {{
            const data = {{
                rater_name: raterName,
                current_question: currentQuestion,
                responses: responses,
                demographic: demographicData,
                showing_demographic: showingDemographic,
                last_saved: new Date().toISOString()
            }};
            localStorage.setItem(storageKey, JSON.stringify(data));
        }}

        function loadFromLocalStorage() {{
            const saved = localStorage.getItem(storageKey);
            if (saved) {{
                const data = JSON.parse(saved);
                currentQuestion = data.current_question || 0;
                responses = data.responses || {{}};
                demographicData = data.demographic || {{}};
                showingDemographic = data.showing_demographic !== undefined ? data.showing_demographic : true;
            }}
        }}

        function showAutoSaveIndicator() {{
            const indicator = document.getElementById('autoSaveIndicator');
            indicator.classList.add('show');
            setTimeout(() => indicator.classList.remove('show'), 2000);
        }}

        function downloadProgress() {{
            const data = {{
                rater_name: raterName,
                total_rows: surveyData.length,
                completed: Object.keys(responses).filter(k => responses[k].makes_sense).length,
                last_saved: new Date().toISOString(),
                demographic: demographicData,
                responses: Object.values(responses)
            }};

            const blob = new Blob([JSON.stringify(data, null, 2)], {{type: 'application/json'}});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `survey_progress_${{raterName}}_${{new Date().toISOString().split('T')[0]}}.json`;
            a.click();
            URL.revokeObjectURL(url);
        }}

        function loadProgress(event) {{
            const file = event.target.files[0];
            if (!file) return;

            const reader = new FileReader();
            reader.onload = function(e) {{
                try {{
                    const data = JSON.parse(e.target.result);
                    if (data.responses) {{
                        // Convert array back to object indexed by question number
                        responses = {{}};
                        data.responses.forEach((resp, idx) => {{
                            // Find the matching question index
                            const qIdx = surveyData.findIndex(q =>
                                q.experiment_id === resp.experiment_id &&
                                q.log_file_name === resp.log_file_name
                            );
                            if (qIdx !== -1) {{
                                responses[qIdx] = resp;
                            }}
                        }});

                        // Load demographic data if present
                        if (data.demographic) {{
                            demographicData = data.demographic;
                            showingDemographic = false;
                        }}

                        saveToLocalStorage();
                        renderContent();
                        updateProgress();
                        alert('Progress loaded successfully!');
                    }}
                }} catch (error) {{
                    alert('Error loading file: ' + error.message);
                }}
            }};
            reader.readAsText(file);
        }}

        function submitSurvey() {{
            const completed = Object.keys(responses).filter(k => {{
                const r = responses[k];
                return r.root_cause_rating && r.root_cause_origin_rating &&
                       r.action_suggestions_rating && r.rationale_rating;
            }}).length;

            if (!demographicData.role || !demographicData.experience || !demographicData.department || !demographicData.tcms_experience) {{
                alert('Please complete all demographic information before submitting.');
                showingDemographic = true;
                renderContent();
                return;
            }}

            if (completed < surveyData.length) {{
                const proceed = confirm(
                    `You have completed ${{completed}} out of ${{surveyData.length}} questions. ` +
                    `Are you sure you want to submit?`
                );
                if (!proceed) return;
            }}

            // Generate CSV with new format including conclusion questions
            const csvRows = [];
            csvRows.push('experiment_id,log_file_name,root_cause_rating,root_cause_origin_rating,action_suggestions_rating,rationale_rating,comments,rater_name,rater_role,rater_experience,rater_department,rater_tcms_experience,conclusion_trust,conclusion_recommendation,conclusion_q4_improvement_comment,conclusion_q5_contact_consent,conclusion_q5_email,timestamp');

            surveyData.forEach((item, idx) => {{
                const resp = responses[idx] || {{}};
                const row = [
                    `"${{item.experiment_id}}"`,
                    `"${{item.log_file_name}}"`,
                    `"${{resp.root_cause_rating || ''}}"`,
                    `"${{resp.root_cause_origin_rating || ''}}"`,
                    `"${{resp.action_suggestions_rating || ''}}"`,
                    `"${{resp.rationale_rating || ''}}"`,
                    `"${{(resp.comments || '').replace(/"/g, '""')}}"`,
                    `"${{raterName}}"`,
                    `"${{demographicData.role || ''}}"`,
                    `"${{demographicData.experience || ''}}"`,
                    `"${{demographicData.department || ''}}"`,
                    `"${{demographicData.tcms_experience || ''}}"`,
                    `"${{conclusionData.q2 || ''}}"`,
                    `"${{conclusionData.q3 || ''}}"`,
                    `"${{(conclusionData.q4 || '').replace(/"/g, '""')}}"`,
                    `"${{conclusionData.q5_contact || ''}}"`,
                    `"${{(conclusionData.q5_email || '').replace(/"/g, '""')}}"`,
                    `"${{new Date().toISOString()}}"`
                ];
                csvRows.push(row.join(','));
            }});

            const csv = csvRows.join('\\n');
            const blob = new Blob([csv], {{type: 'text/csv'}});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `survey_responses_${{raterName.toLowerCase()}}.csv`;
            a.click();
            URL.revokeObjectURL(url);

            alert('Survey responses downloaded! Please upload the CSV file to the shared folder.');
        }}
    </script>
</body>
</html>'''

    # Write to file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"✓ Generated {output_file} ({len(data_rows)} questions)")


def create_survey_package(survey_html_file, package_name, data_rows):
    """
    Create a ZIP package containing the survey HTML and all required log files.

    Args:
        survey_html_file: Path to the generated survey HTML file
        package_name: Name for the ZIP file (without extension)
        data_rows: DataFrame rows containing the survey data (to extract log file names)
    """
    zip_path = Path(__file__).parent / f"{package_name}.zip"
    logs_dir = Path(__file__).parent / "html_logs"

    # Collect all required log files
    required_logs = set()
    for idx, row in data_rows.iterrows():
        log_file_name = row['log_file_name']
        html_log_name = log_file_name.replace('.json', '.html')
        required_logs.add(html_log_name)

    print(f"  Creating ZIP package: {zip_path.name}")
    print(f"  Including {len(required_logs)} log files...")

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add the survey HTML file (at root level)
        zipf.write(survey_html_file, survey_html_file.name)

        # Add all required log files (in logs/ folder)
        for log_file in required_logs:
            log_path = logs_dir / log_file
            if log_path.exists():
                zipf.write(log_path, f"logs/{log_file}")
            else:
                print(f"  Warning: Log file not found: {log_file}")

    print(f"  ✓ Created {zip_path.name} ({zip_path.stat().st_size / 1024 / 1024:.2f} MB)")


def main():
    # Load the survey data
    # TODO: replace with actual experiments results data
    data_file = Path(__file__).parent / "survey_data_dummy.csv"

    if not data_file.exists():
        print(f"ERROR: {data_file} not found!")
        print("Please run the export cell in survey_preparation.ipynb first.")
        return

    df = pd.read_csv(data_file)
    print(f"Loaded {len(df)} rows from {data_file}")

    # Define rater assignments

    rater_1_items = df.iloc[0:6]  # 6 items
    rater_2_items = df.iloc[2:8]  # 6 items
    rater_3_items = df.iloc[4:10]  # 6 items
    rater_4_items = df.iloc[6:12]  # 6 items
    rater_5_items = df.iloc[8:14]  # 6 items
    rater_6_items = df.iloc[10:16]  # 6 items
    rater_7_items = df.iloc[12:18]  # 6 items
    rater_8_items = df.iloc[14:20]  # 6 items
    rater_9_items = pd.concat([df.iloc[16:20], df.iloc[0:2]])  # 6 items
    rater_10_items = pd.concat([df.iloc[18:20], df.iloc[0:4]])  # 6 items
    rater_11_items = df.iloc[1:7]  # 6 items

    assignments = [
        ("Rater_1", rater_1_items, "survey_rater_1.html"),
        ("Rater_2", rater_2_items, "survey_rater_2.html"),
        ("Rater_3", rater_3_items, "survey_rater_3.html"),
        ("Rater_4", rater_4_items, "survey_rater_4.html"),
        ("Rater_5", rater_5_items, "survey_rater_5.html"),
        ("Rater_6", rater_6_items, "survey_rater_6.html"),
        ("Rater_7", rater_7_items, "survey_rater_7.html"),
        ("Rater_8", rater_8_items, "survey_rater_8.html"),
        ("Rater_9", rater_9_items, "survey_rater_9.html"),
        ("Rater_10", rater_10_items, "survey_rater_10.html"),
        ("Rater_11", rater_11_items, "survey_rater_11.html"),
    ]

    # Print assignment summary
    print("\n=== Rater Assignment Summary ===")
    coverage = {i: 0 for i in range(len(df))}
    for rater_name, data_rows, _ in assignments:
        indices = data_rows.index.tolist()
        print(f"{rater_name}: Items {[i for i in indices]}")
        for idx in indices:
            coverage[idx] += 1
    
    print("\n=== Coverage Analysis ===")
    print(f"Each rater evaluates: 6 items")
    print(f"Total ratings: {15 * 6} = 90")
    print(f"Average ratings per item: {sum(coverage.values()) / len(coverage):.1f}")
    print(f"Min ratings per item: {min(coverage.values())}")
    print(f"Max ratings per item: {max(coverage.values())}")
    print("\nItem coverage:")
    for item_idx, count in coverage.items():
        print(f"  Item {item_idx}: rated {count} times") 

    # Generate HTML files and ZIP packages
    output_dir = Path(__file__).parent
    for rater_name, data_rows, filename in assignments:
        output_file = output_dir / filename
        generate_html_survey(data_rows, rater_name, output_file)

        # Create ZIP package for distribution
        package_name = filename.replace('.html', '')
        create_survey_package(output_file, package_name, data_rows)

    print("All survey files and ZIP packages generated successfully!")


if __name__ == "__main__":
    main()
