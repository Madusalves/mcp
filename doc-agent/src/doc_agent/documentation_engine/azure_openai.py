"""Wrapper opcional do Azure OpenAI: transforma os fatos ja coletados pelo
project_scanner em prosa para o README. Nunca inventa fatos novos - o prompt e
construido apenas com o que foi extraido deterministicamente do codigo."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

from doc_agent.analyzer.project_scanner import ProjectMetadata
from doc_agent.documentation_engine.readme_generator import GeneratedProse

_SYSTEM_PROMPT = (
    "Voce ajuda a escrever a prosa de um README tecnico a partir de fatos extraidos "
    "automaticamente do codigo-fonte de um projeto .NET. Use APENAS os fatos fornecidos. "
    "Nunca invente funcionalidades, integracoes ou proposito de negocio que nao estejam "
    "explicitos nos dados. Se os dados nao permitirem inferir algo com confianca, "
    "responda com string vazia para esse campo. Responda em portugues do Brasil, em tom "
    "tecnico e direto. Responda APENAS com um JSON valido, sem markdown, no formato: "
    '{"one_liner": "...", "purpose": "...", "architecture_summary": "..."}'
)


@dataclass
class AzureOpenAIConfig:
    endpoint: str
    api_key: str
    deployment: str
    api_version: str


def load_config() -> AzureOpenAIConfig | None:
    """Le as credenciais do ambiente. Retorna None se alguma estiver faltando,
    sinalizando que o chamador deve rodar em modo sem-IA."""
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    api_key = os.environ.get("AZURE_OPENAI_API_KEY")
    deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT")
    api_version = os.environ.get("AZURE_OPENAI_API_VERSION")

    if not (endpoint and api_key and deployment and api_version):
        return None

    return AzureOpenAIConfig(
        endpoint=endpoint,
        api_key=api_key,
        deployment=deployment,
        api_version=api_version,
    )


def _build_facts_payload(metadata: ProjectMetadata) -> dict:
    return {
        "project_name": metadata.primary_project_name,
        "target_frameworks": sorted({p.target_framework for p in metadata.csproj_files if p.target_framework}),
        "is_web_project": any(p.is_web_sdk for p in metadata.csproj_files),
        "nuget_packages": [pkg.name for csproj in metadata.csproj_files for pkg in csproj.packages],
        "controllers": [
            {
                "name": c.class_name,
                "summary": c.summary,
                "endpoints": [f"{e.method} {e.route}" for e in c.endpoints],
            }
            for c in metadata.controllers
        ],
        "minimal_api_endpoints": [f"{e.method} {e.route}" for e in metadata.minimal_api_endpoints],
        "xml_doc_comments": [{"symbol": c.symbol, "summary": c.summary} for c in metadata.xml_doc_comments],
        "top_level_structure": metadata.top_level_entries,
    }


def generate_prose(metadata: ProjectMetadata, config: AzureOpenAIConfig) -> GeneratedProse:
    """Chama o Azure OpenAI para gerar a prosa do README. Levanta a excecao original
    do cliente OpenAI em caso de falha - quem chama decide como degradar."""
    from openai import AzureOpenAI

    client = AzureOpenAI(
        azure_endpoint=config.endpoint,
        api_key=config.api_key,
        api_version=config.api_version,
    )

    facts = _build_facts_payload(metadata)
    response = client.chat.completions.create(
        model=config.deployment,
        temperature=0.2,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(facts, ensure_ascii=False)},
        ],
    )

    content = response.choices[0].message.content or "{}"
    data = json.loads(content)

    return GeneratedProse(
        one_liner=data.get("one_liner") or None,
        purpose=data.get("purpose") or None,
        architecture_summary=data.get("architecture_summary") or None,
    )
