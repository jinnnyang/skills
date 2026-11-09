---
name: skills-ecosystem
description: Manage the open agent skills ecosystem with the `npx skills` CLI (skills.sh registry). Use when the user wants to find, install, update, try, or remove skills ("find a skill for X", "install a skill", "update my skills"), or wants to install skills from this catalog repo (jinnnyang/skills) into an agent.
license: MIT
---

# Skills Ecosystem (`npx skills`)

`npx skills` 是开放技能生态的包管理器(上游 [vercel-labs/skills](https://github.com/vercel-labs/skills),MIT):注册表 [skills.sh](https://skills.sh),技能格式即本仓库遵循的 [agentskills.io](https://agentskills.io/specification) 规范。本技能管**发现/安装/更新/移除**;技能**创作**方法论见 `meta/skill-creator` 与 `meta/writing-for-agents`,不在本文重复。

## 前置条件

- Node.js ≥ 22.20(本机已装 v24.15.0,满足)
- 关闭遥测:`DISABLE_TELEMETRY=1`(或 `DO_NOT_TRACK=1`)
- 私有仓库走已有 Git 凭据(Git credential helper → GitHub CLI → SSH 回退);`GITHUB_TOKEN`/`GH_TOKEN` 可显式指定

## 发现技能

1. 先看 [skills.sh 排行榜](https://skills.sh/)(按安装量排序,常见需求通常已有高安装量技能,如 vercel-labs/agent-skills、anthropics/skills)
2. 再搜索:`npx skills find [query] [--owner <owner>]`(无参数进入 fzf 式交互搜索)
3. **推荐前必须验证质量**:安装量(优先 1K+,<100 谨慎)、来源(官方组织优先)、仓库 star 数;给出技能名、用途、安装量、安装命令、skills.sh 链接

## 安装技能

```bash
npx skills add <source>                # 交互选择技能与目标 agent
npx skills add <owner>/<repo> -s <skill> -a <agent> -g -y   # 非交互
```

Source 格式:`owner/repo`、`owner/repo@v1.2.3`(tag/commit)、GitHub/GitLab/Azure/任意 git URL、指向仓库内技能子目录的 tree URL、本地路径 `./dir`、直接 SKILL.md 或压缩包下载 URL(限 10 MiB / 解压 25 MiB / 1000 文件)。

| 选项 | 作用 |
|---|---|
| `-g` | 装到用户级 `~/<agent>/skills/`(默认装到当前项目 `./<agent>/skills/`) |
| `-a <agents...>` | 指定目标 agent(`claude-code`、`codex`、`hermes-agent` 等 79 个,见 docs/agents.md;`'*` 为全部) |
| `-s <skills...>` | 按名选技能(`'*'` 为全部;带空格的技能名要加引号) |
| `-l` / `--list` | 只列出仓库内可用技能,不安装 |
| `--copy` | 拷贝文件而非 symlink(symlink 是推荐默认:单一真源,易更新) |
| `-y` / `--all` | 跳过确认 / 全部装到全部 agent |

## 管理已装技能

```bash
npx skills list                    # 列出已装(可 -g 只看全局,-a 按 agent 过滤)
npx skills check                   # 检查更新(有更新时 exit 1,可做 CI 门禁)
npx skills update [skills...]      # 更新全部或指定技能(-g 全局 / -p 项目 / -y 跳过 scope 提问)
npx skills remove [skills...]      # 移除(--all 即 --skill '*' --agent '*' -y)
npx skills use <owner>/<repo>@<skill>   # 免安装试用:输出 prompt 或 --agent 直接启动该 agent
```

项目级安装记录在 `skills-lock.json`(source、路径、内容哈希),`check`/`update`/`experimental_install`(从锁恢复)都靠它;CI 里默认 `--frozen-lockfile`,内容不符即失败。`experimental_sync` 可把 npm 依赖自带的技能和 `package.json` 的 `skills` 数组同步进项目。

## 从本仓库安装

本仓库(`jinnnyang/skills`)本身就是合法技能源:`skills/<分类>/<技能>/SKILL.md` 目录布局 + `.claude-plugin/marketplace.json` 清单都在 CLI 的发现规则内:

```bash
npx skills add jinnnyang/skills --list                    # 列出本仓库全部技能
npx skills add jinnnyang/skills -s term-cli -a claude-code -g -y
npx skills add ./                                        # 本地路径直装(开发自用)
```

自定义技能目录可写在仓库根 `skills.sh.json` 的 `paths` 字段。

## 注意

- Hermes Agent 内请改用原生 `hermes skills search/install/list`(npx skills 装到 Hermes 不读取的目录);详见 `subagents/hermes-agent`
- prime-agent 不在 CLI 支持的 79 个 agent 之列,其技能目录由 harness 自身管理
- 实验命令(`experimental_*`)名称与行为可能随时变更,勿在脚本里硬依赖

## 参考

上游文档(docs/ 目录):commands.md(完整命令参考)、creating-skills.md(格式与发现规则)、agents.md(79 agent 路径表)、troubleshooting.md(环境变量与遥测)。
