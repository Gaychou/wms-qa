"""Project identification from repository manifests.

Supports Maven, npm, SDK-style .NET and classic .NET Framework projects.
"""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_IGNORED_DIR_NAMES = {
    ".git",
    ".vs",
    "node_modules",
    "target",
    "dist",
    "build",
    "bin",
    "obj",
    ".next",
    "coverage",
    "test-results",
    ".qa-agent",
}

_MAX_SCAN_DEPTH = 8


class ProjectDiscoveryError(Exception):
    """Raised when no project can be identified for a task/case."""


@dataclass(frozen=True)
class ProjectInfo:
    name: str
    root: Path
    kind: str  # "maven" | "npm" | "dotnet" | "dotnet-framework"
    manifest: Path | None = None
    framework: str = ""
    is_test: bool = False


def _xml_local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _read_maven_artifact_id(pom_path: Path) -> str | None:
    try:
        root = ET.parse(pom_path).getroot()
    except (ET.ParseError, OSError):
        return None
    for child in root:
        if _xml_local_name(child.tag) == "artifactId":
            return (child.text or "").strip() or None
    return None


def _is_maven_aggregator(pom_path: Path) -> bool:
    try:
        root = ET.parse(pom_path).getroot()
    except (ET.ParseError, OSError):
        return False
    packaging = ""
    has_modules = False
    for child in root:
        tag = _xml_local_name(child.tag)
        if tag == "packaging":
            packaging = (child.text or "").strip().lower()
        elif tag == "modules":
            has_modules = any(_xml_local_name(grandchild.tag) == "module" for grandchild in child)
    return packaging == "pom" and has_modules


def _read_npm_name(package_json_path: Path) -> str | None:
    try:
        data = json.loads(package_json_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(data, dict):
        return None
    name = data.get("name")
    return str(name).strip() or None if name else None


def _read_csproj(csproj_path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "name": csproj_path.stem,
        "framework": "",
        "kind": "dotnet",
        "is_test": False,
        "packages": [],
        "sdk": "",
    }
    try:
        root = ET.parse(csproj_path).getroot()
    except (ET.ParseError, OSError):
        return result

    sdk = str(root.attrib.get("Sdk") or "").strip()
    values: dict[str, str] = {}
    references: list[str] = []

    for elem in root.iter():
        tag = _xml_local_name(elem.tag)
        value = (elem.text or "").strip()
        if tag in {
            "AssemblyName",
            "TargetFramework",
            "TargetFrameworks",
            "TargetFrameworkVersion",
            "IsTestProject",
        } and value:
            values.setdefault(tag, value)
        if tag in {"PackageReference", "Reference"}:
            include = str(elem.attrib.get("Include") or elem.attrib.get("Update") or "").strip()
            if include:
                references.append(include.split(",", 1)[0])

    framework = (
        values.get("TargetFramework")
        or values.get("TargetFrameworks", "").split(";")[0]
        or values.get("TargetFrameworkVersion")
        or ""
    )
    # Old .NET Framework projects normally have TargetFrameworkVersion and no SDK attribute.
    kind = "dotnet-framework" if values.get("TargetFrameworkVersion") and not sdk else "dotnet"
    ref_lc = {item.lower() for item in references}
    test_tokens = {
        "microsoft.net.test.sdk",
        "mstest.testframework",
        "mstest.testadapter",
        "xunit",
        "xunit.runner.visualstudio",
        "nunit",
        "nunit.framework",
        "nunit3testadapter",
        "microsoft.visualstudio.qualitytools.unittestframework",
    }
    name = values.get("AssemblyName") or csproj_path.stem
    is_test = (
        values.get("IsTestProject", "").lower() == "true"
        or any(token in ref_lc for token in test_tokens)
        or bool(re.search(r"(?:^|[._-])tests?$", name, re.I))
    )
    result.update(
        {
            "name": name,
            "framework": framework,
            "kind": kind,
            "is_test": is_test,
            "packages": sorted(references),
            "sdk": sdk,
        }
    )
    return result


def _scan_repo_for_projects(repo: Path) -> list[ProjectInfo]:
    found: list[ProjectInfo] = []
    seen_manifests: set[Path] = set()

    def add(project: ProjectInfo) -> None:
        key = (project.manifest or project.root).resolve()
        if key in seen_manifests:
            return
        seen_manifests.add(key)
        found.append(project)

    def walk(directory: Path, depth: int) -> None:
        if depth > _MAX_SCAN_DEPTH or not directory.is_dir():
            return

        pom = directory / "pom.xml"
        if pom.exists():
            artifact_id = _read_maven_artifact_id(pom)
            if artifact_id and not _is_maven_aggregator(pom):
                add(ProjectInfo(
                    name=artifact_id,
                    root=directory.resolve(),
                    kind="maven",
                    manifest=pom.resolve(),
                ))

        for csproj in sorted(directory.glob("*.csproj")):
            meta = _read_csproj(csproj)
            add(ProjectInfo(
                name=str(meta["name"]),
                root=directory.resolve(),
                kind=str(meta["kind"]),
                manifest=csproj.resolve(),
                framework=str(meta["framework"]),
                is_test=bool(meta["is_test"]),
            ))

        package_json = directory / "package.json"
        if package_json.exists():
            name = _read_npm_name(package_json)
            if name:
                add(ProjectInfo(
                    name=name,
                    root=directory.resolve(),
                    kind="npm",
                    manifest=package_json.resolve(),
                ))

        try:
            children = sorted(path for path in directory.iterdir() if path.is_dir())
        except OSError:
            return
        for child in children:
            if child.name in _IGNORED_DIR_NAMES or child.name.startswith("."):
                continue
            walk(child, depth + 1)

    walk(repo, 0)
    return found


def _projects_from_context_manifests(
    context: dict[str, Any] | None,
    repo: Path,
) -> list[ProjectInfo]:
    if not context:
        return []
    stack = context.get("stack")
    manifests = stack.get("manifests") if isinstance(stack, dict) else None
    if not isinstance(manifests, list):
        return []

    found: list[ProjectInfo] = []
    for entry in manifests:
        raw_path = entry.get("path") if isinstance(entry, dict) else entry
        if not raw_path:
            continue
        manifest_path = Path(str(raw_path))
        if not manifest_path.is_absolute():
            manifest_path = repo / manifest_path
        if not manifest_path.exists():
            continue

        if manifest_path.name == "pom.xml":
            artifact_id = _read_maven_artifact_id(manifest_path)
            if artifact_id:
                found.append(ProjectInfo(
                    name=artifact_id,
                    root=manifest_path.parent.resolve(),
                    kind="maven",
                    manifest=manifest_path.resolve(),
                ))
        elif manifest_path.name == "package.json":
            name = _read_npm_name(manifest_path)
            if name:
                found.append(ProjectInfo(
                    name=name,
                    root=manifest_path.parent.resolve(),
                    kind="npm",
                    manifest=manifest_path.resolve(),
                ))
        elif manifest_path.suffix.lower() == ".csproj":
            meta = _read_csproj(manifest_path)
            found.append(ProjectInfo(
                name=str(meta["name"]),
                root=manifest_path.parent.resolve(),
                kind=str(meta["kind"]),
                manifest=manifest_path.resolve(),
                framework=str(meta["framework"]),
                is_test=bool(meta["is_test"]),
            ))
    return found


def discover_projects(repo: Path, context: dict[str, Any] | None = None) -> list[ProjectInfo]:
    """Discover buildable projects under repo plus context-declared manifests."""
    repo = Path(repo).resolve()
    projects = _scan_repo_for_projects(repo) if repo.exists() else []
    known = {(project.manifest or project.root).resolve() for project in projects}
    for extra in _projects_from_context_manifests(context, repo):
        key = (extra.manifest or extra.root).resolve()
        if key not in known:
            projects.append(extra)
            known.add(key)
    return projects


def _case_text(case: dict[str, Any]) -> str:
    parts = [str(case.get(key, "")) for key in ("title", "module", "businessActor", "operationPath")]
    steps = case.get("steps")
    if isinstance(steps, list):
        parts.extend(str(step) for step in steps)
    return " ".join(parts).lower()


def resolve_target_project(
    repo: Path,
    case: dict[str, Any],
    layer: str,
    context: dict[str, Any] | None = None,
) -> ProjectInfo:
    """Pick the project a spec task should target.

    Backend preference is .NET/.NET Framework/Maven, then npm. Existing test
    projects are preferred for unit/integration work when their name/root
    matches the business case.
    """
    projects = discover_projects(repo, context)
    if not projects:
        raise ProjectDiscoveryError(
            f"未识别到可执行项目：repo={repo} 中没有 pom.xml/package.json/*.csproj，"
            "也没有 context.stack.manifests 可用"
        )

    text = _case_text(case)

    def matches_text(project: ProjectInfo) -> bool:
        haystack = f"{project.name} {project.root.name}".lower()
        return any(token and token in haystack for token in text.split()) or any(
            token and token in text
            for token in (project.name.lower(), project.root.name.lower())
        )

    backends = [
        p for p in projects
        if p.kind in {"dotnet", "dotnet-framework", "maven"} and not p.is_test
    ]
    backend_tests = [
        p for p in projects
        if p.kind in {"dotnet", "dotnet-framework", "maven"} and p.is_test
    ]
    npm_projects = [p for p in projects if p.kind == "npm"]

    if layer in {"unit", "integration"}:
        for project in backend_tests:
            if matches_text(project):
                return project
        for project in backends:
            if matches_text(project):
                return project
        if backends:
            return backends[0]
        if backend_tests:
            return backend_tests[0]

    if layer == "api":
        for project in backends:
            if matches_text(project):
                return project
        if backends:
            return backends[0]

    for project in npm_projects:
        if matches_text(project):
            return project
    if npm_projects:
        return npm_projects[0]
    return projects[0]
