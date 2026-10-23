# triage

把外部 issue / PR 走过 triage 角色状态机：分类、验证、必要时 grilling，最终产出 agent-ready brief（模板见 AGENT-BRIEF.md）。被否决的设计决策记录在 OUT-OF-SCOPE.md。

## 已知上游耦合（暂不处理）

- 角色名到实际 label 字符串的映射依赖 `/setup-matt-pocock-skills` 配置；缺失时口头指定映射即可。

## 依赖

- 深度使用 `grilling`（本仓库 `skills/engineering/grilling`）。

| Field | Value |
|---|---|
| Origin | Vendored from [mattpocock/skills](https://github.com/mattpocock/skills) v1.3.1 (`engineering/triage`) |
| Author / License | Matt Pocock / MIT（LICENSE 随目录保留） |
| Vendored scope | SKILL.md、AGENT-BRIEF.md、OUT-OF-SCOPE.md 原样拷贝；剔除 `agents/openai.yaml`（Codex UI 元数据） |
| Local modifications | none |
