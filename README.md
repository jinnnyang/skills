# Personal Skills

基于 [Agent Skills 标准](https://agentskills.io/specification)（Anthropic 主导的开放规范）的个人技能库。技能是自包含目录：一个 `SKILL.md`（YAML frontmatter + 指令正文），可选 `scripts/`、`references/`、`assets/`。

## 仓库结构

```
skills/
├── .claude-plugin/marketplace.json  # Claude Code 插件市场注册表（技能分发入口）
├── skills/
│   └── skill-creator/               # 元技能：创建/测试/评估/优化其他技能（含完整 CI/CD 式评估管线）
├── spec/
│   └── agent-skills-spec.md         # 规范指针（正文见 agentskills.io/specification）
├── template/
│   └── SKILL.md                     # 新建技能的最小模板
├── README.md
└── .gitignore
```

## 当前状态

- **骨架阶段**：仅含 `skill-creator` 元技能（含 agents/、scripts/、eval-viewer/、references/、assets/ 全管线）。
- 自有技能将陆续迁入（原 more-skills 中的技能计划迁移至此）。

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

- `skill-creator` 源自 [anthropics/skills](https://github.com/anthropics/skills)（Apache-2.0），`LICENSE.txt` 随目录保留。
- 仓库未包含 anthropics 的 `document-skills`（docx/pdf/pptx/xlsx）：其为 source-available 许可、不可再分发，仅可自行参考其设计思路实现。
- 其余第三方依赖与声明见各技能目录内 LICENSE / THIRD_PARTY_NOTICES。

## 待办

- [x] marketplace.json 的 `name` / `owner` / `email` 已替换为实际标识（2026-10-15：email=jinnnyang@139.com）
- [ ] 迁移自有技能（从 more-skills 挑选）
- [ ] 技能迁移后按分组扩充插件定义
