# -*- coding: utf-8 -*-
#
# PyMan - Python HTTP Request Executor
# Author: Huberto Gastal Mayer (hubertogm@gmail.com)
# License: GPLv3 (https://www.gnu.org/licenses/gpl-3.0.html)
# Project: PyMan - A CLI tool for executing HTTP request collections defined in YAML
#

import argparse
import re
import html
import json
from datetime import datetime
import os

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Execution Report - PyMan</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f4f7f9;
            color: #333;
            line-height: 1.6;
        }}
        .container {{
            max-width: 1200px;
            margin: 20px auto;
            padding: 20px;
            background-color: #fff;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08);
        }}
        header h1 {{
            color: #2c3e50;
            margin-top: 0;
            border-bottom: 2px solid #e0e0e0;
            padding-bottom: 10px;
        }}
        header p {{
            color: #7f8c8d;
            font-size: 0.9em;
        }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        .summary-card {{
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            color: #fff;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        .summary-card .value {{
            font-size: 2.5em;
            font-weight: 700;
            display: block;
        }}
        .summary-card .label {{
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .bg-blue {{ background: linear-gradient(45deg, #3498db, #2980b9); }}
        .bg-green {{ background: linear-gradient(45deg, #2ecc71, #27ae60); }}
        .bg-red {{ background: linear-gradient(45deg, #e74c3c, #c0392b); }}
        .bg-purple {{ background: linear-gradient(45deg, #9b59b6, #8e44ad); }}
        
        .filters {{
            margin-bottom: 20px;
            display: flex;
            gap: 10px;
        }}
        .filter-btn {{
            background-color: #ecf0f1;
            border: none;
            padding: 10px 15px;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
            color: #34495e;
            transition: all 0.2s ease-in-out;
        }}
        .filter-btn:hover {{ background-color: #bdc3c7; }}
        .filter-btn.active {{ background-color: #3498db; color: white; }}

        .execution-item {{
            border: 1px solid #e0e0e0;
            border-left-width: 5px;
            border-radius: 5px;
            margin-bottom: 15px;
            overflow: hidden;
            transition: box-shadow 0.3s;
        }}
        .execution-item:hover {{
            box-shadow: 0 2px 8px rgba(0,0,0,0.07);
        }}
        .execution-item.status-failed {{ border-left-color: #e74c3c; }}
        .execution-item.status-passed {{ border-left-color: #2ecc71; }}
        .execution-item.status-error {{ border-left-color: #f39c12; }} /* Color for script errors */

        summary {{
            padding: 15px;
            cursor: pointer;
            display: grid;
            grid-template-columns: 80px 1fr 120px 100px;
            align-items: center;
            gap: 15px;
            background-color: #fdfdfd;
        }}
        summary::-webkit-details-marker {{ display: none; }}
        summary:hover {{ background-color: #f5f5f5; }}

        .method {{
            font-weight: bold;
            padding: 5px 8px;
            border-radius: 4px;
            color: #fff;
            text-align: center;
        }}
        .method-GET {{ background-color: #2980b9; }}
        .method-POST {{ background-color: #27ae60; }}
        .method-PUT {{ background-color: #f39c12; }}
        .method-DELETE {{ background-color: #c0392b; }}
        .method-PATCH {{ background-color: #8e44ad; }}
        .method-NA {{ background-color: #7f8c8d; }} /* Style for N/A method */

        .item-name {{ font-weight: 500; color: #34495e; word-break: break-all; }}
        .response-code, .response-time {{ text-align: right; color: #7f8c8d; }}
        
        .details-content {{
            padding: 0 20px 20px;
            background-color: #fafafa;
            border-top: 1px solid #eee;
        }}
        .details-content h4 {{ margin-top: 20px; color: #2c3e50; border-bottom: 1px solid #ddd; padding-bottom: 5px;}}
        .details-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            border-top: 1px solid #eee;
            padding-top: 15px;
        }}
        .assertions-list {{ list-style-type: none; padding: 0; }}
        .assertion-item {{
            padding: 8px 0;
            border-bottom: 1px dashed #e0e0e0;
            display: flex;
            align-items: flex-start; /* Align top for long error messages */
        }}
        .assertion-item:last-child {{ border-bottom: none; }}
        .assertion-status {{
            margin-right: 10px;
            font-weight: bold;
            font-size: 1.2em;
            flex-shrink: 0; /* Prevent icon shrinking */
        }}
        .assertion-passed {{ color: #2ecc71; }}
        .assertion-failed {{ color: #e74c3c; }}
        .assertion-message {{ 
            color: #e74c3c; 
            font-family: monospace; 
            font-size: 0.9em; 
            margin-top: 5px; 
            background: #fbeaea; 
            padding: 5px; 
            border-radius: 3px;
            white-space: pre-wrap; /* Wrap lines in error messages */
            word-break: break-all;
        }}
        
        pre {{
            background-color: #2d2d2d;
            color: #f1f1f1;
            padding: 15px;
            border-radius: 5px;
            white-space: pre-wrap;
            word-wrap: break-word;
            font-family: "Courier New", Courier, monospace;
            font-size: 0.9em; /* Reduce font size for JSON/Headers */
        }}
        .pre-header {{ font-size: 0.8em; }} /* Even smaller size for headers */
        
        /* Style for script errors */
        .script-error-details {{
             background-color: #fff3cd; /* Light yellow background */
             color: #856404; /* Dark text */
             padding: 15px;
             margin-top: 10px;
             border: 1px solid #ffeeba;
             border-radius: 5px;
             font-family: monospace;
             white-space: pre-wrap;
             word-break: break-all;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>PyMan Execution Report</h1>
            <p><strong>Collection:</strong> {collection_name}</p>
            <p><strong>Execution Date:</strong> {execution_date}</p>
        </header>

        <section class="summary">
            <div class="summary-grid">
                <div class="summary-card bg-blue">
                    <span class="value">{total_requests}</span>
                    <span class="label">Requests</span>
                </div>
                <div class="summary-card bg-purple">
                    <span class="value">{total_tests}</span>
                    <span class="label">Tests</span>
                </div>
                <div class="summary-card bg-green">
                    <span class="value">{passed_requests}</span>
                    <span class="label">Passed</span>
                </div>
                <div class="summary-card bg-red">
                    <span class="value">{failed_requests}</span>
                    <span class="label">Failed</span>
                </div>
            </div>
            <p style="text-align:center; color: #7f8c8d;">Total execution time: {total_time:.2f}s</p>
        </section>
        
        <section class="results">
            <h2>Detailed Results</h2>
            <div class="filters">
                <button class="filter-btn active" onclick="filterResults('all')">All</button>
                <button class="filter-btn" onclick="filterResults('failed')">Failures Only</button>
            </div>
            <div id="executions-list">
                {executions_html}
            </div>
        </section>
    </div>

    <script>
        function filterResults(filter) {{
            const items = document.querySelectorAll('.execution-item');
            const buttons = document.querySelectorAll('.filter-btn');

            buttons.forEach(btn => btn.classList.remove('active'));
            document.querySelector(`button[onclick="filterResults('${{filter}}')"]`).classList.add('active');

            items.forEach(item => {{
                if (filter === 'all') {{
                    item.style.display = 'block';
                }} else if (filter === 'failed') {{
                    // Show items with failed tests OR script errors
                    if (item.classList.contains('status-failed') || item.classList.contains('status-error')) {{
                        item.style.display = 'block';
                    }} else {{
                        item.style.display = 'none';
                    }}
                }}
            }});
        }}
    </script>
</body>
</html>
"""

def parse_log_file(log_path):
    """Parses the log file and extracts execution data."""
    executions = []
    current_execution = None
    # Flags to track multi-line content
    in_request_headers = False
    in_request_body = False
    in_response_headers = False
    in_response_body = False
    in_script_error = False

    # Regex patterns to extract key information
    req_file_re = re.compile(r"Processing request file: (.*)")
    req_dispatch_re = re.compile(r"Dispatching (GET|POST|PUT|DELETE|PATCH) to: (.*)")
    req_headers_start_re = re.compile(r"DEBUG - HEADERS: (.*)")
    req_body_start_re = re.compile(r"DEBUG - DATA: (.*)")
    resp_status_re = re.compile(r"INFO - STATUS: (\d+)")
    resp_headers_start_re = re.compile(r"DEBUG - HEADERS \(Response\): (.*)")
    script_exec_re = re.compile(r"Executing script: (.*)")
    test_passed_re = re.compile(r"PASSED: (.*)")
    test_failed_re = re.compile(r"FAILED: (.*)")
    script_error_start_re = re.compile(r"ERROR - Error executing script (.*): (.*)")
    traceback_re = re.compile(r"^\s+.*|Traceback.*") # Traceback lines
    collection_name_re = re.compile(r"INFO - Collection Name: (.*)") # Regex to get collection name from log
    summary_re = re.compile(r"Summary: (\d+) total, (\d+) success, (\d+) failure")

    collection_name = "Unknown"
    summary = {'total': 0, 'success': 0, 'failure': 0}
    start_time = None
    end_time = None
    current_time = None

    with open(log_path, 'r', encoding='utf-8') as f:
        for line in f:
            # Try to extract timestamp to calculate time
            try:
                timestamp_str = line.split(' - ')[0]
                current_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f')
                if start_time is None:
                    start_time = current_time
                end_time = current_time # Update end time with each line
            except (ValueError, IndexError):
                pass # Ignore lines without the expected timestamp format

            # Extract collection name if available
            match = collection_name_re.search(line)
            if match:
                collection_name = match.group(1).strip()
                continue # Move to next line after finding collection name

            # Start of a new request execution block
            match = req_file_re.search(line)
            if match:
                if current_execution: # Append previous execution if exists
                    executions.append(current_execution)
                # Initialize data structure for the new execution
                current_execution = {
                    'name': os.path.basename(match.group(1).strip()),
                    'file_path': match.group(1).strip(),
                    'method': 'N/A',
                    'url': 'N/A',
                    'req_headers': '',
                    'req_body': '',
                    'status_code': None,
                    'status_text': 'N/A', # Will be added based on status code
                    'resp_headers': '',
                    'resp_body': '',
                    'tests': [],
                    'script_error': None,
                    'start_time': current_time,
                    'end_time': None
                }
                # Reset flags
                in_request_headers = False
                in_request_body = False
                in_response_headers = False
                in_response_body = False
                in_script_error = False
                continue

            # Skip lines until the first request is found
            if not current_execution:
                continue

            # Capture request details
            match = req_dispatch_re.search(line)
            if match:
                current_execution['method'] = match.group(1)
                current_execution['url'] = match.group(2).strip()
                continue

            # Capture Request Headers (potentially multi-line if broken by logger)
            match = req_headers_start_re.search(line)
            if match:
                # Use eval to convert the dict string back to dict for pretty printing
                try:
                    headers_dict = eval(match.group(1).strip())
                    current_execution['req_headers'] = json.dumps(headers_dict, indent=2, ensure_ascii=False)
                except Exception as e:
                    current_execution['req_headers'] = f"Error parsing headers: {match.group(1).strip()}\n{e}"
                in_request_headers = True # Flag headers started
                continue
            # Note: This simple parser doesn't handle headers spanning multiple log lines well.

            # Capture Request Body (assuming it's on one line in the log)
            match = req_body_start_re.search(line)
            if match:
                # Try decoding if it looks like bytes (b'...')
                body_str = match.group(1).strip()
                if body_str.startswith("b'") and body_str.endswith("'"):
                    try:
                        body_str = eval(body_str).decode('utf-8', errors='replace')
                    except Exception:
                        body_str = body_str # Keep original if decoding fails
                # Try formatting if it's JSON
                try:
                    body_json = json.loads(body_str)
                    current_execution['req_body'] = json.dumps(body_json, indent=2, ensure_ascii=False)
                except json.JSONDecodeError:
                    current_execution['req_body'] = body_str # Keep as plain text if not JSON
                in_request_body = True # Flag body captured
                continue

            # Capture Response Status
            match = resp_status_re.search(line)
            if match:
                current_execution['status_code'] = int(match.group(1))
                # Add descriptive text (simplified map)
                status_map = {
                    200: "OK", 201: "Created", 204: "No Content",
                    400: "Bad Request", 401: "Unauthorized", 403: "Forbidden",
                    404: "Not Found", 422: "Unprocessable Content",
                    500: "Internal Server Error"
                }
                current_execution['status_text'] = status_map.get(current_execution['status_code'], "Unknown Status")
                continue

            # Capture Response Headers (potentially multi-line)
            match = resp_headers_start_re.search(line)
            if match:
                 try:
                    headers_dict = eval(match.group(1).strip())
                    # Format as key: value per line for HTML <pre> tag
                    formatted_headers = "\n".join([f"<strong>{k}:</strong> {v}" for k, v in headers_dict.items()])
                    current_execution['resp_headers'] = formatted_headers
                 except Exception as e:
                    current_execution['resp_headers'] = f"Error parsing headers: {match.group(1).strip()}\n{e}"
                 in_response_headers = True # Flag response headers started
                 continue
            # Note: Simple handling for multi-line headers.

            # Assume response body comes *after* response headers in the log.
            # Capture Response Body (can be multi-line)
            # Check if the line is NOT a typical log line (INFO, DEBUG, etc.)
            if in_response_headers and not re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} - (INFO|DEBUG|ERROR|WARNING)", line):
                 # Try to format as JSON
                 try:
                     # Clean potential escape characters
                     clean_line = line.strip().encode('utf-8').decode('unicode_escape')
                     # Attempt to concatenate if it's multi-line JSON (basic approach)
                     potential_json = current_execution.get('resp_body_raw', '') + clean_line
                     body_json = json.loads(potential_json)
                     # Pretty print JSON
                     current_execution['resp_body'] = json.dumps(body_json, indent=2, ensure_ascii=False)
                     current_execution['resp_body_raw'] = potential_json # Store raw for next line concat
                 except json.JSONDecodeError:
                     # If not valid JSON, just append the line as plain text
                     current_execution['resp_body'] = current_execution.get('resp_body', '') + line
                     current_execution['resp_body_raw'] = current_execution.get('resp_body_raw', '') + line # Store raw
                 in_response_body = True # Flag we are reading the body
                 continue
            elif in_response_body: # If we were reading the body and now encounter a log line, body section ends.
                in_response_body = False
                in_response_headers = False # Response section finished

            # Capture test results from post-run scripts
            match = test_passed_re.search(line)
            if match:
                current_execution['tests'].append({'status': 'passed', 'name': match.group(1).strip(), 'message': None})
                continue

            match = test_failed_re.search(line)
            if match:
                fail_detail = match.group(1).strip().split('|', 1) # Split name and message
                fail_name = fail_detail[0].strip()
                fail_msg = fail_detail[1].strip() if len(fail_detail) > 1 else "Assertion failed"
                current_execution['tests'].append({'status': 'failed', 'name': fail_name, 'message': fail_msg})
                continue

            # Capture script execution errors
            match = script_error_start_re.search(line)
            if match:
                in_script_error = True
                current_execution['script_error'] = f"Error in script {os.path.basename(match.group(1).strip())}: {match.group(2).strip()}\n"
                continue

            # Capture traceback for script errors
            if in_script_error and traceback_re.match(line):
                current_execution['script_error'] += line.strip() + "\n"
                continue
            elif in_script_error: # End of traceback if a non-traceback line appears
                in_script_error = False

            # Capture final summary line
            match = summary_re.search(line)
            if match:
                summary['total'] = int(match.group(1))
                summary['success'] = int(match.group(2))
                summary['failure'] = int(match.group(3))

            # Update end time for the current execution on each relevant line
            if current_execution and current_time:
                 current_execution['end_time'] = current_time


    # Append the last processed execution
    if current_execution:
        executions.append(current_execution)

    # Calculate total time
    total_time = (end_time - start_time).total_seconds() if start_time and end_time else 0

    return collection_name, executions, summary, total_time

def generate_html_report(collection_name, executions, summary, total_time, output_path):
    """Generates the HTML file from the parsed data."""
    executions_html = ""
    total_tests = 0
    passed_tests_count = 0 # Count of individual passed tests

    for exec_data in executions:
        # Determine overall status of the request execution
        has_failed_tests = any(t['status'] == 'failed' for t in exec_data['tests'])
        has_script_error = exec_data['script_error'] is not None
        
        # Assign CSS class and status text based on outcome
        if has_script_error:
            status_class = "status-error" # Specific CSS class for script errors
            final_status_code = exec_data['status_code'] if exec_data['status_code'] else 'Error'
            final_status_text = 'Script Error'
        elif has_failed_tests:
            status_class = "status-failed"
            final_status_code = exec_data['status_code']
            final_status_text = exec_data.get('status_text', 'Fail')
        else:
            status_class = "status-passed"
            final_status_code = exec_data['status_code']
            final_status_text = exec_data.get('status_text', 'Pass')

        # Calculate request duration
        req_time_ms = 0
        if exec_data['start_time'] and exec_data['end_time']:
             req_time_ms = int((exec_data['end_time'] - exec_data['start_time']).total_seconds() * 1000)

        # Build HTML for the tests list
        tests_html = ""
        if exec_data['tests']:
            total_tests += len(exec_data['tests'])
            for test in exec_data['tests']:
                status_icon = "✔" if test['status'] == 'passed' else "❌"
                status_css = f"assertion-{test['status']}"
                error_message_html = ""
                # Include error message detail if test failed
                if test['status'] == 'failed' and test['message']:
                    error_message_html = f"<div class='assertion-message'><pre>{html.escape(test['message'])}</pre></div>"
                
                tests_html += f"""
                <li class="assertion-item">
                    <span class="assertion-status {status_css}">{status_icon}</span>
                    <div>
                        <span>{html.escape(test['name'])}</span>
                        {error_message_html}
                    </div>
                </li>
                """
                if test['status'] == 'passed':
                     passed_tests_count += 1
        else:
            tests_html = "<li class='assertion-item'>No tests were executed for this request.</li>"

        # Format script error details if present
        script_error_html = ""
        if exec_data['script_error']:
            script_error_html = f"""
            <h4>Script Error</h4>
            <div class='script-error-details'>
                <pre>{html.escape(exec_data['script_error'])}</pre>
            </div>
            """

        # Format Headers and Body safely, handling potential missing data
        req_headers_html = f"<pre class='pre-header'>{html.escape(exec_data.get('req_headers', 'N/A'))}</pre>" if exec_data.get('req_headers') else "<pre>N/A</pre>"
        req_body_html = f"<pre>{html.escape(exec_data.get('req_body', 'N/A'))}</pre>" if exec_data.get('req_body') else "<pre>No request body.</pre>"
        # Response headers might already be formatted with HTML <br>, handle appropriately
        resp_headers_formatted = exec_data.get('resp_headers', 'N/A')
        resp_headers_html = f"<pre class='pre-header'>{resp_headers_formatted}</pre>" if resp_headers_formatted != 'N/A' else "<pre>N/A</pre>"
        resp_body_html = f"<pre>{html.escape(exec_data.get('resp_body', 'N/A'))}</pre>" if exec_data.get('resp_body') else "<pre>No response body.</pre>"

        # Construct the HTML block for this execution item
        executions_html += f"""
        <details class="execution-item {status_class}">
            <summary>
                <span class="method method-{exec_data.get('method','NA').replace('/', '')}">{html.escape(exec_data.get('method','N/A'))}</span>
                <span class="item-name">{html.escape(exec_data.get('name','Unnamed Request'))}</span>
                <span class="response-code">{final_status_code} {html.escape(final_status_text)}</span>
                <span class="response-time">{req_time_ms} ms</span>
            </summary>
            <div class="details-content">
                <h4>Executed Tests</h4>
                <ul class='assertions-list'>
                    {tests_html}
                </ul>
                {script_error_html}
                <div class="details-grid">
                    <div class="request-details">
                        <h4>Request Data</h4>
                        <h5>URL</h5>
                        <pre>{html.escape(exec_data.get('url', 'N/A'))}</pre>
                        <h5>Headers</h5>
                        {req_headers_html}
                        <h5>Body</h5>
                        {req_body_html}
                    </div>
                    <div class="response-details">
                        <h4>Response Data</h4>
                        <h5>Headers</h5>
                        {resp_headers_html}
                        <h5>Body</h5>
                        {resp_body_html}
                    </div>
                </div>
            </div>
        </details>
        """

    # Calculate overall success/failure counts based on request outcomes
    failed_requests_count = sum(1 for e in executions if any(t['status'] == 'failed' for t in e['tests']) or e['script_error'])
    passed_requests_count = len(executions) - failed_requests_count

    # Populate the main HTML template
    final_html = HTML_TEMPLATE.format(
        collection_name=html.escape(collection_name),
        execution_date=datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        total_requests=len(executions),
        total_tests=total_tests, # Total individual tests
        passed_requests=passed_requests_count, # Based on requests (pass if no failed tests AND no script error)
        failed_requests=failed_requests_count, # Based on requests (fail if any failed test OR script error)
        total_time=total_time,
        executions_html=executions_html
    )

    # Save the generated HTML to the specified file
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(final_html)
        print(f"HTML report successfully generated at: {output_path}")
    except IOError as e:
        print(f"Error writing HTML file to {output_path}: {e}")
        exit(1)


if __name__ == "__main__":
    # Setup command-line argument parsing
    parser = argparse.ArgumentParser(description="Converts a PyMan log file into an HTML report.")
    parser.add_argument("log_file", help="Path to the PyMan log file.")
    parser.add_argument("output_html", nargs='?', help="Path for the output HTML file (optional).")

    args = parser.parse_args()

    # Validate log file existence
    if not os.path.exists(args.log_file):
        print(f"Error: Log file not found: {args.log_file}")
        exit(1)

    # Determine output file path
    output_file = args.output_html
    if not output_file:
        # Create default filename if not provided
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"pyman_report_{timestamp}.html"

    # Execute parsing and HTML generation
    try:
        collection_name, executions, summary, total_time = parse_log_file(args.log_file)
        generate_html_report(collection_name, executions, summary, total_time, output_file)
    except Exception as e:
        # Catch-all for any unexpected errors during processing
        print(f"An error occurred while processing the log or generating the report: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
