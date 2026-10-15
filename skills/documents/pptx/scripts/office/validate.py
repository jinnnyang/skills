"""Validate OOXML XML parts against the ECMA-376 / ISO-IEC 29500 schemas.

Usage:
    python validate.py unpacked/ | file.pptx [--original SRC] [--verbose]

For each XML part under the package, picks the schema by part name and
XSD-validates it. Relationships and content-type checks run separately
from the schema pass:

  - every relationship Target resolves to a part in the package
  - every part with a relationship has a .rels, and vice versa
  - [Content_Types].xml covers every part (Override or Default)

--original (used when the deck was built from a template) baselines the
schema pass: failures the template's own parts already produce are
suppressed, so you see only what your edits introduced. Structural
checks always run in full — template-inherited problems are still worth
knowing about.
"""

from __future__ import annotations

import argparse
import posixpath
import sys
import tempfile
import zipfile
from functools import lru_cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from office.pkg import (  # noqa: E402
    OOXML_FAMILY,
    RelsFile,
    parse_part,
    part_text,
    rels_path_for,
    target_part_path,
)

import lxml.etree  # noqa: E402

SCHEMAS = Path(__file__).resolve().parent / "schemas"

SCHEMA_MAPPINGS = {
    "ppt/presentation.xml": "ISO-IEC29500-4_2016/pml.xsd",
    "[Content_Types].xml": "ecma/fouth-edition/opc-contentTypes.xsd",
    "_rels/.rels": "ecma/fouth-edition/opc-relationships.xsd",
    "docProps/app.xml": "ISO-IEC29500-4_2016/shared-documentPropertiesExtended.xsd",
    "docProps/core.xml": "ecma/fouth-edition/opc-coreProperties.xsd",
    "docProps/custom.xml": "ISO-IEC29500-4_2016/shared-documentPropertiesCustom.xsd",
}

DIR_SCHEMA = {
    "ppt/slides": "ISO-IEC29500-4_2016/pml.xsd",
    "ppt/slideLayouts": "ISO-IEC29500-4_2016/pml.xsd",
    "ppt/slideMasters": "ISO-IEC29500-4_2016/pml.xsd",
    "ppt/notesSlides": "ISO-IEC29500-4_2016/pml.xsd",
    "ppt/notesMasters": "ISO-IEC29500-4_2016/pml.xsd",
    "ppt/theme": "ISO-IEC29500-4_2016/dml-main.xsd",
    "ppt/charts": "ISO-IEC29500-4_2016/dml-chart.xsd",
    "docProps/thumbnail.jpeg": None,  # not XML
}


@lru_cache(maxsize=None)
def load_schema(rel: str):
    xsd_path = SCHEMAS / rel
    doc = lxml.etree.parse(str(xsd_path))
    return lxml.etree.XMLSchema(doc)


def schema_for(part: str) -> str | None:
    if part in SCHEMA_MAPPINGS:
        return SCHEMA_MAPPINGS[part]
    if not part.endswith(".xml"):
        return None
    parent = posixpath.dirname(part)
    if parent in DIR_SCHEMA:
        return DIR_SCHEMA[parent]
    name = posixpath.basename(part)
    if name.endswith(".rels"):
        return "ecma/fouth-edition/opc-relationships.xsd"
    return None


def xml_parts(unpacked: Path) -> list[str]:
    return sorted(
        p.relative_to(unpacked).as_posix()
        for p in unpacked.rglob("*")
        if p.is_file() and p.suffix.lower() in {".xml", ".rels"}
    )


def run_schema_pass(unpacked: Path, baseline: set[str] | None, verbose: bool) -> list[str]:
    errors = []
    for part in xml_parts(unpacked):
        rel = schema_for(part)
        if rel is None:
            continue
        schema = load_schema(rel)
        doc = lxml.etree.parse(str(unpacked / part))
        if schema.validate(doc):
            continue
        for err in schema.error_log:
            msg = f"{part}: line {err.line}: {err.message}"
            if baseline is not None:
                bpart = part
                baseline_hit = any(
                    m.endswith(err.message.split()[-1]) or err.message in m
                    for m in baseline
                )
                if baseline_hit:
                    continue
            errors.append(msg)
    return errors


def baseline_errors(unpacked: Path) -> set[str]:
    """Schema error messages the ORIGINAL package already produces."""
    msgs = set()
    for part in xml_parts(unpacked):
        rel = schema_for(part)
        if rel is None:
            continue
        schema = load_schema(rel)
        doc = lxml.etree.parse(str(unpacked / part))
        if schema.validate(doc):
            continue
        for err in schema.error_log:
            msgs.add(err.message)
    return msgs


def rels_owner(rels_path: str) -> str:
    """'_rels/x.rels' form -> the part it describes."""
    parent = posixpath.dirname(posixpath.dirname(rels_path))
    stem = posixpath.basename(rels_path)[: -len(".rels")]
    return posixpath.join(parent, stem) if parent else stem


def run_structural_pass(unpacked: Path) -> list[str]:
    errors = []
    parts = {
        p.relative_to(unpacked).as_posix() for p in unpacked.rglob("*") if p.is_file()
    }

    # every Target resolves; rIds are unique per .rels
    for rp in sorted(p for p in parts if p.endswith(".rels")):
        owner = rels_owner(rp)
        ids = []
        rels = RelsFile(unpacked / rp)
        for e in rels.entries:
            ids.append(e["Id"])
            if e.get("TargetMode") == "External":
                continue
            target = target_part_path(owner, e["Target"])
            if target not in parts:
                errors.append(f"{rp}: unresolved target {e['Target']!r} (part {owner!r})")
        dupes = {i for i in ids if ids.count(i) > 1}
        if dupes:
            errors.append(f"{rp}: duplicate rIds {sorted(dupes)}")

    # every part with relationships outside the root has a .rels
    for p in sorted(parts):
        if p.endswith(".rels") or p in {"[Content_Types].xml"}:
            continue
        if posixpath.dirname(p) == "docProps" and not p.endswith(".xml"):
            continue
        rp = rels_path_for(p)
        if rp not in parts and _expects_rels(p):
            errors.append(f"{p}: no .rels part ({rp} missing)")

    # content types cover every part
    ct_path = unpacked / "[Content_Types].xml"
    if ct_path.is_file():
        ct = parse_part(ct_path)
        defaults = {
            el.getAttribute("Extension").lower()
            for el in ct.getElementsByTagName("Default")
        }
        overrides = {
            el.getAttribute("PartName") for el in ct.getElementsByTagName("Override")
        }
        for p in sorted(parts):
            if p == "[Content_Types].xml":
                continue
            if ("/" + p) in overrides:
                continue
            ext = p.rsplit(".", 1)[-1].lower()
            if ext in defaults:
                continue
            errors.append(f"[Content_Types].xml: no coverage for {p!r}")
    else:
        errors.append("[Content_Types].xml missing")
    return errors


def _expects_rels(part: str) -> bool:
    """Parts that conventionally carry a .rels even if only for a layout."""
    return part.startswith(("ppt/slides/", "ppt/slideLayouts/", "ppt/slideMasters/",
                            "ppt/notesSlides/", "ppt/notesMasters/",
                            "ppt/presentation.xml"))


def main() -> int:
    ap = argparse.ArgumentParser(description="XSD-validate OOXML parts and check package structure.")
    ap.add_argument("package", help="unpacked directory or packed .pptx/.potx")
    ap.add_argument("--original", help="template-derived source; baselines schema errors")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    path = Path(args.package)
    if not path.exists():
        print(f"Error: {path} does not exist", file=sys.stderr)
        return 2

    tmp_ctx = None
    if path.is_file():
        fam = OOXML_FAMILY.get(path.suffix.lower())
        if fam is None:
            print(f"Error: unsupported file type {path.suffix!r}", file=sys.stderr)
            return 2
        tmp_ctx = tempfile.TemporaryDirectory()
        unpacked = Path(tmp_ctx.name) / "pkg"
        from office.pkg import safe_extract

        try:
            with zipfile.ZipFile(path) as zf:
                safe_extract(zf, unpacked)
        except (zipfile.BadZipFile, ValueError, OSError) as exc:
            print(f"Error: cannot unpack {path}: {exc}", file=sys.stderr)
            return 2
    else:
        unpacked = path

    baseline_msgs = None
    if args.original:
        orig = Path(args.original)
        if not orig.is_file():
            print(f"Error: --original {orig} is not a file", file=sys.stderr)
            return 2
        with tempfile.TemporaryDirectory() as td:
            ou = Path(td) / "pkg"
            from office.pkg import safe_extract

            with zipfile.ZipFile(orig) as zf:
                safe_extract(zf, ou)
            baseline_msgs = baseline_errors(ou)

    structural = run_structural_pass(unpacked)
    schema_errors = run_schema_pass(unpacked, baseline_msgs, args.verbose)

    for e in structural:
        print(f"STRUCTURE {e}")
    for e in schema_errors:
        print(f"SCHEMA    {e}")

    n = len(structural) + len(schema_errors)
    if n == 0:
        print("All checks passed.")
        code = 0
    else:
        print(f"\n{n} problem(s) found.")
        code = 1
    if tmp_ctx:
        tmp_ctx.cleanup()
    return code


if __name__ == "__main__":
    sys.exit(main())
