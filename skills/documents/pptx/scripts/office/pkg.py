"""Shared helpers for OOXML package surgery.

Working set for unpacking an OOXML package (a .pptx is a ZIP of XML
parts), doing surgical edits on the unpacked tree, and repacking it:

  - safe_extract / rezip: zip in and out, with path-traversal protection
    and an atomic, OPC-ordered repack ([Content_Types].xml first, stored)
  - RelsFile: read, allocate, add, remove, and save one .rels part
  - content-types helpers: keep [Content_Types].xml in sync with parts
  - parse helpers: minidom round-trips that preserve namespace prefixes
    (defusedxml hardening; ElementTree rewrites prefixes and corrupts
    OOXML documents)

Everything operates on plain files and stdlib types.
"""

from __future__ import annotations

import os
import posixpath
import re
import stat
import tempfile
import zipfile
from pathlib import Path
from xml.dom.minidom import Document

from defusedxml.minidom import parse, parseString

# extension -> OOXML family, used to pick validators and entry parts
OOXML_FAMILY = {
    ".docx": "docx",
    ".dotx": "docx",
    ".pptx": "pptx",
    ".potx": "pptx",
    ".xlsx": "xlsx",
    ".xltx": "xlsx",
}

NS_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
SLIDE_REL_TYPE = f"{NS_R}/slide"
SLIDE_LAYOUT_REL_TYPE = f"{NS_R}/slideLayout"
SLIDE_MASTER_REL_TYPE = f"{NS_R}/slideMaster"
NOTES_SLIDE_REL_TYPE = f"{NS_R}/notesSlide"

SLIDE_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.presentationml.slide+xml"
)
SLIDE_LAYOUT_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"
)

_UNSAFE_PART = re.compile(r"^[A-Za-z]:[\\/]|^/|\.\.")


def part_text(data: bytes) -> str:
    """Decode an XML part the way OPC consumers do."""
    return data.decode("utf-8", "surrogateescape")


def parse_part(path: Path):
    """Hardened DOM parse of one XML part on disk."""
    return parse(str(path))


def parse_xml(text: str):
    """Hardened DOM parse of an XML string."""
    return parseString(text)


def safe_extract(zf: zipfile.ZipFile, dest: Path) -> None:
    """Extract a zip into dest, refusing absolute paths, traversal, links."""
    dest = dest.resolve()
    for m in zf.infolist():
        if stat.S_ISLNK(m.external_attr >> 16):
            raise ValueError(f"symlink archive entry not allowed: {m.filename!r}")
        if _UNSAFE_PART.search(m.filename):
            raise ValueError(f"unsafe archive entry: {m.filename!r}")
        target = (dest / m.filename).resolve()
        if not target.is_relative_to(dest):
            raise ValueError(f"unsafe archive entry: {m.filename!r}")
        zf.extract(m, dest)


def rezip(src_dir: Path, out_path: Path) -> None:
    """Pack src_dir into out_path atomically.

    [Content_Types].xml is written first and uncompressed — some OPC
    consumers expect it early in the archive. The output goes to a temp
    file next to the destination and is moved into place only on success,
    so a failure never truncates the target.
    """
    files = sorted(p for p in src_dir.rglob("*") if p.is_file())
    ct = src_dir / "[Content_Types].xml"
    fd, tmp_name = tempfile.mkstemp(
        prefix=out_path.name + ".", suffix=".tmp", dir=out_path.parent
    )
    tmp_out = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as fh:
            with zipfile.ZipFile(fh, "w", zipfile.ZIP_DEFLATED) as zf:
                if ct.exists():
                    zf.write(ct, ct.relative_to(src_dir), compress_type=zipfile.ZIP_STORED)
                for f in files:
                    if f == ct:
                        continue
                    zf.write(f, f.relative_to(src_dir))
        if out_path.exists():
            mode = out_path.stat().st_mode & 0o777
        else:
            umask = os.umask(0)
            os.umask(umask)
            mode = 0o666 & ~umask
        os.chmod(tmp_out, mode)
        os.replace(tmp_out, out_path)
    finally:
        if tmp_out.exists():
            tmp_out.unlink()


def rels_path_for(part: str) -> str:
    """Package path of the .rels part for `part` (e.g. ppt/slides/slide1.xml)."""
    parent = posixpath.dirname(part)
    stem = posixpath.basename(part)
    return posixpath.join(parent, "_rels", f"{stem}.rels")


def target_part_path(owner_part: str, target: str) -> str:
    """Resolve an OPC Target (relative to the owning part) to a package path."""
    if target.startswith("/"):
        return target.lstrip("/")
    base = posixpath.dirname(owner_part)
    return posixpath.normpath(posixpath.join(base, target)).replace("\\", "/")


def rel_target(from_part: str, to_part: str) -> str:
    """Relative OPC Target string pointing from one part to another."""
    from_dir = posixpath.dirname(from_part)
    return posixpath.relpath(to_part, from_dir or ".").replace("\\", "/")


def slide_number(name: str) -> int:
    """'slide12.xml' -> 12 (0 when the name does not match)."""
    m = re.fullmatch(r"slide(\d+)\.xml", name)
    return int(m.group(1)) if m else 0


class RelsFile:
    """One .rels part: ordered relationships with stable rId allocation."""

    def __init__(self, path: Path):
        self.path = path
        self.entries: list[dict] = []
        if path.is_file():
            doc = parse_part(path)
            for el in doc.getElementsByTagName("Relationship"):
                self.entries.append(dict(el.attributes.items()))

    def _dom(self):
        doc = Document()
        root = doc.createElement("Relationships")
        root.setAttribute("xmlns", REL_NS)
        for e in self.entries:
            el = doc.createElement("Relationship")
            for k, v in e.items():
                el.setAttribute(k, v)
            root.appendChild(el)
        doc.appendChild(root)
        return doc

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_bytes(self._dom().toxml(encoding="UTF-8"))

    def next_id(self) -> str:
        used = {
            int(e["Id"][3:])
            for e in self.entries
            if e["Id"].startswith("rId") and e["Id"][3:].isdigit()
        }
        return f"rId{max(used, default=0) + 1}"

    def add(self, rel_type: str, target: str, *, external: bool = False) -> str:
        rid = self.next_id()
        entry = {"Id": rid, "Type": rel_type, "Target": target}
        if external:
            entry["TargetMode"] = "External"
        self.entries.append(entry)
        return rid

    def remove(self, rid: str) -> None:
        self.entries = [e for e in self.entries if e["Id"] != rid]

    def target_of(self, rid: str) -> str | None:
        for e in self.entries:
            if e["Id"] == rid:
                return e["Target"]
        return None

    def find_by_type(self, rel_type: str) -> list[dict]:
        return [e for e in self.entries if e["Type"] == rel_type]


def content_types_add_override(unpacked: Path, part: str, content_type: str) -> None:
    """Ensure an Override entry exists for a part in [Content_Types].xml."""
    ct_path = unpacked / "[Content_Types].xml"
    doc = parse_part(ct_path)
    want = "/" + part
    for el in doc.getElementsByTagName("Override"):
        if el.getAttribute("PartName") == want:
            return
    o = doc.createElement("Override")
    o.setAttribute("PartName", want)
    o.setAttribute("ContentType", content_type)
    doc.documentElement.appendChild(o)
    ct_path.write_bytes(doc.toxml(encoding="UTF-8"))


def content_types_remove_part(unpacked: Path, part: str) -> None:
    """Drop the Override entry for a part, if any."""
    ct_path = unpacked / "[Content_Types].xml"
    doc = parse_part(ct_path)
    want = "/" + part
    changed = False
    for el in list(doc.getElementsByTagName("Override")):
        if el.getAttribute("PartName") == want:
            el.parentNode.removeChild(el)
            changed = True
    if changed:
        ct_path.write_bytes(doc.toxml(encoding="UTF-8"))


def next_free_name(directory: Path, pattern: str) -> str:
    """First name matching glob-style `pattern` (with %d) not taken on disk."""
    taken = {p.name for p in directory.iterdir()} if directory.is_dir() else set()
    n = 1
    while pattern % n in taken:
        n += 1
    return pattern % n
