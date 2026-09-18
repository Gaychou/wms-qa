#!/usr/bin/env python3
"""回归测试：services 分层配置是按 id 合并，不是二选一。

历史缺陷：加载器写的是

    if local_path.exists():   data = read_json(local_path)
    elif config_path.exists(): data = read_json(config_path)

纯优先级、不合并。而文件和文档都叫它 local **override**——用户按提示只写
「想改的那几项」是最符合直觉的用法，结果是他没写到的服务静默消失：

    local/services.local.json 只放 web  →  services_config: 1 services
    （api 不见了，而报错只会说「api 不可达」，看不出是配置被整体替换）

现在改为按 id 合并：同 id 私有覆盖公有，其余保留，新 id 追加。
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from qa_agent import load_services_config


def _write(path: Path, services: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"version": "1.0", "services": services}, ensure_ascii=False),
                    encoding="utf-8")


def _ids(repo: Path) -> list[str]:
    return [s["id"] for s in load_services_config(repo).get("services", [])]


def _public(repo: Path) -> Path:
    return repo / ".qa-agent" / "config" / "services.json"


def _local(repo: Path) -> Path:
    return repo / ".qa-agent" / "local" / "services.local.json"


def test_public_only(tmp_path):
    _write(_public(tmp_path), [{"id": "web"}, {"id": "api"}])
    assert _ids(tmp_path) == ["web", "api"]


def test_local_only(tmp_path):
    _write(_local(tmp_path), [{"id": "web"}])
    assert _ids(tmp_path) == ["web"]


def test_local_overrides_same_id_and_keeps_the_rest(tmp_path):
    """本测试存在的理由：只改一项，不该把别的服务弄丢。"""
    _write(_public(tmp_path), [{"id": "web", "dir": ""}, {"id": "api", "dir": ""}])
    _write(_local(tmp_path), [{"id": "web", "dir": "frontend", "startCmd": "npm run dev"}])

    services = load_services_config(tmp_path)["services"]

    assert [s["id"] for s in services] == ["web", "api"], "未在 local 里列出的 api 被弄丢了"
    web = next(s for s in services if s["id"] == "web")
    assert web["dir"] == "frontend", "同 id 应以私有为准"
    assert web["startCmd"] == "npm run dev"


def test_local_can_add_a_new_service(tmp_path):
    _write(_public(tmp_path), [{"id": "web"}])
    _write(_local(tmp_path), [{"id": "admin"}])

    assert _ids(tmp_path) == ["web", "admin"], "私有里新增的服务应追加进来"


def test_public_order_is_preserved(tmp_path):
    _write(_public(tmp_path), [{"id": "a"}, {"id": "b"}, {"id": "c"}])
    _write(_local(tmp_path), [{"id": "b"}])

    assert _ids(tmp_path) == ["a", "b", "c"], "覆盖不应打乱顺序"


def test_missing_files_are_tolerated(tmp_path):
    assert load_services_config(tmp_path)["services"] == []
