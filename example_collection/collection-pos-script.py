# collection-pos-script.py
# This script runs AFTER EACH request in the collection.
# It's useful for tearing down, analyzing responses, or logging.

print("[GLOBAL POST-SCRIPT]: Request finished.")

if 'response' in locals() and response:
    print(f"[GLOBAL POST-SCRIPT]: Response status code: {response.status_code}")
    
    # Calculates the total time since the pre-script ran.
    # This is just an example; PyMan's logger already provides timing information.
    if 'TIMESTAMP_START' in environment_vars:
        duration_ms = (pm.timestamp() - environment_vars['TIMESTAMP_START']) * 1000
        print(f"[GLOBAL POST-SCRIPT]: Elapsed time since PRE-SCRIPT: {duration_ms:.2f}ms")
else:
    print("[GLOBAL POST-SCRIPT]: Response context not found (the request may have failed).")