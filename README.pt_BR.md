# PyMan - Executor de Requisições via CLI

PyMan: Um executor de requisições HTTP leve, baseado em sistema de arquivos, para linha de comando. Inspirado no Postman e Bruno, executa coleções definidas em arquivos YAML, com suporte a scripts de pré/pós-execução (Python), ambientes e múltiplos tipos de dados. Perfeito para automatizar e versionar seus testes de API junto com o código. ⚡️🐍

---

## Instalação

### Para usuários

Para instalar a versão mais recente diretamente do GitHub, execute:

```console
[sudo] pip install git+https://github.com/betogm/pyman.git
```

### Para desenvolvedores

Se você clonou o repositório e deseja usá-lo para desenvolvimento, siga estes passos:

1.  Certifique-se de ter o Python 3.8+ instalado.
2.  Crie e ative um ambiente virtual (`venv`).

    ```console
    # Crie o ambiente
    python3 -m venv venv
    
    # Ative o ambiente
    source venv/bin/activate
    ```

3.  Instale as dependências.

    ```console
    pip install -r requirements.txt
    ```

Para executar a ferramenta sem a necessidade de instalá-la no sistema, utilize o comando `pyman`. Este modo é ideal para desenvolvimento.

Caso prefira instalar o pacote localmente, você tem duas opções:

-   **Modo editável:** As suas alterações no código-fonte são aplicadas imediatamente.
    ```console
    pip install -e .
    ```

-   **Instalação padrão:**
    ```console
    pip install .
    ```

Após a instalação local, você pode usar o comando `pyman` diretamente.

## Como Usar

Execute o `pyman` com o comando `run` e o alvo desejado. Para desenvolvimento, você também pode usar `pyman`. Os exemplos abaixo usam o comando `pyman`.

### Executar uma coleção inteira

Por padrão, as requisições são executadas em ordem alfabética, com base na estrutura de pastas e arquivos.

```console
pyman run .
```

### Executar uma pasta específica

```console
pyman run Example_Collection/get-request
```

### Executar um arquivo de requisição específico

```console
pyman run Example_Collection/post-request/post-data.yaml
```

### Executar uma coleção com uma ordem específica

Você pode definir ordens de execução personalizadas em um arquivo `config.yaml` na raiz da sua coleção. Use a flag `--collection-order` para especificar qual ordem executar.

```console
pyman run . --collection-order=TestUpload
```

### Relatório HTML

Por padrão, o PyMan gera um relatório HTML após a execução. Para desativá-lo, use a flag `--no-report`:

```console
pyman run . --no-report
```

## Configuração da Coleção

Você pode criar um arquivo `config.yaml` no diretório raiz da sua coleção para definir metadados e ordens de execução personalizadas.

```yaml
# /sua_colecao/config.yaml

COLLECTION_NAME: "Minha Suíte de Testes de API"
DESCRIPTION: "Esta coleção testa os principais endpoints da API pública."

COLLECTIONS_ORDER:
  # A ordem 'Default' é usada quando a flag --collection-order não é fornecida
  Default:
    - auth/login.yaml
    - users/get-users.yaml
    - users/create-user.yaml
  
  # Uma ordem personalizada para rodar apenas testes de upload
  UploadTests:
    - auth/login.yaml
    - files/upload-image.yaml
    - files/upload-document.yaml
```

-   `COLLECTION_NAME`: O nome da coleção, usado como título nos logs e relatórios HTML.
-   `DESCRIPTION`: Uma breve descrição, também exibida no cabeçalho do relatório.
-   `COLLECTIONS_ORDER`: Um dicionário onde cada chave é o nome de uma ordem de execução personalizada. O valor é uma lista de caminhos para os arquivos de requisição, relativos à raiz da coleção.

## Variáveis de Ambiente

Se sua coleção requer variáveis que não estão definidas no `config.yaml`, o PyMan procurará por um arquivo `.environment-variables` no diretório raiz da coleção.

Este arquivo deve conter pares chave-valor (um por linha) no formato `CHAVE="VALOR"`.

**Arquivo de Modelo (Template):**
Você pode fornecer um arquivo `.environment-variables-template`. Se o arquivo `.environment-variables` não existir, o PyMan o criará automaticamente copiando o arquivo de modelo.

Para forçar a substituição do `.environment-variables` existente pelo modelo, use a flag `--force-env`:

```bash
pyman run minha_colecao --force-env
```

Exemplo de `.environment-variables`:
```env
BASE_URL="https://api.exemplo.com"
API_KEY="chave_secreta"
```

## Estrutura de Diretórios

O PyMan espera a seguinte estrutura de arquivos e diretórios:

```text
/seu-projeto/
|
|-- /sua_colecao/
|   |-- config.yaml                  <-- (Opcional) Metadados e ordem de execução da coleção
|   |-- .environment-variables       <-- Variáveis globais (ex: BASE_URL="https://api.com")
|   |-- collection-pre-script.py     <-- Script Python executado UMA VEZ antes da coleção
|   |-- collection-pos-script.py     <-- Script Python executado UMA VEZ depois da coleção
|
|   |-- /logs/
|   |
|   |-- /get-request/
|   |   |-- config.yaml          <-- Metadados da pasta (ex: FOLDER_NAME="Buscar Dados")
|   |   |
|   |   |-- get-data.yaml        <-- Arquivo da Requisição (ver formato abaixo)
|   |   |-- get-data-pos-script.py  <-- Script DEPOIS desta requisição
|   |   |-- get-data-pre-script.py  <-- Script ANTES desta requisição
|   |
|   |-- /post-request/
|       |-- ...
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
-   `shared` (objeto): Um objeto especial para compartilhar variáveis e funções entre diferentes scripts dentro da mesma execução de coleção. Isso é particularmente útil para `collection-pre-script.py` configurar dados globais ou funções utilitárias que podem ser acessadas por scripts de pré/pós-requisição individuais.

    Além dos helpers nativos fornecidos pelo objeto `pm`, você pode importar e usar qualquer biblioteca Python padrão ou de terceiros instalada no seu ambiente, como o `Faker` para gerar dados de teste realistas.

    **Exemplo: Compartilhando Variáveis e Funções**

    ```python
    # collection-pre-script.py
    # Este script é executado uma vez antes de tudo.

    # Você pode importar qualquer biblioteca Python instalada, como o Faker para gerar dados de teste.
    from faker import Faker
    fake = Faker('pt_BR') # Usando a localização em português

    log.info("Iniciando o Collection Pre-Script...")

    # 1. Gerar dados de teste realistas com o Faker e salvá-los no ambiente
    environment_vars["nome_novo_usuario"] = fake.name()
    environment_vars["email_novo_usuario"] = fake.email()
    log.info(f"Usuário de teste gerado: {environment_vars['nome_novo_usuario']} ({environment_vars['email_novo_usuario']})")

    # 2. Definir uma variável global compartilhada usando os helpers do PyMan
    # Qualquer script subsequente pode ler ou modificar este valor.
    shared.id_sessao_global = pm.random_uuid()
    log.info(f"ID de Sessão Global definido: {shared.id_sessao_global}")

    # 3. Definir uma função global compartilhada
    # Primeiro, defina a função normalmente
    def obter_token_autenticacao(username, password):
        """
        Uma função de exemplo que simula a obtenção de um token.
        Em um caso real, você poderia até fazer uma requisição aqui.
        """
        log.info(f"Simulando obtenção de token para: {username}")
        # (Lógica para buscar o token...)
        token = f"token_{pm.random_chars(10)}"
        
        # Salva o token também no escopo compartilhado
        shared.ultimo_token_gerado = token
        return token

    # 4. Anexar a função ao objeto 'shared'
    # Isso torna 'shared.obter_token_autenticacao' acessível globalmente.
    shared.obter_token_autenticacao = obter_token_autenticacao

    # 5. Você também pode definir variáveis de ambiente (isso já funcionava)
    environment_vars["inicio_execucao"] = pm.timestamp()

    log.info("Collection Pre-Script concluído.")
    ```

-   `response` (`requests.Response`): Disponível **apenas em scripts `pos-script`**. Contém o objeto de resposta da requisição (`response.status_code`, `response.json()`).

### Exemplo de `pos-script.py`

```python
# meu-request-pos-script.py

try:
    # 1. Teste simples para o status code usando uma função lambda
    pm.test("O status code da resposta é 200 OK", lambda: assert response.status_code == 200)

    # Se a requisição foi bem-sucedida, prossiga com testes mais detalhados
    if response.status_code == 200:
        response_body = response.json()

        # 2. Teste mais complexo para a estrutura da resposta usando uma função dedicada
        def testar_estrutura_do_corpo():
            assert "id" in response_body, "A resposta deve conter um 'id'"
            assert "token" in response_body, "A resposta deve conter um 'token'"
            assert isinstance(response_body["token"], str)
            assert len(response_body["token"]) > 16, "O token deve ter mais de 16 caracteres"
        
        pm.test("O corpo da resposta tem a estrutura correta e um token válido", testar_estrutura_do_corpo)

        # 3. Teste para cabeçalhos usando outra lambda
        pm.test("O cabeçalho Content-Type é application/json",
                lambda: "application/json" in response.headers.get("Content-Type", ""))

        # 4. Salvar dados em variáveis de ambiente para as próximas requisições
        if 'id' in response_body:
            environment_vars['LAST_ID_CRIADO'] = response_body['id']
            log.info(f"ID salvo no ambiente: {environment_vars['LAST_ID_CRIADO']}")
            
except Exception as e:
    log.error(f"Erro no script POS: {e}", exc_info=True)

```

### Importando do Bruno

Você pode importar uma coleção existente do Bruno usando o comando `import-bruno`:

```bash
pyman import-bruno -c caminho/para/diretorio_colecao -o minha_colecao_pyman
```

Argumentos:
- `-c` ou `--collection`: Caminho para o diretório da coleção Bruno.
- `-o` ou `--output`: Nome do diretório de saída para a coleção PyMan.
- `--numbered`: (Opcional) Adiciona prefixo numérico a pastas e arquivos (padrão: "yes").

### Importando do Postman

O PyMan possui um comando integrado para converter coleções do Postman v2.1 para o formato PyMan. Este comando converte os arquivos JSON do Postman para a estrutura de diretórios e arquivos YAML do PyMan.

### Como Usar o Importador

Use o comando `import-postman`, fornecendo o caminho para a sua coleção do Postman e um diretório de saída.

```console
pyman import-postman -c /caminho/para/sua/postman_collection.json -o minha_nova_colecao_pyman
```

Para ver todas as opções disponíveis e obter ajuda, execute:

```console
pyman import-postman --help
```

### Argumentos

-   `-c`, `--collection`: **(Obrigatório)** Caminho para o arquivo `.json` da coleção do Postman.
-   `-o`, `--output`: **(Obrigatório)** Nome do diretório de saída onde a coleção do PyMan será criada.
-   `-e`, `--environment`: (Opcional) Caminho para um arquivo de ambiente `.json` do Postman. As variáveis serão convertidas para um arquivo `.environment-variables`.
-   `--numbered`: (Opcional) Escolha se deseja adicionar prefixos numéricos a pastas e arquivos para ordenação. Opções: `yes`, `no`. (Padrão: `yes`).
-   `--numbered-folders`: (Opcional) Controla especificamente a numeração para pastas. Sobrescreve `--numbered`. Opções: `yes`, `no`.
-   `--numbered-files`: (Opcional) Controla especificamente a numeração para arquivos. Sobrescreve `--numbered`. Opções: `yes`, `no`.

### Detalhes da Conversão

-   **Pastas e Requisições**: São convertidos em diretórios aninhados e arquivos `.yaml`.
-   **Ambientes**: As variáveis do ambiente do Postman são salvas no arquivo `.environment-variables`.
-   **Scripts (Pre-request & Test)**: O importador tenta uma conversão básica de código Javascript simples (como `pm.environment.set` e `console.log`) para Python. Para scripts mais complexos, o código JS original é comentado no arquivo de script `.py` correspondente com um aviso de `TODO`, exigindo conversão manual.

---

## Autores

-   Huberto Gastal Mayer
-   Google Gemini, pela ajuda e tempo ganho, obrigado!
