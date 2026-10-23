# grill-me

`grilling` 的 user-invoked 入口：`/grill-me` 触发一轮拷问式访谈，锐化一个计划或设计。正文只有一行「Call the Skill tool with "grilling"」。

## 依赖

- 运行时调用 `grilling`（本仓库 `skills/engineering/grilling`），必须同时安装。

| Field | Value |
|---|---|
| Origin | Vendored from [mattpocock/skills](https://github.com/mattpocock/skills) v1.3.1 (`productivity/grill-me`) |
| Author / License | Matt Pocock / MIT（LICENSE 随目录保留） |
| Vendored scope | SKILL.md 原样拷贝；剔除 `agents/openai.yaml`（Codex UI 元数据） |
| Local modifications | none |
