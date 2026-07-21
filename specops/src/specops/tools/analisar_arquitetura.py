"""Implementacao da ferramenta MCP analisar_arquitetura: orquestra scanner ->
architecture_analyzer -> architecture_report."""

from __future__ import annotations

from specops.analyzer.architecture_analyzer import analyze_architecture
from specops.analyzer.project_scanner import ProjectValidationError, scan_project
from specops.documentation_engine.architecture_report import generate_architecture_report
from specops.source_resolver import SourceResolutionError, resolve_project_source


def analisar_arquitetura(caminho_projeto: str | None = None, repositorio_git: str | None = None) -> str:
    """Infere o estilo arquitetural de um projeto .NET e aponta violacoes de
    dependencia entre camadas.

    Informe exatamente um dos dois: `caminho_projeto` (pasta local, deve conter ao
    menos um .csproj ou .sln) ou `repositorio_git` (URL https publica de um
    repositorio, para uso via servidor hospedado sem acesso ao disco local - clona
    raso, analisa e descarta).

    Classifica os projetos em camadas (Domain/Application/Infrastructure/
    Presentation) pelo nome e usa o grafo de ProjectReference entre eles para
    detectar dependencias na direcao errada. Se esse sinal nao for suficiente,
    cai para uma varredura de nomes de pasta (Controllers/Services/Repositories/
    Models para MVC, Ports/Adapters para Hexagonal).
    """
    try:
        with resolve_project_source(caminho_projeto, repositorio_git) as root_path:
            metadata = scan_project(root_path)
            analysis = analyze_architecture(metadata)
            return generate_architecture_report(analysis, metadata.primary_project_name)
    except (SourceResolutionError, ProjectValidationError) as exc:
        raise ValueError(str(exc)) from exc
