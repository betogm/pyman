# PyMan - CLI Request Executor

PyMan: A lightweight, filesystem-based HTTP request runner for the CLI. Inspired by Postman and Bruno, it executes collections defined in YAML files, supporting pre/post-run scripts (Python), environments, and multiple data types. Perfect for automating and version-controlling your API tests right alongside your code. ⚡️🐍

---

## Installation

1.  Make sure you have Python 3.8+ installed.
2.  Create and activate a virtual environment (`venv`).

  ```console
  # Create the environment
  python3 -m venv venv
  
  # Activate the environment
  source venv/bin/activate
  ```

3.  Install dependencies (create a `requirements.txt` file if it doesn't exist).

  ```console
  pip install -r requirements.txt
  ```

## How to Use

Run `pyman.py` (inside the `pyman` folder) with the `run` command and the desired target.

### Run an entire collection

To run all requests at the project root:

```console
python pyman/pyman.py run .
```

### Run a specific folder

```console
python pyman/pyman.py run Example_Collection/get-request
```

### Run a specific request file

```console
python pyman/pyman.py run Example_Collection/post-request/post-data.yaml
```

## Directory Structure

PyMan expects the following file and directory structure:

```text
/your-project/
|
|-- /tests_collection/         <-- (No spaces in name, e.g., get-users)
|   |-- .environment-variables       <-- Global variables (e.g., BASE_URL="https://api.com")
|   |-- collection-pre-script.py     <-- Python script executed BEFORE EACH request
|   |-- collection-pos-script.py     <-- Python script executed AFTER EACH request
|   |
|   |-- /logs/
|   |   |-- run_20251027_103000.log   <-- Execution logs (created automatically)
|   |
|   |-- /example-get-request/
|   |   |-- config.yaml          <-- Folder metadata (e.g., FOLDER_NAME="Fetch Data")
|   |   |
|   |   |-- get-data.yaml        <-- Request file (see format below)
|   |   |-- get-data-pos-script.py  <-- Script AFTER this request
|   |   |-- get-data-pre-script.py  <-- Script BEFORE this request
|   |
|   |-- /example-post-request/
|       |-- ...
|
|-- /another-folder/
|   |-- ...
```

## Request File Format (.yaml)

Requests are defined in `.yaml` files with a clear structure, separating method, URL, parameters, authentication, headers, and body.

```yaml
# Example request file: get-data.yaml

request:
  method: GET
  url: "{{BASE_URL}}/get"

params:
  param1: "value"
  random: "{{pm.random_int(1, 100)}}"

authentication:
  bearer_token: "{{AUTH_TOKEN}}"

headers:
  Accept: "application/json"
  User-Agent: "{{USER_AGENT}}"

# The body is optional for methods like GET
body: ""
```

For `POST` requests with a `JSON` body, the structure is similar:

```yaml
# Example POST file: post-data.yaml

request:
  method: POST
  url: "{{BASE_URL}}/post"

authentication:
  bearer_token: "{{PROD_TOKEN}}"

headers:
  Content-Type: "application/json"

body: |
  {
  "name": "My Item",
  "value": {{pm.random_int(1, 100)}}
  }
```

## Scripts (Pre and Post)

Scripts are Python files that have access to three global variables:

-   `env` (dict): The environment variables dictionary. You can read (`env['BASE_URL']`) and write (`env['NEW_VAR'] = 'value'`) to it.
-   `pm` (module): The `pyman_helpers` module. Use `pm.random_int()` or `pm.random_adjective()`.
-   `response` (`requests.Response`): Available **only in `pos-script` scripts**. Contains the request response object (`response.status_code`, `response.json()`).

### Example `pos-script.py`

```python
# my-request-pos-script.py

try:
  if response.status_code == 200:
    print("POS Script: Request OK!")
    data = response.json()
    
    # Extract an ID from the response and save it to the environment
    if 'id' in data:
      env['LAST_CREATED_ID'] = data['id']
      print(f"ID saved to environment: {env['LAST_CREATED_ID']}")
      
except Exception as e:
  print(f"Error in POS script: {e}")

```