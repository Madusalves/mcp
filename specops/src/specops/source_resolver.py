"""Resolve de onde vem o codigo a ser analisado: um caminho local (uso via stdio,
mesma maquina) ou uma URL de repositorio Git publico (uso via HTTP, servidor
hospedado sem acesso ao disco de quem chama). Os analyzers so recebem um Path no
final - nao sabem qual dos dois modos foi usado."""

from __future__ import annotations

import re
import subprocess
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

_ALLOWED_GIT_HOSTS = {"github.com", "gitlab.com", "bitbucket.org", "dev.azure.com"}
_CLONE_TIMEOUT_SECONDS = 60
_MAX_REPO_SIZE_BYTES = 200 * 1024 * 1024

_HTTPS_HOST_RE = re.compile(r"^https://([^/]+)/")


class SourceResolutionError(ValueError):
    """Levantado quando nem caminho_projeto nem repositorio_git sao validos."""


def _validate_git_url(url: str) -> None:
    match = _HTTPS_HOST_RE.match(url)
    host = match.group(1).lower() if match else None
    if host not in _ALLOWED_GIT_HOSTS:
        raise SourceResolutionError(
            f"URL de repositorio nao permitida: '{url}'. So sao aceitos repositorios "
            f"publicos via https em: {', '.join(sorted(_ALLOWED_GIT_HOSTS))}."
        )


def _clone_shallow(url: str, dest: Path) -> None:
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", "--quiet", url, str(dest)],
            check=True,
            timeout=_CLONE_TIMEOUT_SECONDS,
            capture_output=True,
        )
    except subprocess.TimeoutExpired as exc:
        raise SourceResolutionError("Tempo limite excedido ao clonar o repositorio.") from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode(errors="ignore") if exc.stderr else ""
        raise SourceResolutionError(f"Falha ao clonar o repositorio: {stderr.strip()}") from exc


def _enforce_size_limit(path: Path) -> None:
    total_size = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    if total_size > _MAX_REPO_SIZE_BYTES:
        limit_mb = _MAX_REPO_SIZE_BYTES // (1024 * 1024)
        raise SourceResolutionError(f"Repositorio maior que o limite de {limit_mb}MB.")


@contextmanager
def resolve_project_source(
    caminho_projeto: str | None,
    repositorio_git: str | None,
) -> Iterator[Path]:
    """Exatamente um dos dois deve ser informado.

    - `caminho_projeto`: retorna o Path diretamente (uso local, stdio).
    - `repositorio_git`: clona raso (--depth 1) em um diretorio temporario,
      valida host/tamanho, e limpa o diretorio ao sair do `with` (sucesso ou erro).
    """
    if bool(caminho_projeto) == bool(repositorio_git):
        raise SourceResolutionError(
            "Informe exatamente um dos dois: caminho_projeto (uso local) ou "
            "repositorio_git (uso remoto, URL publica de repositorio)."
        )

    if caminho_projeto:
        yield Path(caminho_projeto)
        return

    assert repositorio_git is not None
    _validate_git_url(repositorio_git)
    with tempfile.TemporaryDirectory(prefix="specops-") as tmp_dir:
        dest = Path(tmp_dir) / "repo"
        _clone_shallow(repositorio_git, dest)
        _enforce_size_limit(dest)
        yield dest
