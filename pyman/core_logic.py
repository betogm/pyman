# -*- coding: utf-8 -*-
#
# PyMan - Python HTTP Request Executor
# Author: Huberto Gastal Mayer (hubertogm@gmail.com)
# License: GPLv3 (https://www.gnu.org/licenses/gpl-3.0.html)
# Project: PyMan - A CLI tool for executing HTTP request collections defined in YAML
#

import logging
import os
import re
import sys
import requests
import yaml
from datetime import datetime
from urllib.parse import urlencode
from request_parser import parse_request_file

# --- Logging Setup ---

def setup_logging(collection_root):
    """
    Configures logging to console and file.
    Creates the 'logs' directory if it doesn't exist.
    """
    log_dir = os.path.join(collection_root, 'logs')
    if not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir)
        except OSError as e:
            print(f"Error creating log directory {log_dir}: {e}")
            sys.exit(1)

    # Log format
    log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # Log file name with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f'run_{timestamp}.log')

    log = logging.getLogger('pyman')
    log.setLevel(logging.DEBUG)

    # File handler
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(logging.DEBUG)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)
    console_handler.setLevel(logging.INFO) # Shows INFO and above on the console

    # Add handlers
    if not log.hasHandlers():
        log.addHandler(console_handler)
        log.addHandler(file_handler)
    
    return log

# --- Configuration Loading ---

def load_environment(collection_root):
    """
    Loads the .environment-variables file from the collection root.
    """
    env = {}
    env_file = os.path.join(collection_root, '.environment-variables')
    if not os.path.exists(env_file):
        return env

    try:
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env[key.strip()] = value.strip().strip('"\'') # Remove quotes
    except Exception as e:
        print(f"Error loading .environment-variables: {e}")
    
    return env

def load_folder_config(folder_path):
    """
    Loads the config.yaml file from a subdirectory.
    """
    config = {}
    config_file_yaml = os.path.join(folder_path, 'config.yaml')
    config_file_yml = os.path.join(folder_path, 'config.yml')

    config_file_to_load = None
    if os.path.exists(config_file_yaml):
        config_file_to_load = config_file_yaml
    elif os.path.exists(config_file_yml):
        config_file_to_load = config_file_yml
    else:
        return config # Returns an empty dict if no config file is found
        
    try:
        with open(config_file_to_load, 'r', encoding='utf-8') as f:
            loaded_config = yaml.safe_load(f)
            if isinstance(loaded_config, dict):
                config = loaded_config
            else:
                logging.getLogger('pyman').warning(f"Configuration file {config_file_to_load} does not contain a YAML dictionary.")

    except yaml.YAMLError as e:
        print(f"YAML syntax error in {config_file_to_load}: {e}")
    except Exception as e:
        print(f"Error loading {config_file_to_load}: {e}")
    
    return config

# --- Script Execution (Pre/Post) ---

def execute_script(script_path, env, pm, response=None):
    """
    Executes a Python script (pre or post) if it exists.
    Injects 'env', 'pm', and 'response' (if available) into the script's global scope.
    """
    log = logging.getLogger('pyman')
    if not os.path.exists(script_path):
        log.debug(f"Script not found, skipping: {script_path}")
        return

    log.info(f"Executing script: {script_path}")
    
    script_globals = {
        'env': env,
        'pm': pm,
        'response': response # Will be None for pre-scripts
    }
    
    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            script_code = f.read()
        
        # Compiles and executes the code in the defined scope
        exec(compile(script_code, script_path, 'exec'), script_globals)
        
    except Exception as e:
        log.error(f"Error executing script {script_path}: {e}", exc_info=True)
        # Allows execution to continue, but logs the error

# --- Substitution Logic ---

def substitute_variables(text, env, pm):
    """
    Substitutes {{var_name}} and {{pm.helper()}} variables in a string.
    """
    if not isinstance(text, str):
        return text

    # Pattern 1: {{var_name}} (environment variables)
    def replacer_env(match):
        var_name = match.group(1).strip()
        return str(env.get(var_name, match.group(0))) # Returns the original if not found

    text = re.sub(r'\{\{\s*([a-zA-Z0-9_]+)\s*\}\}', replacer_env, text)

    # Pattern 2: {{pm.helper(...)}} (helper functions)
    def replacer_pm(match):
        func_call_str = match.group(1).strip() # Ex: "pm.random_int(1, 10)"
        try:
            # Evaluates the expression 'pm.random_int(1, 10)'
            # 'pm' is the imported module
            result = eval(func_call_str, {'pm': pm})
            return str(result)
        except Exception as e:
            logging.getLogger('pyman').warning(f"Error evaluating helper '{{{{{func_call_str}}}}}': {e}")
            return match.group(0) # Returns the original if it fails

    text = re.sub(r'\{\{\s*(pm\.[a-zA-Z0-9_.]+\(.*\))\s*\}\}', replacer_pm, text)
    
    return text

# --- Request Execution ---

def execute_request(request_file_path, env, pm):
    """
    Parses, prepares, and executes a single HTTP request.
    """
    log = logging.getLogger('pyman')
    log.info("-" * 50)
    log.info(f"Executing request: {request_file_path}")
    request_dir = os.path.dirname(request_file_path) # For relative file paths

    try:
        parsed_request = parse_request_file(request_file_path)
    except Exception as e:
        log.error(f"Failed to parse file {request_file_path}: {e}", exc_info=True)
        return None

    # --- 1. Substitute variables (except in the body, which is handled later) ---
    try:
        url = substitute_variables(parsed_request['url'], env, pm)
        method = parsed_request['method'].upper()

        params = {}
        for k, v in parsed_request['params'].items():
            params[substitute_variables(k, env, pm)] = substitute_variables(v, env, pm)

        if params:
            query_string = urlencode(params)
            if '?' not in url:
                url += '?'
            elif not url.endswith('&'):
                url += '&'
            url += query_string
        
        headers = {}
        for k, v in parsed_request['headers'].items():
            headers[substitute_variables(k, env, pm)] = substitute_variables(v, env, pm)
            
        auth = {}
        for k, v in parsed_request['auth'].items():
            auth[k] = substitute_variables(v, env, pm)

        body = parsed_request['body'] # Gets the body (can be str, dict, or None)

    except Exception as e:
        log.error(f"Error substituting variables (URL/Headers/Auth): {e}", exc_info=True)
        return None

    # --- 2. Prepare Payloads (data, files) and Headers ---
    data_payload = None   # For 'data=' (raw, urlencoded)
    files_payload = None  # For 'files=' (multipart)
    auth_tuple = None     # For 'auth=' (basic auth)
    
    # Check if it is multipart
    content_type = headers.get('Content-Type', '')
    is_multipart = 'multipart/form-data' in content_type

    if isinstance(body, str):
        # Body is 'raw' (JSON, XML, etc.)
        data_payload = substitute_variables(body, env, pm).encode('utf-8')
        
    elif isinstance(body, dict):
        if is_multipart and method in ('POST', 'PUT', 'PATCH'):
            # Body is multipart/form-data
            log.info("Processing body as multipart/form-data")
            data_fields = {}  # Text fields
            file_fields = {}  # File fields

            for key, value in body.items():
                if isinstance(value, dict) and value.get('type') == 'file':
                    # It's a file
                    src = value.get('src')
                    if not src:
                        log.warning(f"File field '{key}' has no 'src'. Skipping.")
                        continue
                    
                    src_subbed = substitute_variables(src, env, pm)
                    
                    # Allows absolute or relative paths to the .yaml file
                    file_path = src_subbed if os.path.isabs(src_subbed) else os.path.join(request_dir, src_subbed)
                    
                    if not os.path.exists(file_path):
                        log.error(f"File not found for '{key}': {file_path}")
                        continue # Skip this file
                    
                    try:
                        file_name = os.path.basename(file_path)
                        # 'rb' is crucial for files
                        file_fields[key] = (file_name, open(file_path, 'rb'), 'application/octet-stream') # Add generic MIME type
                        log.info(f"Attaching file: '{key}' -> {file_path}")
                    except Exception as e:
                        log.error(f"Could not open file '{file_path}': {e}")
                else:
                    # It's a normal form field
                    data_fields[key] = substitute_variables(str(value), env, pm)
            
            data_payload = data_fields   # 'requests' uses 'data' for text fields in multipart
            files_payload = file_fields # 'requests' uses 'files' for files
            
            # Let 'requests' set the Content-Type and boundary
            if 'Content-Type' in headers:
                log.debug("Removing 'Content-Type' header; 'requests' will handle the boundary.")
                del headers['Content-Type']
                
        else:
            # Body is a dict, but not multipart (assume x-www-form-urlencoded)
            # 'requests' sends this as 'application/x-www-form-urlencoded' by default
            data_payload = {k: substitute_variables(str(v), env, pm) for k, v in body.items()}

    # --- 3. Authentication ---
    if 'Bearer Token' in auth:
        headers['Authorization'] = f"Bearer {auth['Bearer Token']}"
        log.debug("Applying Bearer Token authentication")
        
    elif 'Basic Auth' in auth:
        # 'requests' handles Base64 encoding
        auth_tuple = (
            substitute_variables(auth.get('Basic Auth', {}).get('username'), env, pm), 
            substitute_variables(auth.get('Basic Auth', {}).get('password'), env, pm)
        )
        log.debug("Applying Basic Auth authentication")

    # --- 4. Make the request ---
    response = None
    try:
        log.info(f"Dispatching {method} to: {url}")
        log.debug(f"HEADERS: {headers}")
        if data_payload:
            log.debug(f"DATA: {data_payload}")
        if files_payload:
            log.debug(f"FILES: {list(files_payload.keys())}")


        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            data=data_payload,    # Used for raw, urlencoded, and multipart text fields
            files=files_payload,   # Used for multipart files
            auth=auth_tuple,       # Used for Basic Auth
            timeout=60             # 60-second timeout
        )

        log.info(f"STATUS: {response.status_code}")
        log.debug(f"HEADERS (Response): {response.headers}")
        
    except requests.exceptions.RequestException as e:
        log.error(f"Error in request: {e}")
        return None # Returns None if the request fails
    finally:
        # --- 5. Cleanup (Close open files) ---
        if files_payload:
            log.debug(f"Closing {len(files_payload)} files.")
            for _, file_tuple in files_payload.items():
                # file_tuple = (filename, file_object, mimetype)
                file_tuple[1].close() # file_tuple[1] is the 'open()' object

    return response

# --- Main Execution Loop ---

def run_collection(target_path, collection_root, request_files_to_run, log, pm):
    """
    The main loop that orchestrates the execution of the collection and scripts.
    """
    log.info(f"Starting execution. Collection root: {collection_root}")
    log.info(f"Target: {target_path}")

    # 1. Load global environment
    try:
        env = load_environment(collection_root)
        log.info(f"Global environment variables loaded: {len(env)} keys.")
    except Exception as e:
        log.error(f"Critical failure loading environment: {e}")
        return

    # 2. Define collection script paths
    collection_pre_script = os.path.join(collection_root, 'collection-pre-script.py')
    collection_pos_script = os.path.join(collection_root, 'collection-pos-script.py')

    # 3. Iterate over request files
    summary = {'total': len(request_files_to_run), 'success': 0, 'failure': 0}

    for req_file in request_files_to_run:
        req_name = os.path.basename(req_file)
        req_base_name = os.path.splitext(req_name)[0]
        req_dir = os.path.dirname(req_file)

        # Define request script paths
        req_pre_script = os.path.join(req_dir, f"{req_base_name}-pre-script.py")
        req_pos_script = os.path.join(req_dir, f"{req_base_name}-pos-script.py")

        try:
            # --- EXECUTION ORDER ---

            # 1. Collection Pre-script
            execute_script(collection_pre_script, env, pm)
            
            # 2. Request Pre-script
            execute_script(req_pre_script, env, pm)

            # 3. The Request
            response = execute_request(req_file, env, pm)

            # 4. Request Post-script
            # Passes the 'response', even if it is None (in case of failure)
            execute_script(req_pos_script, env, pm, response=response)

            # 5. Collection Post-script
            execute_script(collection_pos_script, env, pm, response=response)

            # --- End of Order ---

            if response is not None and response.status_code < 400:
                summary['success'] += 1
            else:
                summary['failure'] += 1

        except Exception as e:
            log.error(f"Unexpected error during the cycle of {req_name}: {e}", exc_info=True)
            summary['failure'] += 1

    # --- End of Loop ---
    log.info("-" * 50)
    log.info("Execution finished.")
    log.info(f"Summary: {summary['total']} total, {summary['success']} success, {summary['failure']} failure.")
    log.info("-" * 50)