"""Entrypoint do servidor MCP Doc-Agent. Expoe a ferramenta gerar_readme via stdio."""

from __future__ import annotations

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from doc_agent.tools.analisar_arquitetura import analisar_arquitetura as _analisar_arquitetura
from doc_agent.tools.gerar_readme import gerar_readme as _gerar_readme

load_dotenv()

mcp = FastMCP("doc-agent")


@mcp.tool()
def gerar_readme(caminho_projeto: str) -> str:
    """Gera um rascunho de README.md a partir de um projeto .NET local.

    Args:
        caminho_projeto: Caminho absoluto de uma pasta contendo um projeto/solution .NET
            (deve conter ao menos um arquivo .csproj ou .sln).

    Returns:
        O conteudo do README.md em markdown.
    """
    return _gerar_readme(caminho_projeto)


@mcp.tool()
def analisar_arquitetura(caminho_projeto: str) -> str:
    """Infere o estilo arquitetural de um projeto .NET local e aponta violacoes
    de dependencia entre camadas.

    Args:
        caminho_projeto: Caminho absoluto de uma pasta contendo um projeto/solution .NET
            (deve conter ao menos um arquivo .csproj ou .sln).

    Returns:
        Relatorio em markdown com estilo detectado, confianca, camadas
        reconhecidas e violacoes encontradas.
    """
    return _analisar_arquitetura(caminho_projeto)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
