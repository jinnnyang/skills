# Personal Skills

基于 [Agent Skills 标准](https://agentskills.io/specification)（Anthropic 主导的开放规范）的个人技能库。技能是自包含目录：一个 `SKILL.md`（YAML frontmatter + 指令正文），可选 `scripts/`、`references/`、`assets/`。

## 仓库结构

```
skills/
├── .claude-plugin/marketplace.json  # Claude Code 插件市场注册表（由 scripts/gen_marketplace.py 生成）
├── skills/
│   ├── documents/
│   │   └── ...                      # Office/PDF 文件格式处理（docx、pptx 等）
│   ├── engineering/                 # 软件工程工作流（vendor 自 mattpocock/skills, MIT）：grilling/to-spec/to-tickets/code-review/diagnosing-bugs/retro 等
│   ├── github/
│   │   └── ...                      # GitHub 工作流（gh CLI / git）
│   ├── subagents/
│   │   ├── ...                      # 外部编码智能体委托（Codex/Claude Code/OpenCode/prime-agent）
│   │   └── handoff/                 # 跨代理/跨 session handoff 文档导出（vendor 自 mattpocock/skills；后台变体并入 claude-code 技能）
│   ├── terminal/
│   │   ├── term-cli/                # 交互式终端会话控制（vendor 自 EliasOenal/term-cli, BSD-3-Clause-Clear）
│   │   └── powershell-safe-invocation/  # PowerShell 安全调用规范（vendor 自 Misaka-Mikoto-Tech, MIT）
│   ├── creative/
│   │   └── human-signal/            # 去 AI 味写作（vendor 自 Doubao 桌面端技能，仅个人内部使用）
│   ├── design/
│   │   ├── doubao-visualization/    # 统一可视化（ECharts/HTML-SVG/原图叠加，vendor 自 Doubao，仅个人内部使用）
│   │   └── html-page/               # 单页 HTML 开发 + 截图自检（vendor 自 Doubao，仅个人内部使用）
│   └── meta/
│       ├── skill-creator/           # 元技能：创建/测试/评估/优化其他技能（源自 anthropics/skills, Apache-2.0）
│       ├── skill-creator-for-work/  # 字节版技能创建指南（vendor 自 Doubao 桌面端技能, Apache-2.0）
│       ├── verifier-hub/            # 产物确定性校验 CLI（vendor 自 Doubao 桌面端技能，仅个人内部使用）
│       └── writing-for-agents/      # 元技能：给 agent 写文档的方法论（vendor 自 mattpocock/skills, MIT）
├── spec/
│   └── agent-skills-spec.md         # 规范指针（正文见 agentskills.io/specification）
├── template/
│   └── SKILL.md                     # 新建技能的最小模板
├── scripts/
│   └── gen_marketplace.py           # 扫描 skills/ 生成 marketplace.json 注册表
├── README.md
└── .gitignore
```

## 当前状态

- `meta/skill-creator`：源自 anthropics/skills（Apache-2.0），含 agents/、scripts/、eval-viewer/ 全管线。
- `documents/pptx`：自研 PPTX 技能（SKILL.md、脚本、校验器均为原创；XSD 来自 ECMA-376/W3C 官方发布，许可见其 SCHEMAS-LICENSE.md）。
- `terminal/term-cli`：vendor 自 [EliasOenal/term-cli](https://github.com/EliasOenal/term-cli)（BSD-3-Clause-Clear），仅拷贝 SKILL.md + term-cli/term-assist 脚本 + LICENSE + install.sh；硬依赖 tmux，Windows 需 WSL/MSYS。见其 README.md。
- `terminal/powershell-safe-invocation`：vendor 自 [Misaka-Mikoto-Tech/agent-skills](https://github.com/Misaka-Mikoto-Tech/agent-skills)（MIT），SKILL.md + reference.md 原样拷贝。
- `engineering/*`（13 个）+ `subagents/handoff` + `meta/writing-for-agents`：vendor 自 [mattpocock/skills](https://github.com/mattpocock/skills) v1.3.1（MIT）。分类调整：原 productivity/engineering/in-progress 三桶按本仓库语义收进 engineering/（工作流）、subagents/（跨代理接力）、meta/（元技能）。每个技能剔除 `agents/openai.yaml`，LICENSE 随目录保留，详见各自 README.md。
- 未收编（对委派工作流价值低）：implement、implement-spec、tdd、ask-matt、teach、wizard、wait-what、writing-beats/fragments/shape、pr、research、improve-codebase-architecture、setup-matt-pocock-skills。
- docx/pdf/xlsx 的 anthropic 原版技能为 source-available、不可再分发，存于本地参考目录（仓库外），后续按需自研替代。

## 添加一个新技能

1. 在 `skills/` 下建目录，写入 `SKILL.md`（frontmatter 必填 `name` + `description`，可选 `license`/`allowed-tools`/`metadata`/`compatibility`；`name` 限 kebab-case ≤64 字符，`description` 限 1024 字符且不得含尖括号）；
2. 推荐用 `skill-creator` 起草、评估、优化 description；
3. 在 `.claude-plugin/marketplace.json` 的插件 `skills[]` 数组注册 `./skills/<skill-name>`。

## 使用 skill-creator

直接向 Claude 说"用 skill-creator 创建/改进/评估某个技能"即可触发。它内置完整流程：

- 访谈澄清意图 → 起草 SKILL.md → 写测试用例（`evals/evals.json`）
- 并行子代理评估（带技能 vs 不带技能对照组）→ 量化断言打分（grading.json）
- 聚合 benchmark → 浏览器审查（eval-viewer）→ 反馈迭代
- description 优化（train/test 分层防过拟合）→ 打包 `.skill`（package_skill.py）

## 快速校验

```bash
# 依赖：PyYAML（python -m pip install pyyaml 或 uv pip install pyyaml）
# 校验 skill-creator 结构是否合法（10 道验证门）
python skills/skill-creator/scripts/quick_validate.py skills/skill-creator
```

## 来源与许可

- `meta/skill-creator` 源自 [anthropics/skills](https://github.com/anthropics/skills)（Apache-2.0），`LICENSE.txt` 随目录保留。
- `documents/pptx` 为自研实现：SKILL.md 与脚本均为原创；`scripts/office/schemas/` 下的 XSD 是 ECMA-376（Ecma International，版权政策允许带声明分发）与 W3C 的官方标准文件，来源与声明见该目录 `SCHEMAS-LICENSE.md`。
- anthropics 的 `document-skills`（docx/pdf/pptx 原版、xlsx）：source-available、不可再分发，不随仓库分发；本地参考副本存于仓库外，仅作设计参考。

## 待办

- [x] marketplace.json 的 `name` / `owner` / `email` 已替换为实际标识（2026-10-15：email=jinnnyang@139.com）
- [x] 迁移自有技能（更名重组：skill-creator → meta/，自研 pptx 落地 documents/）
- [ ] docx/xlsx 按需自研替代（原版留在仓库外参考目录）
- [ ] 按分组扩充插件定义
