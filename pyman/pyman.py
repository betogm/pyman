# -*- coding: utf-8 -*-
#
# PyMan - Python HTTP Request Executor
# Author: Huberto Gastal Mayer (hubertogm@gmail.com)
# License: GPLv3 (https://www.gnu.org/licenses/gpl-3.0.html)
# Project: PyMan - A CLI tool for executing HTTP request collections defined in YAML
#

import argparse
import os
import sys


try:
    from core_logic import (
        setup_logging,
        run_collection
    )
    from pyman_helpers import PyManHelpers
except ImportError as e:
    print(f"Import error: {e}")
    print("Ensure that core_logic.py and pyman_helpers.py are in the same 'app' directory.")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="PyMan - A CLI HTTP request executor")
    
    parser.add_argument(
        'command',
        choices=['run'],
        help="The command to be executed."
    )
    parser.add_argument(
        'target',
        help="The path to the collection (directory) or request (.yaml) to be executed."
    )

    args = parser.parse_args()

    # --- Path Resolution ---
    # The 'target' can be relative to where the command was executed.
    target_path = os.path.abspath(args.target)
    
    # We assume that the "collection root" is the directory containing
    # the .environment-variables file.
    # If the target is a file, we go up until we find the .env file or reach the root.
    
    collection_root = ''
    
    if os.path.isdir(target_path):
        # If the target is a directory, we assume it is the collection root
        collection_root = target_path
    else:
        # If it is a file, we search for the root by going up
        current_dir = os.path.dirname(target_path)
        while current_dir != os.path.dirname(current_dir): # While it is not the system root
            if os.path.exists(os.path.join(current_dir, '.environment-variables')):
                collection_root = current_dir
                break
            current_dir = os.path.dirname(current_dir)
        
        if not collection_root:
            # If not found, use the file's directory as the "root"
            collection_root = os.path.dirname(target_path)

    if not os.path.exists(target_path):
        print(f"Error: Path not found: {target_path}")
        sys.exit(1)

    # 1. Configure Logging
    # The log will always be saved in 'logs' inside the collection root
    try:
        log = setup_logging(collection_root)
    except Exception as e:
        print(f"Error configuring logging in {collection_root}: {e}")
        sys.exit(1)

    # 2. Instantiate Helpers
    # The 'pm' module is injected into the scripts
    try:
        pm = PyManHelpers(log)
    except Exception as e:
        log.error(f"Error instantiating PyManHelpers: {e}")
        sys.exit(1)

    # 3. Find files to be executed
    request_files_to_run = []
    if os.path.isdir(target_path):
        log.info(f"Executing collection in directory: {target_path}")
        for root, dirs, files in os.walk(target_path):
            # Ignore the logs directory itself
            if 'logs' in dirs:
                dirs.remove('logs')
                
            files.sort() # Ensures alphabetical order
            for file in files:
                if file.endswith(('.yaml', '.yml')) and file != 'config.yaml':
                    request_files_to_run.append(os.path.join(root, file))
                    
    elif os.path.isfile(target_path) and target_path.endswith(('.yaml', '.yml')):
        log.info(f"Executing single request: {target_path}")
        request_files_to_run.append(target_path)
    else:
        log.error(f"The target is not a valid collection directory or a .yaml/.yml file: {target_path}")
        sys.exit(1)
        
    if not request_files_to_run:
        log.warning(f"No .yaml/.yml files found in: {target_path}")
        sys.exit(0)

    # 4. Start execution
    try:
        run_collection(target_path, collection_root, request_files_to_run, log, pm)
    except Exception as e:
        log.error(f"An unhandled exception occurred: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
