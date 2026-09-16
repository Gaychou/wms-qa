# QA 管道产物契约

本文档定义 QA 管道各阶段之间的产物契约——每个阶段产出的文件格式、必需字段、以及下游阶段的消费方式。

## 管道总览

```
context-profiler → risk-analyzer → testcase-designer → script-generator → runner-reporter → code-reviewer
     │                  │                  │                   │                  │                │
     ▼                  ▼                  ▼                   ▼                  ▼                ▼
  context.json     risk-analysis.json  test-cases.json   test-spec-tasks.json  completion-check  code-review.json
  existing-index   (增强后)            (confirmed)        coverage-balance     latest-run        code-review-check
  env-checks                                                                    report.html       readiness-check
```

## 阶段产物契约

### 阶段 0→1：context-profiler → risk-analyzer

| 产物 | 必需字段 | 消费者校验 |
|------|---------|-----------|
| `context.json` | `files[]`, `module`, `dependencies` | risk-analyzer 校验 `files` 非空 |
| `existing-case-index.json` | `cases[]`, `generatedAt` | risk-analyzer 校验 schema |
| `environment-checks.json` | `services`, `status`, `blockers[]` | risk-analyzer 仅引用 |

### 阶段 1→2：risk-analyzer → testcase-designer

| 产物 | 必需字段 | 消费者校验 |
|------|---------|-----------|
| `risk-analysis.json` | `risks[]`（每条含 `id`, `priority`, `businessPath`, `requiredAssertions`）, `coverageGaps[]` | testcase-designer 校验 P0/P1 风险与用例映射 |

> `coverageStatus` / `coverageGaps` 是 risk-analyzer 阶段的**设计输入预判**（提示哪些风险需设计用例），不是覆盖真相。

### 阶段 2→3：testcase-designer → script-generator

| 产物 | 必需字段 | 消费者校验 |
|------|---------|-----------|
| `test-cases.json` | `status=confirmed`, `cases[]`（每条含 `id`, `priority`, `steps`, `expected`, `traceability[]`） | script-generator 校验 `status=confirmed` |

> **覆盖真相只存在于用例的 `traceability`**（正向：用例→风险）。报告渲染时从 traceability 动态投影「风险→用例」，不回填到 risk-analysis，避免双源同步。

### 阶段 3→4：script-generator → runner-reporter

| 产物 | 必需字段 | 消费者校验 |
|------|---------|-----------|
| `test-spec-tasks.json` | 根级 `generationProfile`/`minSpecsByPriority`/`targetRatio`；`tasks[]` 每条含 `targetFile`, `command`, `assertions`, `oracle`（结构化对象，至少 `type`+`assertion`） | runner-reporter 校验 task 可执行；`coverage-balance` 读 `minSpecsByPriority` 自动匹配 |
| `coverage-balance.json` | `status=passed` | runner-reporter 校验 coverage gate 通过 |

### 阶段 4→5：runner-reporter → code-reviewer

| 产物 | 必需字段 | 消费者校验 |
|------|---------|-----------|
| `completion-check.json` | `status=passed` | code-reviewer 校验 completion gate 通过 |
| `latest-run.json` | `summary.totalCases > 0`、`cases[]`、`unmatchedLogs=[]` | 证据完整性门禁校验非空、无未匹配日志 |
| `runs/run-*.meta.json` | sidecar 元数据：`runId/caseId/taskId/script/logFile/exitCode/executedAt/outcome` | `aggregate-runs` 优先读 sidecar 聚合 |
| `latest-report.html` | 完整报告 | code-reviewer 引用聚合视图 |

### 阶段 5→最终判定

| 产物 | 必需字段 | 判定逻辑 |
|------|---------|---------|
| `code-review.json` | `status`, `findings[]`, `scope`（对象 `{files:[], description:""}`） | 有 P0/P1 blocking → Not Ready |
| `code-review-check.json` | `status=passed` | 门禁不通过 → Not Ready |
| `evidence-integrity-check.json` | `status=passed` | 证据链断裂 → Incomplete，不允许判 Ready |
| `readiness-check.json` | `status` | 综合判定 → Ready/Conditionally Ready/Not Ready/Incomplete |

## 产物校验顺序

每个阶段切换前，由 quality-assurance-agent 逐项校验上游产物：

1. **存在性检查**：文件是否存在且非空
2. **Schema 校验**：必需字段是否齐全
3. **编码完整性**：`check-mojibake --strict` 无 U+FFFD
4. **门禁状态**：上游门禁是否通过

任一检查不通过 → 退回上游阶段补齐，不允许跳过。
