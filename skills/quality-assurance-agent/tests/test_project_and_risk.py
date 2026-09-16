from __future__ import annotations

import json
from pathlib import Path

import pytest


def write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_discovers_maven_and_npm_projects(tmp_path):
    from qa_core.project_manifest import discover_projects

    write(
        tmp_path / "backend" / "pom.xml",
        "<project><modelVersion>4.0.0</modelVersion><artifactId>demo-api</artifactId></project>",
    )
    write(tmp_path / "web" / "package.json", json.dumps({"name": "demo-web"}))

    projects = discover_projects(tmp_path)

    assert [(p.name, p.root.relative_to(tmp_path).as_posix(), p.kind) for p in projects] == [
        ("demo-api", "backend", "maven"),
        ("demo-web", "web", "npm"),
    ]


def test_discovers_maven_modules_without_using_parent_artifact_as_target(tmp_path):
    from qa_core.project_manifest import discover_projects

    write(
        tmp_path / "pom.xml",
        "<project><artifactId>root-parent</artifactId><packaging>pom</packaging>"
        "<modules><module>service</module></modules></project>",
    )
    write(
        tmp_path / "service" / "pom.xml",
        "<project><parent><artifactId>root-parent</artifactId></parent>"
        "<artifactId>demo-service</artifactId></project>",
    )

    projects = discover_projects(tmp_path)

    assert [(p.name, p.kind) for p in projects] == [("demo-service", "maven")]


def test_uses_context_manifests_when_files_are_not_under_repo(tmp_path):
    from qa_core.project_manifest import discover_projects

    external = tmp_path / "outside" / "package.json"
    write(external, json.dumps({"name": "external-ui"}))
    repo = tmp_path / "repo"
    repo.mkdir()
    context = {"stack": {"manifests": [str(external)]}}

    projects = discover_projects(repo, context)

    assert len(projects) == 1
    assert projects[0].name == "external-ui"
    assert projects[0].root == external.parent.resolve()


def test_resolve_api_target_prefers_maven_project_matching_case_text(tmp_path):
    from qa_core.project_manifest import resolve_target_project

    write(
        tmp_path / "demo-api" / "pom.xml",
        "<project><artifactId>demo-api</artifactId></project>",
    )
    write(tmp_path / "demo-web" / "package.json", json.dumps({"name": "demo-web"}))

    target = resolve_target_project(
        tmp_path,
        {"title": "后端 API 下单", "module": "order", "steps": []},
        "api",
    )

    assert target.name == "demo-api"
    assert target.kind == "maven"


def test_resolve_target_raises_when_no_project_exists(tmp_path):
    from qa_core.project_manifest import ProjectDiscoveryError, resolve_target_project

    with pytest.raises(ProjectDiscoveryError, match="未识别到可执行项目"):
        resolve_target_project(tmp_path, {"title": "下单"}, "api")


def test_target_project_for_task_uses_repo_manifest(qa, tmp_path):
    write(
        tmp_path / "demo-backend" / "pom.xml",
        "<project><artifactId>demo-backend</artifactId></project>",
    )
    case = {"id": "TC-P0-001", "title": "下单 API", "module": "order", "steps": []}

    project = qa.target_project_for_task(case, "api", tmp_path)

    assert project == "demo-backend"
    assert "unrelated-service" not in project


def test_build_spec_task_uses_manifest_project_in_target_and_command(qa, tmp_path):
    write(
        tmp_path / "demo-backend" / "pom.xml",
        "<project><artifactId>demo-backend</artifactId></project>",
    )
    case = {
        "id": "TC-P0-001",
        "title": "下单 API",
        "module": "order",
        "priority": "P0",
        "steps": ["发起下单"],
        "expected": ["成功"],
    }

    task = qa.build_spec_task(
        case,
        "api",
        {"kind": "main", "title": "主路径", "assertion": "成功"},
        1,
        tmp_path,
    )

    assert task["targetProject"] == "demo-backend"
    assert task["targetFile"].startswith("demo-backend/")
    assert task["command"].startswith("cd demo-backend &&")


def _init_git_repo(repo: Path) -> None:
    import subprocess

    subprocess.run(["git", "init", "-q"], cwd=str(repo), check=True)
    subprocess.run(["git", "config", "user.email", "qa@example.com"], cwd=str(repo), check=True)
    subprocess.run(["git", "config", "user.name", "qa"], cwd=str(repo), check=True)


def test_risk_candidate_files_module_wins_over_git_diff(qa, tmp_path):
    repo = tmp_path
    _init_git_repo(repo)
    write(repo / "committed.ts", "console.log('base')\n")
    subprocess_add_commit = __import__("subprocess").run
    subprocess_add_commit(["git", "add", "-A"], cwd=str(repo), check=True)
    subprocess_add_commit(["git", "commit", "-q", "-m", "base"], cwd=str(repo), check=True)

    write(repo / "committed.ts", "console.log('changed')\n")
    write(repo / "target-module" / "Service.java", "class Service {}\n")

    files = qa._risk_candidate_files(repo, {}, module=["target-module"])

    rels = sorted(str(p.relative_to(repo)).replace("\\", "/") for p in files)
    assert rels == ["target-module/Service.java"]


def test_risk_candidate_files_raises_on_empty_module_match(qa, tmp_path):
    with pytest.raises(qa.QaAgentError, match="未匹配到任何文件"):
        qa._risk_candidate_files(tmp_path, {}, module=["does-not-exist"])


def test_risk_candidate_files_falls_back_to_git_then_context_then_repo(qa, tmp_path):
    repo = tmp_path
    _init_git_repo(repo)
    write(repo / "base.ts", "1\n")
    run = __import__("subprocess").run
    run(["git", "add", "-A"], cwd=str(repo), check=True)
    run(["git", "commit", "-q", "-m", "base"], cwd=str(repo), check=True)
    write(repo / "base.ts", "2\n")

    files = qa._risk_candidate_files(repo, {"changedFiles": ["context-only.ts"]})
    rels = sorted(str(p.relative_to(repo)).replace("\\", "/") for p in files if p.exists() or p.name == "base.ts")
    assert "base.ts" in rels


def test_analyze_risks_data_records_module_selection_source(qa, tmp_path):
    repo = tmp_path
    write(repo / "auth" / "AuthService.java", "class AuthService { void login(String token) {} }\n")

    result = qa.analyze_risks_data(repo, module=["auth"])

    assert result["scope"]["selectionSource"] == "module"
    assert result["scope"]["requestedModules"] == ["auth"]
    assert result["inspectedFiles"] == ["auth/AuthService.java".replace("/", os_sep())]


def os_sep() -> str:
    import os

    return os.sep


def test_analyze_risks_data_marks_ui_risk_as_requiring_e2e(qa, tmp_path):
    repo = tmp_path
    write(
        repo / "web" / "QuickActionModal.tsx",
        "function QuickActionModal() { approve(); review(); }\n",
    )

    result = qa.analyze_risks_data(repo, module=["web"])

    state_risks = [r for r in result["risks"] if r["category"] == "state-transition"]
    assert state_risks, "expected a state-transition risk from approve/review tokens"
    assert state_risks[0]["requiresE2E"] is True
    assert "ui" in result["requiredOracles"]
