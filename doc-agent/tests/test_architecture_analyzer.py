from pathlib import Path

from doc_agent.analyzer import architecture_analyzer as arch
from doc_agent.analyzer import project_scanner as scanner

FIXTURES_DIR = Path(__file__).parent / "fixtures"
ARCHITECTURE_FIXTURES_DIR = Path(__file__).parent / "fixtures_architecture"


def test_analyze_architecture_detects_clean_architecture_without_violations() -> None:
    metadata = scanner.scan_project(ARCHITECTURE_FIXTURES_DIR / "clean_architecture")

    analysis = arch.analyze_architecture(metadata)

    assert analysis.style == "Clean Architecture (ou variante Onion)"
    assert analysis.confidence == 1.0
    assert analysis.violations == []
    assert {layer.name for layer in analysis.layers} == {"Domain", "Application", "Infrastructure", "Api"}


def test_analyze_architecture_detects_violation() -> None:
    metadata = scanner.scan_project(ARCHITECTURE_FIXTURES_DIR / "clean_architecture_with_violation")

    analysis = arch.analyze_architecture(metadata)

    assert len(analysis.violations) == 1
    violation = analysis.violations[0]
    assert violation.source == "Application"
    assert violation.source_layer == "application"
    assert violation.target == "Infrastructure"
    assert violation.target_layer == "infrastructure"


def test_analyze_architecture_detects_mvc_layered_from_folders() -> None:
    metadata = scanner.scan_project(ARCHITECTURE_FIXTURES_DIR / "mvc_layered")

    analysis = arch.analyze_architecture(metadata)

    assert analysis.style == "MVC em camadas"
    assert analysis.confidence == 1.0
    assert analysis.violations == []


def test_analyze_architecture_returns_indeterminado_when_no_signal() -> None:
    metadata = scanner.scan_project(FIXTURES_DIR)

    analysis = arch.analyze_architecture(metadata)

    assert analysis.style == "Indeterminado"
    assert analysis.confidence == 0.0
    assert analysis.layers == []
    assert analysis.notes
