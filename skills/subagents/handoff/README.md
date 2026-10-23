# handoff

把当前对话压缩成 handoff 文档交给下一个 agent 接力：写入系统临时目录（非工作区），含「suggested skills」节；不重复 spec/ADR/issue/diff 已有内容，只引用路径；脱敏。用户传入的参数视为下个 session 的重点说明。

## 在本仓库的角色

跨代理/跨 session 的胶水：Hermes ↔ Codex/Claude Code 之间导出可移植状态。落盘版；「不落盘直接拉起 Claude Code 后台代理」的变体已并入 `skills/subagents/claude-code` 的 Background Mode（--bg）节。

| Field | Value |
|---|---|
| Origin | Vendored from [mattpocock/skills](https://github.com/mattpocock/skills) v1.3.1 (`productivity/handoff`) |
| Author / License | Matt Pocock / MIT（LICENSE 随目录保留） |
| Vendored scope | SKILL.md 原样拷贝；剔除 `agents/openai.yaml`（Codex UI 元数据） |
| Local modifications | none |
