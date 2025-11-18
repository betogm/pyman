# collection-pre-script.py
# This script runs BEFORE EACH request in the collection.
# It's useful for setting up global state or logging.

print("[GLOBAL PRE-SCRIPT]: Preparing to execute a request.")

# Here, we are modifying the environment_vars dictionary globally.
# This variable will be available in all subsequent requests and scripts.
environment_vars['TIMESTAMP_START'] = pm.timestamp()

print(f"[GLOBAL PRE-SCRIPT]: The Base URL is {environment_vars.get('BASE_URL')}")
print(f"[GLOBAL PRE-SCRIPT]: Starting timestamp set to {environment_vars['TIMESTAMP_START']}.")