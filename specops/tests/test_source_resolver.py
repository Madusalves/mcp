from pathlib import Path

import pytest

from specops import source_resolver as resolver


def test_raises_when_neither_source_is_given() -> None:
    with pytest.raises(resolver.SourceResolutionError):
        with resolver.resolve_project_source(None, None):
            pass


def test_raises_when_both_sources_are_given() -> None:
    with pytest.raises(resolver.SourceResolutionError):
        with resolver.resolve_project_source("C:/algum/lugar", "https://github.com/usuario/repo"):
            pass


def test_local_path_is_returned_directly(tmp_path: Path) -> None:
    with resolver.resolve_project_source(str(tmp_path), None) as root_path:
        assert root_path == tmp_path


def test_raises_for_host_outside_allowlist() -> None:
    with pytest.raises(resolver.SourceResolutionError):
        with resolver.resolve_project_source(None, "https://evil.example.com/usuario/repo.git"):
            pass


def test_raises_for_non_https_scheme() -> None:
    with pytest.raises(resolver.SourceResolutionError):
        with resolver.resolve_project_source(None, "file:///etc/passwd"):
            pass


def test_raises_for_ssh_style_url() -> None:
    with pytest.raises(resolver.SourceResolutionError):
        with resolver.resolve_project_source(None, "git@github.com:usuario/repo.git"):
            pass


def test_git_source_is_cloned_and_cleaned_up(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_clone(url: str, dest: Path) -> None:
        dest.mkdir(parents=True)
        (dest / "Sample.csproj").write_text("<Project />")

    monkeypatch.setattr(resolver, "_clone_shallow", fake_clone)

    captured_path: Path | None = None
    with resolver.resolve_project_source(None, "https://github.com/usuario/repo") as root_path:
        captured_path = root_path
        assert root_path.exists()
        assert (root_path / "Sample.csproj").exists()

    assert captured_path is not None
    assert not captured_path.exists()


def test_git_source_raises_when_repo_too_large(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_clone(url: str, dest: Path) -> None:
        dest.mkdir(parents=True)
        (dest / "big.bin").write_bytes(b"0" * 1024)

    monkeypatch.setattr(resolver, "_clone_shallow", fake_clone)
    monkeypatch.setattr(resolver, "_MAX_REPO_SIZE_BYTES", 100)

    with pytest.raises(resolver.SourceResolutionError):
        with resolver.resolve_project_source(None, "https://github.com/usuario/repo"):
            pass
