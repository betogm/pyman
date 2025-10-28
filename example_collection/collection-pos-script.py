# collection-pos-script.py
# This script runs AFTER EACH request in the collection.

print("[Global POS Script]: Request finished.")

if 'response' in locals() and response:
    print(f"[Global POS Script]: Response status received: {response.status_code}")
    
    # Calculates the total time (although the logger already does this)
    if 'TIMESTAMP_START' in environment_vars:
        duration_ms = (pm.timestamp() - environment_vars['TIMESTAMP_START']) * 1000
        print(f"[Global POS Script]: Time since PRE script: {duration_ms}ms")
else:
    print("[Global POS Script]: Response context not found (probably failed).")