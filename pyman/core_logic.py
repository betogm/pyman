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

def write_environment_file(collection_root, environment_vars):
    """
    Writes the environment dictionary back to the .environment-variables file.
    """
    log = logging.getLogger('pyman')
    env_file = os.path.join(collection_root, '.environment-variables')
    try:
        with open(env_file, 'w', encoding='utf-8') as f:
            for key, value in environment_vars.items():
                f.write(f'{key}="{value}"\n')
        log.debug(f"Environment variables successfully written to {env_file}")
    except Exception as e:
        log.error(f"Error writing to .environment-variables file: {e}")

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

def execute_script(script_path, environment_vars, pm, log, response=None):
    """
    Executes a Python script (pre or post) if it exists.
    Injects 'environment_vars', 'pm', 'log', and 'response' (if available) into the script's global scope.
    """
    if not os.path.exists(script_path):
        log.debug(f"Script not found, skipping: {script_path}")
        return

    log.info(f"Executing script: {script_path}")
    
    # Deep copy to detect changes
    before_env = environment_vars.copy()

    script_globals = {
        'environment_vars': environment_vars,
        'pm': pm,
        'log': log,
        'response': response # Will be None for pre-scripts
    }
    
    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            script_code = f.read()
        
        exec(compile(script_code, script_path, 'exec'), script_globals)

        # Check for changes and return a flag
        if environment_vars != before_env:
            log.info("Environment variables were modified by the script.")
            return True # Indicates changes were made

    except Exception as e:
        log.error(f"Error executing script {script_path}: {e}")

    return False # No changes made

# --- Substitution Logic ---

def substitute_variables(text, environment_vars, pm):
    """
    Substitutes {{var_name}} and {{pm.helper()}} variables in a string.
    """
    if not isinstance(text, str):
        return text

    # Pattern 1: {{var_name}} (environment variables)
    def replacer_env(match):
        var_name = match.group(1).strip()
        return str(environment_vars.get(var_name, match.group(0))) # Returns the original if not found

    text = re.sub(r'\{\{\s*([a-zA-Z0-9_]+)\s*\}\}', replacer_env, text)

    # Pattern 2: {{pm.helper(...)}} (helper functions)
    def replacer_pm(match):
        func_call_str = match.group(1).strip()
        try:
            result = eval(func_call_str, {'pm': pm})
            return str(result)
        except Exception as e:
            logging.getLogger('pyman').warning(f"Error evaluating helper '{{{{{func_call_str}}}}}': {e}")
            return match.group(0)

    text = re.sub(r'\{\{\s*(pm\.[a-zA-Z0-9_.]+\(.*\))\s*\}\}', replacer_pm, text)
    
    return text

# --- Request Execution ---

def execute_request(request_file_path, environment_vars, pm, parsed_request):
    """
    Prepares and executes a single HTTP request based on a pre-parsed structure.
    """
    log = logging.getLogger('pyman')
    request_dir = os.path.dirname(request_file_path)

    try:
        url = substitute_variables(parsed_request['url'], environment_vars, pm)
        method = parsed_request['method'].upper()

        params = {}
        for k, v in parsed_request['params'].items():
            params[substitute_variables(k, environment_vars, pm)] = substitute_variables(v, environment_vars, pm)

        if params:
            query_string = urlencode(params)
            if '?' not in url:
                url += '?'
            elif not url.endswith('&'):
                url += '&'
            url += query_string
        
        headers = {}
        for k, v in parsed_request['headers'].items():
            headers[substitute_variables(k, environment_vars, pm)] = substitute_variables(v, environment_vars, pm)
            
        auth = {}
        for k, v in parsed_request['auth'].items():
            auth[k] = substitute_variables(v, environment_vars, pm)

        body = parsed_request['body']

    except Exception as e:
        log.error(f"Error substituting variables (URL/Headers/Auth): {e}", exc_info=True)
        return None

    data_payload = None
    files_payload = None
    auth_tuple = None
    
    content_type = headers.get('Content-Type', '')
    is_multipart = 'multipart/form-data' in content_type

    if isinstance(body, str):
        data_payload = substitute_variables(body, environment_vars, pm).encode('utf-8')
        
    elif isinstance(body, dict):
        if is_multipart and method in ('POST', 'PUT', 'PATCH'):
            log.info("Processing body as multipart/form-data")
            data_fields = {}
            file_fields = {}

            for key, value in body.items():
                if isinstance(value, dict) and value.get('type') == 'file':
                    src = value.get('src')
                    if not src:
                        log.warning(f"File field '{key}' has no 'src'. Skipping.")
                        continue
                    
                    src_subbed = substitute_variables(src, environment_vars, pm)
                    file_path = src_subbed if os.path.isabs(src_subbed) else os.path.join(request_dir, src_subbed)
                    
                    if not os.path.exists(file_path):
                        log.error(f"File not found for '{key}': {file_path}")
                        continue
                    
                    try:
                        file_name = os.path.basename(file_path)
                        file_fields[key] = (file_name, open(file_path, 'rb'), 'application/octet-stream')
                        log.info(f"Attaching file: '{key}' -> {file_path}")
                    except Exception as e:
                        log.error(f"Could not open file '{file_path}': {e}")
                else:
                    data_fields[key] = substitute_variables(str(value), environment_vars, pm)
            
            data_payload = data_fields
            files_payload = file_fields
            
            if 'Content-Type' in headers:
                del headers['Content-Type']
                
        else:
            data_payload = {k: substitute_variables(str(v), environment_vars, pm) for k, v in body.items()}

    if 'Bearer Token' in auth:
        headers['Authorization'] = f"Bearer {auth['Bearer Token']}"
        
    elif 'Basic Auth' in auth:
        auth_tuple = (
            substitute_variables(auth.get('Basic Auth', {}).get('username'), environment_vars, pm), 
            substitute_variables(auth.get('Basic Auth', {}).get('password'), environment_vars, pm)
        )

    response = None
    try:
        log.info(f"Dispatching {method} to: {url}")
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            data=data_payload,
            files=files_payload,
            auth=auth_tuple,
            timeout=60
        )
        log.info(f"STATUS: {response.status_code}")
        
    except requests.exceptions.RequestException as e:
        log.error(f"Error in request: {e}")
        return None
    finally:
        if files_payload:
            for _, file_tuple in files_payload.items():
                file_tuple[1].close()

    return response

# --- Request Processing ---

def process_request_file(req_file, environment_vars, pm, collection_root, summary, executed_set):
    """
    Processes a single request file, including its pre-requests and scripts.
    """
    log = logging.getLogger('pyman')
    if req_file in executed_set:
        log.debug(f"Skipping already executed request: {req_file}")
        return
    
    log.info("-" * 50)
    log.info(f"Processing request file: {req_file}")
    executed_set.add(req_file)

    try:
        parsed_request = parse_request_file(req_file)
    except Exception as e:
        log.error(f"Failed to parse file {req_file}: {e}", exc_info=True)
        summary['failure'] += 1
        return

    req_dir = os.path.dirname(req_file)

    for pre_req_path in parsed_request.get('pre-requests', []):
        abs_pre_req_path = os.path.abspath(os.path.join(req_dir, pre_req_path))
        if not os.path.exists(abs_pre_req_path):
            log.error(f"Pre-request file not found: {abs_pre_req_path}")
            summary['failure'] += 1
            continue
        
        log.info(f"Found pre-request: {pre_req_path}")
        process_request_file(abs_pre_req_path, environment_vars, pm, collection_root, summary, executed_set)

    req_name = os.path.basename(req_file)
    req_base_name = os.path.splitext(req_name)[0]

    collection_pre_script = os.path.join(collection_root, 'collection-pre-script.py')
    collection_pos_script = os.path.join(collection_root, 'collection-pos-script.py')
    req_pre_script = os.path.join(req_dir, f"{req_base_name}-pre-script.py")
    req_pos_script = os.path.join(req_dir, f"{req_base_name}-pos-script.py")

    try:
        if execute_script(collection_pre_script, environment_vars, pm, log):
            write_environment_file(collection_root, environment_vars)
        
        if execute_script(req_pre_script, environment_vars, pm, log):
            write_environment_file(collection_root, environment_vars)

        log.info(f"Executing main request: {req_name}")
        response = execute_request(req_file, environment_vars, pm, parsed_request)

        if execute_script(req_pos_script, environment_vars, pm, log, response=response):
            write_environment_file(collection_root, environment_vars)

        if execute_script(collection_pos_script, environment_vars, pm, log, response=response):
            write_environment_file(collection_root, environment_vars)

        if response is not None and response.status_code < 400:
            summary['success'] += 1
        else:
            summary['failure'] += 1

    except Exception as e:
        log.error(f"Unexpected error during the cycle of {req_name}: {e}")
        summary['failure'] += 1

# --- Main Execution Loop ---

def run_collection(target_path, collection_root, request_files_to_run, log, pm):
    """
    The main loop that orchestrates the execution of the collection.
    """
    log.info(f"Starting execution. Collection root: {collection_root}")
    log.info(f"Target: {target_path}")

    try:
        environment_vars = load_environment(collection_root)
        log.info(f"Global environment variables loaded: {len(environment_vars)} keys.")
    except Exception as e:
        log.error(f"Critical failure loading environment: {e}")
        return

    summary = {'total': len(request_files_to_run), 'success': 0, 'failure': 0}
    executed_set = set()

    for req_file in request_files_to_run:
        process_request_file(req_file, environment_vars, pm, collection_root, summary, executed_set)

    log.info("-" * 50)
    log.info("Execution finished.")
    log.info(f"Summary: {summary['total']} total, {summary['success']} success, {summary['failure']} failure.")
    log.info("-" * 50)