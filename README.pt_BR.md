# PyMan - Executor de Requisições via CLI

PyMan: A lightweight, filesystem-based HTTP request runner for CLI. Inspired by Postman and Bruno, it executes collections defined in YAML files, supporting pre/post-run scripts (Python), environments, and multiple data types. Perfect for automating and version-controlling your API tests right alongside your code. ⚡️🐍

---

## Instalação

1.  Certifique-se de ter o Python 3.8+ instalado.
2.  Crie e ative um ambiente virtual (`venv`).

    ```console
    # Crie o ambiente
    python3 -m venv venv
    
    # Ative o ambiente
    source venv/bin/activate
    ```

3.  Instale as dependências (crie um arquivo `requirements.txt` se não existir).

    ```console
    pip install -r requirements.txt
    ```

## Como Usar

Execute o `pyman.py` (dentro da pasta `pyman`) com o comando `run` e o alvo desejado.

### Executar uma coleção inteira

Para executar todas as requisições na raiz do projeto:

```console
python pyman/pyman.py run .
```

### Executar uma pasta específica

```console
python pyman/pyman.py run Example_Collection/get-request
```

### Executar um arquivo de requisição específico

```console
python pyman/pyman.py run Example_Collection/post-request/post-data.yaml
```

## Estrutura de Diretórios

O PyMan espera a seguinte estrutura de arquivos e diretórios:

```text
/seu-projeto/
|
|-- /tests_collection/         <-- (Nome sem espaços, ex: get-users)
|   |-- .environment-variables       <-- Variáveis globais (ex: BASE_URL="https://api.com")
|   |-- collection-pre-script.py     <-- Script Python executado ANTES de CADA requisição
|   |-- collection-pos-script.py     <-- Script Python executado DEPOIS de CADA requisição
|
|   |-- /logs/
|   |   |-- run_20251027_103000.log   <-- Logs de execução (criado automaticamente)
|   |
|   |-- /example-get-request/
|   |   |-- config.yaml          <-- Metadados da pasta (ex: FOLDER_NAME="Buscar Dados")
|   |   |
|   |   |-- get-data.yaml        <-- Arquivo da Requisição (ver formato abaixo)
|   |   |-- get-data-pos-script.py  <-- Script DEPOIS desta requisição
|   |   |-- get-data-pre-script.py  <-- Script ANTES desta requisição
|   |
|   |-- /example-post-request/
|       |-- ...
|
|-- /outra-pasta/
|   |-- ...
```

## Formato do Arquivo de Requisição (.yaml)

As requisições são definidas em arquivos `.yaml` com uma estrutura clara, separando método, URL, parâmetros, autenticação, cabeçalhos e corpo.

```yaml
# Exemplo de arquivo de requisição: get-data.yaml

request:
  method: GET
  url: "{{BASE_URL}}/get"

params:
  param1: "valor"
  random: "{{pm.random_int(1, 100)}}"

authentication:
  bearer_token: "{{AUTH_TOKEN}}"

headers:
  Accept: "application/json"
  User-Agent: "{{USER_AGENT}}"

# O corpo (body) é opcional para métodos como GET
body: ""
```

Para requisições `POST` com corpo `JSON`, a estrutura é similar:

```yaml
# Exemplo de arquivo POST: post-data.yaml

request:
  method: POST
  url: "{{BASE_URL}}/post"

authentication:
  bearer_token: "{{PROD_TOKEN}}"

headers:
  Content-Type: "application/json"

body: |
  {
    "name": "Meu Item",
    "value": {{pm.random_int(1, 100)}}
  }
```

## Scripts (Pre e Pos)

Scripts são arquivos Python que têm acesso a três variáveis globais:

-   `env` (dict): O dicionário de variáveis de ambiente. Você pode ler (`env['BASE_URL']`) e escrever (`env['NOVA_VAR'] = 'valor'`) nele.
-   `pm` (module): O módulo `pyman_helpers`. Use `pm.random_int()` ou `pm.random_adjective()`.
-   `response` (`requests.Response`): Disponível **apenas em scripts `pos-script`**. Contém o objeto de resposta da requisição (`response.status_code`, `response.json()`).

### Exemplo de `pos-script.py`

```python
# meu-request-pos-script.py

try:
    if response.status_code == 200:
        print("Script POS: Requisição OK!")
        data = response.json()
        
        # Extrai um ID da resposta e salva no ambiente
        if 'id' in data:
            env['LAST_ID_CRIADO'] = data['id']
            print(f"ID salvo no ambiente: {env['LAST_ID_CRIADO']}")
            
except Exception as e:
    print(f"Erro no script POS: {e}")

```