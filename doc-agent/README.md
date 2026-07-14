# doc-agent

Servidor MCP (Model Context Protocol) local, em Python, com duas ferramentas:

- **`gerar_readme`** — le a estrutura de um projeto .NET no seu disco e devolve um
  rascunho de `README.md`, para que voce apenas revise e aprove em vez de escrever do zero.
- **`analisar_arquitetura`** — infere o estilo arquitetural do projeto (Clean
  Architecture, MVC em camadas, Hexagonal...) e aponta violacoes de dependencia entre
  camadas, tambem sem IA.

Fase 0/1 do projeto Doc-Agent: roda 100% local, sem Azure DevOps, sem Loop, sem publicar
nada — so le arquivos e retorna texto.

## Como funciona `gerar_readme`

1. Voce aponta `gerar_readme` para a pasta de um projeto/solution .NET (precisa ter ao
   menos um `.csproj` ou `.sln`).
2. O `project_scanner` le, de forma deterministica: target framework, pacotes NuGet
   (via XML dos `.csproj`), estrutura de pastas de alto nivel, controllers/endpoints
   (`[HttpGet]`, `[HttpPost]`, etc. e `app.MapGet(...)` de minimal APIs) e comentarios
   XML (`///`).
3. Se as credenciais do Azure OpenAI estiverem configuradas, a prosa das secoes
   narrativas (o que o sistema faz, para que serve) e escrita por IA — mas **sempre
   com base apenas nos fatos coletados no passo 2**, nunca inventando informacao nova.
4. Se as credenciais nao estiverem configuradas, a ferramenta roda em **modo sem-IA**:
   monta um README estruturado a partir dos metadados, com placeholders
   (`<!-- TODO: preencher -->`) onde a informacao nao pode ser inferida do codigo, e
   avisa isso no topo do conteudo gerado.
5. O conteudo e retornado como texto markdown — nada e escrito no seu disco.

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
cd mcp/doc-agent
uv sync
```

Alternativa sem `uv`:

```bash
cd mcp/doc-agent
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -e .
```

## Configurar o Azure OpenAI (opcional)

Copie `.env.example` para `.env` e preencha:

```bash
cp .env.example .env
```

```text
AZURE_OPENAI_ENDPOINT=https://<seu-recurso>.openai.azure.com
AZURE_OPENAI_API_KEY=<sua-chave>
AZURE_OPENAI_DEPLOYMENT=<nome-do-deployment-de-chat>
AZURE_OPENAI_API_VERSION=2024-10-21
```

Se qualquer uma dessas variaveis estiver faltando, o `gerar_readme` roda automaticamente
em modo sem-IA — nao e preciso configurar nada para testar a ferramenta.

## Rodar os testes

```bash
uv run pytest -v
```

## Subir o servidor (stdio)

```bash
uv run doc-agent
```

O processo fica esperando um cliente MCP conectar via stdio (nao ha saida se estiver
tudo certo — o protocolo e binario/JSON-RPC sobre stdin/stdout).

Para inspecionar manualmente com o [MCP Inspector](https://modelcontextprotocol.io/docs/tools/inspector):

```bash
npx @modelcontextprotocol/inspector uv --directory . run doc-agent
```

## Conectar ao Claude Code

Opcao 1 — CLI:

```bash
claude mcp add doc-agent -- uv --directory "d:/ProjetosPessoais/mcp-doc/mcp/doc-agent" run doc-agent
```

Opcao 2 — editar `.mcp.json` (na raiz do projeto onde voce usa o Claude Code):

```json
{
  "mcpServers": {
    "doc-agent": {
      "command": "uv",
      "args": [
        "--directory",
        "d:/ProjetosPessoais/mcp-doc/mcp/doc-agent",
        "run",
        "doc-agent"
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
    "doc-agent": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "--directory",
        "d:/ProjetosPessoais/mcp-doc/mcp/doc-agent",
        "run",
        "doc-agent"
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

## Estrutura do projeto

```text
src/doc_agent/
  server.py                          # cria o FastMCP e registra as ferramentas; entrypoint stdio
  tools/
    gerar_readme.py                  # orquestra analyzer -> IA opcional -> documentation_engine
    analisar_arquitetura.py          # orquestra analyzer -> documentation_engine (sem IA)
  analyzer/
    project_scanner.py               # le .csproj/.sln, estrutura, controllers, XML docs
    architecture_analyzer.py         # infere estilo arquitetural e violacoes de dependencia
  template_engine/
    markdown.py                      # helpers genericos de markdown (heading, secao, listas)
  documentation_engine/
    readme_generator.py              # monta o README (com ou sem prosa de IA), usa o template_engine
    azure_openai.py                  # wrapper opcional do Azure OpenAI
    architecture_report.py           # monta o relatorio de arquitetura, usa o template_engine
tests/                               # pytest
  fixtures/                          # projeto .NET de exemplo (gerar_readme)
  fixtures_architecture/             # solutions de exemplo (analisar_arquitetura)
```

## Fora de escopo nesta fase

Azure DevOps, abertura de Pull Requests, Microsoft Loop, Microsoft Graph, Microsoft
Agent Framework, transporte HTTP e autenticação Entra ID. Ver `../README.md` para a
visão completa das fases futuras.
