# code-review

双轴评审 HEAD 与指定基线（commit/branch/tag/merge-base）间的 diff：Standards 轴（是否符合仓库成文规范）+ Spec 轴（是否实现原始 issue/spec 要求），并行子代理跑，结果并排呈现。

## 已知上游耦合（暂不处理）

- 提到 `/setup-matt-pocock-skills` 的 issue tracker 配置；缺失时提示手动运行，不影响核心评审流程。

## 在本仓库的角色

委派收尾的质量闸门：执行代理交活后用它把关，再进 PR。

| Field | Value |
|---|---|
| Origin | Vendored from [mattpocock/skills](https://github.com/mattpocock/skills) v1.3.1 (`engineering/code-review`) |
| Author / License | Matt Pocock / MIT（LICENSE 随目录保留） |
| Vendored scope | SKILL.md 原样拷贝；剔除 `agents/openai.yaml`（Codex UI 元数据） |
| Local modifications | none |
