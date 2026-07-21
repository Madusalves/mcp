"""Entrypoint do servidor MCP SpecOps. Expoe gerar_readme e analisar_arquitetura.

Transporte selecionavel por variavel de ambiente (SPECOPS_TRANSPORT):
- "stdio" (padrao): uso local, cliente inicia o processo (Claude Code, VS Code, Cursor).
- "streamable-http": servidor hospedado, cliente conecta por URL. Nesse modo as
  tools recebem repositorio_git em vez de caminho_projeto (ver source_resolver.py).
"""

from __future__ import annotations

import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import HTMLResponse

from specops.tools.analisar_arquitetura import analisar_arquitetura as _analisar_arquitetura
from specops.tools.gerar_readme import gerar_readme as _gerar_readme

mcp = FastMCP(
    "specops",
    host=os.environ.get("HOST", "127.0.0.1"),
    port=int(os.environ.get("PORT", "8000")),
)

_LANDING_PAGE = Path(__file__).parent / "static" / "index.html"


@mcp.custom_route("/", methods=["GET"])
async def landing_page(request: Request) -> HTMLResponse:
    """Pagina estatica publica (nao MCP) explicando o servidor, so ativa em modo HTTP."""
    return HTMLResponse(_LANDING_PAGE.read_text(encoding="utf-8"))


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
    mcp.run(transport=os.environ.get("SPECOPS_TRANSPORT", "stdio"))


if __name__ == "__main__":
    main()
