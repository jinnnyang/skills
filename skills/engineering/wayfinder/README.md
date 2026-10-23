# wayfinder

大雾型超大工作（单 session 装不下）的寻路规划：把「通往目的地的路」画成 issue tracker 上的共享决策票地图（decision tickets，问的是决策不是施工切片），一次解一票，路线清晰后移交 to-spec。

## 依赖

- 步骤 1 调用 `grilling` + `domain-modeling`（均在本仓库 `skills/engineering/`）。

## 场景

按需使用：仅大型 greenfield / 方向未明的规划需要；常规规模直接 grill → to-spec → to-tickets。

| Field | Value |
|---|---|
| Origin | Vendored from [mattpocock/skills](https://github.com/mattpocock/skills) v1.3.1 (`engineering/wayfinder`) |
| Author / License | Matt Pocock / MIT（LICENSE 随目录保留） |
| Vendored scope | SKILL.md 原样拷贝；剔除 `agents/openai.yaml`（Codex UI 元数据） |
| Local modifications | none |
