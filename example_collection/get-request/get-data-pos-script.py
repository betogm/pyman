# get-data-pos-script.py
# This script runs AFTER the 'get-data.yaml' request.

print("[REQ POST-SCRIPT]: Analyzing GET response...")

try:
    if response.status_code == 200:
        data = response.json()
        
        # Saves the origin IP returned by httpbin to the environment
        origin_ip = data.get('origin')
        if origin_ip:
            environment_vars['LAST_ORIGIN_IP'] = origin_ip
            print(f"[REQ POST-SCRIPT]: Origin IP saved to environment: {origin_ip}")
            
        # Checks the header sent in the request
        request_user_agent = data.get('headers', {}).get('User-Agent')
        print(f"[REQ POST-SCRIPT]: User-Agent sent: {request_user_agent}")
        
except Exception as e:
    print(f"[REQ POST-SCRIPT]: Error analyzing JSON: {e}")