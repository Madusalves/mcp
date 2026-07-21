# SpecOps

Servidor MCP (Model Context Protocol) em Python, com duas ferramentas:

- **`gerar_readme`** — le a estrutura de um projeto .NET e devolve um
  rascunho de `README.md`, para que voce apenas revise e aprove em vez de escrever do zero.
- **`analisar_arquitetura`** — infere o estilo arquitetural do projeto (Clean
  Architecture, MVC em camadas, Hexagonal...) e aponta violacoes de dependencia entre
  camadas.

Nenhuma das duas chama IA por conta própria — o specops só faz leitura e análise
determinística do código. A prosa/narrativa (o que preenche os `<!-- TODO -->`) fica
por conta de quem está chamando a tool: o assistente de IA do seu editor (Cursor,
Claude, etc.) já tem IA própria e contexto de conversa suficiente pra completar isso,
sem o servidor precisar ter (nem pagar por) uma IA embutida.

Roda de duas formas:
- **Local (stdio)** — voce instala e conecta na sua IDE, aponta pra um projeto no seu
  disco (`caminho_projeto`). Ver [Conectar ao Claude Code](#conectar-ao-claude-code) /
  [Conectar ao VS Code](#conectar-ao-vs-code).
- **Hospedado (HTTP)** — um servidor publico que qualquer pessoa conecta por URL, sem
  instalar nada; nesse modo as ferramentas recebem `repositorio_git` (URL publica) em
  vez de um caminho local. Ver [Rodando como serviço público (HTTP)](#rodando-como-servico-publico-http).

Fase 0/1 do projeto SpecOps: sem Azure DevOps, sem Loop, sem publicar nada — so le
codigo (do disco ou de um repositorio publico) e retorna texto.

## Como funciona `gerar_readme`

1. Voce aponta `gerar_readme` para a pasta de um projeto/solution .NET (precisa ter ao
   menos um `.csproj` ou `.sln`).
2. O `project_scanner` le, de forma deterministica: target framework, pacotes NuGet
   (via XML dos `.csproj`), estrutura de pastas de alto nivel, controllers/endpoints
   (`[HttpGet]`, `[HttpPost]`, etc. e `app.MapGet(...)` de minimal APIs) e comentarios
   XML (`///`).
3. O `readme_generator` monta um README estruturado a partir desses metadados. Onde a
   informacao nao pode ser inferida do codigo (proposito de negocio, resumo
   narrativo), insere um placeholder `<!-- TODO: preencher -->` em vez de inventar —
   **nunca chama nenhuma IA por conta propria**.
4. O conteudo e retornado como texto markdown — nada e escrito no seu disco. Preencher
   os TODOs fica por conta de quem chamou a tool (voce, ou o assistente de IA do seu
   editor, que ja tem contexto pra isso).

## Como funciona `analisar_arquitetura`

Tambem 100% deterministico, sem IA. Usa dois sinais, em ordem de prioridade:

1. **Grafo de `ProjectReference`** entre os `.csproj` da solution: cada projeto e
   classificado em uma camada (Domain/Application/Infrastructure/Presentation) pelo
   nome, e as referencias entre eles sao comparadas contra as dependencias permitidas
   de Clean Architecture (ex.: `Application` so pode depender de `Domain`). Qualquer
   referencia fora dessa regra vira uma violacao no relatorio. So e usado quando pelo
   menos 3 das 4 camadas sao reconhecidas.
2. Se esse sinal nao for suficiente, cai para uma **varredura de nomes de pasta**
   (`Controllers/Services/Repositories/Models` para MVC em camadas, `Ports/Adapters`
   para Hexagonal). Sem grafo de dependencia aqui, entao sem deteccao de violacao.

Se nenhum dos dois sinais for conclusivo, o relatorio volta `Indeterminado` em vez de
arriscar um palpite.

## Pre-requisitos

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/) instalado (recomendado). Sem `uv`, use `venv` + `pip`.

## Instalar

```bash
cd mcp/specops
uv sync
```

Alternativa sem `uv`:

```bash
cd mcp/specops
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -e .
```

## Rodar os testes

```bash
uv run pytest -v
```

## Subir o servidor (stdio)

```bash
uv run specops
```

O processo fica esperando um cliente MCP conectar via stdio (nao ha saida se estiver
tudo certo — o protocolo e binario/JSON-RPC sobre stdin/stdout). Esse e o modo padrao
(`SPECOPS_TRANSPORT` nao definido). Para rodar em HTTP, ver a secao
[Rodando como serviço público (HTTP)](#rodando-como-servico-publico-http).

Para inspecionar manualmente com o [MCP Inspector](https://modelcontextprotocol.io/docs/tools/inspector):

```bash
npx @modelcontextprotocol/inspector uv --directory . run specops
```

## Conectar ao Claude Code

Opcao 1 — CLI:

```bash
claude mcp add specops -- uv --directory "d:/ProjetosPessoais/mcp-doc/mcp/specops" run specops
```

Opcao 2 — editar `.mcp.json` (na raiz do projeto onde voce usa o Claude Code):

```json
{
  "mcpServers": {
    "specops": {
      "command": "uv",
      "args": [
        "--directory",
        "d:/ProjetosPessoais/mcp-doc/mcp/specops",
        "run",
        "specops"
      ]
    }
  }
}
```

## Conectar ao VS Code

Em `.vscode/mcp.json`:

```json
{
  "servers": {
    "specops": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "--directory",
        "d:/ProjetosPessoais/mcp-doc/mcp/specops",
        "run",
        "specops"
      ]
    }
  }
}
```

## Usando as ferramentas

Depois de conectado, peça ao agente algo como:

> Use a ferramenta gerar_readme para o projeto em `C:\meus-projetos\MeuSistema`

A ferramenta retorna o markdown do README pronto para você revisar, ajustar os
placeholders e colar no repositório.

> Use a ferramenta analisar_arquitetura para o projeto em `C:\meus-projetos\MeuSistema`

Retorna um relatório markdown com o estilo arquitetural detectado, a confiança da
inferência, as camadas reconhecidas e as violações de dependência encontradas.

Se você estiver conectado no servidor **hospedado** (HTTP), use `repositorio_git` em
vez de `caminho_projeto`:

> Use a ferramenta gerar_readme para o repositório `https://github.com/usuario/MeuSistema`

Exatamente um dos dois parâmetros deve ser informado por chamada — nunca os dois, nunca
nenhum.

## Rodando como serviço público (HTTP)

Nesse modo o servidor roda hospedado (não é mais o cliente quem inicia o processo), e
por isso não tem acesso ao disco de quem está usando. As ferramentas passam a receber
`repositorio_git` (URL https pública) em vez de `caminho_projeto` — o servidor clona
raso (`--depth 1`), analisa e descarta o repositório a cada chamada.

**Limites de abuso aplicados** (não é um serviço público sem controle nenhum, mas
também não é hardening de segurança completo — é o mínimo pra não virar um proxy de
clone-de-repo-qualquer):
- só aceita `https://` de `github.com`, `gitlab.com`, `bitbucket.org` ou `dev.azure.com`;
- timeout de 60s no clone;
- repositório maior que 200MB é rejeitado.

### Rodar localmente em modo HTTP

```bash
SPECOPS_TRANSPORT=streamable-http PORT=8000 uv run specops
```

Sobe em `http://127.0.0.1:8000/mcp`.

### Build da imagem Docker

```bash
docker build -t specops .
docker run -p 8000:8000 specops
```

### Deploy no Railway

Escolha atual para hospedar esta primeira versão pública: deploy via Dockerfile
direto do GitHub, sem CLI obrigatória, com dashboard simples (`railway.json` já
aponta pro `Dockerfile` existente, então nenhuma outra config de build é
necessária).

O que fazer no **dashboard do Railway** (conta em <https://railway.app>, login com
GitHub):

1. **New Project → Deploy from GitHub repo** → selecionar `Madusalves/mcp`.
2. Como esse repo é um monorepo (`specops` é uma subpasta, não a raiz), nas
   **Settings** do serviço criado:
   - **Root Directory**: `specops` (sem isso o Railway tenta buildar a raiz do
     repo e não acha o `Dockerfile`).
   - **Builder**: deve cair em "Dockerfile" automaticamente a partir do
     `railway.json` que está em `specops/railway.json`, assim que o Root
     Directory acima estiver configurado.
3. **Variables**: nenhuma variável precisa ser adicionada manualmente —
   `SPECOPS_TRANSPORT`, `HOST` e `PORT` já vêm do `Dockerfile`. O Railway injeta
   seu próprio valor de `PORT` em runtime, que sobrescreve o `ENV PORT=8000` do
   Dockerfile automaticamente — o `server.py` já lê `PORT`/`HOST` do ambiente, então
   não precisa mexer em nada aqui.
4. **Settings → Networking → Generate Domain**: expõe a porta 8000 publicamente e
   gera uma URL `https://<algo>.up.railway.app`.
5. Deploy automático a cada push na branch `main` já vem habilitado por padrão ao
   conectar o repo (não precisa configurar CI separado).

A URL final do MCP fica `https://<seu-projeto>.up.railway.app/mcp`.

Se preferir a CLI em vez do dashboard:

```bash
railway login              # abre o navegador para autenticar
railway link                # dentro de mcp/specops/, conecta a pasta a um projeto Railway
railway up                  # build + deploy a partir do Dockerfile local
railway domain               # gera/mostra o domínio público
```

### Deploy no Fly.io (alternativa)

Ponto de partida alternativo, não usado no deploy atual: tem tier gratuito, deploy
via Docker em minutos, sem burocracia de assinatura (dá pra migrar para Azure
Container Apps depois, se isso passar a estar ligado a um tenant/empresa específica
— é só trocar o alvo do container, o código não muda).

```bash
fly auth login          # uma vez, cria/loga na conta
fly launch               # dentro de mcp/specops/; detecta o Dockerfile e o fly.toml
fly deploy
```

A URL final fica `https://<seu-app>.fly.dev/mcp`.

### Conectar um cliente ao servidor hospedado

Em vez de `"command"` (stdio), a config do cliente aponta pra URL:

```json
{
  "mcpServers": {
    "specops": {
      "type": "http",
      "url": "https://<seu-projeto>.up.railway.app/mcp"
    }
  }
}
```

Funciona assim no Cursor (`~/.cursor/mcp.json` ou `.cursor/mcp.json` do projeto),
Claude Code (`.mcp.json`) e VS Code (`.vscode/mcp.json`, com `"type": "http"`).

## Estrutura do projeto

```text
src/specops/
  server.py                          # cria o FastMCP, registra as ferramentas; entrypoint stdio/HTTP
  source_resolver.py                 # caminho local ou clone raso de repositorio_git (com limites de abuso)
  tools/
    gerar_readme.py                  # orquestra source_resolver -> analyzer -> documentation_engine
    analisar_arquitetura.py          # orquestra source_resolver -> analyzer -> documentation_engine
  analyzer/
    project_scanner.py               # le .csproj/.sln, estrutura, controllers, XML docs
    architecture_analyzer.py         # infere estilo arquitetural e violacoes de dependencia
  template_engine/
    markdown.py                      # helpers genericos de markdown (heading, secao, listas)
  documentation_engine/
    readme_generator.py              # monta o README (estruturado, sem IA), usa o template_engine
    architecture_report.py           # monta o relatorio de arquitetura, usa o template_engine
tests/                               # pytest
  fixtures/                          # projeto .NET de exemplo (gerar_readme)
  fixtures_architecture/             # solutions de exemplo (analisar_arquitetura)
Dockerfile                           # imagem para o modo HTTP hospedado
railway.json                         # config de deploy no Railway (builder Dockerfile)
fly.toml                             # config de deploy no Fly.io (alternativa, ponto de partida para `fly launch`)
```

## Fora de escopo nesta fase

Azure DevOps, abertura de Pull Requests, Microsoft Loop, Microsoft Graph, Microsoft
Agent Framework, autenticação Entra ID, upload de `.zip`, contas/API keys/rate
limiting real, e deploy automático via CI (o deploy no Fly.io é manual por enquanto).
Ver `../README.md` para a visão completa das fases futuras.
