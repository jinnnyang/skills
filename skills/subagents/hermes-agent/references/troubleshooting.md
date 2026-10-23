# Troubleshooting

### Voice not working
1. Check `stt.enabled: true` in config.yaml
2. Verify provider: `python -c "import pm; pm.sync_venv(['stt-whisper'], explicit=True)"` or set API key
3. In gateway: `/restart`. In CLI: exit and relaunch.

### Tool not available
1. `hermes tools` — check if toolset is enabled for your platform
2. Some tools need env vars (check `.env`)
3. `/reset` after enabling tools

### New sessions use the wrong default model
1. Read the profile's `config.yaml` FIRST — confirm whether `model:` is present
   and what it says. A plugin/bootstrap may have never written it.
2. Grep `logs/agent.log` for `bootstrap skipped` / `coverage` — plugin config
   bootstraps are TTL-gated and stamp even on failure (see windows-quirks for
   the GBK variant). A fresh-looking stamp does not mean the write succeeded.
3. Force a re-run by setting the plugin's `*_TTL_SECONDS=0` and re-executing
   its bootstrap entrypoint, then re-verify config.yaml contents directly.
4. State-snapshots (`state-snapshots/<ts>-pre-update/config.yaml`) are useful
   as a known-good reference for what the config once contained.

### Model/provider issues
1. `hermes doctor` — check config and dependencies
2. `hermes auth` — re-authenticate OAuth providers (or `hermes auth add <provider>`)
3. Check `.env` has the right API key
4. **Copilot 403**: `gh auth login` tokens do NOT work for Copilot API. You must use the Copilot-specific OAuth device code flow via `hermes model` → GitHub Copilot.

### Changes not taking effect
- **Tools/skills:** `/reset` starts a new session with updated toolset
- **Config changes:** In gateway: `/restart`. In CLI: exit and relaunch.
- **Code changes:** Restart the CLI or gateway process

### Custom provider missing from a pi/prime-family coding CLI (silent, not an error)
When a coding CLI from the pi codebase (prime-agent etc.) shows none of your custom providers and headless exits silently after its ready banner: check whether the CLI requires `apiKey` EMBEDDED in its `models.json` provider block. The TS predecessor (pi) stores keys in a separate `auth.json` and omits the field; the Rust rewrite validates `apiKey` as REQUIRED inside `models.json` and silently filters out providers lacking it — no error surfaces. Copying config between same-lineage tools without checking the credential-location contract produces 'provider vanished' symptoms. Fix: add `"apiKey": "..."` to the provider block. Also verify the tool's agent-dir env var actually points at the directory you edited (a stale inherited value silently redirects all config reads). To read such a large repo's code efficiently, pull a full digest once (Gitingest via the github-read-repo skill) and grep locally instead of per-file API round-trips.

### "Behind N commits" update check — identifying the commits
- `hermes update --check` checks the INSTALLED checkout (typically `%LOCALAPPDATA%\hermes\hermes-agent`), not the repo in your current working directory. Run `git log` in the install dir, not in a dev clone.
- The verdict is cached in `<HERMES_HOME>/source-checks/<install_id>.json` (24h TTL). Its `commits` array lists exactly the commits the banner counted, with sha/summary/author — read that JSON FIRST to answer "what are the N commits"; do not reconstruct them from remote refs before checking.
- On shallow installs (installer checkouts are `--depth 1`) the count comes from the GitHub compare API (`_github_compare_behind` in `hermes_cli/source_check.py`), not local rev-list — so local `git rev-list` can legitimately disagree with the banner. `hermes update --check --force` bypasses the cache; `git fetch` in the dev repo does not refresh it.

### web_extract shows a stale page (result caching)
`web_search`/`web_extract` cache results for 20 minutes (PR #94618) — a
repeat fetch of the same URL within the TTL is served from cache, which
can look like "my website changes aren't showing up."

Automatic carveouts (always fetched live, never cached):
- localhost / 127.0.0.1 / `*.local` / `*.localhost` / single-label LAN
  hostnames / private + link-local IP ranges (dev servers, hot-reload
  builds, chat-GUI artifact previews)
- URLs matched by `security.website_blocklist`
- failed responses and keyless-rescue-served responses

Developing a site tested over the PUBLIC internet (Vercel/Netlify
preview, ngrok/cloudflared tunnel, staging domain)? Public DNS isn't
auto-carved-out — list the host in config.yaml:

```yaml
web:
  cache_exempt_hosts:      # always fetched live; effective immediately
    - mysite.vercel.app
    - "*.ngrok-free.app"
    - mysite.dev           # suffix match: also covers preview.mysite.dev
```

Blunt instruments: `web.cache_ttl_minutes: 1` (min) or
`web.cache_enabled: false` disables both caches entirely.

### Skills not showing
1. `hermes skills list` — verify installed
2. `hermes skills config` — check platform enablement
3. Load explicitly: `hermes -s name` (or the skill's own `/<name>` slash command)

### Gateway issues
Check logs first:
```bash
grep -i "failed to send\|error" ~/.hermes/logs/gateway.log | tail -20
```

Common gateway problems:
- **Gateway dies on SSH logout**: Enable linger: `sudo loginctl enable-linger $USER`
- **Gateway dies on WSL2 close**: WSL2 requires `systemd=true` in `/etc/wsl.conf` for systemd services to work. Without it, gateway falls back to `nohup` (dies when session closes).
- **Gateway crash loop**: Reset the failed state: `systemctl --user reset-failed hermes-gateway`

### Platform-specific issues
- **Discord bot silent**: Must enable **Message Content Intent** in Bot → Privileged Gateway Intents.
- **Slack bot only works in DMs**: Must subscribe to `message.channels` event. Without it, the bot ignores public channels.
- **Windows-specific issues** (`Alt+Enter` newline, WinError 10106, UTF-8 BOM config, line endings): see `references/windows-quirks.md`.

### Auxiliary models not working
If `auxiliary` tasks (vision, compression, session_search) fail silently, the `auto` provider can't find a backend. Either set `OPENROUTER_API_KEY` or `GOOGLE_API_KEY`, or explicitly configure each auxiliary task's provider:
```bash
hermes config set auxiliary.vision.provider <your_provider>
hermes config set auxiliary.vision.model <model_name>
```

### "Reset permissions" / auto-approving everything
See `references/security-privacy.md` — wipe the "Always allow" stores, don't touch yolo mode.

