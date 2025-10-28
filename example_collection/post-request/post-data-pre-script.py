# post-data-pre-script.py

print("[REQ PRE Script]: Preparing to send the POST.")

# Checks if the variable from the previous request (GET) exists
if 'LAST_ORIGIN_IP' in environment_vars:
    print(f"[REQ PRE Script]: The previous request (GET) saved the IP: {environment_vars['LAST_ORIGIN_IP']}")
else:
    print("[REQ PRE Script]: 'LAST_ORIGIN_IP' variable not yet defined (run the GET first).")
    # Defines a default value if it doesn't exist
    if 'LAST_origin_ip' not in environment_vars:
        environment_vars['LAST_ORIGIN_IP'] = "not-defined"