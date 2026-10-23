# visualization

统一可视化技能：把适合图形表达的内容转成确定性、可复核的图表/图解。五种模式路由——ECharts 精确数据图、HTML/SVG 信息图与交互演示、原图叠加标注、生成式知识配图、纯文字降级。核心纪律：数据不可生图（精确数值只走 ECharts/HTML/SVG）、静态默认（交互必须揭示新信息）、证据保真、失败可降级。`scripts/validate_skill.py` 校验结构与加载预算。

| Field | Value |
|---|---|
| Origin | Vendored from Doubao desktop agent workspace skills (`...\.doubao\agent_mode\workspace\.skills\doubao-visualization`) |
| Author / License | ByteDance Doubao team / 未附许可；仅个人内部使用，不用于商业用途 |
| Vendored scope | SKILL.md、references/（22 个文件）、examples/、schemas/、scripts/ 原样拷贝 |
| Local modifications | frontmatter `name: doubao-visualization` → `visualization`（目录同步改名为 `skills/design/visualization/`，`scripts/validate_skill.py` 的 name 断言一并更新）；剔除 `agents/openai.yaml` |

## 平台独立性

实测无豆包平台耦合：输出协议是 ` ```echarts` 代码块和 ` ```html type="renderer"` 标签，不依赖 present_files/design-cli 等 Doubao 工具。references 中唯一提平台的是 echarts-source.md（来源追溯说明，无害保留）。

## 与本仓库的关系

补充 `creative/` 系（svg-illustration、architecture-diagram、baoyu-infographic）缺的**数据可视化**一环：ECharts option 规范、交互/几何/数学渲染稳定性、移动端适配都有专册。
