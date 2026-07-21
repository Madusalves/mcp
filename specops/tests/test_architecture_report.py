from pathlib import Path

from specops.analyzer import architecture_analyzer as arch
from specops.analyzer import project_scanner as scanner
from specops.documentation_engine.architecture_report import generate_architecture_report

ARCHITECTURE_FIXTURES_DIR = Path(__file__).parent / "fixtures_architecture"


def test_generate_architecture_report_includes_required_sections() -> None:
    metadata = scanner.scan_project(ARCHITECTURE_FIXTURES_DIR / "clean_architecture")
    analysis = arch.analyze_architecture(metadata)

    report = generate_architecture_report(analysis, metadata.primary_project_name)

    assert "**Estilo detectado:** Clean Architecture (ou variante Onion)" in report
    assert "**Confianca:** 100%" in report
    assert "## Camadas identificadas" in report
    assert "## Violacoes encontradas" in report
    assert "Nenhuma violacao encontrada entre as camadas reconhecidas." in report


def test_generate_architecture_report_formats_violation_line() -> None:
    metadata = scanner.scan_project(ARCHITECTURE_FIXTURES_DIR / "clean_architecture_with_violation")
    analysis = arch.analyze_architecture(metadata)

    report = generate_architecture_report(analysis, metadata.primary_project_name)

    assert "`Application` (application) depende de `Infrastructure` (infrastructure)" in report
