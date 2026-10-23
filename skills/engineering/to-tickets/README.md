# to-tickets

把计划/spec/对话拆成 tracer-bullet 垂直切片 ticket：每个 ticket 声明阻塞边（blocked-by），独立可拿取。用户审批粒度与依赖边后发布：本地 tracker 写 `.scratch/<slug>/issues/<NN>-<slug>.md`（一票一文件，阻塞者在前），真实 tracker（GitHub/Linear）逐票发 issue 用原生阻塞链接。

## 已知上游耦合（暂不处理）

- 同 to-spec：依赖 `/setup-matt-pocock-skills` 的 tracker 配置，缺失时口头指定即可。

## 在本仓库的角色

「任务拆分」核心：拆好的 ticket 天然适合逐个丢给 Codex/Claude Code 并行执行（配合 `skills/subagents/` 委派技能）。

| Field | Value |
|---|---|
| Origin | Vendored from [mattpocock/skills](https://github.com/mattpocock/skills) v1.3.1 (`engineering/to-tickets`) |
| Author / License | Matt Pocock / MIT（LICENSE 随目录保留） |
| Vendored scope | SKILL.md 原样拷贝；剔除 `agents/openai.yaml`（Codex UI 元数据） |
| Local modifications | none |
