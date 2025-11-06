# -*- coding: utf-8 -*-
#
# PyMan - Python HTTP Request Executor - Core Logic
# Author: Huberto Gastal Mayer (hubertogm@gmail.com)
# License: GPLv3
#
# This is the core_logic version compatible with pyman.py (v--report)
# Now with color logging for the console.

import requests
import logging
import logging.handlers
import os
import re
import sys
import time
import json
import yaml # For loading config.yaml
from datetime import datetime
from urllib.parse import urlencode # For building query params
import io
from contextlib import redirect_stdout


# Import helper and parser relative to the 'app' directory
try:
    from .request_parser import parse_request_file
    from .pyman_helpers import PyManHelpers
except ImportError as e:
    print(f"Import error in core_logic.py: {e}")
    print("Ensure request_parser.py and pyman_helpers.py are in the same directory.")
    raise

# --- Global Variables ---
# Regex for variable substitution {{variable_name}} or {{pm.function(arg1, arg2)}}
VAR_REGEX = re.compile(r"\{\{(.*?)\}\}")

# --- (NEW) ANSI Color Codes for Logging ---
class Color:
    """ANSI color codes for terminal output."""
    GREY = "\033[90m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

class ColorFormatter(logging.Formatter):
    """Custom formatter to add colors to console log messages."""
    
    # Define simple formats for console
    FORMATS = {
        logging.DEBUG: logging.Formatter(f'{Color.GREY}DEBUG: %(message)s{Color.RESET}'),
        logging.INFO: logging.Formatter('%(message)s'), # Simple message for INFO
        logging.WARNING: logging.Formatter(f'{Color.YELLOW}WARNING: %(message)s{Color.RESET}'),
        logging.ERROR: logging.Formatter(f'{Color.RED}ERROR: %(message)s{Color.RESET}'),
        logging.CRITICAL: logging.Formatter(f'{Color.BOLD}{Color.RED}CRITICAL: %(message)s{Color.RESET}'),
    }

    def format(self, record):
        # Get the default formatter based on the log level
        log_fmt = self.FORMATS.get(record.levelno, self.FORMATS[logging.INFO])
        
        # Call the base formatter
        message = log_fmt.format(record)

        # Apply special colors for INFO messages based on content
        if record.levelno == logging.INFO:
            if record.message.strip().startswith("PASSED:"):
                message = f"{Color.GREEN}{message}{Color.RESET}"
            elif record.message.startswith("Dispatching"):
                message = f"{Color.CYAN}{message}{Color.RESET}"
            elif record.message.startswith("Executing collection") or \
                 record.message.startswith("Processing request file"):
                message = f"{Color.BOLD}{message}{Color.RESET}"
            elif record.message.startswith("Summary:") or \
                 record.message.startswith("---") or \
                 record.message.startswith("Execution finished."):
                message = f"{Color.BOLD}{message}{Color.RESET}"
            # Default INFO (like 'Environment variables loaded') remains no color
        
        # Apply special color for FAILED (which is an ERROR level)
        elif record.levelno == logging.ERROR:
             if "FAILED:" in record.message or "Error executing script" in record.message:
                 # Make errors bold red
                 message = f"{Color.BOLD}{Color.RED}ERROR: {record.message}{Color.RESET}"

        return message

# --- Logging Setup ---
def setup_logging(collection_root, collection_name="pyman_run", collection_description=None):
    """Configures logging to file and console."""
    log_dir = os.path.join(collection_root, 'logs')
    os.makedirs(log_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Use the collection name in the log file, if available
    safe_collection_name = re.sub(r'\W+', '_', collection_name)
    log_filename = f"run_{safe_collection_name}_{timestamp}.log"
    log_filepath = os.path.join(log_dir, log_filename)

    log = logging.getLogger('pyman')
    log.setLevel(logging.DEBUG) # Capture everything

    # Remove existing handlers to avoid duplicate logs
    if log.hasHandlers():
        for handler in log.handlers[:]:
            log.removeHandler(handler)
            handler.close()

    # File Handler - Logs everything (DEBUG level)
    try:
        fh = logging.FileHandler(log_filepath, encoding='utf-8')
        fh.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S,%f')
        fh.setFormatter(file_formatter)
        log.addHandler(fh)
    except Exception as e:
        print(f"Error creating file handler for {log_filepath}: {e}")
        raise

    # Console Handler - Logs INFO level and above
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(ColorFormatter())
    log.addHandler(ch)

    # Log collection metadata
    log.info(f"Collection Name: {collection_name}")
    if collection_description:
        log.info(f"Collection Description: {collection_description}")

    # Return both the logger and the path
    return log, log_filepath

# --- Configuration Loading ---
def load_collection_config(collection_root):
    """Loads the main config.yaml from the collection root."""
    config_path = os.path.join(collection_root, 'config.yaml')
    if not os.path.exists(config_path):
        config_path = os.path.join(collection_root, 'config.yml')

    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
                if config_data and isinstance(config_data, dict):
                    return config_data
        except Exception as e:
            # Using print because logger might not be configured yet
            print(f"Warning: Could not read or parse config file at {config_path}: {e}")
    return {} # Return empty dict if no config found

def get_collection_name(collection_root, config=None):
    """Tries to get the collection name from config or defaults to directory name."""
    if config is None:
        config = load_collection_config(collection_root)
    
    return config.get('COLLECTION_NAME', os.path.basename(collection_root))

def get_collection_description(collection_root, config=None):
    """Gets the collection description from the config."""
    if config is None:
        config = load_collection_config(collection_root)
    
    return config.get('DESCRIPTION', None)

def load_environment(collection_root, log):
    """Loads environment variables from .environment-variables file."""
    env_vars = {}
    env_file = os.path.join(collection_root, '.environment-variables')
    if os.path.exists(env_file):
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        # Strip quotes from value
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        env_vars[key.strip()] = value.strip()
            log.info(f"Global environment variables loaded: {len(env_vars)} keys.")
        except Exception as e:
            log.error(f"Error loading environment variables from {env_file}: {e}")
    else:
        log.warning(f"Environment file not found: {env_file}")
    return env_vars
    
def write_environment_file(collection_root, environment_vars, log):
    """
    Writes the environment dictionary back to the .environment-variables file.
    """
    env_file = os.path.join(collection_root, '.environment-variables')
    try:
        # Remove internal keys before saving
        clean_vars = {k: v for k, v in environment_vars.items() if not k.startswith('_')}
        
        with open(env_file, 'w', encoding='utf-8') as f:
            for key, value in clean_vars.items():
                # Add quotes if the value contains spaces or special chars
                if re.search(r'[\s#"\']', str(value)):
                     f.write(f'{key}="{value}"\n')
                else:
                     f.write(f'{key}={value}\n')
        log.debug(f"Environment variables successfully written to {env_file}")
    except Exception as e:
        log.error(f"Error writing to .environment-variables file: {e}")


def load_folder_config(folder_path, log):
    """Loads folder-specific configuration from config.yaml."""
    config_vars = {}
    config_file = os.path.join(folder_path, 'config.yaml')
    if not os.path.exists(config_file):
        config_file = os.path.join(folder_path, 'config.yml')

    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                if isinstance(data, dict):
                    config_vars = data
                    log.debug(f"Folder config loaded from {config_file}: {len(config_vars)} keys.")
                else:
                    log.warning(f"Invalid format in folder config file: {config_file}. Expected a dictionary.")
        except yaml.YAMLError as e:
             log.error(f"YAML syntax error in folder config {config_file}: {e}")
        except Exception as e:
            log.error(f"Error loading folder config from {config_file}: {e}")
    else:
         log.debug(f"No folder config file found in {folder_path}")
    return config_vars

# --- Variable Substitution ---
def substitute_variables(text, variables, pm_instance, log):
    """Substitutes {{variable}} placeholders in a string."""
    if not isinstance(text, str):
        return text

    def replace_match(match):
        expression = match.group(1).strip()
        # Check if it's a pm helper function call
        if expression.startswith("pm."):
            try:
                # Evaluate the expression
                # NOTE: This is powerful, but can be a security risk if scripts are not trusted.
                # For this use case (local scripts), it is acceptable.
                return str(eval(expression, {'pm': pm_instance}))
            except Exception as e:
                log.error(f"Error executing pm helper function '{{{{{expression}}}}}': {e}")
                return match.group(0) # Keep original on error
        else:
            # Simple variable substitution
            return str(variables.get(expression, match.group(0))) # Keep original if var not found

    return VAR_REGEX.sub(replace_match, text)

def substitute_variables_recursive(data, variables, pm_instance, log):
    """Recursively substitutes variables in nested dicts and lists."""
    if isinstance(data, dict):
        return {k: substitute_variables_recursive(v, variables, pm_instance, log) for k, v in data.items()}
    elif isinstance(data, list):
        return [substitute_variables_recursive(item, variables, pm_instance, log) for item in data]
    elif isinstance(data, str):
        return substitute_variables(data, variables, pm_instance, log)
    else:
        return data

# --- Script Execution ---
def execute_script(script_path, environment_vars, response, log, pm, shared_scope=None):
    """
    Executes a Python script, captures its output, and handles specific errors.
    Returns a tuple: (env_changed, script_output, script_failed_exception, assertion_error).
    """
    if not os.path.exists(script_path):
        log.debug(f"Script not found, skipping: {script_path}")
        return False, "", None, False

    log.info(f"Executing script: {script_path}")
    
    env_before = environment_vars.copy()
    script_output = io.StringIO()
    script_failed_exception = None
    assertion_error = False
    
    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            script_code = f.read()

        script_globals = {
            'pm': pm,
            'environment_vars': environment_vars,
            'response': response,
            'log': log,
            'requests': requests,
            'json': json,
            'os': os,
            're': re,
            'time': time,
            'shared': shared_scope
        }

        # Initialize pm.failed_tests if it doesn't exist
        if not hasattr(pm, 'failed_tests'):
            pm.failed_tests = []

        with redirect_stdout(script_output):
            exec(compile(script_code, script_path, 'exec'), script_globals)



    except requests.exceptions.JSONDecodeError as e:
        script_failed_exception = e
        # Log an elegant, user-friendly error instead of a raw traceback
        error_message = (
            f"❌ [{pm.request_name or 'Unnamed Test'}] - FAILED: The test script encountered an error.\n"
            f"   Error: Failed to decode JSON from the response body.\n"
            f"   This usually happens when the script expects a JSON response (e.g., calling response.json()),\n"
            f"   but the server returned a non-JSON response (e.g., HTML, plain text, or an empty body)."
        )
        print(error_message) # This will be captured by script_output
        log.error(f"JSONDecodeError in {script_path}: {e}", exc_info=False)

    except Exception as e:
        script_failed_exception = e
        log.error(f"Error executing script {script_path}: {e}", exc_info=True)
        if isinstance(e, AssertionError):
            assertion_error = True

    # Check if the script modified the environment
    env_changed = environment_vars != env_before
    if env_changed:
        log.info("Environment variables were modified by the script.")
        
    output = script_output.getvalue()
    # Also log the script's captured output to the file for debugging
    if output.strip():
        log.debug(f"--- Script Output ---\n{output.strip()}\n---------------------")

    # return env_changed, output, script_failed_exception
    return env_changed, output, script_failed_exception, assertion_error

# --- Request Execution ---
def execute_request(request_data, current_vars, pm_instance, log, has_pos_script=False):
    """Executes a single HTTP request based on parsed data."""
    method = request_data['method']
    base_url = substitute_variables(request_data['url'], current_vars, pm_instance, log)
    headers = substitute_variables_recursive(request_data['headers'], current_vars, pm_instance, log)
    auth_config = substitute_variables_recursive(request_data['auth'], current_vars, pm_instance, log)
    body = substitute_variables_recursive(request_data['body'], current_vars, pm_instance, log)
    params = substitute_variables_recursive(request_data['params'], current_vars, pm_instance, log)
    
    # Build the final URL with query params
    url = base_url
    if params:
        query_string = urlencode(params)
        if '?' not in url:
            url += '?'
        elif not url.endswith('&'):
            url += '&'
        url += query_string

    auth = None
    files = None # For multipart/form-data

    # --- Authentication ---
    if 'Bearer Token' in auth_config:
        log.debug("Applying Bearer Token authentication")
        token = auth_config['Bearer Token']
        headers['Authorization'] = f"Bearer {token}"
    elif 'Basic Auth' in auth_config:
        log.debug("Applying Basic Auth authentication")
        username = auth_config['Basic Auth'].get('username', '')
        password = auth_config['Basic Auth'].get('password', '')
        auth = (username, password)
    # Add other auth methods here

    # --- Body & Content-Type Handling ---
    data = None
    json_payload = None
    content_type = headers.get('Content-Type', '').lower()

    if body is not None:
        if isinstance(body, dict) and 'multipart/form-data' in content_type:
            log.debug("Preparing multipart/form-data payload")
            files = {}
            data_payload = {} # Use 'data' for non-file fields
            
            # Try to find the 'collection_root' for relative paths
            collection_root = current_vars.get('_collection_root', os.path.dirname(request_data.get('file_path', '.')))
            request_dir = os.path.dirname(request_data.get('file_path', '.'))

            for key, value_config in body.items():
                if isinstance(value_config, dict) and value_config.get('type') == 'file':
                    file_path_raw = value_config.get('src', '')
                    file_path = substitute_variables(file_path_raw, current_vars, pm_instance, log)

                    if not os.path.isabs(file_path):
                        # 1. Relative to the request's 'files' subdirectory
                        path_in_files_sub = os.path.join(request_dir, 'files', file_path)
                        # 2. Relative to the request's directory
                        path_in_req_dir = os.path.join(request_dir, file_path)
                        # 3. Relative to the collection root
                        path_in_root = os.path.join(collection_root, file_path)
                        
                        if os.path.exists(path_in_files_sub):
                            final_path = path_in_files_sub
                        elif os.path.exists(path_in_req_dir):
                            final_path = path_in_req_dir
                        elif os.path.exists(path_in_root):
                             final_path = path_in_root
                        else:
                            log.error(f"File not found for multipart: {file_path_raw} (Tried: {path_in_files_sub}, {path_in_req_dir}, {path_in_root})")
                            continue
                    else:
                        final_path = file_path

                    if os.path.exists(final_path):
                        try:
                           files[key] = (os.path.basename(final_path), open(final_path, 'rb'))
                           log.debug(f"Attaching file '{key}': {final_path}")
                        except Exception as e:
                             log.error(f"Error opening file {final_path} for multipart upload: {e}")
                    else:
                        log.error(f"File not found for multipart upload: {final_path} (raw: {file_path_raw})")
                else:
                    data_payload[key] = substitute_variables(str(value_config), current_vars, pm_instance, log)
            
            data = data_payload # Assign non-file fields to 'data'
            if 'Content-Type' in headers:
                del headers['Content-Type'] # Let requests set the boundary

        elif isinstance(body, str): # Raw body
            data = body.encode('utf-8')
            if not content_type:
                 headers['Content-Type'] = 'text/plain'
        elif isinstance(body, dict): # form-urlencoded or JSON
            if 'application/x-www-form-urlencoded' in content_type:
                data = body # requests will urlencode
            else:
                json_payload = body
                if 'application/json' not in content_type:
                    headers['Content-Type'] = 'application/json'
        else:
            log.warning(f"Unsupported body type: {type(body)}. Ignoring body.")

    # --- Make the Request ---
    response = None
    start_time_req = time.time()
    try:
        log.info(f"Dispatching {method} to: {url}")
        log.debug(f"HEADERS: {headers}")
        if data: log.debug(f"DATA: {data if isinstance(data, dict) else data[:200]}") # Log dict or first 200 bytes
        if json_payload: log.debug(f"JSON: {json.dumps(json_payload, indent=2, ensure_ascii=False)}")
        if files: log.debug(f"FILES: {list(files.keys())}")

        response = requests.request(
            method,
            url,
            headers=headers,
            data=data,
            json=json_payload,
            auth=auth,
            files=files,
            timeout=30
        )
        
    except requests.exceptions.HTTPError as e:
        log.error(f"HTTP Error: {e.response.status_code} {e.response.reason} for url: {url}")
        if e.response is not None:
             log.debug(f"Error Response Body: {e.response.text[:500]}")
             response = e.response
    except requests.exceptions.RequestException as e:
        log.error(f"Request failed: {e}")
    except Exception as e:
        log.error(f"An unexpected error occurred during the request: {e}", exc_info=True)
    finally:
        end_time_req = time.time()
        duration_ms = (end_time_req - start_time_req) * 1000
        
        status_text = "N/A"
        status_code = 0
        if response is not None:
            status_code = response.status_code
            status_text = response.reason
            
        status_message = f"STATUS: {status_code} {status_text} ({duration_ms:.0f} ms)"
        if has_pos_script:
            log.info(status_message)
        else:
            if status_code >= 500:
                log.error(status_message)
            elif status_code >= 400:
                log.warning(status_message)
            elif status_code > 0:
                log.info(status_message)
        # If status_code is 0 or response is None, an error was already logged.
        
        if response is not None:
            log.debug(f"HEADERS (Response): {dict(response.headers)}")
            try:
                resp_json = response.json()
                log.debug(f"BODY (Response JSON): \n{json.dumps(resp_json, indent=2, ensure_ascii=False)}")
            except json.JSONDecodeError:
                # Log as plain text if not JSON, truncated to avoid spam
                resp_text = response.text
                if len(resp_text) > 1000:
                     log.debug(f"BODY (Response Text): {resp_text[:1000]}... (truncated)")
                else:
                     log.debug(f"BODY (Response Text): {resp_text}")

    if files:
        for f_tuple in files.values():
            try:
                f_tuple[1].close()
            except Exception as e:
                log.warning(f"Error closing file handle: {e}")

    return response

# --- Collection Runner ---
def run_collection(target_path, collection_root, request_files, log, pm):
    """Runs a collection of requests or a single request."""
    log.info(f"Starting execution. Collection root: {collection_root}")
    log.info(f"Target: {target_path}")

    global_env_vars = load_environment(collection_root, log)
    global_env_vars['_collection_root'] = collection_root # Add root path

    results = {'total': 0, 'success': 0, 'failure': 0, 'warnings': 0}
    failed_files = []
    
    # Create a shared scope object for all scripts in the collection
    shared_scope = type("SharedScope", (object,), {})()

    # --- Execute Collection Pre-script (ONCE) ---
    collection_pre_script = os.path.join(collection_root, 'collection-pre-script.py')
    if os.path.exists(collection_pre_script):
        log.info("-" * 50)
        env_changed, _, _, _ = execute_script(collection_pre_script, global_env_vars, None, log, pm, shared_scope=shared_scope)
        if env_changed:
            write_environment_file(collection_root, global_env_vars, log)

    last_response = None # To hold the response of the last executed request
    for req_file in request_files:
        log.info("-" * 50)
        log.info(f"Processing request file: {req_file}")
        results['total'] += 1
        request_success = True # Assume success until proven otherwise

        # Use a copy for the request to keep global env clean between requests
        current_vars = global_env_vars.copy()
        
        folder_path = os.path.dirname(req_file)
        folder_vars = load_folder_config(folder_path, log)
        current_vars.update(folder_vars)

        response = None
        try:
            # Parse Request File
            try:
                request_data = parse_request_file(req_file)
                request_data['file_path'] = req_file # Add path for reference
                pm.request_name = request_data.get('name', os.path.basename(req_file)) # Set request name for pm
            except Exception as e:
                 log.error(f"Failed to parse request file {req_file}: {e}", exc_info=True)
                 request_success = False

            if request_success:
                # Request Pre-script
                req_pre_script = req_file.replace('.yaml', '-pre-script.py').replace('.yml', '-pre-script.py')
                env_changed, _, script_error, _ = execute_script(req_pre_script, current_vars, None, log, pm, shared_scope=shared_scope)
                if env_changed:
                    global_env_vars.update(current_vars)
                    write_environment_file(collection_root, global_env_vars, log)
                if script_error:
                    request_success = False # Fail if pre-script has an error

                # Main Request

                req_pos_script = req_file.replace('.yaml', '-pos-script.py').replace('.yml', '-pos-script.py')

                has_pos_script = os.path.exists(req_pos_script)

                response = execute_request(request_data, current_vars, pm, log, has_pos_script)

                if response is not None:

                    last_response = response # Save for collection-pos-script

                    pm.set_response(response)



                # Request Post-script

                post_env_changed, _, post_script_error, post_assertion_error = execute_script(req_pos_script, current_vars, response, log, pm, shared_scope=shared_scope)

                if post_env_changed:

                    global_env_vars.update(current_vars)

                    write_environment_file(collection_root, global_env_vars, log)



                # --- NEW SUCCESS/FAILURE LOGIC ---

                http_status = response.status_code if response is not None else 0



                if has_pos_script:

                    if post_assertion_error:
                        log.error(f"❌ [{pm.request_name or 'Unnamed Test'}] - FAILED: Post-script assertions failed.")
                        request_success = False

                    elif post_script_error is not None:
                        log.error(f"❌ [{pm.request_name or 'Unnamed Test'}] - FAILED: Post-script execution error.")
                        request_success = False

                else:

                    # ⚙️ MODO 2: Sem post-script -> classificar pela resposta HTTP
                    if http_status >= 500:
                        log.error(f"❌ [{pm.request_name or 'Unnamed Test'}] - FAILED: Server error {http_status}.")
                        request_success = False

                    elif 400 <= http_status < 500:
                        log.warning(f"⚠️ [{pm.request_name or 'Unnamed Test'}] - WARNING: Client error {http_status}.")
                        results['warnings'] += 1
                        # request_success remains True for a warning

                    elif http_status == 0:
                        log.error(f"❌ [{pm.request_name or 'Unnamed Test'}] - FAILED: No response received.")

                    request_success = False

        except Exception as e:
            log.error(f"Critical error during processing of {req_file}: {e}", exc_info=True)
            request_success = False

        if request_success:
            results['success'] += 1
        else:
            results['failure'] += 1
            failed_files.append(req_file)

    # --- Execute Collection Post-script (ONCE) ---
    collection_pos_script = os.path.join(collection_root, 'collection-pos-script.py')
    if os.path.exists(collection_pos_script):
        log.info("-" * 50)
        # Use the global environment and the last response from the loop
        env_changed, _, _, _ = execute_script(collection_pos_script, global_env_vars, last_response, log, pm, shared_scope=shared_scope)
        if env_changed:
            write_environment_file(collection_root, global_env_vars, log)

    log.info("-" * 50)
    log.info("Execution finished.")
    passed_asserts = len(pm.passed_tests)
    failed_asserts = len(pm.failed_tests)
    summary_message = (
        f"✅ Summary: {results['total']} total requests | "
        f"🟢 {results['success']} success | "
        f"⚠️ {results['warnings']} warnings | "
        f"🔴 {results['failure']} failure\n"
        f"           Asserts: {passed_asserts + failed_asserts} total | "
        f"🟢 {passed_asserts} passed | "
        f"🔴 {failed_asserts} failed"
    )
    log.info(summary_message)
    log.info("-" * 50)

    # Raise exception if there were failures, so pyman.py can catch it
    if results['failure'] > 0:
        failed_files_str = "\n".join([f'  - {os.path.relpath(f, collection_root)}' for f in set(failed_files)])
        raise Exception(f"{results['failure']} request(s) failed:\n{failed_files_str}")

