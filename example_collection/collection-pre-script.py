# collection-pre-script.py
# This script runs BEFORE EACH request in the collection.

print("[Global PRE Script]: Preparing to execute a request.")

# Modifying the environment globally
env['TIMESTAMP_START'] = pm.timestamp()

print(f"[Global PRE Script]: Base URL is {env.get('BASE_URL')}")