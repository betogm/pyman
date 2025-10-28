# -*- coding: utf-8 -*-
#
# PyMan - Python HTTP Request Executor
# Author: Huberto Gastal Mayer (hubertogm@gmail.com)
# License: GPLv3 (https://www.gnu.org/licenses/gpl-3.0.html)
# Project: PyMan - A CLI tool for executing HTTP request collections defined in YAML
#

import logging
import yaml

log = logging.getLogger('pyman')

def parse_request_file(file_path):
    """
    Parses the .yaml request file using the PyYAML library.
    """
    parsed = {
        'method': 'GET',
        'url': '',
        'params': {},
        'auth': {},
        'headers': {},
        'body': '',
        'pre-requests': []
    }

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            
            if not data or not isinstance(data, dict):
                raise ValueError("YAML file is empty or not a dictionary.")
                
    except yaml.YAMLError as e:
        log.error(f"YAML syntax error in {file_path}: {e}")
        raise
    except Exception as e:
        log.error(f"Could not read request file: {file_path} - {e}")
        raise

    # 1. Method and URL
    req_data = data.get('request', {})
    parsed['method'] = req_data.get('method', 'GET').upper()
    base_url = req_data.get('url', '')
    parsed['url'] = base_url

    # 2. Parameters (Query Params)
    parsed['params'] = data.get('params', {})

    # 3. Authentication
    # Normalizes to the format expected by core_logic
    auth_data = data.get('authentication', {})
    if 'bearer_token' in auth_data:
        parsed['auth']['Bearer Token'] = auth_data['bearer_token']
    if 'basic_auth' in auth_data:
        parsed['auth']['Basic Auth'] = auth_data['basic_auth']

    # 4. Headers
    parsed['headers'] = data.get('headers', {})
                
    # 5. Body
    # YAML with | (literal block) preserves the format, including line breaks
    parsed['body'] = data.get('body', '')

    # 6. Pre-requests
    parsed['pre-requests'] = data.get('pre-requests', [])

    return parsed