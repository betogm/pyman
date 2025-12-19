# -*- coding: utf-8 -*-
#
# Bruno to PyMan Converter
# Author: Huberto Gastal Mayer (with AI help)
# License: GPLv3
# Project: PyMan
#

import os
import re
import argparse
import sys
import logging
import yaml

# --- Custom YAML Dumper ---
class ForceLiteralDumper(yaml.SafeDumper):
    def represent_scalar(self, tag, value, style=None):
        if '\n' in value:
            style = '|'
        return super().represent_scalar(tag, value, style)

def slugify(text):
    """
    Converts a name into a safe filename.
    """
    if not text:
        return 'item'
    text = str(text)
    text = text.lower()
    text = re.sub(r'\s+', '-', text)
    text = re.sub(r'[^a-z0-9\-_]', '', text)
    text = re.sub(r'-+', '-', text)
    text = text.strip('-')
    if not text:
        text = 'request'
    return text

def parse_bru_file(filepath):
    """
    Parses a single .bru file and returns a dictionary representation
    similar to what we need for PyMan (or an intermediate structure).
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    data = {}
    current_block = None
    block_content = []
    
    # Regex to detect block start: "block_name {"
    block_start_re = re.compile(r'^([\w\:\-]+)\s*\{')
    
    for line in lines:
        stripped = line.strip()
        
        # Skip empty lines if not in a block (or handle them?)
        if not stripped:
            continue

        # Check for block end
        if current_block and stripped == '}':
            data[current_block] = block_content
            current_block = None
            block_content = []
            continue

        # Check for block start
        match = block_start_re.match(stripped)
        if match and current_block is None:
            current_block = match.group(1)
            continue
        
        # If in a block, add line to content
        if current_block:
            block_content.append(line) # Keep indentation and newlines for body
            continue

        # If not in a block and not empty, it might be a top-level property or comment
        # Bruno format is mostly blocks, but let's ignore comments
        if stripped.startswith('#'):
            continue

    return parse_bru_data(data)

def parse_bru_data(raw_data):
    """
    Refines the raw block data into a Pyman request dictionary.
    """
    req = {}
    
    # 1. Meta (Name, Type, Seq)
    meta_lines = raw_data.get('meta', [])
    meta = {}
    for line in meta_lines:
        parts = line.strip().split(':', 1)
        if len(parts) == 2:
            meta[parts[0].strip()] = parts[1].strip()
    
    req_name = meta.get('name', 'untitled')
    
    # 2. Request (Method and URL)
    # Bruno uses "get { ... }", "post { ... }" blocks.
    method = 'GET' # Default
    url_chars = ''
    
    methods = ['get', 'post', 'put', 'delete', 'patch', 'options', 'head']
    for m in methods:
        if m in raw_data:
            method = m.upper()
            # Parse URL from the block
            for line in raw_data[m]:
                if line.strip().startswith('url:'):
                    url_chars = line.strip().split(':', 1)[1].strip()
                    break
    
    req['request'] = {
        'method': method,
        'url': url_chars
    }

    # 3. Headers
    headers_lines = raw_data.get('headers', [])
    if headers_lines:
        headers = {}
        for line in headers_lines:
            parts = line.strip().split(':', 1)
            if len(parts) == 2:
                headers[parts[0].strip()] = parts[1].strip()
        if headers:
            req['headers'] = headers

    # 4. Body
    # Bruno has different body blocks: body:json, body:text, body:xml, etc.
    # We need to find which one is present.
    body_content = None
    
    if 'body:json' in raw_data:
        # Join lines and try to parse/prettify or just use as is
        body_str = "".join(raw_data['body:json']).strip()
        # Remove indentation if possible or just dump as string
        req['body'] = body_str
        # Ensure header if not present? Pyman adds it if body is json string? 
        # Actually Pyman usually expects 'Content-Type': 'application/json' in headers if body is JSON.
        
    elif 'body:text' in raw_data:
        req['body'] = "".join(raw_data['body:text']).strip()
        
    elif 'body:form-urlencoded' in raw_data:
        # Key: value lines
        form_data = {}
        for line in raw_data['body:form-urlencoded']:
            parts = line.strip().split(':', 1)
            if len(parts) == 2:
                form_data[parts[0].strip()] = parts[1].strip()
        if form_data:
            req['body'] = form_data
            if 'headers' not in req: req['headers'] = {}
            req['headers']['Content-Type'] = 'application/x-www-form-urlencoded'

    # 5. Auth (Basic, Bearer)
    auth_lines = raw_data.get('auth', [])
    if auth_lines:
        # TODO: Parse auth params more carefully if needed.
        # Often looks like:
        # auth:basic {
        #   username: ...
        #   password: ...
        # }
        # But top level 'auth' usually just sets the type?
        # Bruno format:
        # auth {
        #   mode: bearer
        # }
        # auth:bearer {
        #   token: ...
        # }
        pass 
    
    # Handle specific auth blocks
    if 'auth:bearer' in raw_data:
         token = ''
         for line in raw_data['auth:bearer']:
             if line.strip().startswith('token:'):
                 token = line.strip().split(':', 1)[1].strip()
         if token:
             req['authentication'] = {'bearer_token': token}

    elif 'auth:basic' in raw_data:
        username = ''
        password = ''
        for line in raw_data['auth:basic']:
            if line.strip().startswith('username:'):
                username = line.strip().split(':', 1)[1].strip()
            elif line.strip().startswith('password:'):
                password = line.strip().split(':', 1)[1].strip()
        req['authentication'] = {
            'basic_auth': {'username': username, 'password': password}
        }

    return req_name, req

def process_directory(source_dir, output_dir, log, wrapper_folder_counter, wrapper_request_counter, options):
    """
    Recursively walks the source directory and converts .bru files to Pyman .yaml.
    """
    # Create the corresponding output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Write config.yaml for the current folder if it doesn't exist
    # (Assuming the valid Bruno collection name is the directory name)
    folder_name = os.path.basename(source_dir)
    config_path = os.path.join(output_dir, 'config.yaml')
    if not os.path.exists(config_path):
        config_data = {'FOLDER_NAME': folder_name}
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    # List items in the directory
    try:
        items = sorted(os.listdir(source_dir))
    except Exception as e:
        log.error(f"Failed to list directory {source_dir}: {e}")
        return wrapper_folder_counter, wrapper_request_counter

    # Separate files and directories
    files = [i for i in items if os.path.isfile(os.path.join(source_dir, i))]
    dirs = [i for i in items if os.path.isdir(os.path.join(source_dir, i))]

    # Counters for this level
    folder_counter = wrapper_folder_counter
    request_counter = wrapper_request_counter

    # Process .bru files
    for filename in files:
        if filename.endswith('.bru') and filename != 'collection.bru': # collection.bru is meta
            filepath = os.path.join(source_dir, filename)
            log.info(f"Processing request: {filepath}")
            
            try:
                name, pyman_req = parse_bru_file(filepath)
                
                # Determine filename
                if options.get('numbered_files'):
                    request_counter += 10
                    prefix = f"{request_counter:03d}-"
                    out_filename = prefix + slugify(name) + ".yaml"
                else:
                    out_filename = slugify(name) + ".yaml"
                
                out_filepath = os.path.join(output_dir, out_filename)
                
                with open(out_filepath, 'w', encoding='utf-8') as f:
                     yaml.dump(pyman_req, f, Dumper=ForceLiteralDumper, allow_unicode=True, default_flow_style=False, sort_keys=False)
                     
            except Exception as e:
                log.error(f"Failed to parse {filepath}: {e}")

    # Process subdirectories
    for dirname in dirs:
        if dirname.startswith('.'): # Skip hidden dirs
            continue
            
        # Determine output folder name
        if options.get('numbered_folders'):
            folder_counter += 10
            prefix = f"{folder_counter:03d}-"
            out_dirname = prefix + slugify(dirname)
        else:
            out_dirname = slugify(dirname)
            
        sub_source = os.path.join(source_dir, dirname)
        sub_output = os.path.join(output_dir, out_dirname)
        
        # Recursive call - RESET counters for subdirectories? 
        # In Postman importer, we passed counters to process_item and it returned updated ones *for the same level*.
        # Here we are iterating.
        # But wait, usually numbering is per-directory.
        # So we should pass 0, 0 to the recursive call?
        # Yes, reset counters for the new inner level.
        process_directory(sub_source, sub_output, log, 0, 0, options)

    # Return counters? Not strictly necessary if we reset for each level in recursion, 
    # but the calling function might care if we were linear. Here strict hierarchy matches.
    return

def main():
    log = logging.getLogger('bruno_importer')
    log.setLevel(logging.INFO)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    if not log.hasHandlers():
        log.addHandler(console_handler)

    parser = argparse.ArgumentParser(description="Converts a Bruno collection to the PyMan structure.")
    parser.add_argument("-c", "--collection", help="Path to the Bruno collection directory.", required=True)
    parser.add_argument("-o", "--output", help="Output directory for the PyMan collection.", required=True)
    parser.add_argument(
        "--numbered", 
        choices=['yes', 'no'], 
        default='yes', 
        help="Whether to add numbering to folders and files (default: yes)."
    )
    # Add granular options if needed, similar to postman importer
    
    args = parser.parse_args()
    
    source_path = os.path.abspath(args.collection)
    output_path = os.path.abspath(args.output)
    
    if not os.path.isdir(source_path):
        log.error(f"Collection path is not a directory: {source_path}")
        sys.exit(1)
        
    options = {
        'numbered_files': args.numbered == 'yes',
        'numbered_folders': args.numbered == 'yes'
    }

    log.info(f"Importing Bruno collection from {source_path} to {output_path}...")
    
    process_directory(source_path, output_path, log, 0, 0, options)
    
    log.info("Conversion completed!")

if __name__ == "__main__":
    main()
