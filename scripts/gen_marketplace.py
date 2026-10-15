#!/usr/bin/env python3
"""Scan skills/ for directories containing SKILL.md and regenerate
.claude-plugin/marketplace.json skills[] entries.

Usage: python scripts/gen_marketplace.py [--root PATH] [--check]
  --root   repo root (default: script's parent dir)
  --check  verify registry matches scan, exit 1 on drift (CI-friendly)
"""

import argparse
import json
import sys
from pathlib import Path

MARKETPLACE = Path(".claude-plugin") / "marketplace.json"


def scan_skills(root: Path) -> list[str]:
    """Recursively find dirs containing SKILL.md, return repo-relative
    posix paths sorted by depth then name. Symlinks are not followed
    (prevents infinite recursion); a skill dir reached via symlink is
    still reported, via its symlink path."""
    found: list[tuple[int, Path]] = []

    def walk(dir_path: Path, depth: int, seen_real: set) -> None:
        real = dir_path.resolve()
        if real in seen_real:
            return  # cycle guard (symlink loop)
        seen_real = seen_real | {real}
        try:
            entries = sorted(dir_path.iterdir())
        except OSError:
            return
        for entry in entries:
            if entry.name == "SKILL.md" and entry.is_file():
                found.append((depth, entry.parent))
                continue  # no need to descend into a skill dir
            if entry.is_dir():
                # follow symlinked dirs but not into already-visited reals
                walk(entry, depth + 1, seen_real)

    walk(root / "skills", 0, set())
    found.sort(key=lambda t: (t[0], str(t[1])))
    return [str(p.relative_to(root)).replace("\\", "/") for _, p in found]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    root: Path = args.root

    skill_paths = scan_skills(root)
    if not skill_paths:
        print("ERROR: no SKILL.md found under skills/", file=sys.stderr)
        return 2

    mf_path = root / MARKETPLACE
    if not mf_path.exists():
        print(f"ERROR: {mf_path} not found", file=sys.stderr)
        return 2

    mf = json.loads(mf_path.read_text(encoding="utf-8"))
    plugins = mf.get("plugins", [])
    if len(plugins) != 1:
        print(f"ERROR: expected exactly 1 plugin, got {len(plugins)}", file=sys.stderr)
        return 2

    current = plugins[0].get("skills", [])
    if args.check:
        if current == skill_paths:
            print(f"OK: registry up to date ({len(skill_paths)} skills)")
            return 0
        print("DRIFT: registry out of date", file=sys.stderr)
        print(f"  registry: {current}", file=sys.stderr)
        print(f"  scan:     {skill_paths}", file=sys.stderr)
        return 1

    plugins[0]["skills"] = skill_paths
    mf_path.write_text(json.dumps(mf, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Updated {mf_path}: {len(skill_paths)} skills")
    for p in skill_paths:
        print(f"  {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
