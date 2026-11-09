# skills-ecosystem

用 `npx skills` CLI(vercel-labs/skills,MIT)管理开放技能生态:发现(skills.sh 排行榜 + `find`)、安装(`add`,project/global、symlink/copy、锁文件)、更新(`check`/`update`)、移除(`remove`)、免安装试用(`use`),以及把本仓库作为技能源直装。

| Field | Value |
|---|---|
| Origin | 自研;内容依据 [vercel-labs/skills](https://github.com/vercel-labs/skills) 的 `docs/`(commands.md、creating-skills.md、agents.md、troubleshooting.md,MIT) |
| Author / License | 本仓库自研 / MIT |
| Vendored scope | 无文件拷贝;`npx skills add jinnnyang/skills --list` 与 `npx skills add ./ --list` 已实测(2026-11-09,CLI 发现 39 个技能) |
| Local modifications | 不适用(原创) |

## 与本仓库的关系

- `meta/skill-creator`(anthropics/skills)— 管技能**创作**与评估
- `meta/writing-for-agents`(mattpocok/skills)— 管写给 agent 的文档质量
- 本技能 — 管技能生态的**发现/安装/更新/移除**,三者互补

## 与上游 find-skills 的关系

上游自带 `skills/find-skills` 技能(只覆盖发现+安装);全局 `~/.agents/skills/find-skills` 已装原版 + Hermes 补丁。本技能覆盖完整生命周期并补充本仓库特有用法,避免重复 vendor。
