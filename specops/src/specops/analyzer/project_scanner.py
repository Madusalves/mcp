"""Leitura deterministica de um projeto .NET: .csproj/.sln, estrutura de pastas,
controllers/endpoints e comentarios XML. Nao usa IA - so parsing de arquivos."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path, PureWindowsPath
from xml.etree import ElementTree as ET

IGNORED_TOP_LEVEL_DIRS = {"bin", "obj", ".git", ".vs", "node_modules"}


class ProjectValidationError(ValueError):
    """Levantado quando o caminho informado nao e um projeto .NET valido."""


@dataclass
class PackageReference:
    name: str
    version: str | None


@dataclass
class CsprojInfo:
    path: Path
    project_name: str
    target_framework: str | None
    packages: list[PackageReference]
    generates_documentation_file: bool
    is_web_sdk: bool
    project_references: list[str]


@dataclass
class EndpointInfo:
    method: str
    route: str | None
    handler_file: str


@dataclass
class ControllerInfo:
    class_name: str
    file: str
    summary: str | None
    endpoints: list[EndpointInfo] = field(default_factory=list)


@dataclass
class XmlDocComment:
    symbol: str
    summary: str
    file: str


@dataclass
class ProjectMetadata:
    root_path: Path
    csproj_files: list[CsprojInfo]
    sln_files: list[Path]
    top_level_entries: list[str]
    controllers: list[ControllerInfo]
    minimal_api_endpoints: list[EndpointInfo]
    xml_doc_comments: list[XmlDocComment]

    @property
    def primary_project_name(self) -> str:
        if self.sln_files:
            return self.sln_files[0].stem
        if self.csproj_files:
            web_projects = [p for p in self.csproj_files if p.is_web_sdk]
            return (web_projects or self.csproj_files)[0].project_name
        return self.root_path.name

    @property
    def has_web_endpoints(self) -> bool:
        return bool(self.controllers) or bool(self.minimal_api_endpoints)


def validate_project_path(root_path: Path) -> tuple[list[Path], list[Path]]:
    """Confirma que root_path existe e contem ao menos um .csproj ou .sln.

    Retorna (csproj_paths, sln_paths). Levanta ProjectValidationError caso contrario.
    """
    if not root_path.exists():
        raise ProjectValidationError(f"O caminho '{root_path}' nao existe.")
    if not root_path.is_dir():
        raise ProjectValidationError(f"O caminho '{root_path}' nao e uma pasta.")

    csproj_files = sorted(root_path.rglob("*.csproj"))
    sln_files = sorted(root_path.rglob("*.sln"))

    if not csproj_files and not sln_files:
        raise ProjectValidationError(
            f"Nenhum arquivo .csproj ou .sln encontrado em '{root_path}'. "
            "Confirme que o caminho aponta para um projeto ou solution .NET."
        )

    return csproj_files, sln_files


def parse_csproj(csproj_path: Path) -> CsprojInfo:
    tree = ET.parse(csproj_path)
    root = tree.getroot()

    sdk = root.attrib.get("Sdk", "")
    is_web_sdk = "Web" in sdk

    target_framework = None
    generates_doc = False
    for prop_group in root.findall("PropertyGroup"):
        if target_framework is None:
            tf = prop_group.findtext("TargetFramework") or prop_group.findtext("TargetFrameworks")
            if tf:
                target_framework = tf.strip()
        doc_flag = prop_group.findtext("GenerateDocumentationFile")
        if doc_flag and doc_flag.strip().lower() == "true":
            generates_doc = True

    packages: list[PackageReference] = []
    project_references: list[str] = []
    for item_group in root.findall("ItemGroup"):
        for pkg_ref in item_group.findall("PackageReference"):
            name = pkg_ref.attrib.get("Include") or pkg_ref.attrib.get("Update")
            if not name:
                continue
            version = pkg_ref.attrib.get("Version")
            if version is None:
                version_el = pkg_ref.find("Version")
                version = version_el.text.strip() if version_el is not None and version_el.text else None
            packages.append(PackageReference(name=name, version=version))
        for proj_ref in item_group.findall("ProjectReference"):
            include = proj_ref.attrib.get("Include")
            if not include:
                continue
            project_references.append(PureWindowsPath(include).stem)

    return CsprojInfo(
        path=csproj_path,
        project_name=csproj_path.stem,
        target_framework=target_framework,
        packages=packages,
        generates_documentation_file=generates_doc,
        is_web_sdk=is_web_sdk,
        project_references=project_references,
    )


def scan_top_level_structure(root_path: Path) -> list[str]:
    entries = []
    for entry in sorted(root_path.iterdir()):
        if entry.name in IGNORED_TOP_LEVEL_DIRS or entry.name.startswith("."):
            continue
        suffix = "/" if entry.is_dir() else ""
        entries.append(f"{entry.name}{suffix}")
    return entries


_CONTROLLER_CLASS_RE = re.compile(
    r"(?:///\s*<summary>\s*\n(?P<summary>(?:\s*///.*\n)+?)\s*///\s*</summary>\s*\n)?"
    r"(?:\[.*?\]\s*\n)*"
    r"public\s+(?:partial\s+)?class\s+(?P<name>\w+Controller)\b",
    re.MULTILINE,
)
_HTTP_ATTR_RE = re.compile(r'\[Http(?P<verb>Get|Post|Put|Delete|Patch)(?:\("(?P<route>[^"]*)"\))?\]')
_MINIMAL_API_RE = re.compile(
    r'\b(?:app|routes|group)\.Map(?P<verb>Get|Post|Put|Delete|Patch)\(\s*"(?P<route>[^"]*)"'
)
_XML_SUMMARY_RE = re.compile(
    r"(?P<summary>(?:^[ \t]*///.*\n)+)"
    r"^[ \t]*(?:\[.*?\]\s*\n)*"
    r"[ \t]*(?:public|private|protected|internal)[^\n{;]*?\b(?P<symbol>\w+)\s*\(",
    re.MULTILINE,
)


def _clean_summary(raw: str) -> str:
    lines = [line.strip().lstrip("/").strip() for line in raw.strip().splitlines()]
    text = " ".join(line for line in lines if line and "<summary>" not in line and "</summary>" not in line)
    return text.strip()


def find_controllers(root_path: Path) -> list[ControllerInfo]:
    controllers: list[ControllerInfo] = []
    for cs_file in root_path.rglob("*.cs"):
        if any(part in IGNORED_TOP_LEVEL_DIRS for part in cs_file.parts):
            continue
        if not cs_file.name.endswith("Controller.cs"):
            continue
        try:
            text = cs_file.read_text(encoding="utf-8-sig")
        except (UnicodeDecodeError, OSError):
            continue

        match = _CONTROLLER_CLASS_RE.search(text)
        if not match:
            continue

        summary = _clean_summary(match.group("summary")) if match.group("summary") else None
        rel_file = str(cs_file.relative_to(root_path)).replace("\\", "/")
        controller = ControllerInfo(class_name=match.group("name"), file=rel_file, summary=summary)

        for http_match in _HTTP_ATTR_RE.finditer(text):
            controller.endpoints.append(
                EndpointInfo(
                    method=f"HTTP{http_match.group('verb').upper()}",
                    route=http_match.group("route"),
                    handler_file=rel_file,
                )
            )

        controllers.append(controller)

    return controllers


def find_minimal_api_endpoints(root_path: Path) -> list[EndpointInfo]:
    endpoints: list[EndpointInfo] = []
    for cs_file in root_path.rglob("*.cs"):
        if any(part in IGNORED_TOP_LEVEL_DIRS for part in cs_file.parts):
            continue
        try:
            text = cs_file.read_text(encoding="utf-8-sig")
        except (UnicodeDecodeError, OSError):
            continue

        rel_file = str(cs_file.relative_to(root_path)).replace("\\", "/")
        for match in _MINIMAL_API_RE.finditer(text):
            endpoints.append(
                EndpointInfo(
                    method=f"HTTP{match.group('verb').upper()}",
                    route=match.group("route"),
                    handler_file=rel_file,
                )
            )

    return endpoints


def extract_xml_doc_comments(root_path: Path, limit: int = 40) -> list[XmlDocComment]:
    comments: list[XmlDocComment] = []
    for cs_file in root_path.rglob("*.cs"):
        if any(part in IGNORED_TOP_LEVEL_DIRS for part in cs_file.parts):
            continue
        try:
            text = cs_file.read_text(encoding="utf-8-sig")
        except (UnicodeDecodeError, OSError):
            continue

        rel_file = str(cs_file.relative_to(root_path)).replace("\\", "/")
        for match in _XML_SUMMARY_RE.finditer(text):
            summary = _clean_summary(match.group("summary"))
            if not summary:
                continue
            comments.append(XmlDocComment(symbol=match.group("symbol"), summary=summary, file=rel_file))
            if len(comments) >= limit:
                return comments

    return comments


def scan_project(root_path: Path) -> ProjectMetadata:
    """Ponto de entrada: valida o caminho e coleta todos os metadados deterministicos."""
    csproj_paths, sln_paths = validate_project_path(root_path)

    return ProjectMetadata(
        root_path=root_path,
        csproj_files=[parse_csproj(p) for p in csproj_paths],
        sln_files=sln_paths,
        top_level_entries=scan_top_level_structure(root_path),
        controllers=find_controllers(root_path),
        minimal_api_endpoints=find_minimal_api_endpoints(root_path),
        xml_doc_comments=extract_xml_doc_comments(root_path),
    )
