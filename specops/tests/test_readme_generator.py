from pathlib import Path

from specops.analyzer import project_scanner as scanner
from specops.documentation_engine import readme_generator as generator

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _sample_metadata() -> scanner.ProjectMetadata:
    return scanner.scan_project(FIXTURES_DIR)


def test_generate_readme_uses_placeholder_for_narrative_sections() -> None:
    readme = generator.generate_readme(_sample_metadata())
    assert generator.TODO in readme


def test_generate_readme_includes_project_name_and_title() -> None:
    readme = generator.generate_readme(_sample_metadata())
    assert readme.startswith("<!--")
    assert "# SampleApi" in readme


def test_generate_readme_lists_packages_and_target_framework() -> None:
    readme = generator.generate_readme(_sample_metadata())
    assert "net8.0" in readme
    assert "MediatR" in readme
    assert "Microsoft.EntityFrameworkCore.SqlServer" in readme


def test_generate_readme_infers_db_hint_from_package_name() -> None:
    readme = generator.generate_readme(_sample_metadata())
    assert "SQL Server" in readme


def test_generate_readme_lists_detected_endpoints() -> None:
    readme = generator.generate_readme(_sample_metadata())
    assert "OrdersController" in readme
    assert "HTTPGET" in readme


def test_generate_readme_has_all_required_sections() -> None:
    readme = generator.generate_readme(_sample_metadata())
    for heading in (
        "## Para que serve",
        "## Como rodar localmente",
        "## Arquitetura em 30 segundos",
        "## Estrutura do projeto",
        "## Documentacao",
        "## Contatos",
    ):
        assert heading in readme
