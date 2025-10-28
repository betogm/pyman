# collection-pre-script.py
# This script runs BEFORE EACH request in the collection.

print("[Global PRE Script]: Preparing to execute a request.")

# Modifying the environment_varsironment globally
environment_vars['TIMESTAMP_START'] = pm.timestamp()

print(f"[Global PRE Script]: Base URL is {environment_vars.get('BASE_URL')}")