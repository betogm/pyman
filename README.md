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

By default, requests are executed in alphabetical order based on the directory and file structure.

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

### Run a collection with a specific order

You can define custom execution orders in a `config.yaml` file at the root of your collection. Use the `--collection-order` flag to specify which order to run.

```console
python pyman/pyman.py run . --collection-order=TestUpload
```

## Collection Configuration

You can create a `config.yaml` file in the root directory of your collection to define metadata and custom execution orders.

```yaml
# /your_collection/config.yaml

COLLECTION_NAME: "My API Test Suite"
DESCRIPTION: "This collection tests the main endpoints of the public API."

COLLECTIONS_ORDER:
  # The 'Default' order is used when no --collection-order flag is provided
  Default:
    - auth/login.yaml
    - users/get-users.yaml
    - users/create-user.yaml
  
  # A custom order for running only upload tests
  UploadTests:
    - auth/login.yaml
    - files/upload-image.yaml
    - files/upload-document.yaml
```

-   `COLLECTION_NAME`: The name of the collection, used as the title in logs and HTML reports.
-   `DESCRIPTION`: A brief description, also shown in the report header.
-   `COLLECTIONS_ORDER`: A dictionary where each key is the name of a custom execution order. The value is a list of request file paths, relative to the collection root.

## Directory Structure

PyMan expects the following file and directory structure:

```text
|-- /your_collection/
|   |-- config.yaml                  <-- (Optional) Collection metadata and execution order
|   |-- .environment-variables       <-- Global variables (e.g., BASE_URL="https://api.com")
|   |-- collection-pre-script.py     <-- Python script executed ONCE before the collection
|   |-- collection-pos-script.py     <-- Python script executed ONCE after the collection
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
-   `shared` (object): A special object for sharing variables and functions across different scripts within the same collection run. This is particularly useful for `collection-pre-script.py` to set up global data or utility functions that can be accessed by individual request pre/post-scripts.

    In addition to the native helpers provided by the `pm` object, you can import and use any standard or third-party Python library installed in your environment, such as `Faker` for generating realistic test data.

    **Example: Sharing Variables and Functions**

    ```python
    # collection-pre-script.py
    # This script is executed once before everything.

    # You can import any installed Python library, like Faker for generating test data.
    from faker import Faker
    fake = Faker()

    log.info("Starting Collection Pre-Script...")

    # 1. Generate realistic test data with Faker and save it to the environment
    environment_vars["new_user_name"] = fake.name()
    environment_vars["new_user_email"] = fake.email()
    log.info(f"Generated test user: {environment_vars['new_user_name']} ({environment_vars['new_user_email']})")

    # 2. Define a shared global variable using PyMan's helpers
    # Any subsequent script can read or modify this value.
    shared.global_session_id = pm.random_uuid()
    log.info(f"Global Session ID defined: {shared.global_session_id}")

    # 3. Define a shared global function
    # First, define the function normally
    def get_auth_token(username, password):
        """
        An example function that simulates obtaining a token.
        In a real case, you could even make a request here.
        """
        log.info(f"Simulating token acquisition for: {username}")
        # (Logic to fetch the token...)
        token = f"token_{pm.random_chars(10)}"
        
        # Also save the token to the shared scope
        shared.last_generated_token = token
        return token

    # 4. Attach the function to the 'shared' object
    # This makes 'shared.get_auth_token' globally accessible.
    shared.get_auth_token = get_auth_token

    # 5. You can also define environment variables (this already worked)
    environment_vars["execution_start"] = pm.timestamp()

    log.info("Collection Pre-Script completed.")
    ```

-   `response` (`requests.Response`): Available **only in post-scripts**. Contains the request's response object (`response.status_code`, `response.json()`).

### Example of `pos-script.py`

```python
# my-request-pos-script.py

try:
    # 1. Simple test for status code using a lambda function
    pm.test("Status code is 200 OK", lambda: assert response.status_code == 200)

    # If the request was successful, proceed with more detailed tests
    if response.status_code == 200:
        response_body = response.json()

        # 2. More complex test for response structure using a dedicated function
        def test_body_structure():
            assert "id" in response_body, "Response should contain an 'id'"
            assert "token" in response_body, "Response should contain a 'token'"
            assert isinstance(response_body["token"], str)
            assert len(response_body["token"]) > 16, "Token should be longer than 16 characters"
        
        pm.test("Response body has the correct structure and a valid token", test_body_structure)

        # 3. Test for headers using another lambda
        pm.test("Content-Type header is application/json",
                lambda: "application/json" in response.headers.get("Content-Type", ""))

        # 4. Save data to environment variables for the next requests
        if 'id' in response_body:
            environment_vars['LAST_CREATED_ID'] = response_body['id']
            log.info(f"ID saved to environment: {environment_vars['LAST_CREATED_ID']}")
            
except Exception as e:
    log.error(f"Error in POS script: {e}", exc_info=True)

```

## Importing from Postman

PyMan has a built-in command to convert Postman v2.1 collections into the PyMan format. This command converts Postman's JSON files into PyMan's YAML-based directory structure.

### How to Use the Importer

Use the `import-postman` command, providing the path to your Postman collection and an output directory.

```console
python pyman/pyman.py import-postman -c /path/to/your/postman_collection.json -o my_new_pyman_collection
```

To see all available options and get help, run:

```console
python pyman/pyman.py import-postman --help
```

### Arguments

-   `-c`, `--collection`: **(Required)** Path to the Postman collection `.json` file.
-   `-o`, `--output`: **(Required)** Name of the output directory where the PyMan collection will be created.
-   `-e`, `--environment`: (Optional) Path to a Postman environment `.json` file. The variables will be converted into a `.environment-variables` file.
-   `--numbered`: (Optional) Choose whether to add numerical prefixes to folders and files for ordering. Choices: `yes`, `no`. (Default: `yes`).
-   `--numbered-folders`: (Optional) Specifically control numbering for folders. Overrides `--numbered`. Choices: `yes`, `no`.
-   `--numbered-files`: (Optional) Specifically control numbering for files. Overrides `--numbered`. Choices: `yes`, `no`.

### Conversion Details

-   **Folders and Requests**: Are converted into nested directories and `.yaml` files.
-   **Environments**: Variables from the Postman environment are saved in the `.environment-variables` file.
-   **Scripts (Pre-request & Test)**: The importer attempts a basic conversion of simple Javascript code (like `pm.environment.set` and `console.log`) to Python. For more complex scripts, the original JS code is commented out in the corresponding `.py` script file with a `TODO` notice, requiring manual conversion.

---

## Authors

-   Huberto Gastal Mayer
-   Google Gemini, for the help and time saved, thank you!
