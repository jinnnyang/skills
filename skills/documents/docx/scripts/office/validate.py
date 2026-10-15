"""Validate WordprocessingML (docx) parts against the ECMA-376 schemas.

Usage:
    python office/validate.py unpacked/ | file.docx [--original SRC] [--verbose]

Picks the XSD by part path and validates each XML part. Relationship
resolution and [Content_Types] coverage run as a separate structural
pass. The schema pass can be baselined with --original, so errors a
source document already carries are not re-reported as your own.

Exit codes: 0 all clean, 1 problems found, 2 usage/unpack error.
"""

from __future__ import annotations

import argparse
import posixpath
import re
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
    content_types_remove_part,
    parse_part,
    rels_path_for,
    safe_extract,
    target_part_path,
)

import lxml.etree  # noqa: E402

SCHEMAS = Path(__file__).resolve().parent / "schemas"

# Exact part -> schema, keyed on the package path. docProps parts are
# deliberately not XSD-validated: their schema (opc-coreProperties.xsd)
# imports the Dublin Core dc/dcterms schemas, which are not shipped with
# this schema set, so lxml cannot build the validator. They are still
# covered by the structural pass.
SCHEMA_MAPPINGS = {
    "word/document.xml": "ISO-IEC29500-4_2016/wml.xsd",
    "word/styles.xml": "ISO-IEC29500-4_2016/wml.xsd",
    "word/settings.xml": "ISO-IEC29500-4_2016/wml.xsd",
    "word/webSettings.xml": "ISO-IEC29500-4_2016/wml.xsd",
    "word/fontTable.xml": "ISO-IEC29500-4_2016/wml.xsd",
    "word/numbering.xml": "ISO-IEC29500-4_2016/wml.xsd",
    "word/footnotes.xml": "ISO-IEC29500-4_2016/wml.xsd",
    "word/endnotes.xml": "ISO-IEC29500-4_2016/wml.xsd",
    "word/glossary/document.xml": "ISO-IEC29500-4_2016/wml.xsd",
    "word/comments.xml": "ISO-IEC29500-4_2016/wml.xsd",
    # commentsExtended.xml is a Microsoft w15 extension that the ECMA-376
    # wml.xsd does not cover, so it is not XSD-validated here (it is still
    # checked by the structural pass).

    "word/people.xml": "ISO-IEC29500-4_2016/wml.xsd",
    "_rels/.rels": "ecma/fouth-edition/opc-relationships.xsd",
}

# Fallback by directory.
DIR_SCHEMA = {
    "word/theme": "ISO-IEC29500-4_2016/dml-main.xsd",
}


class _XmlNsResolver(lxml.etree.Resolver):
    """Serve w3c/xml.xsd when a schema imports the XML namespace without a
    schemaLocation (wml.xsd does exactly this)."""

    def resolve(self, url, id, context):
        if url == "http://www.w3.org/XML/1998/namespace":
            return self.resolve_filename(
                str(SCHEMAS / "w3c" / "xml.xsd"), context
            )
        return None


@lru_cache(maxsize=None)
def load_schema(rel: str):
    xsd_path = SCHEMAS / rel
    parser = lxml.etree.XMLParser()
    parser.resolvers.add(_XmlNsResolver())
    doc = lxml.etree.parse(str(xsd_path), parser)
    return lxml.etree.XMLSchema(doc)


_HEADER_FOOTER = re.compile(r"word/(?:header|footer)\d+\.xml$")


def schema_for(part: str) -> str | None:
    """Return the schema path for an XML part, or None if unvalidatable."""
    if part in SCHEMA_MAPPINGS:
        return SCHEMA_MAPPINGS[part]
    if _HEADER_FOOTER.match(part):
        return "ISO-IEC29500-4_2016/wml.xsd"
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
            if verbose:
                print(f"  skip (no schema): {part}")
            continue
        schema = load_schema(rel)
        doc = lxml.etree.parse(str(unpacked / part))
        if schema.validate(doc):
            continue
        for err in schema.error_log:
            msg = f"{part}: line {err.line}: {err.message}"
            if baseline is not None and _baselined(err.message, baseline):
                continue
            errors.append(msg)
    return errors


def _baselined(message: str, baseline: set[str]) -> bool:
    """True if a schema error was already present in the baseline package."""
    last_token = message.split()[-1] if message.split() else ""
    return any(
        m.endswith(last_token) or message in m
        for m in baseline
    )


def baseline_errors(unpacked: Path) -> set[str]:
    """Schema error messages the original package already produces."""
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
    """'_rels/x.rels' form -> the package path of the part it describes."""
    parent = posixpath.dirname(posixpath.dirname(rels_path))
    stem = posixpath.basename(rels_path)[: -len(".rels")]
    return posixpath.join(parent, stem) if parent else stem


def run_structural_pass(unpacked: Path) -> list[str]:
    errors = []
    parts = {
        p.relative_to(unpacked).as_posix() for p in unpacked.rglob("*") if p.is_file()
    }

    # Every relationship target resolves; rIds are unique per .rels.
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

    # Parts that conventionally carry their own .rels must have one.
    for p in sorted(parts):
        if p.endswith(".rels") or p == "[Content_Types].xml":
            continue
        if posixpath.dirname(p) == "docProps" and not p.endswith(".xml"):
            continue
        rp = rels_path_for(p)
        if rp not in parts and _expects_rels(p):
            errors.append(f"{p}: no .rels part ({rp} missing)")

    # Content types cover every part.
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
    """Only the main document part carries its own .rels in a docx; every
    other word/ part (headers, footnotes, comments, ...) is related from
    word/document.xml.rels."""
    return part == "word/document.xml"


def main() -> int:
    ap = argparse.ArgumentParser(
        description="XSD-validate docx OOXML parts and check package structure."
    )
    ap.add_argument("package", help="unpacked directory or packed .docx/.dotx")
    ap.add_argument("--original", help="source package; baselines pre-existing schema errors")
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
        unpacked.mkdir(parents=True)
        try:
            with zipfile.ZipFile(path) as zf:
                safe_extract(zf, unpacked)
        except (zipfile.BadZipFile, ValueError, OSError) as exc:
            print(f"Error: cannot unpack {path}: {exc}", file=sys.stderr)
            return 2
    else:
        unpacked = path

    baseline = None
    if args.original:
        orig = Path(args.original)
        if not orig.is_file():
            print(f"Error: --original {orig} is not a file", file=sys.stderr)
            return 2
        with tempfile.TemporaryDirectory() as td:
            ou = Path(td) / "pkg"
            ou.mkdir(parents=True)
            with zipfile.ZipFile(orig) as zf:
                safe_extract(zf, ou)
            baseline = baseline_errors(ou)

    structural = run_structural_pass(unpacked)
    schema_errors = run_schema_pass(unpacked, baseline, args.verbose)

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
