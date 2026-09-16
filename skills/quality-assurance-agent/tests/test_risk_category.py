"""测试风险类别：收敛固定枚举 + 枚举自带中文。"""
from __future__ import annotations


def test_all_risk_rules_categories_have_chinese_label(qa):
    """RISK_RULES 里工具生成的每个 category 都在固定枚举中文映射里（枚举收敛无遗漏）。"""
    rule_categories = {r["category"] for r in qa.RISK_RULES}
    missing = rule_categories - set(qa.RISK_CATEGORY_LABELS)
    assert not missing, f"RISK_RULES 的 category 缺中文映射：{missing}"


def test_risk_category_label_covers_previous_run_categories(qa):
    """上一轮实际出现的 category 都能被中文覆盖（不再露英文）。"""
    for cat in ["business-rule", "concurrency", "data-consistency", "privacy", "provably-fair"]:
        zh = qa._risk_category_label(cat)
        # 中文标签里不应再是纯英文原文
        assert zh != cat, f"category {cat} 未映射到中文"
        assert cat in zh, "英文原文应作为注解保留在括号里"


def test_risk_category_label_has_chinese(qa):
    assert "并发" in qa._risk_category_label("concurrency")
    assert "公平" in qa._risk_category_label("provably-fair")
    assert "权限" in qa._risk_category_label("permission-boundary")


def test_risk_category_label_unknown_falls_back(qa):
    """枚举外 category：fallback 原文，不崩。"""
    assert "mystery-cat" in qa._risk_category_label("mystery-cat")
