from pathlib import Path

import pytest

from doc_agent.analyzer import project_scanner as scanner

FIXTURES_DIR = Path(__file__).parent / "fixtures"
ARCHITECTURE_FIXTURES_DIR = Path(__file__).parent / "fixtures_architecture"


def test_validate_project_path_raises_for_missing_path(tmp_path: Path) -> None:
    with pytest.raises(scanner.ProjectValidationError):
        scanner.validate_project_path(tmp_path / "does-not-exist")


def test_validate_project_path_raises_when_no_csproj_or_sln(tmp_path: Path) -> None:
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    with pytest.raises(scanner.ProjectValidationError):
        scanner.validate_project_path(empty_dir)


def test_validate_project_path_finds_csproj() -> None:
    csproj_files, sln_files = scanner.validate_project_path(FIXTURES_DIR)
    assert csproj_files == [FIXTURES_DIR / "SampleApi.csproj"]
    assert sln_files == []


def test_parse_csproj_extracts_metadata() -> None:
    info = scanner.parse_csproj(FIXTURES_DIR / "SampleApi.csproj")

    assert info.project_name == "SampleApi"
    assert info.target_framework == "net8.0"
    assert info.is_web_sdk is True
    assert info.generates_documentation_file is True

    package_names = {pkg.name for pkg in info.packages}
    assert package_names == {
        "Microsoft.EntityFrameworkCore.SqlServer",
        "Swashbuckle.AspNetCore",
        "MediatR",
    }
    ef_package = next(pkg for pkg in info.packages if pkg.name == "Microsoft.EntityFrameworkCore.SqlServer")
    assert ef_package.version == "8.0.4"


def test_parse_csproj_extracts_project_references() -> None:
    info = scanner.parse_csproj(ARCHITECTURE_FIXTURES_DIR / "clean_architecture" / "Application" / "Application.csproj")

    assert info.project_references == ["Domain"]


def test_scan_top_level_structure_excludes_ignored_dirs(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "bin").mkdir()
    (tmp_path / "obj").mkdir()
    (tmp_path / "README.md").write_text("# hi")

    entries = scanner.scan_top_level_structure(tmp_path)

    assert "src/" in entries
    assert "README.md" in entries
    assert "bin/" not in entries
    assert "obj/" not in entries


def test_find_controllers_extracts_summary_and_endpoints() -> None:
    controllers = scanner.find_controllers(FIXTURES_DIR)

    assert len(controllers) == 1
    controller = controllers[0]
    assert controller.class_name == "OrdersController"
    assert controller.summary == "Expoe operacoes de consulta de pedidos."
    assert len(controller.endpoints) == 1
    assert controller.endpoints[0].method == "HTTPGET"
    assert controller.endpoints[0].route == "{id}"


def test_extract_xml_doc_comments_finds_method_summary() -> None:
    comments = scanner.extract_xml_doc_comments(FIXTURES_DIR)

    symbols = {c.symbol for c in comments}
    assert "GetById" in symbols
    get_by_id = next(c for c in comments if c.symbol == "GetById")
    assert get_by_id.summary == "Retorna um pedido pelo identificador."


def test_scan_project_returns_full_metadata() -> None:
    metadata = scanner.scan_project(FIXTURES_DIR)

    assert metadata.primary_project_name == "SampleApi"
    assert metadata.has_web_endpoints is True
    assert len(metadata.csproj_files) == 1
    assert len(metadata.controllers) == 1
