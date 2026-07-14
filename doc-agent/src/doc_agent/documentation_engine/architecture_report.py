"""Monta o relatorio markdown de analise de arquitetura a partir de
ArchitectureAnalysis. So formatacao - a inferencia mora em architecture_analyzer.py."""

from __future__ import annotations

from doc_agent.analyzer.architecture_analyzer import ArchitectureAnalysis
from doc_agent.template_engine import markdown as md


def _format_confidence(analysis: ArchitectureAnalysis) -> str:
    return f"{round(analysis.confidence * 100)}%"


def generate_architecture_report(analysis: ArchitectureAnalysis, project_name: str) -> str:
    lines: list[str] = []

    lines.append(md.heading(f"Analise de Arquitetura - {project_name}", level=1))
    lines.append("")
    lines.append(f"**Estilo detectado:** {analysis.style}")
    lines.append(f"**Confianca:** {_format_confidence(analysis)}")
    lines.append("")

    if analysis.layers:
        layer_lines = [f"**{layer.layer.capitalize()}** -> `{layer.name}`" for layer in analysis.layers]
    else:
        layer_lines = [md.TODO]
    lines.extend(md.section("Camadas identificadas", md.bullet_list(layer_lines)))

    if analysis.violations:
        violation_lines = [
            f"`{v.source}` ({v.source_layer}) depende de `{v.target}` ({v.target_layer})"
            for v in analysis.violations
        ]
    else:
        violation_lines = ["Nenhuma violacao encontrada entre as camadas reconhecidas."]
    lines.extend(md.section("Violacoes encontradas", violation_lines))

    if analysis.notes:
        lines.extend(md.section("Observacoes", md.bullet_list(analysis.notes)))

    return "\n".join(lines)
