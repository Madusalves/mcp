"""Entrypoint do servidor MCP Doc-Agent. Expoe gerar_readme e analisar_arquitetura.

Transporte selecionavel por variavel de ambiente (DOC_AGENT_TRANSPORT):
- "stdio" (padrao): uso local, cliente inicia o processo (Claude Code, VS Code, Cursor).
- "streamable-http": servidor hospedado, cliente conecta por URL. Nesse modo as
  tools recebem repositorio_git em vez de caminho_projeto (ver source_resolver.py).
"""

from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP

from doc_agent.tools.analisar_arquitetura import analisar_arquitetura as _analisar_arquitetura
from doc_agent.tools.gerar_readme import gerar_readme as _gerar_readme

mcp = FastMCP(
    "doc-agent",
    host=os.environ.get("HOST", "127.0.0.1"),
    port=int(os.environ.get("PORT", "8000")),
)


@mcp.tool()
def gerar_readme(caminho_projeto: str | None = None, repositorio_git: str | None = None) -> str:
    """Gera um rascunho de README.md a partir de um projeto .NET.

    Args:
        caminho_projeto: Caminho absoluto de uma pasta local contendo um projeto/solution
            .NET (deve conter ao menos um arquivo .csproj ou .sln). Use este OU repositorio_git.
        repositorio_git: URL https publica de um repositorio (GitHub, GitLab, Bitbucket
            ou Azure DevOps). O servidor clona raso, analisa e descarta. Use este OU
            caminho_projeto.

    Returns:
        O conteudo do README.md em markdown.
    """
    return _gerar_readme(caminho_projeto, repositorio_git)


@mcp.tool()
def analisar_arquitetura(caminho_projeto: str | None = None, repositorio_git: str | None = None) -> str:
    """Infere o estilo arquitetural de um projeto .NET e aponta violacoes
    de dependencia entre camadas.

    Args:
        caminho_projeto: Caminho absoluto de uma pasta local contendo um projeto/solution
            .NET (deve conter ao menos um arquivo .csproj ou .sln). Use este OU repositorio_git.
        repositorio_git: URL https publica de um repositorio (GitHub, GitLab, Bitbucket
            ou Azure DevOps). O servidor clona raso, analisa e descarta. Use este OU
            caminho_projeto.

    Returns:
        Relatorio em markdown com estilo detectado, confianca, camadas
        reconhecidas e violacoes encontradas.
    """
    return _analisar_arquitetura(caminho_projeto, repositorio_git)


def main() -> None:
    mcp.run(transport=os.environ.get("DOC_AGENT_TRANSPORT", "stdio"))


if __name__ == "__main__":
    main()
