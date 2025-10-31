# -*- coding: utf-8 -*-
#
# Postman to PyMan Converter
# Author: Huberto Gastal Mayer (with AI help)
# License: GPLv3
# Project: PyMan - A CLI tool for executing HTTP request collections defined in YAML
#
# This script converts a Postman v2.1 collection (JSON)
# into the PyMan directory and YAML file structure.
#

import json
import os
import re
import argparse
import sys
import logging
import yaml # Required for the custom dumper

def slugify(text):
    """
    Converts a folder or request name (e.g., "Get All Users")
    into a safe filename (e.g., "get-all-users").
    """
    if not text:
        return 'item'
    text = str(text)
    text = text.lower()
    text = re.sub(r'\s+', '-', text) # Replaces spaces with hyphens
    text = re.sub(r'[^a-z0-9\-_]', '', text) # Removes non-alphanumeric characters
    text = re.sub(r'-+', '-', text) # Removes duplicate hyphens
    text = text.strip('-')
    if not text:
        text = 'request' # Ensures it's not empty
    return text

def convert_js_to_py(script_lines):
    """
    Tries a very basic conversion of Postman JS to Python.
    Complex scripts will just be commented out.
    """
    py_lines = []
    converted_simple = False
    
    # Simple conversion patterns
    patterns = {
        r'pm\.environment\.set\("([^"]+)",\s*"([^"]+)"\);?': r'environment_vars["\1"] = "\2"',
        r"pm\.environment\.set\('([^']+)',\s*'([^']+)'\);?": r"environment_vars['\1'] = '\2'",
        r'pm\.environment\.set\("([^"]+)",\s*([^)]+)\);?': r'environment_vars["\1"] = \2', # For pm.environment.set("id", 123)
        r'console\.log\((.*)\);?': r'log.info(f"PM_LOG: {\1}")' # Converts console.log
    }

    # Tries simple line-by-line conversion
    for line in script_lines:
        original_line = line
        converted = False
        for js_regex, py_template in patterns.items():
            if re.match(js_regex, line.strip()):
                py_lines.append(re.sub(js_regex, py_template, line.strip()))
                converted_simple = True
                converted = True
                break
        if not converted:
            py_lines.append(original_line) # Keeps the original line if no conversion is found
            
    # If we made any conversions, return the script.
    # If we couldn't convert ANYTHING, comment everything out.
    if converted_simple and all(
        any(re.match(js_regex, l.strip()) for js_regex in patterns) or not l.strip() 
        for l in script_lines if l.strip()
    ):
        return "\n".join(py_lines)

    # If it's complex, comment it all out and add a TODO
    todo_comment = (
        '"""\n'
        'TODO: THE SCRIPT BELOW REQUIRES MANUAL CONVERSION FROM JAVASCRIPT (POSTMAN) TO PYTHON (PYMAN)\n'
        '\n'
        '--- START OF ORIGINAL JAVASCRIPT CODE ---\n'
    )
    js_code = "\n".join(script_lines)
    end_comment = (
        '\n--- END OF ORIGINAL JAVASCRIPT CODE ---\n'
        '"""\n'
        '# Conversion example:\n'
        '# JS: pm.environment.set("var_name", "value");\n'
        '# PY: environment_vars["var_name"] = "value"\n'
        '\n'
        '# JS: pm.test("Status code is 200", () => { pm.response.to.have.status(200); });\n'
        '# PY: pm.test("Status code is 200", lambda: assert response.status_code == 200)\n'
    )
    
    return f"{todo_comment}{js_code}{end_comment}"

def process_environment_file(environment_filepath, output_pyman_env_path, log):
    """
    Parses a Postman environment JSON file and writes it to the
    .environment-variables format.
    """
    if not environment_filepath:
        log.info("No environment file provided, creating empty .environment-variables.")
        with open(output_pyman_env_path, 'w', encoding='utf-8') as f:
            f.write("# TODO: Add your environment variables here.\n")
            f.write("# Ex: BASE_URL=\"https://api.example.com\"\n")
        return

    if not os.path.exists(environment_filepath):
        log.error(f"Error: Environment file not found: {environment_filepath}")
        log.warning("Creating an empty .environment-variables file instead.")
        process_environment_file(None, output_pyman_env_path, log) # Call recursively to create empty file
        return

    log.info(f"Processing Postman environment file: {environment_filepath}")
    
    try:
        with open(environment_filepath, 'r', encoding='utf-8') as f:
            env_data = json.load(f)
    except json.JSONDecodeError:
        log.error("Error: The environment file is not valid JSON.")
        sys.exit(1)
    except Exception as e:
        log.error(f"Error reading environment file: {e}")
        sys.exit(1)

    variables = env_data.get('values', [])
    if not variables and 'name' in env_data:
        log.warning("Warning: Environment file does not seem to contain a 'values' key. It might be an invalid format.")
        log.warning("Creating an empty .environment-variables file.")
        process_environment_file(None, output_pyman_env_path, log) # Call recursively to create empty file
        return
        
    count = 0
    with open(output_pyman_env_path, 'w', encoding='utf-8') as f:
        f.write(f"# Imported from {env_data.get('name', 'Postman Environment')}\n")
        f.write(f"# Source: {os.path.basename(environment_filepath)}\n\n")
        
        for var in variables:
            # Only import enabled variables
            if var.get('enabled', True) and var.get('key'):
                key = var.get('key')
                value = var.get('value', '')
                
                # Add quotes to values to handle spaces and special chars, mimicking pyman's format
                f.write(f'{key}="{value}"\n')
                count += 1
                
    log.info(f"Successfully imported {count} enabled variables to {output_pyman_env_path}.")


def process_item(item, current_path, log, folder_counter, request_counter, should_number_folders, should_number_files):
    """
    Processes a single item (folder or request) from the Postman collection.
    Returns the updated folder_counter and request_counter.
    """
    name = item.get('name', 'untitled')
    
    # It's a Folder
    if 'item' in item:
        if should_number_folders:
            folder_counter += 10
            formatted_folder_idx = f"{folder_counter:03d}-"
            folder_name = formatted_folder_idx + slugify(name)
        else:
            folder_name = slugify(name)

        folder_path = os.path.join(current_path, folder_name)
        log.info(f"Creating directory: {folder_path}")
        os.makedirs(folder_path, exist_ok=True)
        
        # Write the folder's config.yaml
        config_data = {'FOLDER_NAME': name}
        config_path = os.path.join(folder_path, 'config.yaml')
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            
        # Process items inside the folder, resetting counters for the new level
        sub_folder_counter = 0
        sub_request_counter = 0
        for sub_item in item['item']:
            # Recursively call process_item, passing the current sub-counters
            # and updating them based on the return value.
            sub_folder_counter, sub_request_counter = process_item(
                sub_item, folder_path, log, sub_folder_counter, sub_request_counter, should_number_folders, should_number_files
            )
        return folder_counter, request_counter # Return the counters for the current level

    # It's a Request
    elif 'request' in item:
        if should_number_files:
            request_counter += 10
            formatted_request_idx = f"{request_counter:03d}-"
            req_name = formatted_request_idx + slugify(name)
        else:
            req_name = slugify(name)

        req_filename = f"{req_name}.yaml"
        req_filepath = os.path.join(current_path, req_filename)
        log.info(f"Creating request file: {req_filepath}")
        
        req = item['request']
        pyman_req = {} # Dictionary for the YAML
        
        # 1. Request (Method and URL)
        pyman_req['request'] = {
            'method': req.get('method', 'GET'),
            'url': req.get('url', {}).get('raw', '')
        }
        
        # 2. Params (Query Params)
        query_params = req.get('url', {}).get('query', [])
        if query_params:
            pyman_req['params'] = {param['key']: param['value'] for param in query_params if not param.get('disabled')}

        # 3. Authentication
        auth = req.get('auth', {})
        if auth:
            auth_type = auth.get('type')
            if auth_type == 'bearer':
                pyman_req['authentication'] = {'bearer_token': auth['bearer'][0]['value']}
            elif auth_type == 'basic':
                pyman_req['authentication'] = {
                    'basic_auth': {
                        'username': next((p['value'] for p in auth['basic'] if p['key'] == 'username'), ''),
                        'password': next((p['value'] for p in auth['basic'] if p['key'] == 'password'), '')
                    }
                }
            else:
                pyman_req['authentication'] = {'TODO': f"Authentication type '{auth_type}' not supported. Configure manually."}

        # 4. Headers
        headers = req.get('header', [])
        if headers:
            pyman_req['headers'] = {h['key']: h['value'] for h in headers if not h.get('disabled')}

        # 5. Body
        body = req.get('body', {})
        if body and 'mode' in body:
            mode = body['mode']
            if mode == 'raw':
                raw_body = body.get('raw', '')
                if raw_body: # Only process if not empty
                    try:
                        json_data = json.loads(raw_body)
                        pretty_json_string = json.dumps(json_data, indent=2, ensure_ascii=False)
                        pyman_req['body'] = pretty_json_string
                    except json.JSONDecodeError:
                        pyman_req['body'] = raw_body
                else:
                    pyman_req['body'] = '' # Empty body
            
            elif mode == 'urlencoded':
                pyman_req['body'] = {p['key']: p['value'] for p in body['urlencoded'] if not p.get('disabled')}
                if 'headers' not in pyman_req: pyman_req['headers'] = {}
                pyman_req['headers']['Content-Type'] = 'application/x-www-form-urlencoded'
            
            elif mode == 'formdata':
                pyman_req['body'] = {}
                for p in body['formdata']:
                    if p.get('disabled'):
                        continue
                    if p.get('type') == 'file':
                        pyman_req['body'][p['key']] = {'type': 'file', 'src': p.get('src', 'TODO_SPECIFY_FILE_PATH')}
                    else:
                        pyman_req['body'][p['key']] = p.get('value', '')
            
            elif mode == 'file':
                 pyman_req['body'] = {'file_part': {'type': 'file', 'src': body.get('file', {}).get('src', 'TODO_SPECIFY_FILE_PATH')}}

        # Save the request YAML file
        with open(req_filepath, 'w', encoding='utf-8') as f:
            yaml.dump(pyman_req, f, Dumper=ForceLiteralDumper, allow_unicode=True, default_flow_style=False, sort_keys=False)

        # 6. Scripts (Pre-request and Test)
        events = item.get('event', [])
        for event in events:
            script_type = event.get('listen')
            script_code = event.get('script', {}).get('exec', [])
            
            if not script_code:
                continue
                
            py_code = convert_js_to_py(script_code)
            
            if script_type == 'prerequest':
                script_filename = f"{req_name}-pre-script.py"
            elif script_type == 'test':
                script_filename = f"{req_name}-pos-script.py"
            else:
                continue
                
            script_filepath = os.path.join(current_path, script_filename)
            log.info(f"Creating script (for manual conversion): {script_filepath}")
            with open(script_filepath, 'w', encoding='utf-8') as f:
                f.write("#!/usr/bin/env python\n")
                f.write("# -*- coding: utf-8 -*-\n\n")
                f.write(py_code)
        return folder_counter, request_counter # Return the counters for the current level
    
    # If it's neither a folder nor a request, just return the counters unchanged
    return folder_counter, request_counter

# --- Custom YAML Dumper ---
# This class tells PyYAML to ALWAYS use the '|' (literal) style
# for strings containing newlines.
class ForceLiteralDumper(yaml.SafeDumper):
    def represent_scalar(self, tag, value, style=None):
        if '\n' in value:
            style = '|'
        return super().represent_scalar(tag, value, style)

def main():
    """
    Main function to run the importer.
    """
    # Basic logging configuration for the console
    log = logging.getLogger('postman_importer')
    log.setLevel(logging.INFO)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    
    # Avoids adding duplicate handlers if the script is called multiple times
    if not log.hasHandlers():
        log.addHandler(console_handler)

    parser = argparse.ArgumentParser(description="Converts a Postman v2.1 JSON collection to the PyMan YAML structure.")
    parser.add_argument("-c", "--collection", help="Path to the Postman .json collection file.", required=True)
    parser.add_argument("-o", "--output", help="Output directory name for the PyMan collection.", required=True)
    parser.add_argument("-e", "--environment", help="Path to the Postman environment .json file (optional).", required=False, default=None)
    parser.add_argument(
        "--numbered", 
        choices=['yes', 'no'], 
        default='yes', 
        help="Whether to add numbering to folders and files (default: yes)."
    )
    parser.add_argument(
        "--numbered-folders", 
        choices=['yes', 'no'], 
        default=None, 
        help="Whether to add numbering to folders (overrides --numbered)."
    )
    parser.add_argument(
        "--numbered-files", 
        choices=['yes', 'no'], 
        default=None, 
        help="Whether to add numbering to files (overrides --numbered)."
    )

    args = parser.parse_args()

    # Determine numbering preferences with precedence
    should_number_folders = (args.numbered_folders == 'yes') if args.numbered_folders is not None else (args.numbered == 'yes')
    should_number_files = (args.numbered_files == 'yes') if args.numbered_files is not None else (args.numbered == 'yes')

    # Check if the input file exists
    if not os.path.exists(args.collection):
        log.error(f"Input file not found: {args.collection}")
        sys.exit(1)

    # Create the output directory
    output_path = os.path.abspath(args.output)
    if os.path.exists(output_path):
        log.warning(f"The output directory '{output_path}' already exists. Files may be overwritten.")
    else:
        os.makedirs(output_path, exist_ok=True)

    log.info(f"Starting conversion from {args.collection} to {output_path}...")

    # Load the Postman JSON
    try:
        with open(args.collection, 'r', encoding='utf-8') as f:
            collection = json.load(f)
    except json.JSONDecodeError:
        log.error("Error: The input file is not valid JSON.")
        sys.exit(1)
    except Exception as e:
        log.error(f"Error reading input file: {e}")
        sys.exit(1)

    # Basic validation
    info = collection.get('info', {})
    if not info or info.get('schema', '').find('v2.1.0') == -1:
        log.warning("This script is designed for Postman v2.1.0 collections. Conversion might be unstable.")

    # Process .environment-variables
    env_path = os.path.join(output_path, '.environment-variables')
    process_environment_file(args.environment, env_path, log)

    # Process collection-level scripts
    events = collection.get('event', [])
    for event in events:
        script_type = event.get('listen')
        script_code = event.get('script', {}).get('exec', [])
        
        if not script_code:
            continue
            
        py_code = convert_js_to_py(script_code)
        
        if script_type == 'prerequest':
            script_filename = "collection-pre-script.py"
        elif script_type == 'test':
            script_filename = "collection-pos-script.py"
        else:
            continue
            
        script_filepath = os.path.join(output_path, script_filename)
        log.info(f"Creating collection script (for manual conversion): {script_filepath}")
        with open(script_filepath, 'w', encoding='utf-8') as f:
            f.write("#!/usr/bin/env python\n")
            f.write("# -*- coding: utf-8 -*-\n\n")
            f.write(py_code)

    # Start recursive processing of items
    items = collection.get('item', [])
    
    top_level_folder_counter = 0
    top_level_request_counter = 0
    
    for item in items:
        # process_item now returns the updated counters
        top_level_folder_counter, top_level_request_counter = process_item(
            item, output_path, log, 
            top_level_folder_counter, top_level_request_counter,
            should_number_folders, should_number_files
        )

    log.info("Conversion completed successfully!")

if __name__ == "__main__":
    main()