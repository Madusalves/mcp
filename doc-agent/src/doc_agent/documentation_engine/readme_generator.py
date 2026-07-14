"""Monta o rascunho de README.md a partir de ProjectMetadata.

Funciona em dois modos:
- Sem IA: so organiza os fatos coletados pelo project_scanner, com placeholders
  onde a informacao nao pode ser inferida do codigo.
- Com IA: recebe um GeneratedProse (produzido pelo azure_openai.py) e usa a prosa
  para as secoes narrativas, mas os fatos (pacotes, endpoints, comandos) continuam
  vindo sempre do scanner - a IA nunca inventa dados novos.
"""

from __future__ import annotations

from dataclasses import dataclass

from doc_agent.analyzer.project_scanner import ProjectMetadata
from doc_agent.template_engine import markdown as md

TODO = md.TODO

_OBVIOUS_TOP_LEVEL_ENTRIES = {
    "program.cs",
    "startup.cs",
    "appsettings.json",
    "appsettings.development.json",
    ".gitignore",
    ".editorconfig",
    ".dockerignore",
}

_KNOWN_DB_PACKAGE_HINTS = {
    "sqlserver": "SQL Server",
    "npgsql": "PostgreSQL",
    "sqlite": "SQLite",
    "mongodb": "MongoDB",
    "cosmos": "Azure Cosmos DB",
}


@dataclass
class GeneratedProse:
    """Prosa opcional gerada por IA. Todos os campos sao opcionais; quando ausentes,
    o gerador cai de volta para o formato estruturado sem-IA nessa secao."""

    one_liner: str | None = None
    purpose: str | None = None
    architecture_summary: str | None = None


def _is_obvious_entry(entry: str) -> bool:
    return entry.lower() in _OBVIOUS_TOP_LEVEL_ENTRIES or entry.lower().endswith((".csproj", ".sln"))


def _infer_project_type(metadata: ProjectMetadata) -> str:
    if metadata.controllers or metadata.minimal_api_endpoints:
        return "Web API (ASP.NET Core)"
    if any(p.is_web_sdk for p in metadata.csproj_files):
        return "Aplicacao Web (ASP.NET Core)"
    if metadata.csproj_files:
        return "Aplicacao/biblioteca .NET"
    return TODO


def _target_frameworks(metadata: ProjectMetadata) -> list[str]:
    frameworks = {p.target_framework for p in metadata.csproj_files if p.target_framework}
    return sorted(frameworks)


def _dotnet_sdk_prerequisite(metadata: ProjectMetadata) -> str:
    frameworks = _target_frameworks(metadata)
    if not frameworks:
        return f"SDK do .NET (versao {TODO})"
    versions = ", ".join(fw.replace("net", ".NET ") for fw in frameworks)
    return f"SDK do {versions}"

def _format_prerequisites(metadata: ProjectMetadata) -> list[str]:
    return [_dotnet_sdk_prerequisite(metadata)]


def _format_run_steps(metadata: ProjectMetadata) -> list[str]:
    steps = ["dotnet restore", "dotnet build"]
    if metadata.has_web_endpoints:
        steps.append("dotnet run")
        steps.append(f"Acesse `{TODO}` (URL/porta definida em `launchSettings.json` ou `appsettings.json`)")
    else:
        steps.append("dotnet run")
    return steps

def _format_packages(metadata: ProjectMetadata, limit: int = 12) -> list[str]:
    lines = []
    seen = set()
    for csproj in metadata.csproj_files:
        for pkg in csproj.packages:
            if pkg.name in seen:
                continue
            seen.add(pkg.name)
            version = f" ({pkg.version})" if pkg.version else ""
            lines.append(f"{pkg.name}{version}")
    return lines[:limit]


def _infer_dependency_hints(metadata: ProjectMetadata) -> list[str]:
    hints = []
    for csproj in metadata.csproj_files:
        for pkg in csproj.packages:
            lowered = pkg.name.lower()
            for keyword, label in _KNOWN_DB_PACKAGE_HINTS.items():
                if keyword in lowered and label not in hints:
                    hints.append(label)
    return hints


def _format_structure(metadata: ProjectMetadata) -> list[str]:
    return [entry for entry in metadata.top_level_entries if not _is_obvious_entry(entry)]


def _format_endpoints(metadata: ProjectMetadata, limit: int = 15) -> list[str]:
    lines = []
    for controller in metadata.controllers:
        header = f"**{controller.class_name}**"
        if controller.summary:
            header += f" - {controller.summary}"
        lines.append(header)
        for endpoint in controller.endpoints:
            route = endpoint.route or ""
            lines.append(f"  - `{endpoint.method}` `{route}`")
    for endpoint in metadata.minimal_api_endpoints:
        lines.append(f"- `{endpoint.method}` `{endpoint.route}` ({endpoint.handler_file})")
    return lines[:limit]


def generate_readme(
    metadata: ProjectMetadata,
    prose: GeneratedProse | None = None,
    ai_used: bool = False,
) -> str:
    prose = prose or GeneratedProse()
    lines: list[str] = []

    if not ai_used:
        lines.append(
            "<!-- Gerado em modo sem-IA: Azure OpenAI nao configurado. "
            "Apenas metadados estruturados extraidos do codigo, sem prosa gerada por IA. -->"
        )
        lines.append("")

    project_name = metadata.primary_project_name
    one_liner = prose.one_liner or TODO
    lines.append(md.heading(project_name, level=1))
    lines.append("")
    lines.append(one_liner)
    lines.append("")

    lines.extend(md.section("Para que serve", [prose.purpose or TODO]))

    lines.append(md.heading("Como rodar localmente", level=2))
    lines.append("")
    lines.append(md.heading("Pre-requisitos", level=3))
    lines.extend(md.bullet_list(_format_prerequisites(metadata)))
    lines.append("")
    lines.append(md.heading("Passos", level=3))
    lines.extend(md.numbered_list(_format_run_steps(metadata)))
    lines.append("")

    lines.append(md.heading("Arquitetura em 30 segundos", level=2))
    lines.append("")
    lines.append(f"- **Tipo:** {_infer_project_type(metadata)}")
    frameworks = _target_frameworks(metadata)
    if frameworks:
        lines.append(f"- **Target framework:** {', '.join(frameworks)}")
    packages = _format_packages(metadata)
    if packages:
        lines.append(f"- **Principais dependencias (NuGet):** {', '.join(packages)}")
    else:
        lines.append(f"- **Principais dependencias (NuGet):** {TODO}")
    hints = _infer_dependency_hints(metadata)
    if hints:
        lines.append(f"- **Indicios de armazenamento/infra:** {', '.join(hints)} (inferido de pacotes NuGet)")
    lines.append(f"- **O que consome este sistema:** {TODO}")
    if prose.architecture_summary:
        lines.append("")
        lines.append(prose.architecture_summary)
    if metadata.has_web_endpoints:
        lines.append("")
        lines.append(md.heading("Endpoints identificados", level=3))
        lines.extend(_format_endpoints(metadata))
    lines.append("")

    structure = _format_structure(metadata)
    structure_body = md.bullet_list([f"`{entry}`" for entry in structure]) if structure else [TODO]
    lines.extend(md.section("Estrutura do projeto", structure_body))

    lines.extend(
        md.section(
            "Documentacao",
            md.bullet_list(["ADRs: `docs/adr/`", "Specs: `docs/specs/`", "Runbooks: `docs/runbooks/`"]),
        )
    )

    lines.extend(
        md.section(
            "Contatos",
            md.bullet_list([f"Time responsavel: {TODO}", f"Canal de suporte: {TODO}"]),
        )
    )

    return "\n".join(lines)
