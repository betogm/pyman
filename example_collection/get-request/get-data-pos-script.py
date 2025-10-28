# get-data-pos-script.py

print("[REQ POS Script]: Analyzing GET response...")

try:
    if response.status_code == 200:
        data = response.json()
        
        # Saves the origin IP returned by httpbin to the environment_varsironment
        origin_ip = data.get('origin')
        if origin_ip:
            environment_vars['LAST_ORIGIN_IP'] = origin_ip
            print(f"[REQ POS Script]: Origin IP saved to environment_vars: {origin_ip}")
            
        # Checks the header
        request_user_agent = data.get('headers', {}).get('User-Agent')
        print(f"[REQ POS Script]: User-Agent sent: {request_user_agent}")
        
except Exception as e:
    print(f"[REQ POS Script]: Error analyzing JSON: {e}")