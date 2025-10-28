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
/your-project/
|
|-- README.md
|-- requirements.txt
|-- pyproject.toml
|
|-- /pyman/
|   |-- pyman.py
|   |-- core_logic.py
|   |-- request_parser.py
|   |-- pyman_helpers.py
|
|   |-- run_20251027_103000.log   <-- Execution logs (created automatically)
|
|   |-- /example_collection/         <-- (Name without spaces, e.g., get-users)
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
        env["AUTH_TOKEN"] = token
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

## Scripts (Pre e Pos)

Scripts são arquivos Python que têm acesso a quatro variáveis globais:

-   `environment_vars` (dict): O dicionário de variáveis de ambiente. Você pode ler (`environment_vars['BASE_URL']`) e escrever (`environment_vars['NOVA_VAR'] = 'valor'`) nele. **Alterações feitas neste dicionário serão automaticamente salvas de volta no arquivo `.environment-variables` após a execução do script.**
-   `pm` (module): O módulo `pyman_helpers`. Use `pm.random_int()`, `pm.random_adjective()`, ou `pm.test()`.
-   `log` (Logger): A instância do logger da execução atual. Você pode usá-la para registrar mensagens no log do PyMan (ex: `log.info('Mensagem')`, `log.error('Erro')`).
-   `pm.test(name, condition_func)`: Uma função para realizar asserções nos seus scripts, similar ao `pm.test()` do Postman. `name` é o nome do teste (string) e `condition_func` é uma função lambda ou regular que contém a lógica de asserção. Se a asserção falhar, o teste será marcado como `FAILED` no log. Exemplo:
    ```python
    pm.test("Status code is 200", lambda: assert response.status_code == 200)
    ```
    **Nota:** Se uma asserção falhar, o `pm.test()` registrará o erro, mas não interromperá a execução do script nem gerará um traceback completo.
-   `response` (`requests.Response`): Disponível **apenas em scripts `pos-script`**. Contém o objeto de resposta da requisição (`response.status_code`, `response.json()`).

### Example of `pos-script.py`

```python
# my-request-pos-script.py

try:
    if response.status_code == 200:
        print("POS script: Request OK!")
        data = response.json()
        
        # Extracts an ID from the response and saves it to the environment
        if 'id' in data:
            env['LAST_CREATED_ID'] = data['id']
            print(f"ID saved to environment: {env['LAST_CREATED_ID']}")
            
except Exception as e:
    print(f"Error in POS script: {e}")

```