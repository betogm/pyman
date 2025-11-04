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
import logging # Required to inspect handlers

try:
    from core_logic import (
        setup_logging,
        run_collection,
        get_collection_name,
        load_collection_config,
        get_collection_description
    )
    from pyman_helpers import PyManHelpers
    # Import reporter functions
    from log_reporter import parse_log_file, generate_html_report
except ImportError as e:
    print(f"Import error: {e}")
    print("Ensure that core_logic.py, pyman_helpers.py, and log_reporter.py are in the same 'app' directory.")
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
    # New argument for generating the report
    parser.add_argument(
        '--report',
        action='store_true', # Defines it as a boolean flag
        help="Automatically generate an HTML report after execution."
    )

    parser.add_argument(
        '--collection-order',
        type=str,
        default='Default',
        help="The name of the execution order from COLLECTIONS_ORDER in config.yaml."
    )

    args = parser.parse_args()

    # --- Path Resolution ---
    target_path = os.path.abspath(args.target)
    collection_root = ''
    
    if os.path.isdir(target_path):
        collection_root = target_path
    else:
        current_dir = os.path.dirname(target_path)
        while current_dir != os.path.dirname(current_dir): # While it is not the system root
            if os.path.exists(os.path.join(current_dir, '.environment-variables')):
                collection_root = current_dir
                break
            current_dir = os.path.dirname(current_dir)
        
        if not collection_root:
            collection_root = os.path.dirname(target_path)

    if not os.path.exists(target_path):
        print(f"Error: Path not found: {target_path}")
        sys.exit(1)

    # 1. Load config and metadata
    collection_config = load_collection_config(collection_root)
    collection_name = get_collection_name(collection_root, config=collection_config)
    collection_description = get_collection_description(collection_root, config=collection_config)

    # 2. Configure Logging
    log_file_path = None
    try:
        log, log_file_path = setup_logging(collection_root, collection_name, collection_description)
    except Exception as e:
        print(f"Error configuring logging in {collection_root}: {e}")
        sys.exit(1)

    if log_file_path:
        log.info(f"Log file will be saved to: {log_file_path}")
    else:
        log.warning("Could not determine log file path. Report generation may fail.")

    # 3. Instantiate Helpers
    try:
        pm = PyManHelpers(log)
    except Exception as e:
        log.error(f"Error instantiating PyManHelpers: {e}")
        sys.exit(1)

    # 4. Find files to be executed
    request_files_to_run = []
    
    # Check for custom execution order
    collections_order = collection_config.get('COLLECTIONS_ORDER', {})
    selected_order_name = args.collection_order
    
    if collections_order and selected_order_name in collections_order:
        log.info(f"Using custom execution order: '{selected_order_name}'")
        relative_paths = collections_order[selected_order_name]
        if not isinstance(relative_paths, list):
            log.error(f"COLLECTIONS_ORDER '{selected_order_name}' is not a valid list.")
            sys.exit(1)
            
        for rel_path in relative_paths:
            # Ensure path is clean and uses correct separators
            clean_path = os.path.normpath(str(rel_path))
            abs_path = os.path.join(collection_root, clean_path)
            if os.path.exists(abs_path):
                request_files_to_run.append(abs_path)
            else:
                log.warning(f"File specified in COLLECTIONS_ORDER not found: {abs_path}")
    else:
        # Fallback to default alphabetical discovery
        if os.path.isdir(target_path):
            log.info(f"Executing collection in alphabetical order: {target_path}")
            for root, dirs, files in os.walk(target_path):
                # Ignore special directories
                dirs[:] = [d for d in dirs if d not in ['logs', 'reports', 'files', '.venv', 'venv', '__pycache__']]
                dirs.sort()
                
                files.sort() # Ensures alphabetical order
                for file in files:
                    # Only run .yaml/.yml files that are not config files
                    if file.endswith(('.yaml', '.yml')) and not file.lower().startswith('config.'):
                        request_files_to_run.append(os.path.join(root, file))
                        
        elif os.path.isfile(target_path) and target_path.endswith(('.yaml', '.yml')):
            log.info(f"Executing single request: {target_path}")
            request_files_to_run.append(target_path)
        else:
            log.error(f"The target is not a valid collection directory or a .yaml/.yml file: {target_path}")
            sys.exit(1)
        
    if not request_files_to_run:
        log.warning(f"No .yaml/.yml request files found in: {target_path}")
        if log_file_path:
            print(f"\nLog file generated at: {log_file_path}")
        sys.exit(0) # Exit cleanly, no work to do

    # 4. Start execution
    execution_failed = False # Flag to track if the run itself failed
    try:
        run_collection(target_path, collection_root, request_files_to_run, log, pm)
    except Exception as e:
        # This exception is raised by run_collection on failure.
        # The error message is already formatted.
        log.error(str(e))
        execution_failed = True # Mark the run as failed
    finally:
        # --- Always print log path ---
        if log_file_path:
            print(f"\nLog file generated at: {log_file_path}")
        else:
            print("\nExecution finished, but log file path could not be determined.")

        # 5. Generate report if requested
        if args.report:
            if log_file_path and os.path.exists(log_file_path):
                log.info("Generating HTML report...")
                try:
                    # Create 'reports' directory in collection root
                    report_dir = os.path.join(collection_root, "reports")
                    os.makedirs(report_dir, exist_ok=True)
                    
                    # Generate new filename
                    log_filename = os.path.basename(log_file_path)
                    # report_name = "report_collection_name_timestamp.html"
                    report_filename = "report_" + log_filename.replace("run_", "").replace(".log", ".html")
                    report_file_path = os.path.join(report_dir, report_filename)

                    # Call reporter functions
                    parsed_collection_name, parsed_collection_desc, executions, summary, total_time = parse_log_file(log_file_path)
                    generate_html_report(parsed_collection_name, parsed_collection_desc, executions, summary, total_time, report_file_path)
                    
                    # Print the final report path
                    print(f"HTML report generated at: {report_file_path}")
                
                except Exception as e:
                    log.error(f"Failed to generate HTML report: {e}", exc_info=True)
                    print(f"Error: Failed to generate HTML report: {e}")
                    sys.exit(1) # Exit with error if report generation fails
            else:
                log.warning("Report generation skipped: Log file not found.")
                print("Report generation skipped: Log file not found.")
        
        # Exit with error code 1 if the collection run failed
        if execution_failed:
            sys.exit(1)


if __name__ == "__main__":
    main()

