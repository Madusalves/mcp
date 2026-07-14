"""Implementacao da ferramenta MCP gerar_readme: orquestra scanner -> (IA opcional) -> gerador."""

from __future__ import annotations

import logging
from pathlib import Path

from doc_agent.analyzer.project_scanner import ProjectValidationError, scan_project
from doc_agent.documentation_engine import azure_openai
from doc_agent.documentation_engine.readme_generator import GeneratedProse, generate_readme

logger = logging.getLogger(__name__)


def gerar_readme(caminho_projeto: str) -> str:
    """Gera um rascunho de README.md a partir de um projeto .NET local.

    Le a estrutura do projeto em `caminho_projeto` (deve conter ao menos um .csproj
    ou .sln), extrai metadados deterministicos (target framework, pacotes NuGet,
    controllers/endpoints, comentarios XML) e monta um README seguindo um padrao fixo.
    Se as credenciais do Azure OpenAI estiverem configuradas no ambiente, usa IA para
    redigir a prosa das secoes narrativas; caso contrario, roda em modo sem-IA e avisa
    isso no proprio conteudo retornado. Onde a informacao nao puder ser inferida do
    codigo, insere um placeholder em vez de inventar fatos.
    """
    root_path = Path(caminho_projeto)

    try:
        metadata = scan_project(root_path)
    except ProjectValidationError as exc:
        raise ValueError(str(exc)) from exc

    config = azure_openai.load_config()
    if config is None:
        return generate_readme(metadata, ai_used=False)

    try:
        prose = azure_openai.generate_prose(metadata, config)
        return generate_readme(metadata, prose=prose, ai_used=True)
    except Exception:
        logger.exception("Falha ao gerar prosa via Azure OpenAI; caindo para modo sem-IA.")
        return generate_readme(metadata, prose=GeneratedProse(), ai_used=False)
