# diagnosing-bugs

疑难 bug / 性能回归的诊断闭环：复现 → 假设 → 插桩验证 → 修复 → 回归，先理解根因再动手改。探索时读 `GLOSSARY.md` 与相关 ADR 建立模块心智模型。`scripts/hitl-loop.template.sh` 是 human-in-the-loop 循环模板。

## 在本仓库的角色

兜底技能：执行代理修不掉的 bug 才升级到这一步。

| Field | Value |
|---|---|
| Origin | Vendored from [mattpocock/skills](https://github.com/mattpocock/skills) v1.3.1 (`engineering/diagnosing-bugs`) |
| Author / License | Matt Pocock / MIT（LICENSE 随目录保留） |
| Vendored scope | SKILL.md、scripts/hitl-loop.template.sh 原样拷贝；剔除 `agents/openai.yaml`（Codex UI 元数据） |
| Local modifications | none |
