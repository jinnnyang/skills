# human-signal

去 AI 味写作技能：生成、改写或诊断文本中的 AI 味，让文本真实、可信、有作者声音。核心原则：保真第一（只改怎么说不改说什么）、低误报（自然的文本允许「不需要大改」）、风格保真（学用户的节奏词汇而非套通用人味）、产物取胜（人感是手段不是目的）。11 份 references 覆盖体裁/平台/受众/领域/评估/案例/模式库。

| Field | Value |
|---|---|
| Origin | Vendored from Doubao desktop agent workspace skills (`...\.doubao\agent_mode\workspace\.skills\doubao-human-signal` v2.2.9) |
| Author / License | ByteDance Doubao team / 未附许可声明；经确认仅个人内部使用，不用于商业用途，不对外分发 |
| Vendored scope | SKILL.md、references/ 11 个文件原样拷贝 |
| Local modifications | frontmatter `name: doubao-human-signal` → `human-signal`（去平台前缀）；剔除 `agents/openai.yaml` |

## 与本仓库的关系

与 `creative/humanizer` 同主题（去 AI 味），二者对照使用：humanizer 是 Hermes 生态版本，本技能是字节实战版（含评估方法、模式库、平台分册），冲突时按效果取用。
