"""Monta o rascunho de README.md a partir de ProjectMetadata.

So organiza os fatos coletados pelo project_scanner - nunca inventa informacao.
Onde o codigo nao permite inferir algo (proposito de negocio, resumo narrativo),
insere um placeholder TODO em vez de chutar. O specops nao chama nenhuma IA por
conta propria: preencher esses TODOs (ou reescrever a prosa) fica a cargo de quem
chamou a tool - tipicamente o proprio assistente de IA do editor (Cursor, Claude,
etc.), que ja tem acesso ao restante do contexto da conversa.
"""

from __future__ import annotations

from specops.analyzer.project_scanner import ProjectMetadata
from specops.template_engine import markdown as md

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


def generate_readme(metadata: ProjectMetadata) -> str:
    lines: list[str] = []

    lines.append(
        "<!-- Rascunho gerado deterministicamente a partir do codigo. Secoes com "
        f"{TODO} nao podem ser inferidas do repositorio - complete-as ou peca para "
        "o assistente de IA do seu editor preencher usando o contexto da conversa. -->"
    )
    lines.append("")

    project_name = metadata.primary_project_name
    lines.append(md.heading(project_name, level=1))
    lines.append("")
    lines.append(TODO)
    lines.append("")

    lines.extend(md.section("Para que serve", [TODO]))

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
