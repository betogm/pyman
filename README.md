# PyMan - CLI Request Runner

PyMan: A lightweight, filesystem-based HTTP request runner for CLI. Inspired by Postman and Bruno, it executes collections defined in YAML files, supporting pre/post-run scripts (Python), environments, and multiple data types. Perfect for automating and version-controlling your API tests right alongside your code. ⚡️🐍

---

## Installation

1.  Make sure you have Python 3.7+ installed.
2.  Create and activate a virtual environment (`venv`).

    ```console
    # Create the environment
    python3 -m venv venv
    
    # Activate the environment
    source venv/bin/activate
    ```

3.  Install the dependencies (create a `requirements.txt` file if it doesn't exist).

    ```console
    pip install -r requirements.txt
    ```

## How to Use

Execute `pyman.py` (inside the `pyman` folder) with the `run` command and the desired target.

### Run an entire collection

To run all requests in the project root:

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
|-- /your_collection/         <-- (Name without spaces, e.g., get-users)
|   |-- .environment-variables       <-- Global variables (e.g., BASE_URL="https://api.com")
|   |-- collection-pre-script.py     <-- Python script executed BEFORE EACH request
|   |-- collection-pos-script.py     <-- Python script executed AFTER EACH request
|   |
|   |-- /logs/
|   |
|   |-- /get-request/
|   |   |-- config.yaml          <-- Folder metadata (e.g., FOLDER_NAME="Fetch Data")
|   |   |
|   |   |-- get-data.yaml        <-- Request File (see format below)
|   |   |-- get-data-pos-script.py  <-- Script AFTER this request
|   |   |-- get-data-pre-script.py  <-- Script BEFORE this request
|   |
|   |-- /post-request/
|       |-- ...
|
|   |-- /another-folder/
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

## Pre-Requests (Chaining Requests)

You can chain requests using the `pre-requests` key in your `.yaml` file. This allows you to execute one or more requests before the main one, which is useful for scenarios like authentication, where you need to obtain a token before making the final call.

The requests listed in `pre-requests` are executed in order, and each one runs its full cycle (including pre and post scripts).

### Example

Imagine `get-resource.yaml` needs an authentication token that is obtained by `login.yaml`.

```yaml
# /collections/auth/login.yaml
# This request gets a token and saves it to the environment via a post-script.

request:
  method: POST
  url: "{{BASE_URL}}/auth"
body: |
  {
    "user": "admin",
    "pass": "secret"
  }
```

```python
# /collections/auth/login-pos-script.py
# Saves the token from the response to the environment.

if response.status_code == 200:
    token = response.json().get("token")
    if token:
        environment_vars["AUTH_TOKEN"] = token
        print("Token saved to environment.")
```

```yaml
# /collections/data/get-resource.yaml
# This request uses the token obtained by the pre-request.

pre-requests:
  - ../auth/login.yaml  # Relative path to the login request

request:
  method: GET
  url: "{{BASE_URL}}/resource"
authentication:
  bearer_token: "{{AUTH_TOKEN}}" # Uses the token saved in the environment
```

When `get-resource.yaml` is executed:
1.  PyMan will first execute `login.yaml`.
2.  The `login-pos-script.py` will run, saving the token.
3.  Finally, the main request in `get-resource.yaml` will be executed, using the token that is now in the environment.

## Scripts (Pre and Post)

Scripts are Python files that have access to four global variables:

-   `environment_vars` (dict): The environment variables dictionary. You can read from it (`environment_vars['BASE_URL']`) and write to it (`environment_vars['NEW_VAR'] = 'value'`). **Changes made to this dictionary will be automatically saved back to the `.environment-variables` file after the script execution.**
-   `pm` (module): The `pyman_helpers` module. Use `pm.random_int()`, `pm.random_adjective()`, or `pm.test()`.
-   `log` (Logger): The logger instance for the current execution. You can use it to log messages to the PyMan log (e.g., `log.info('Message')`, `log.error('Error')`).
-   `pm.test(name, condition_func)`: A function to perform assertions in your scripts, similar to Postman's `pm.test()`. `name` is the test name (string) and `condition_func` is a lambda or regular function containing the assertion logic. If the assertion fails, the test will be marked as `FAILED` in the log. Example:
    ```python
    pm.test("Status code is 200", lambda: assert response.status_code == 200)
    ```
    **Note:** If an assertion fails, `pm.test()` will log the error but will not stop script execution or raise a full traceback.
-   `response` (`requests.Response`): Available **only in post-scripts**. Contains the request's response object (`response.status_code`, `response.json()`).

### Example of `pos-script.py`

```python
# my-request-pos-script.py

try:
    if response.status_code == 200:
        log.info("POS script: Request OK!")
        data = response.json()
        
        # Extracts an ID from the response and saves it to the environment
        if 'id' in data:
            environment_vars['LAST_CREATED_ID'] = data['id']
            log.info(f"ID saved to environment: {environment_vars['LAST_CREATED_ID']}")
            
except Exception as e:
    log.error(f"Error in POS script: {e}")

```

## Importing from Postman

PyMan includes a script to convert Postman v2.1 collections into the PyMan format. The script `pyman/postman_importer.py` converts Postman's JSON files into PyMan's YAML-based directory structure.

### How to Use the Importer

Run the script from your terminal, providing the path to your Postman collection and an output directory.

```console
python pyman/postman_importer.py -c /path/to/your/postman_collection.json -o my_new_pyman_collection
```

### Arguments

-   `-c`, `--collection`: **(Required)** Path to the Postman collection `.json` file.
-   `-o`, `--output`: **(Required)** Name of the output directory where the PyMan collection will be created.
-   `-e`, `--environment`: (Optional) Path to a Postman environment `.json` file. The variables will be converted into a `.environment-variables` file.

### Conversion Details

-   **Folders and Requests**: Are converted into nested directories and `.yaml` files.
-   **Environments**: Variables from the Postman environment are saved in the `.environment-variables` file.
-   **Scripts (Pre-request & Test)**: The importer attempts a basic conversion of simple Javascript code (like `pm.environment.set` and `console.log`) to Python. For more complex scripts, the original JS code is commented out in the corresponding `.py` script file with a `TODO` notice, requiring manual conversion.

---

## Authors

-   Huberto Gastal Mayer
-   Google Gemini, for the help and time saved, thank you!
