# term-cli

将交互式终端能力交给 AI agent：在 tmux 托管的分离会话里跑 dev server、调试器（pdb/gdb）、REPL、SSH、交互式安装器等不阻塞；配合 `term-assist` 由人类接管输密码/MFA。

## Provenance

- **Origin**: https://github.com/EliasOenal/term-cli
- **License**: BSD-3-Clause-Clear（见本目录 `LICENSE`，上游要求保留版权与许可声明）
- **Vendor 范围**: 只拷贝技能所需文件 —— `SKILL.md`、`term-cli`、`term-assist`、`LICENSE`、`install.sh`。上游的 `tests/`、`.github/`、`assets/`、CI 未带入。
- **同步上游**: 以 `README.md` 为准（本文件；上游原 README 见 repo）——变更时对照上游 commit 重新拉取上述文件。
- **本地改动**: 无（文件与上游 main 一致，仅加本 README）。

## Windows 兼容性

`term-cli` 硬依赖 **tmux**，Windows 原生不可用；需在 WSL 或 MSYS2/Git-Bash（含 tmux 包）下运行。
