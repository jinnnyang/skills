# Fork ↔ Upstream Sync: Analyzing and Merging

The user's fork (`jinnnyang/hermes-agent`) holds `main` (fork + few own commits) and an `upstream` branch tracking NousResearch. The fork's history is **not** linear with upstream: past merge points are squash/shallow snapshots, so naive git counts lie. Verify before recommending a merge.

## Procedure

1. Fetch first, but expect `git fetch` on this Windows host to hang for very long stretches on large updates. Run it `terminal(background=true, notify=true)` and do other work; never burn repeated 180s foreground timeouts on it.
2. Get the real change scale from GitHub, not rev-list: the repo page's "N ahead / M behind" banner, or the upstream Releases page (web_search for `NousResearch hermes-agent releases`) for feature summaries when fetch stalls.
3. Sanity-check any rev-list count against the timestamps and commit counts on both sides:
   - `git rev-list --count <a>` vs `git rev-list --count <b>` — a huge asymmetry (e.g. 263 vs 50k) means one side is a squashed/shallow snapshot.
   - `git log <range> | grep -i "initial commit"` — a root commit inside a supposedly-incremental range means the two histories are disjoint and the count is bogus.
4. Measure real content diff with `git diff --shortstat <fork-main> <upstream-tip>`; this is the honest "how much changed" number. Cross-check it against the GitHub banner.
5. Merge normally (`git merge origin/upstream` on main); the GitHub "sync fork" button and fast-forward paths are unavailable when histories are disjoint, so expect one large merge commit.
6. Merge downstream in dependency order: `main → moirai`, then `main → feat/aptapi` and `main → feat/omniroute`. Feature-branch merges are usually zero-conflict once main is done — do them with `git merge main`, never rebase (their old history is disconnected from upstream, rebase would rewrite them). See `fork-branch-topology.md` for the current branch map, merge order, and the recurring fork-only conflict patterns. everything).
7. Push with `git push origin <branches>` in one call; a 50k-commit push takes minutes — run it backgrounded like fetch.

## Branch topology (current)

- `upstream` — mirror of NousResearch main, sync only, never develop here.
- `main` — upstream + the fork's few generic commits (Windows install fixes). Baseline.
- `moirai` — release branch: main + Windows install UX (curl.exe download, irm+iex one-liner, chcp 65001, UTF-8 child-output decode) + aptapi integration (installer defaults to aptapi.dev/v1, aptapi-bootstrap plugin, OmniRoute plugin auto-deploy). All feature branches merge INTO it; its commits do not flow back.
- `feat/aptapi` — aptapi.dev-server-specific features (superset incl. bootstrap plugin). Per user policy: never merged into moirai/main, never cherry-picked between feature branches.
- `feat/omniroute` — subset of feat/aptapi (auto-deploy + update-pipeline changes).
- Typical merge conflicts: `scripts/install.ps1` (fork's `-Utf8Output` switch on Invoke-Logged/Invoke-Native vs upstream's newer error-capture logic — keep BOTH: fork's param + forwarding, upstream's capture body), `hermes_cli/update_cmd.py` (fork's `_track_current_branch` vs upstream's refactored `select_apply_target` — keep upstream's call, pass a `Namespace(branch=tracked)` so a tracked branch skips channel resolution), `tests/pm/test_progress.py` (keep the fork's Windows ASCII-arrow fix; upstream's version lacks it). check — disjoint histories (squash-merged snapshots) make it count the entire upstream history.
- Release pages are the fastest feature summary when fetch is slow: search the releases URL, extract with web_extract; api.github.com is blocked from the web tools but github.com HTML pages work.
