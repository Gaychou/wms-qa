# 数据准备模式参考

## PRE/POST 模式

部分测试脚本在文件头注释中标注了 MCP 数据准备指令，格式为：

```bash
#   PRE:  mcp__mysql_mcp__write_query "UPDATE ... SET field=value WHERE id=..."
#   POST: mcp__mysql_mcp__write_query "UPDATE ... SET field=original WHERE id=..."
```

执行此类脚本时，**必须按以下流程操作**：

1. **解析脚本头**：用 `Read` 工具读取脚本前 30 行，搜索 `PRE:` / `POST:` 行
2. **执行 PRE**：对每条 `PRE:` 行，提取 MCP 工具名和 SQL，通过对应 MCP 工具执行。若 PRE 失败 → task 标记为 `blocked`，记录失败原因，不继续执行脚本
3. **执行脚本**：`ming-qa run-with-env` 或 `bash` 运行脚本
4. **执行 POST**：**无论脚本 pass/fail，都必须执行 POST 还原数据**。若 POST 失败 → 在 evidence 中记录"数据未还原"，标记为需人工介入
5. **核实还原**：POST 后通过 MCP `read_query` 确认数据已恢复。MCP 不可用时通过后端 API 降级核实

PRE/POST 中的变量（如 `<PENDING_ID>`）需在执行前从 spec-task 的 `data` 字段或实际数据库查询结果中解析为具体值。

## 数据准备风险分级

部分 task 需要 DELETE/TRUNCATE 等不可逆操作才能构造测试前提（如 P1-030 需删 t_prize 记录构造孤儿 prizeId）。对此类 task，按以下分级处理：

| 风险等级 | 操作类型 | 处理方式 |
|---------|---------|---------|
| **低** | UPDATE 单字段（余额、状态、flag），有明确还原 SQL | 正常执行 PRE/POST，task 跑完后立即还原 |
| **中** | UPDATE 多表关联字段，或需构造跨表不一致状态 | 执行前在 evidence 中记录完整还原计划，执行后逐条核实 |
| **高** | DELETE / INSERT 到核心业务表，或需修改多行 | 先备份受影响行（SELECT → 保存到 evidence），再执行 PRE，task 跑完后从备份还原。备份 JSON 需包含完整行数据，确保可逐列还原 |
| **禁止** | DROP TABLE / TRUNCATE / ALTER TABLE | 永不自动执行。标记 task 为 blocked，在 blocker 中说明原因，nextAction 写"需人工在隔离环境验证" |

高风险 task 执行前，必须在 evidence 中记录：
- 备份数据的位置和内容摘要
- 还原步骤的逐一验证结果
- 若还原失败 → task 标记为 blocked，不进入下一 task

## 临时数据还原（兜底机制）

对于无法用 PRE/POST 覆盖的临时数据变更，在所有 task 执行后逐条还原：

- 记录修改前的值（在执行 PRE 时同步记录）
- 跑完所有 task 后检查是否有未执行 POST 的残留变更
- 逐条还原并核实

核实方式：MySQL MCP `read_query` 确认值与修改前一致。MySQL MCP 不可用时通过后端 API 降级核实。

优先使用 PRE/POST 模式：每条 task 脚本各自声明自己的 PRE/POST，task 执行完立刻还原，不等到全部跑完才统一还原。这样即使中途有 task 崩溃，也只有当前一条 task 的数据未还原。
