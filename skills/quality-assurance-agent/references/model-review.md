# Multi-Model Test-Case Review

## Gateway Configuration

本工具**不内置任何默认网关地址**，也不会向任何默认地址发送请求。

- Base URL: 必须通过 `QA_AGENT_LLM_BASE_URL` 环境变量或 `--base-url` 显式指定
- API key env var: `QA_AGENT_LLM_API_KEY`
- Interface: OpenAI-compatible chat completions
- 未配置 Base URL 或 API Key 时，多模型交叉审查**跳过**并写入「全部模型失败」结果，不中断整个 QA 流程

## Default Models

以下为默认评审模型列表，需与你自己网关支持的模型名一致，否则按需覆盖：

- `gpt-5.4`
- `claude-sonnet-5`
- `deepseek-v4-pro`

## Reviewer Prompt Contract

Ask each reviewer to return JSON only, with `summary`, `problem`, `impact`, `recommendation`, and any `missingCases` narrative written in Simplified Chinese except product/domain terms and technical identifiers:

```json
{
  "model": "model-name",
  "summary": "short assessment",
  "findings": [
    {
      "id": "MR-001",
      "severity": "P0|P1|P2|P3",
      "caseIds": ["TC-P0-001"],
      "problem": "what is wrong or missing",
      "impact": "why it matters",
      "recommendation": "specific change"
    }
  ],
  "missingCases": [],
  "duplicateCases": [],
  "priorityCorrections": [],
  "confidence": 0.0
}
```

## Synthesis Rules

- Treat multiple-model agreement as high confidence.
- Treat single-model findings as candidates; verify against requirements and code before applying.
- Reject suggestions that contradict facts from source code or requirements.
- Convert accepted findings into concrete `test-cases.json` edits.
- Preserve rejected findings in `model-review.json` with a rejection reason.

## Failure Handling

If a model call fails, record the failure and continue with the other models. Multi-model review is still valid if at least one external model returns useful findings, but the report must state which models failed.

