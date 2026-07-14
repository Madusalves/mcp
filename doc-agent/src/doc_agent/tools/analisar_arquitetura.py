"""Implementacao da ferramenta MCP analisar_arquitetura: orquestra scanner ->
architecture_analyzer -> architecture_report."""

from __future__ import annotations

from pathlib import Path

from doc_agent.analyzer.architecture_analyzer import analyze_architecture
from doc_agent.analyzer.project_scanner import ProjectValidationError, scan_project
from doc_agent.documentation_engine.architecture_report import generate_architecture_report


def analisar_arquitetura(caminho_projeto: str) -> str:
    """Infere o estilo arquitetural de um projeto .NET local e aponta violacoes
    de dependencia entre camadas.

    Le a estrutura do projeto em `caminho_projeto` (deve conter ao menos um .csproj
    ou .sln), classifica os projetos em camadas (Domain/Application/Infrastructure/
    Presentation) pelo nome e usa o grafo de ProjectReference entre eles para
    detectar dependencias na direcao errada. Se esse sinal nao for suficiente,
    cai para uma varredura de nomes de pasta (Controllers/Services/Repositories/
    Models para MVC, Ports/Adapters para Hexagonal).
    """
    root_path = Path(caminho_projeto)

    try:
        metadata = scan_project(root_path)
    except ProjectValidationError as exc:
        raise ValueError(str(exc)) from exc

    analysis = analyze_architecture(metadata)
    return generate_architecture_report(analysis, metadata.primary_project_name)
