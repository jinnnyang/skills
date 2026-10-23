# html-page

单页 HTML 开发技能：设计、生成自包含 .html 交付物（内联 CSS/JS、响应式、组件设计）。必读链：frontend-design.md（设计立场，改编自 anthropics/skills frontend-design, Apache-2.0）→ 灵动报告 interactive-report.md；图表场景走 chart/atlas.md（图表选型图谱 + 交互实现）。`scripts/shot.py` 一次完成加载+截图+结构/错误/溢出检查（Playwright 优先，自动降级 chrome/edge CLI）。

| Field | Value |
|---|---|
| Origin | Vendored from Doubao desktop agent workspace skills (`...\.doubao\agent_mode\workspace\.skills\html`) |
| Author / License | ByteDance Doubao team / 未附许可；仅个人内部使用，不用于商业用途。frontend-design.md 上游为 anthropics/skills（Apache-2.0），文内已注明改编 |
| Vendored scope | SKILL.md、references/、scripts/ 原样拷贝 |
| Local modifications | frontmatter `name: html` → `html-page`（避免与通用技能名冲突）；「发布成 doubao-html 链接」路径改为注明平台不适用；剔除 `agents/`、`assets/` |

## 实测

shot.py 在本机跑通（无 Playwright，自动降级 Chrome CLI 截图 + lint 报告 + auto-fix）。

## 与本仓库的关系

与 `creative/claude-design`、`popular-web-designs` 同域互补：本技能强在「报告型 HTML」——图表交互、灵动叙事报告、截图自检管线。
