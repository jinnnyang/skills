"""Remove unreferenced parts from an unpacked PPTX directory.

Run AFTER <p:sldIdLst> in presentation.xml is final. Deletes:

  - orphaned slides: ppt/slides/slideN.xml whose rId is no longer in
    <p:sldIdLst>, plus their .rels
  - orphaned slide layouts and masters (nothing references them anymore)
  - unreferenced media, charts, embeddings, notesSlides — any part under
    ppt/ that no remaining .rels points at
  - .rels files whose owning part was deleted

Parts referenced from outside ppt/ (docProps, theme files referenced by
slide masters, the presentation itself) are never touched. The root
.rels and [Content_Types].xml are updated to match.

Usage:
    python clean.py unpacked/            # report + delete
    python clean.py unpacked/ --dry-run  # report only
"""

from __future__ import annotations

import argparse
import posixpath
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from office.pkg import (  # noqa: E402
    NS_R,
    RelsFile,
    content_types_remove_part,
    parse_part,
    part_text,
    rels_path_for,
    rel_target,
    slide_number,
    target_part_path,
)

# parts that stay regardless of references from other parts
ROOT_PARTS = {"[Content_Types].xml", "_rels/.rels"}
KEEP_DIRS = {"docProps"}


def fail(msg: str):
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(2)


def package_parts(unpacked: Path) -> set[str]:
    """Every file in the package as a '/'-separated path."""
    return {
        p.relative_to(unpacked).as_posix()
        for p in unpacked.rglob("*")
        if p.is_file()
    }


def referenced_parts(unpacked: Path, parts: set[str]) -> set[str]:
    """Parts referenced by any .rels still on disk (transitively seeded)."""
    seen: set[str] = set()
    queue = ["_rels/.rels"]
    while queue:
        rp = queue.pop()
        rels_path = unpacked / rp
        if not rels_path.is_file():
            continue
        owner = rels_owner(rp)
        rels = RelsFile(rels_path)
        for e in rels.entries:
            if e.get("TargetMode") == "External":
                continue
            target = target_part_path(owner, e["Target"])
            if target in seen or target not in parts:
                continue
            seen.add(target)
            own_rels = rels_path_for(target)
            if own_rels in parts:
                seen.add(own_rels)
                queue.append(own_rels)
    return seen


def rels_owner(rels_path: str) -> str:
    """'_rels/x.rels' form -> the part it describes."""
    parent = posixpath.dirname(posixpath.dirname(rels_path))
    stem = posixpath.basename(rels_path)[: -len(".rels")]
    return posixpath.join(parent, stem) if parent else stem


def slide_order_ids(unpacked: Path) -> set[str]:
    """Package paths of slides still listed in <p:sldIdLst>."""
    pres = unpacked / "ppt" / "presentation.xml"
    if not pres.is_file():
        fail("ppt/presentation.xml missing")
    rels = RelsFile(unpacked / "ppt" / "_rels" / "presentation.xml.rels")
    listed: set[str] = set()
    for e in parse_part(pres).getElementsByTagName("p:sldId"):
        rid = e.getAttribute("r:id") or e.getAttributeNS(NS_R, "id")
        target = rels.target_of(rid)
        if target:
            listed.add(target_part_path("ppt/presentation.xml", target))
    return listed


def clean(unpacked: Path, dry_run: bool) -> int:
    parts = package_parts(unpacked)

    # 1. orphaned slides: on disk but not in sldIdLst; drop their
    #    presentation.xml.rels entries too
    listed = slide_order_ids(unpacked)
    pres_rels_path = unpacked / "ppt" / "_rels" / "presentation.xml.rels"
    pres_rels = RelsFile(pres_rels_path)
    all_slides = {
        p.relative_to(unpacked).as_posix() for p in (unpacked / "ppt" / "slides").glob("slide*.xml")
    }
    orphans = all_slides - listed
    doomed: set[str] = set()
    for s in sorted(orphans, key=slide_number):
        doomed.add(s)
        rp = rels_path_for(s)
        if rp in parts:
            doomed.add(rp)
    if orphans and not dry_run:
        rid_to_part = {
            e["Id"]: target_part_path("ppt/presentation.xml", e["Target"])
            for e in pres_rels.entries
        }
        for rid, part in list(rid_to_part.items()):
            if part in orphans:
                pres_rels.remove(rid)
        pres_rels.save()

    # 2. reachability sweep from the root rels, minus nothing — but slides
    #    already doomed must not keep their exclusive dependencies alive
    parts_after_slides = parts - doomed
    keep = referenced_parts(unpacked, parts_after_slides)

    for p in sorted(parts_after_slides):
        if p in ROOT_PARTS or p in keep:
            continue
        if p.split("/")[0] in KEEP_DIRS:
            continue
        if p.endswith(".rels") and rels_owner(p) not in parts_after_slides - doomed:
            doomed.add(p)
            continue
        if p.startswith("ppt/"):
            doomed.add(p)

    doomed = {p for p in doomed if p in parts and p not in ROOT_PARTS}
    if not doomed:
        print("Nothing to clean.")
        return 0

    width = max(len(p) for p in doomed)
    for p in sorted(doomed):
        print(f"  delete {p}")
    if dry_run:
        print(f"{len(doomed)} part(s) would be removed (dry run).")
        return 0

    for p in doomed:
        (unpacked / p).unlink()
        if not p.endswith(".rels"):
            content_types_remove_part(unpacked, p)

    # empty directories left behind
    for d in sorted((x for x in unpacked.rglob("*") if x.is_dir()), reverse=True):
        if not any(d.iterdir()):
            d.rmdir()

    print(f"Removed {len(doomed)} part(s).")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Remove unreferenced parts from an unpacked PPTX.")
    ap.add_argument("unpacked", help="unpacked package directory")
    ap.add_argument("--dry-run", action="store_true", help="report what would be deleted")
    args = ap.parse_args()

    unpacked = Path(args.unpacked)
    if not (unpacked / "ppt").is_dir():
        fail(f"{unpacked} does not look like an unpacked PPTX (no ppt/ directory)")
    return clean(unpacked, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
