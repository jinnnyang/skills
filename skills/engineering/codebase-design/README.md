# codebase-design

深模块设计的共享词汇表：module / interface / depth / seam / adapter / leverage / locality，及删除测试、「接口即测试面」「一个 adapter = 假想 seam，两个 = 真 seam」等原则。DEEPENING.md 与 DESIGN-IT-TWICE.md 为进阶参考。

## 依赖

- 无外部依赖。上游 improve-codebase-architecture（未收编）会调用它取词汇；TDD 流程也可参考。

| Field | Value |
|---|---|
| Origin | Vendored from [mattpocock/skills](https://github.com/mattpocock/skills) v1.3.1 (`engineering/codebase-design`) |
| Author / License | Matt Pocock / MIT（LICENSE 随目录保留） |
| Vendored scope | SKILL.md、DEEPENING.md、DESIGN-IT-TWICE.md 原样拷贝；剔除 `agents/openai.yaml`（Codex UI 元数据） |
| Local modifications | none |
