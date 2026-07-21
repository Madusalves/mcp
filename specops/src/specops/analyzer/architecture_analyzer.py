"""Inferencia deterministica de estilo arquitetural.

Nao usa IA - so olha para dois sinais que ja existem no codigo:
1. O grafo de ProjectReference entre .csproj (sinal forte: dependencia real
   entre projetos). Se reconhece pelo menos 3 das 4 camadas de Clean
   Architecture/Onion pelos nomes dos projetos, usa esse grafo para apontar
   violacoes de dependencia entre camadas.
2. Na falta desse sinal, os nomes de pasta do repositorio (sinal mais fraco,
   sem grafo de dependencia - so aponta a assinatura mais provavel).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from specops.analyzer.project_scanner import IGNORED_TOP_LEVEL_DIRS, ProjectMetadata

_LAYER_ORDER = ["domain", "application", "infrastructure", "presentation"]

_LAYER_NAME_HINTS: dict[str, list[str]] = {
    "domain": ["domain", "core"],
    "application": ["application", "usecases"],
    "infrastructure": ["infrastructure", "infra", "persistence", "data"],
    "presentation": ["api", "web", "presentation", "ui"],
}

_ALLOWED_REFERENCES: dict[str, set[str]] = {
    "domain": set(),
    "application": {"domain"},
    "infrastructure": {"domain", "application"},
    "presentation": {"domain", "application", "infrastructure"},
}

_FOLDER_SIGNATURES: dict[str, set[str]] = {
    "MVC em camadas": {"controllers", "services", "repositories", "models"},
    "Hexagonal (Ports & Adapters)": {"ports", "adapters"},
}

_MIN_RECOGNIZED_LAYERS = 3
_MIN_FOLDER_SIGNATURE_RATIO = 0.5


@dataclass
class LayerAssignment:
    name: str
    layer: str


@dataclass
class ArchitectureViolation:
    source: str
    source_layer: str
    target: str
    target_layer: str


@dataclass
class ArchitectureAnalysis:
    style: str
    confidence: float
    layers: list[LayerAssignment] = field(default_factory=list)
    violations: list[ArchitectureViolation] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _classify_project_name(project_name: str) -> str | None:
    lowered = project_name.lower()
    for layer in _LAYER_ORDER:
        if any(hint in lowered for hint in _LAYER_NAME_HINTS[layer]):
            return layer
    return None


def _detect_by_project_references(metadata: ProjectMetadata) -> ArchitectureAnalysis | None:
    if len(metadata.csproj_files) < 2:
        return None

    layer_by_project: dict[str, str] = {}
    for csproj in metadata.csproj_files:
        layer = _classify_project_name(csproj.project_name)
        if layer:
            layer_by_project[csproj.project_name] = layer

    distinct_layers = set(layer_by_project.values())
    if len(distinct_layers) < _MIN_RECOGNIZED_LAYERS:
        return None

    violations: list[ArchitectureViolation] = []
    for csproj in metadata.csproj_files:
        source_layer = layer_by_project.get(csproj.project_name)
        if not source_layer:
            continue
        for ref_name in csproj.project_references:
            target_layer = layer_by_project.get(ref_name)
            if not target_layer or target_layer == source_layer:
                continue
            if target_layer not in _ALLOWED_REFERENCES[source_layer]:
                violations.append(
                    ArchitectureViolation(
                        source=csproj.project_name,
                        source_layer=source_layer,
                        target=ref_name,
                        target_layer=target_layer,
                    )
                )

    layers = [LayerAssignment(name=name, layer=layer) for name, layer in sorted(layer_by_project.items())]
    return ArchitectureAnalysis(
        style="Clean Architecture (ou variante Onion)",
        confidence=len(distinct_layers) / len(_LAYER_ORDER),
        layers=layers,
        violations=violations,
    )


def _collect_folder_names(root_path: Path) -> set[str]:
    names: set[str] = set()
    for entry in root_path.rglob("*"):
        if not entry.is_dir():
            continue
        if any(part in IGNORED_TOP_LEVEL_DIRS for part in entry.parts):
            continue
        names.add(entry.name.lower())
    return names


def _detect_by_folder_signature(metadata: ProjectMetadata) -> ArchitectureAnalysis | None:
    found = _collect_folder_names(metadata.root_path)

    best_style: str | None = None
    best_ratio = 0.0
    best_matched: set[str] = set()
    for style, signature in _FOLDER_SIGNATURES.items():
        matched = signature & found
        ratio = len(matched) / len(signature)
        if ratio > best_ratio:
            best_style, best_ratio, best_matched = style, ratio, matched

    if best_style is None or best_ratio < _MIN_FOLDER_SIGNATURE_RATIO:
        return None

    layers = [LayerAssignment(name=folder, layer=folder) for folder in sorted(best_matched)]
    return ArchitectureAnalysis(style=best_style, confidence=best_ratio, layers=layers)


def analyze_architecture(metadata: ProjectMetadata) -> ArchitectureAnalysis:
    """Ponto de entrada: tenta o sinal forte (ProjectReference) e cai para o
    sinal fraco (nomes de pasta) se o primeiro nao for conclusivo."""
    analysis = _detect_by_project_references(metadata)
    if analysis is not None:
        return analysis

    analysis = _detect_by_folder_signature(metadata)
    if analysis is not None:
        return analysis

    return ArchitectureAnalysis(
        style="Indeterminado",
        confidence=0.0,
        notes=[
            "Nao foi possivel reconhecer um padrao de camadas pelos nomes dos "
            "projetos (.csproj) nem pelas pastas do repositorio."
        ],
    )
