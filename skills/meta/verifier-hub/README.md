# verifier-hub

确定性产物校验 CLI：file/xlsx/docx/pdf/pptx/text/archive/rubric 八个家族、58 个子命令，交付前自检「文件结构和数值对不对」这类有确定答案的问题。每次调用输出一个 JSON 对象（`ok` / `result.passed` / `evidence.quote`，`ok` 报工具执行、结论在 `result.passed`），证据可直接引用。**只读**：绝不创建或修改被检查的文件。

| Field | Value |
|---|---|
| Origin | Vendored from Doubao desktop agent workspace skills (`...\.doubao\agent_mode\workspace\.skills\verifier-hub` v2.1) |
| Author / License | ByteDance Doubao team / frontmatter 标注「Proprietary — internal use only」；经确认仅个人内部使用，不用于商业用途，不对外分发 |
| Vendored scope | SKILL.md、README.md（上游原版全文保留于本文件末尾）、bin/verifier + verifier.cmd、lib/*.py、references/、requirements.txt 原样拷贝 |
| Local modifications | none（上游 SKILL.md 中的 skills/ 相对路径在本仓库同样成立） |

## 使用

```bash
python skills/meta/verifier-hub/bin/verifier xlsx get-value report.xlsx --sheet Summary --cell B2
python skills/meta/verifier-hub/bin/verifier docx outline final.docx
python skills/meta/verifier-hub/bin/verifier text must-contain --file README.md --terms "安装"
```

- Windows：无扩展名 `bin/verifier` 不能被 cmd/PowerShell 直接执行，用 `bin/verifier.cmd` 或 `python bin/verifier`；上游 README 标「Windows is not supported」，实际 Python 代码可移植（纯 pathlib、显式 utf-8），本机实测 `python bin/verifier` 可用。
- 依赖：Python 3.10+、openpyxl / python-docx / python-pptx / PyYAML；pdf 家族另需 pymupdf / pdfplumber / pypdf 之一（2026-10-23 本机已装 openpyxl/python-docx/python-pptx/pyyaml/pypdf）。

## 本机实测状态（2026-10-23）

- file / text / pdf / docx / pptx / rubric family：`--help` 与实际调用正常。
- `verifier xlsx --help` 报 `failed to load family 'xlsx': ValueError: badly formed help string`：xlsx 子命令注册在本机 Python 3.14 下触发异常；xlsx 家族不可用，需要时先读 `lib/xlsx.py` 排查。

## 与 Hermes 技能的关系

补「执行代理交活后的机器把关」一环：与 mattpocock `code-review`（模型评审代码）互补——verifier 管文档/表格类产物的确定性校验。

---

# 以下为上游 README 原文（未改动）

# verifier-hub

Deterministic artifact verifier CLI. Used for pre-delivery self-checks by any
agent, and for evidence collection in questionnaire judging mode.

This hub is **read-only / inspection-only**. It never creates or modifies the
files it inspects. It opens xlsx / docx / pdf / pptx / text / zip files and
reports structural and content facts as JSON, so an agent can collect evidence
without parsing binary formats itself or guessing content from a flattened
text trajectory.

## Layout

```
verifier-hub/
├── SKILL.md                        # agent-facing entry point (kept short on purpose)
├── references/
│   ├── subcommands.md              # all 58 subcommands, args + examples
│   └── questionnaire.md            # judge-mode workflow (harness-provided scripts)
├── bin/verifier                    # single CLI dispatcher (argparse, 2-level subparsers)
├── lib/
│   ├── _common.py                  # JSON protocol, error codes, paths, file URIs,
│   │                               # cross-platform binary lookup, install hints
│   ├── _pdf_backend.py             # pymupdf / pdfplumber / pypdf behind one interface
│   ├── file_io.py                  # 4  cmds: artifact-list / validate / extract-text / count
│   ├── xlsx.py                     # 12 cmds: get-value / assert-value / eval-formula / ...
│   ├── docx.py                     # 12 cmds: outline / section-text / page-count / ...
│   ├── pdf.py                      # 4  cmds: pages / text-dump / cjk-check / count-images
│   ├── pptx.py                     # 4  cmds: list-slides / slide-text / find-slide / count-images
│   ├── text.py                     # 9  cmds: must-contain / count-matches / date-extract / ...
│   ├── archive.py                  # 2  cmds: zip-list / zip-check-entries
│   └── rubric.py                   # 11 high-level DSL primitives
├── requirements.txt
└── README.md
```

## Output protocol

Every invocation writes exactly one JSON object to stdout, including bad
arguments and unknown family names:

```json
{"ok": true,  "tool": "xlsx.get-value", "result": {...}, "evidence": {...}}
{"ok": false, "tool": "xlsx.get-value", "error": {"code": "FILE_NOT_FOUND", "msg": "..."}}
```

`ok` reports whether the tool ran. The check verdict lives in `result.passed`,
so a file that fails its check is `ok: true` + `result.passed: false`.
`--help` is the only invocation that prints prose instead of JSON.

`evidence` is meant to be quoted verbatim; it always references the file and
locator that produced the finding, so the quote carries its own provenance.

## PDF backends

`lib/_pdf_backend.py` tries `pymupdf`, then `pdfplumber`, then `pypdf`, and
records the winner in each result's `backend` field. Only one of the three
needs to be installed. pymupdf is preferred because it is already present in
the rollout VM image and covers geometry, text, fonts and images on its own.

## Platform support

Linux and macOS. Windows is not supported: `bin/verifier` is an extension-less
shebang script, so `cmd.exe` and PowerShell cannot execute it directly. The
Python code itself is portable (no POSIX-only syscalls, all file I/O is
explicitly utf-8, all paths go through `pathlib`/`os.path`, `file://` URIs are
built with `as_uri()`), so `python bin/verifier ...` does work if you need it.

## Local development

```bash
cd verifier-hub
pip install -r requirements.txt
./bin/verifier --help
./bin/verifier xlsx --help
./bin/verifier xlsx get-value sample.xlsx --sheet Sheet1 --cell A1
```

## Packaging

The zip published to TOS contains `bin/`, `lib/`, `references/`, `SKILL.md`,
`requirements.txt` and `README.md` at the top level — no wrapper directory,
because the installer creates the per-skill directory from the zip name.
`__pycache__` and test fixtures are excluded: the VM runs Python 3.10 and
would ignore bytecode compiled elsewhere anyway.
