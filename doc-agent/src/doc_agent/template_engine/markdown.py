"""Helpers genericos para montar documentos markdown por secoes.

Nao sabe nada sobre README, ADR ou runbook - so formata headings, secoes e
listas. Os geradores de documento (documentation_engine/) decidem o conteudo;
este modulo decide a forma.
"""

from __future__ import annotations

TODO = "<!-- TODO: preencher -->"


def heading(text: str, level: int = 1) -> str:
    return f"{'#' * level} {text}"


def section(title: str, body: list[str], level: int = 2) -> list[str]:
    """Monta uma secao: heading, linha em branco, corpo, linha em branco."""
    return [heading(title, level), "", *body, ""]


def bullet_list(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items]


def numbered_list(items: list[str]) -> list[str]:
    return [f"{i}. {item}" for i, item in enumerate(items, start=1)]
