# post-data-pre-script.py
# This script runs BEFORE the 'post-data.yaml' request.

print("[REQ PRE-SCRIPT]: Preparing to send the POST request.")

# Checks if the variable from the previous request (GET) exists.
if 'LAST_ORIGIN_IP' in environment_vars:
    print(f"[REQ PRE-SCRIPT]: The previous GET request saved the IP: {environment_vars['LAST_ORIGIN_IP']}")
else:
    print("[REQ PRE-SCRIPT]: 'LAST_ORIGIN_IP' variable not yet defined (run the GET request first).")
    # Defines a default value if it doesn't exist.
    if 'LAST_ORIGIN_IP' not in environment_vars:
        environment_vars['LAST_ORIGIN_IP'] = "not-defined"