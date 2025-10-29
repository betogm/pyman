# PyMan - Executor de Requisições via CLI

PyMan: Um executor de requisições HTTP leve, baseado em sistema de arquivos, para linha de comando. Inspirado no Postman e Bruno, executa coleções definidas em arquivos YAML, com suporte a scripts de pré/pós-execução (Python), ambientes e múltiplos tipos de dados. Perfeito para automatizar e versionar seus testes de API junto com o código. ⚡️🐍

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

## Pre-Requests (Encadeamento de Requisições)

Você pode encadear requisições usando a chave `pre-requests` no seu arquivo `.yaml`. Isso permite executar uma ou mais requisições antes da principal, o que é útil para cenários como autenticação, onde você precisa obter um token antes de fazer a chamada final.

As requisições listadas em `pre-requests` são executadas em ordem, e cada uma executa seu ciclo completo (incluindo pre e pos scripts).

### Exemplo

Imagine que `get-resource.yaml` precisa de um token de autenticação que é obtido por `login.yaml`.

```yaml
# /collections/auth/login.yaml
# Esta requisição obtém um token e o salva no ambiente através de um pos-script.

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
# Salva o token da resposta no ambiente.

if response.status_code == 200:
    token = response.json().get("token")
    if token:
        environment_vars["AUTH_TOKEN"] = token
        print("Token salvo no ambiente.")
```

```yaml
# /collections/data/get-resource.yaml
# Esta requisição usa o token obtido pela pre-request.

pre-requests:
  - ../auth/login.yaml  # Caminho relativo para a requisição de login

request:
  method: GET
  url: "{{BASE_URL}}/resource"
authentication:
  bearer_token: "{{AUTH_TOKEN}}" # Usa o token salvo no ambiente
```

Quando `get-resource.yaml` for executado:
1.  O PyMan primeiro executará `login.yaml`.
2.  O `login-pos-script.py` será executado, salvando o token.
3.  Finalmente, a requisição principal em `get-resource.yaml` será executada, usando o token que agora está no ambiente.

## Scripts (Pre e Pos)

Scripts são arquivos Python que têm acesso a três variáveis globais:

-   `environment_vars` (dict): O dicionário de variáveis de ambiente. Você pode ler (`environment_vars['BASE_URL']`) e escrever (`environment_vars['NOVA_VAR'] = 'valor'`) nele.
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
            environment_vars['LAST_ID_CRIADO'] = data['id']
            print(f"ID salvo no ambiente: {environment_vars['LAST_ID_CRIADO']}")
            
except Exception as e:
    print(f"Erro no script POS: {e}")

```

## Importando do Postman

O PyMan inclui um script para converter coleções do Postman v2.1 para o formato do PyMan. O script `pyman/postman_importer.py` converte os arquivos JSON do Postman para a estrutura de diretórios e arquivos YAML do PyMan.

### Como Usar o Importador

Execute o script a partir do seu terminal, fornecendo o caminho para a sua coleção do Postman e um diretório de saída.

```console
python pyman/postman_importer.py -c /caminho/para/sua/postman_collection.json -o minha_nova_colecao_pyman
```

### Argumentos

-   `-c`, `--collection`: **(Obrigatório)** Caminho para o arquivo `.json` da coleção do Postman.
-   `-o`, `--output`: **(Obrigatório)** Nome do diretório de saída onde a coleção do PyMan será criada.
-   `-e`, `--environment`: (Opcional) Caminho para um arquivo de ambiente `.json` do Postman. As variáveis serão convertidas para um arquivo `.environment-variables`.

### Detalhes da Conversão

-   **Pastas e Requisições**: São convertidos em diretórios aninhados e arquivos `.yaml`.
-   **Ambientes**: As variáveis do ambiente do Postman são salvas no arquivo `.environment-variables`.
-   **Scripts (Pre-request & Test)**: O importador tenta uma conversão básica de código Javascript simples (como `pm.environment.set` e `console.log`) para Python. Para scripts mais complexos, o código JS original é comentado no arquivo de script `.py` correspondente com um aviso de `TODO`, exigindo conversão manual.
