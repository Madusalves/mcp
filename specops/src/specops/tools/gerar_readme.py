"""Implementacao da ferramenta MCP gerar_readme: orquestra fonte -> scanner -> gerador.

Nao chama nenhuma IA - so organiza fatos extraidos deterministicamente do codigo.
Prosa/narrativa fica a cargo do cliente MCP (o assistente de IA do editor de quem
esta chamando a tool), que ja tem contexto suficiente pra preencher os TODOs.
"""

from __future__ import annotations

from specops.analyzer.project_scanner import ProjectValidationError, scan_project
from specops.documentation_engine.readme_generator import generate_readme
from specops.source_resolver import SourceResolutionError, resolve_project_source


def gerar_readme(caminho_projeto: str | None = None, repositorio_git: str | None = None) -> str:
    """Gera um rascunho de README.md a partir de um projeto .NET.

    Informe exatamente um dos dois: `caminho_projeto` (pasta local, deve conter ao
    menos um .csproj ou .sln) ou `repositorio_git` (URL https publica de um
    repositorio, para uso via servidor hospedado sem acesso ao disco local - clona
    raso, analisa e descarta).

    Extrai metadados deterministicos (target framework, pacotes NuGet,
    controllers/endpoints, comentarios XML) e monta um README seguindo um padrao
    fixo. Onde a informacao nao puder ser inferida do codigo (proposito de negocio,
    resumo narrativo), insere um placeholder TODO em vez de inventar - preencher
    isso fica por conta de quem chamou a tool.
    """
    try:
        with resolve_project_source(caminho_projeto, repositorio_git) as root_path:
            metadata = scan_project(root_path)
            return generate_readme(metadata)
    except (SourceResolutionError, ProjectValidationError) as exc:
        raise ValueError(str(exc)) from exc
