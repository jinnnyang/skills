# grilling

拷问式访谈：就一个计划/决策/想法 relentless 地追问用户，直到达成共识。设计树（design tree）逐轮展开，每轮一次性问完 frontier 上的全部问题并给出推荐答案；事实自己查（可派子代理），决策留给用户。

## 在本仓库的角色

「指挥者-执行者」工作流的第一环：给委派代理写 brief 前先拷问计划，消除歧义。grill-me、grill-with-docs、wayfinder 都以它为底层引擎。

## 依赖

- 无外部依赖。被 grill-me、grill-with-docs、wayfinder、triage 引用。

| Field | Value |
|---|---|
| Origin | Vendored from [mattpocock/skills](https://github.com/mattpocock/skills) v1.3.1 (`productivity/grilling`) |
| Author / License | Matt Pocock / MIT（LICENSE 随目录保留） |
| Vendored scope | SKILL.md 原样拷贝；剔除 `agents/openai.yaml`（Codex UI 元数据） |
| Local modifications | none |
