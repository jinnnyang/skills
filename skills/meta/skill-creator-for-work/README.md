# skill-creator-for-work

字节版技能创建指南：创建/更新 SKILL.md 的工作流。核心原则与 Anthropic skill-creator 同源（context window 是公共资源、按任务脆弱性定自由度、示例优于解释），附 output-patterns / workflows 两份参考与 init_skill.py、quick_validate.py 脚本。

| Field | Value |
|---|---|
| Origin | Vendored from Doubao desktop agent workspace skills (`...\.doubao\agent_mode\workspace\.skills\skill-creator-for-work`) |
| Author / License | ByteDance Doubao team / Apache-2.0（LICENSE.txt 随目录保留） |
| Vendored scope | SKILL.md、references/、scripts/、LICENSE.txt 原样拷贝 |
| Local modifications | none（剔除 `agents/`，原本就没有） |

## 与本仓库的关系

本仓库现有三套技能写作方法论，对照使用：
- `meta/skill-creator`（anthropics/skills, Apache-2.0）— 评估管线最完整（evals/对照评测/eval-viewer）
- `meta/writing-for-agents`（mattpocock/skills, MIT）— 写作质量杠杆（leading words、完成判据、删减优先）
- 本技能（字节）— 工作流视角（init/validate 脚本化）

新增技能时以 skill-creator 为主线，另两者做质量校准。
