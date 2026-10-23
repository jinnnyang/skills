# to-spec

把当前对话固化成 spec 并发布到 issue tracker：不做访谈，只综合已有讨论。固定模板：Problem Statement / Solution / User Stories / Implementation Decisions / Testing Decisions / Out of Scope。不写具体文件路径与代码片段（易过时；原型产出的决策性片段除外）。

## 已知上游耦合（暂不处理）

- 正文引用 `/setup-matt-pocock-skills` 提供的 issue tracker 配置；本仓库未收编该技能，缺配置时按提示口头指定 tracker（如 GitHub issues）即可。

## 流程衔接

- 软衔接：通常先 grill-with-docs 再 to-spec，无 Skill tool 硬调用。产出交 to-tickets 拆分。

| Field | Value |
|---|---|
| Origin | Vendored from [mattpocock/skills](https://github.com/mattpocock/skills) v1.3.1 (`engineering/to-spec`) |
| Author / License | Matt Pocock / MIT（LICENSE 随目录保留） |
| Vendored scope | SKILL.md 原样拷贝；剔除 `agents/openai.yaml`（Codex UI 元数据） |
| Local modifications | none |
