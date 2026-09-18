# 配置

配置分两层，**不要混用**：

| 位置 | 内容 | 是否提交到 git |
|---|---|---|
| `.qa-agent/config/qa-agent.config.yaml` | 团队共享配置：服务地址、质量门禁、命令、工具链策略 | ✅ 提交 |
| `.qa-agent/local/.env` | 本地密钥：API Key、测试账号、数据库凭证 | ❌ 已 git-ignored，**绝不提交** |

`init-project` 会生成这两处的模板。

## 完整字段说明

```yaml
version: "1.0"
baseBranch: "main"

branch:
  pattern: "feature/ming-qa-{slug}"

llm:
  baseUrlEnv: "QA_AGENT_LLM_BASE_URL"     # 读哪个环境变量当网关地址
  apiKeyEnv: "QA_AGENT_LLM_API_KEY"       # 读哪个环境变量当 API Key
  defaultBaseUrl: ""                       # 留空 = 不启用多模型交叉审查
  models:                                  # 与你自己网关支持的模型名一致
    - "gpt-5.4"
    - "claude-sonnet-5"
    - "deepseek-v4-pro"
  timeoutSeconds: 300                      # 单模型请求超时（秒）
  stream: true                             # 默认流式，见「关于 llm.stream」

qualityGates:
  maxRepairLoops: 5                        # 单条用例最多修复重跑轮次
  coverage:
    lines: 80
    branches: 70
    functions: 80
    newCode: 90

commands:                                  # 各层的执行命令，留空则该层跳过
  unit: []
  api: []
  integration: []
  e2e: []
  review: []

repair:
  allowedPaths: []                         # 允许自动修复的路径，空 = 不限制
  deniedPaths:
    - ".qa-agent/**"
    - ".github/**"

accounts:
  file: ".qa-agent/local/accounts.local.json"
  exampleFile: ".qa-agent/fixtures/accounts.example.json"

services:
  file: ".qa-agent/local/services.local.json"
  exampleFile: ".qa-agent/fixtures/services.example.json"

database:
  mysqlMcp:
    serverName: "mysql_mcp"
    source: ".mcp.json"
    requiredFor: ["integration", "e2e"]    # 哪些层必需 MySQL

toolchain:
  autoInstall: false                       # 缺 Playwright / MySQL MCP 时：true=自动装，false=问你
  installRetryMax: 2                       # 自动安装失败重试上限（仅网络/超时）

reports:
  outputDir: ".qa-agent/reports"
  keepHistory: true

notify:
  webhook: ""                              # 留空 = 不发送任何通知
```

## 关于 `llm.defaultBaseUrl`

**本工具不内置任何默认网关地址，也不会向任何默认地址发送请求。**

填上你自己的 OpenAI 兼容网关地址后启用；留空则跳过该阶段，其余流程不受影响。

**接口**：`POST {base}/v1/chat/completions`，`Authorization: Bearer <key>`。
base 的写法会自动补全（以 `/v1` 结尾补 `/chat/completions`；已是完整路径则原样使用）。

**模型**：`llm.models` 填你网关上的模型名即可，任何 OpenAI 兼容端点都能接
（GPT / Claude / Gemini / DeepSeek / Qwen / 本地 vLLM / Ollama 等）。

**优先级**：CLI 参数 > 配置文件 `llm` 段 > 内置默认值。

## 关于 `llm.stream`

默认 `true`，即对所有模型走流式（SSE）。这是多数网关的推荐模式。

若你的端点不支持流式，无需改动——工具会自动降级为非流式重试一次。
要强制关闭，用 `--no-stream` 或在配置里写 `stream: false`。

## 关于 `notify.webhook`

默认留空，即**不发送任何通知、不产生任何网络请求**。

配置后的行为：报告自检发现 high 级别问题时，按 4096 字节分片推送 markdown 消息。

### 负载格式说明

工具发送的负载是：

```json
{
  "msgtype": "markdown",
  "markdown": {
    "content": "<消息正文>",
    "text": "<消息正文>",
    "title": "QA 报告质量告警"
  }
}
```

同时带 `content` 和 `text` 是为了兼容不同平台：

| 平台 | 能否直接使用 | 说明 |
|---|---|---|
| 企业微信 | ✅ | 读 `markdown.content` |
| 钉钉 | ✅ | 读 `markdown.text` 与 `markdown.title` |
| 飞书 | ⚠️ 需转换 | 负载结构不同（`msg_type` + `content` 嵌套），需自建转换网关 |
| Slack | ⚠️ 需转换 | 负载结构不同（顶层 `text` 或 Block Kit），需自建转换网关 |

配置示例（企业微信）：

```yaml
notify:
  webhook: "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=<你的key>"
```

配置示例（钉钉，需在安全设置里放行来源 IP 或用加签）：

```yaml
notify:
  webhook: "https://oapi.dingtalk.com/robot/send?access_token=<你的token>"
```

**安全提示**：webhook URL 里通常含有可直接发消息的凭据。
不要把它提交到版本库——放在 `.qa-agent/local/.env` 或 CI 的 secret 里，用
`--webhook` 参数或环境变量注入。

## 命令行覆盖

`--webhook` 参数优先级高于配置文件，适合在 CI 里临时指定：

```bash
ming-qa qa-self-check --webhook "https://..." ...
```
