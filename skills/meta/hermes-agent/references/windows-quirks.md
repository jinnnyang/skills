# Windows-Specific Quirks

Hermes runs natively on Windows (PowerShell, cmd, Windows Terminal, git-bash
mintty, VS Code integrated terminal). Most of it just works, but a handful
of differences between Win32 and POSIX have bitten us — document new ones
here as you hit them so the next person (or the next session) doesn't
rediscover them from scratch.

### Input / Keybindings

**Alt+Enter doesn't insert a newline** — Windows Terminal (and mintty) grab it
for fullscreen before prompt_toolkit sees it. Use **Ctrl+Enter** instead (the
CLI binds it to newline on Windows; raw Ctrl+J does the same, harmlessly).
To inspect how your terminal reports a keystroke, run
`python scripts/keystroke_diagnostic.py` from the repo root.

### Config / Files

**Plugin bootstrap silently skipped on Chinese Windows** — Python's default
stderr encoding on zh-CN Windows is GBK; any `print(..., file=sys.stderr)` of
non-GBK text (emoji like ⚠, box-drawing) raises `UnicodeEncodeError`. If that
print sits inside a try/except around a best-effort routine (plugin config
bootstrap, self-update), the whole routine is skipped and a TTL stamp may
still be written — so it never retries. Check profile
`logs/agent.log` for `bootstrap skipped: 'gbk' codec can't encode`. Fix the
plugin's `_warn`-style helper with a `try/except UnicodeEncodeError` fallback
(`msg.encode('ascii','replace')`), and delete the stamp (or set the plugin's
`*_TTL_SECONDS=0`) to force a re-run. For one-off runs, `PYTHONIOENCODING=utf-8`
also bypasses it.

**HTTP 400 "No models provided" on first run** — `config.yaml` was saved with
a UTF-8 BOM (Notepad does this). Re-save as UTF-8 without BOM;
`hermes config edit` writes correctly.

**curl to R2/Cloudflare-storage URLs fails with `schannel: server closed abruptly`
or `ERROR on write`** — Windows schannel TLS chokes on these hosts (both `curl -o
FILE` and `curl | sh`). Fall back to Python:
`urllib.request.Request(url, headers={'User-Agent':'curl/8'})` + `shutil.copyfileobj`
downloads reliably. When an install script does its own internal curl downloads,
pre-download the artifacts and feed them via the script's local-file/archive flag
instead of letting it fetch.

### External CLIs through WSL
### `execute_code` / Sandbox

**WinError 10106** from the sandbox child process — it can't create an
`AF_INET` socket. Root cause is usually Hermes's env scrubber dropping
`SYSTEMROOT`/`WINDIR`/`COMSPEC` (Python's `socket` needs `SYSTEMROOT` to find
`mswsock.dll`), not a broken Winsock LSP. The `_WINDOWS_ESSENTIAL_ENV_VARS`
allowlist in `tools/code_execution_env.py` covers it; if you still hit it,
echo `os.environ` inside an `execute_code` block to confirm `SYSTEMROOT` is set.

### Testing on Windows

Prepare the checkout through PM first. With its Python 3.14, build an independent
test environment at a fresh path:

```powershell
python -m pm.build_env --source . --out .venv --group dev --group test
```

The output must not exist. Before regeneration, stop its processes and explicitly
remove only that disposable environment. Do not install into the application
payload or modify a selected dependency generation.

Run the canonical runner through Git Bash:

```bash
scripts/run_tests.sh tests/foo/test_bar.py -v --tb=short
```

The runner discovers `.venv/Scripts/python.exe`, clears credentials and
`PYTHONPATH`, and isolates each test file. For an external test environment,
set `HERMES_PYTHON` to its Python executable. PM shell activation alone does
not supply pytest after the runner clears `PYTHONPATH`.

### Path / Filesystem

**Line endings.** Git may warn `LF will be replaced by CRLF`. Cosmetic — the
repo's `.gitattributes` normalizes. Don't let editors auto-convert committed
POSIX-newline files to CRLF.

**Forward slashes work almost everywhere.** `C:/Users/...` is accepted by
every Hermes tool and most Windows APIs. Prefer forward slashes in code
and logs — avoids shell-escaping backslashes in bash.

