# karpathy-llm-wiki

Karpathy 式个人 LLM 知识库:agent 维护 `raw/`(不可变原始材料)与 `wiki/`(编译后的知识文章)两个目录。三种操作——**Ingest**(抓取→分诊→编译/级联更新)、**Query**(带引用的检索问答)、**Lint**(索引/链接/证据一致性检查,安全项自动修)。核心不变量:wiki 文章里每个承重事实都能在所链 raw 文件中逐字找到,由 `scripts/check_evidence.py` 验证。

| Field | Value |
|---|---|
| Origin | https://github.com/Astro-Han/karpathy-llm-wiki |
| Author / License | Astro-Han / MIT（LICENSE 随目录保留） |
| Vendor 基线 | upstream `main` @ `eafcc77`（2026-07-23, "fix: align log inventory and examples"） |
| Vendored scope | `SKILL.md`、`references/`（4 个模板）、`scripts/check_evidence.py`、`LICENSE` 原样拷贝；上游 README 存为 `UPSTREAM-README.md`。未带入:`examples/`、`tests/`、`assets/`、`.gitignore` |
| Local modifications | 无（与上游 `eafcc77` 逐字节一致） |

## 同步上游

变更时对照上游 commit 重新拉取上述文件,再更新本表的 Vendor 基线。

## 依赖

`check_evidence.py` 仅用标准库(re/sys/dataclasses/pathlib),`python3` 直接可跑。
