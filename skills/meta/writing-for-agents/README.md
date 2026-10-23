# writing-for-agents

给 agent 写文档的元技能（技能、AGENTS.md/CLAUDE.md、context pointer 指向的文档通用）：双负载模型（context load / cognitive load）、leading words、二元可检查完成判据、删减优先、渐进披露、co-location。SKILL-MECHANICS.md 专讲技能 frontmatter、invocation 选择与路由技能。

## 在本仓库的角色

维护本仓库所有 SKILL.md / README.md 的写作规范来源；新增技能时与 `meta/skill-creator` 配合（skill-creator 管评估管线，本技能管写作质量）。

## 被依赖

- `engineering/retro` 开头显式调用它。

| Field | Value |
|---|---|
| Origin | Vendored from [mattpocock/skills](https://github.com/mattpocock/skills) v1.3.1 (`productivity/writing-for-agents`) |
| Author / License | Matt Pocock / MIT（LICENSE 随目录保留） |
| Vendored scope | SKILL.md、SKILL-MECHANICS.md 原样拷贝；剔除 `agents/openai.yaml`（Codex UI 元数据） |
| Local modifications | none |
