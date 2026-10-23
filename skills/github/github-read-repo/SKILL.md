---
name: github-read-repo
description: "Pull a GitHub repo's docs, code digest, or architecture diagram (DeepWiki / Gitingest / GitDiagram), then read/edit them section-by-section without flooding context."
version: 2.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [GitHub, DeepWiki, Gitingest, GitDiagram, Documentation, Markdown, Read, Ast]
    related_skills: [github-repo-management, github-auth, github-pr-workflow]
---

# GitHub 仓库内容读取（三源 Pull + 分段 Read/Edit）

为大型 GitHub 仓库拉取**仓库理解资料**，然后按「章节 / 行区间」分段读取或编辑，**避免把整份大文档一次性塞进上下文**。

支持三个数据源，产物互补：

| 源 | 拉什么 | 产物（`data/<源>/<owner>/<repo>/`） | 适合 |
|----|--------|-----------------------------------|------|
| **DeepWiki** | 仓库生成式文档 | `structure.md` + `contents.md`（正文 markdown） | 理解设计理念、架构说明、用法 |
| **Gitingest** | 全量代码摘要 | `digest.txt`（目录结构+各文件正文）+ `summary.md` + `tree.md` + `files.json`（文件→行号索引） | 看代码本体、查具体实现 |
| **GitDiagram** | Mermaid 架构图 | `diagram.mmd`（mermaid 源码）+ `explanation.md` | 一图看懂模块/依赖关系 |

### 命令读取的内容来源

`read` / `edit` / `outline` 都在**本地文件**上操作，读取时不联网。内容来源二选一：

| 来源 | 参数 | 实际路径 |
|------|------|----------|
| 技能缓存（需先 pull） | `--repo <owner/repo>` | `data/<source>/<owner>/<repo>/` 下对应 markdown 主文件 |
| 任意本地文件 | `--file <path>` | 绝对路径，或相对技能目录 |

`--file` 与 `--repo` 互斥，必须二选一。典型流程：先 `pull` 填缓存，再离线 `outline` → `read` / `edit`。
## 前置条件

- 拉取需要网络：DeepWiki 走 `https://mcp.deepwiki.com/mcp`；Gitingest 走 `https://gitingest.com/api/ingest`；GitDiagram 走 `https://gitdiagram.com/api/*`（读取/编辑本地缓存不需要网络）。
- **无法直连外网时必须设代理**：三源拉取都识别 `HTTPS_PROXY`（另支持 `GITINGEST_PROXY` / `GITDIAGRAM_PROXY` / `MCP_PROXY` 分源覆盖）。代理格式为 HTTP CONNECT 代理，如 `http://127.0.0.1:7897`（Clash 混合端口）。脚本经 CONNECT 隧道 + 显式 TLS 握手访问目标（`scripts/utils/tunnel.ts`），设了代理无需任何额外配置。
- 首次使用先安装依赖（技能目录内自带 `package.json`）：

```bash
cd <技能目录>/github-read-repo
npm install
```

> 所有命令都在**技能目录根**（`github-read-repo/`）下运行，路径已锚定到技能目录而非 `cwd`，从任何位置执行结果一致。

## 1. 拉取仓库资料（Pull）

```bash
# DeepWiki 文档
npx tsx scripts/deepwiki.com.ts pull owner/repo
npx tsx scripts/deepwiki.com.ts pull https://github.com/owner/repo
npx tsx scripts/deepwiki.com.ts pull all

# Gitingest 代码摘要
npx tsx scripts/gitingest.com.ts pull owner/repo
npx tsx scripts/gitingest.com.ts pull all

# GitDiagram 架构图（无缓存时自动触发生成，SSE 等待）
npx tsx scripts/gitdiagram.com.ts pull owner/repo
npx tsx scripts/gitdiagram.com.ts status owner/repo   # 先看是否已生成
```

- 分别写入 `data/deepwiki.com/<owner>/<repo>/`、`data/gitingest.com/<owner>/<repo>/`、`data/gitdiagram.com/<owner>/<repo>/`。
- 文件采用**原子写入**（临时文件 + 改名），不会出现半截文档。
- DeepWiki `contents.md` 若小于 10KB 会告警并按失败处理（通常是拉取失败）。
- Gitingest 即时返回（无配额门槛）；GitDiagram 未生成的仓库触发 LLM 生成，有 IP 免费配额，需等待数十秒，且私有仓库需 `GITHUB_PAT` 环境变量（见踩坑）。

## 2. 查看章节大纲（Outline）

```bash
npx tsx scripts/read.md.ts outline --repo owner/repo
npx tsx scripts/read.md.ts outline --repo owner/repo --source gitingest
npx tsx scripts/read.md.ts outline --file path/to/doc.md
```

输出带行号的缩进树，例如：

```
    1  #1 Sample Repo Documentation
    5    #2 Installation
   11    #2 API Reference
   13      #3 getUser(id)
```

`--source` 可选，省略时自动探测：按 deepwiki → gitdiagram → gitingest 顺序找第一个有该仓库缓存的源。

## 3. 分段读取（Read）

```bash
# 按章节标题读取（模糊匹配标题，取该章节到下一个同级标题为止的正文）
npx tsx scripts/read.md.ts read --repo owner/repo --section "API Reference"

# 指定源（默认自动探测）
npx tsx scripts/read.md.ts read --repo owner/repo --source deepwiki --section "标题"
npx tsx scripts/read.md.ts read --repo owner/repo --source gitdiagram --section "标题"

# 按行区间读取（digest.txt / diagram.mmd 这类非 markdown 用这个）
npx tsx scripts/read.md.ts read --file data/gitingest.com/owner/repo/digest.txt --range "10-40"
npx tsx scripts/read.md.ts read --file data/gitdiagram.com/owner/repo/diagram.mmd --range "1-30"

# 按文件名精读 gitingest digest 里的某个文件（用 pull 时生成的 files.json 索引定位）
npx tsx scripts/read.md.ts read --file data/gitingest.com/owner/repo/digest.txt --path "src/main.ts"

# 限制输出行数（配合管道、避免 SIGPIPE 截断）
npx tsx scripts/read.md.ts read --repo owner/repo --section "标题" --limit 80

# 对任意本地 Markdown 文件（用 --file 而非 --repo）
npx tsx scripts/read.md.ts read --file path/to/doc.md --section "标题"
```

- 标题匹配为**规范化模糊匹配**（忽略大小写、空白、反引号/括号等标点），可只输部分标题；**精确匹配恒优先**于模糊候选。
- 匹配不到时，会列出候选章节（带行号与相似度分）。
- 标题得分并列时，选首个**有正文（非空 body）**的章节：DeepWiki 文档里每个页面有 `# Page: <标题>` 分隔 stub（空正文，紧挨在真实 `# <标题>` 之前），命中空 stub 会自动落到下一个有内容的候选。
- `--source` 与 markdown 主文件的对应：deepwiki→`contents.md`、gitdiagram→`explanation.md`、gitingest→`summary.md`。**Gitingest 的正文在 `digest.txt`**（非 markdown、可达数 MB），GitDiagram 的图在 `diagram.mmd`（mermaid），都用 `--file + --range` 或 `--path` 读。

## 3b. 列出 digest 内文件（Files）

```bash
# 列出 gitingest digest 里全部文件 → 起始行号（来自 pull 时生成的 files.json）
npx tsx scripts/read.md.ts files --file data/gitingest.com/owner/repo/digest.txt

# 按子串过滤
npx tsx scripts/read.md.ts files --repo owner/repo --source gitingest --filter "src/"

# 拿到行号后精读
npx tsx scripts/read.md.ts read --file data/gitingest.com/owner/repo/digest.txt --range "start-end"
# 或直接按文件名精读（推荐）
npx tsx scripts/read.md.ts read --file data/gitingest.com/owner/repo/digest.txt --path "src/main.ts"
```

## 4. 分段编辑（Edit，默认只预览）

```bash
# 预览将要发生的改动（不写盘）
npx tsx scripts/read.md.ts edit --repo owner/repo --section "Installation" --replace "## Installation\n新内容"

# 确认无误后真正写入（写入前自动备份为 <file>.backup.<时间戳>）
npx tsx scripts/read.md.ts edit --repo owner/repo --section "Installation" --replace "..." --write

# 不想要备份文件时
npx tsx scripts/read.md.ts edit --repo owner/repo --section "Installation" --replace "..." --write --no-backup
```

- **默认是 dry-run**：只打印旧/新章节，不写文件。
- `--replace` 的内容是「替换后的整段章节」（含标题行），请把标题也带上。
- `--write` 写入前默认生成备份，可用 `--no-backup` 关闭。
- **edit 只对 markdown 主文件有意义**（deepwiki contents / gitdiagram explanation / gitingest summary）；digest.txt / diagram.mmd 不要用 edit（无章节结构）。

## 参数汇总

| 参数 | 适用命令 | 作用 |
|------|----------|------|
| `--repo <owner/repo>` | 全部 | 定位到缓存 `data/<source>/<owner>/<repo>/` 下的 markdown 主文件 |
| `--source <deepwiki\|gitdiagram\|gitingest>` | 全部 | 指定数据源（省略时自动探测 deepwiki → gitdiagram → gitingest，命中时在 stderr 提示所选源） |
| `--file <path>` | 全部 | 使用任意文件路径（相对技能目录或绝对；digest.txt / diagram.mmd 用它） |
| `--section "<标题>"` | read, edit | 按标题定位章节（精确匹配优先，再模糊） |
| `--range "start-end"` | read | 按行号切片 `start..end`（1 起始，含两端） |
| `--path <file>` | read | 按文件名精读 gitingest digest 里的某个文件（依赖 files.json 索引） |
| `--filter <子串>` | files | 只列出路径含该子串的文件 |
| `--limit <N>` | read | 输出最多 N 行（大章节/管道截断时用） |
| `--replace <text>` | edit | 整段章节的替换内容（含标题行） |
| `--write` | edit | 真正写入（默认 dry-run 只预览） |
| `--no-backup` | edit | 跳过写盘前的 `<file>.backup.<时间戳>` 备份 |

**约束**：`--file` / `--repo` 二选一；`--source` 仅配合 `--repo` 使用（`--file` 已显式给路径）；`edit` 只能配 `--section`（不支持 `--range`/`--path`）；`read` 必须给 `--section`、`--range`、`--path` 三者之一，且三者互斥；`files` 只接受 `--file`/`--repo`/`--source`/`--filter`。

## 退出码

| 码 | 含义 |
|----|------|
| 0  | 成功 |
| 1  | 输入错误（参数错误 / 文件不存在 / 章节未找到） |
| 2  | 运行 / I/O / 网络错误 |

## 常用工作流

1. 选源拉取：要文档 → `deepwiki.com.ts pull`；要代码 → `gitingest.com.ts pull`；要架构图 → `gitdiagram.com.ts pull`（或先 `status` 探缓存）。
2. `outline --repo owner/repo` 看有哪些章节。
3. `read --repo owner/repo --section "<标题>"` 只读需要的章节，而不是整篇。
4. 看代码细节时 `files --file data/gitingest.com/owner/repo/digest.txt` 找文件起始行，再 `read --path`（或 `--range`）精读。
5. 需要改文档时，`edit ... --section ... --replace ...` 先预览，再 `--write`。

### 仓库对比（Repo Comparison）

对比两个（或多个）仓库时，三源并行 `pull` 两个 repo（后台终端 + notify=true），然后按相同路径读，保证对比维度对齐：

1. `gitdiagram` 的 `explanation.md` + `diagram.mmd` 是**最快的一图总览**，先读它定架构基调（UI 框架 / 渲染管线 / 是否 3D / 有无插件与自动化层）。
2. deepwiki 的固定章节做逐项对比：CAD 类仓库用 `--section "Workspace Layout and Cargo Members"` / `"Project Structure"` / `"Key Capabilities"`；跨仓库时先 `outline` 找两边**同语义**的章节名（可能不同名）。
3. 产出**决策表**（维度 × 仓库），不要两段散文——用户拿表直接做选型。
4. digest 巨大（对比场景常见 10MB+）时绝不整读，只 `read --path <具体文件>`。
5. 收尾主动问一句“要我展开哪个模块”，对比报告本身点到为止。

## 踩坑与技巧

- **GitDiagram 私有仓库**：需要 `GITHUB_PAT` 环境变量（GitHub token，Contents: Read-only 权限）。无 token 时私有仓库报 "Private repository?" 是**正确行为**。
- **GitDiagram 未生成**：公开仓库也报 not found 通常是站点侧 GitHub 访问暂限，稍后重试或用浏览器打开 `https://gitdiagram.com/<owner>/<repo>` 手动触发。
- **Gitingest digest 很大**（数 MB）：不要 `read` 整篇。用 `files --filter <子串>` 找文件起始行，再 `read --path <file>` 或 `--range` 精读（`files.json` 由 pull 自动生成；旧缓存需重新 pull 一次）。
- **缓存路径回归史**：缓存必须落在 `data/<源>/<owner>/<repo>/`（带源层）。若报 "No cache" 而缓存实际存在，报错会列出磁盘上真实位置；把旧布局目录移到对应 `data/<源>/` 下即可恢复。
- **技能根真实路径**：所有命令启动时向 stderr 打印 `技能根（真实路径）: <realpath>`。本机技能目录可能是 junction/软链，调用起点路径 ≠ 缓存实际写入路径，以打印出的真实路径为准。
- `web_extract` 工具可能被网络策略拦截（报 "URL targets a private or internal network address"，连 github.com / raw.githubusercontent.com 也拦）。兜底：`curl -sSL https://raw.githubusercontent.com/<owner>/<repo>/HEAD/README.md`；列目录用 `curl -sSL "https://api.github.com/repos/<owner>/<repo>/contents/<path>" | grep '"name"'`。**兜底要求本机可直连 GitHub**；只能经代理出网时给 curl 显式加代理：`curl.exe -sSL --proxy http://127.0.0.1:7897 <url>`（PowerShell 下 curl 不自动读 `HTTPS_PROXY`）。
- `read --section` 是模糊匹配，但**精确匹配恒优先**（修复后 `--section "Overview"` 不会误命中 "Diagram: Bend Syntax Overview" 这类子标题）。仍建议：拿不准时先 `outline` 看行号，再 `--section` 或 `--range` 按行号精准读。
- **回答「能不能做X」类能力问题**：grep digest 里 X 的关键字（如 TechDraw/Draft/SVG 导出）计数，再对照 deepwiki「Tool Categories」章节看 X 是否在结构化工具集内。要区分**结构化工具层支持** vs **仅裸代码执行兜底**：代码执行路径理论上能调任意 FreeCAD 命令，但没预校验、不可靠（README 明示易崩）。结论措辞别把两者混为一谈。
- **整篇读某份仓库文档，用 grep 定位再 read_file**：digest.txt 里每个提交文档以 `FILE: <path>` 头分隔，`grep -n 'FILE: docs/gaps.md' digest.txt` 拿到起始行，再 `read_file offset=<起始行> limit=<N>` 按块通读全文（比 files.json + `read --path` 快，且不依赖旧缓存是否重新 pull）。
- **「项目计划/缺什么」类问题，答案在仓库自己提交的文档里**（ROADMAP.md、docs/gaps.md、docs/roadmap.md 等），比 DeepWiki 生成页更权威、更细、更新——直接 grep digest 定位这些文件读全文，别只信 wiki 摘要。gap/roadmap 文档通常按 `## <域>` 分节、带优先级（alpha blocker）与 agent 工时估值，是这类问题的首选来源。
- **GitDiagram 的 explanation.md 无章节结构**：`read --repo … --source gitdiagram --section` 会 exit 1 找不到章节，整篇很短直接 `read_file`（或 `--file`）读即可。
- **digest 超大时避免整篇 read**（常见 10–40MB）：先 `grep -n 'FILE: '` 找目标文件行号，或 `files --filter` 定位，再按区间精读。
- 多仓库并行：`pull` 用后台终端（notify=true）同时跑两个仓库，拉取期间用 curl 读 README 和列目录结构，正好利用等待期。

## Windows / PowerShell 注意（本技能在 Windows 上验证可用）

- 脚本本体（`npx tsx`）在 Windows 正常；`package.json` 声明 `platforms: [windows]`。命令全部在**技能目录根**运行：`Set-Location <技能目录>\github-read-repo`。
- **命令对照**（文档示例为 bash，PowerShell 对应）：

| bash | PowerShell |
|------|-----------|
| `cd <dir> && npm install` | `Set-Location <dir>; npm install` |
| `curl -sSL <url>` | `curl.exe -sSL <url>`（或 `Invoke-WebRequest`） |
| `grep -n '^# ' file` | `Select-String -Path file -Pattern '^# '` |
| `cat file \| head -N` | `Get-Content file -TotalCount N` |
| `npx tsx scripts/read.md.ts ...` | 不变（同一条命令） |

- **管道截断 ≠ 程序失败**：`... | Select-Object -First N` 提前关闭管道，PowerShell 会报退出码 `-1`（SIGPIPE），属预期行为，不代表命令出错。想限制输出用 `--limit N`，不要依赖管道截断。
- **设代理（PowerShell 会话级）**：`$env:HTTPS_PROXY='http://127.0.0.1:7897'`；分源覆盖用 `$env:GITINGEST_PROXY=...` / `$env:GITDIAGRAM_PROXY=...` / `$env:MCP_PROXY=...`。设了之后三源拉取全部走 CONNECT 隧道，无需其他配置。
- **控制台编码**：读含中文/特殊字符的文件（如 digest.txt 的目录树）时，若出现乱码，先 `chcp 65001` 切到 UTF-8 再跑。
- **退出码**：`$LASTEXITCODE` 为 0/1/2（成功 / 输入错误 / 运行·网络错误）；`2>&1` 合并流不影响程序逻辑。
