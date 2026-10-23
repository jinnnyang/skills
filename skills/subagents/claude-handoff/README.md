# claude-handoff

handoff 的 Claude Code 变体：不落盘，把 handoff 摘要作为 prompt 直接拉起后台代理（`claude --bg --name "<名称>" "<摘要>"`），立即返回，用户用 `claude agents` 管理。`--name` 必传且须描述性。

## 依赖

- Claude Code CLI 的 `--bg` / `agents` 子命令。同目录 `handoff` 是它的落盘版。

| Field | Value |
|---|---|
| Origin | Vendored from [mattpocock/skills](https://github.com/mattpocock/skills) v1.3.1 (`in-progress/claude-handoff`) |
| Author / License | Matt Pocock / MIT（LICENSE 随目录保留） |
| Vendored scope | SKILL.md 原样拷贝；剔除 `agents/openai.yaml`（Codex UI 元数据） |
| Local modifications | none |
