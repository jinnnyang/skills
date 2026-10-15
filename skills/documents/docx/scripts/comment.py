"""Add a comment to a docx.

A Word comment lives in several places at once: the comment text itself in
word/comments.xml, a marker around the annotated text in word/document.xml,
a relationship from the document, and a content-type override. This script
wires all of them up and prints the marker snippet it inserted.

Usage:
    python scripts/comment.py doc.docx "Comment text" --find "anchor text" [--author A] [--output OUT]
    python scripts/comment.py doc.docx "Comment text" --paragraph 2 [--author A] [--output OUT]
    python scripts/comment.py unpacked_dir/ "Comment text" --find "anchor text"   # directory, in place

The target paragraph is located by --find (first paragraph whose text
contains the substring) or --paragraph (1-based paragraph index, default 1).

Comment IDs are auto-assigned: the highest existing id in comments.xml
plus one, or 0 when the part does not exist yet. With --extended the
Word-2013 commentsExtended part is written too (harmless enhancement; it
is not required to display a comment).
"""

from __future__ import annotations

import argparse
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.dom.minidom import parseString

sys.path.insert(0, str(Path(__file__).resolve().parent))

from office.pkg import (  # noqa: E402
    OOXML_FAMILY,
    RelsFile,
    content_types_add_override,
    rezip,
    safe_extract,
)

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W15 = "http://schemas.microsoft.com/office/word/2012/wordml"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

COMMENTS_CT = "application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml"
COMMENTS_EXT_CT = "application/vnd.openxmlformats-officedocument.wordprocessingml.commentsExtended+xml"
COMMENTS_REL = f"{R}/comments"
COMMENTS_EXT_REL = "http://schemas.microsoft.com/office/2011/relationships/commentsExtended"


def text_of(par) -> str:
    parts = []
    for n in par.getElementsByTagNameNS(W, "t"):
        for c in n.childNodes:
            if c.nodeType == c.TEXT_NODE:
                parts.append(c.data)
    return "".join(parts)


def find_target(doc, find: str | None, paragraph: int) -> list:
    paras = doc.getElementsByTagNameNS(W, "p")
    if find is not None:
        for p in paras:
            if find in text_of(p):
                return [p]
        raise ValueError(f"no paragraph contains {find!r}")
    idx = (paragraph or 1) - 1
    if not 0 <= idx < len(paras):
        raise ValueError(f"paragraph index {paragraph} out of range (have {len(paras)})")
    return [paras[idx]]


def existing_comment_id(unpacked: Path) -> int:
    comments = unpacked / "word" / "comments.xml"
    if not comments.is_file():
        return 0
    doc = parseString(comments.read_bytes())
    ids = [
        int(c.getAttribute("w:id"))
        for c in doc.getElementsByTagNameNS(W, "comment")
        if c.getAttribute("w:id").isdigit()
    ]
    return (max(ids) + 1) if ids else 0


def comments_part(cid: int, author: str, date: str, text: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:comments xmlns:w="{W}">
  <w:comment w:id="{cid}" w:author="{author}" w:date="{date}">
    <w:p>
      <w:pPr><w:pStyle w:val="CommentText"/></w:pPr>
      <w:r><w:rPr><w:rStyle w:val="CommentReference"/></w:rPr><w:commentReference w:id="{cid}"/></w:r>
      <w:r><w:t>{text}</w:t></w:r>
    </w:p>
  </w:comment>
</w:comments>
"""


def comments_extended_part(cid: int) -> str:
    para_id = f"{cid + 0x10000000:08X}"
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w15:commentsEx xmlns:w15="{W15}">
  <w15:commentEx w15:paraId="{para_id}" w15:paraIdParent="00000000" w15:done="0"/>
</w15:commentsEx>
"""


def marker_snippet(cid: int) -> str:
    return (
        f'<w:commentRangeStart w:id="{cid}"/>'
        f'<w:commentRangeEnd w:id="{cid}"/>'
        f'<w:r><w:commentReference w:id="{cid}"/></w:r>'
    )


def apply(unpacked: Path, text: str, author: str, find, paragraph: int, extended: bool) -> int:
    doc_path = unpacked / "word" / "document.xml"
    if not doc_path.is_file():
        raise ValueError(f"no word/document.xml in {unpacked}")
    doc = parseString(doc_path.read_bytes())
    targets = find_target(doc, find, paragraph)
    cid = existing_comment_id(unpacked)
    date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # markers around each target paragraph
    for par in targets:
        start = doc.createElementNS(W, "w:commentRangeStart")
        start.setAttribute("w:id", str(cid))
        end = doc.createElementNS(W, "w:commentRangeEnd")
        end.setAttribute("w:id", str(cid))
        ref = doc.createElementNS(W, "w:r")
        ref_r = doc.createElementNS(W, "w:commentReference")
        ref_r.setAttribute("w:id", str(cid))
        ref.appendChild(ref_r)
        par.insertBefore(start, par.firstChild)
        par.appendChild(end)
        par.appendChild(ref)

    # comments.xml
    comments_path = unpacked / "word" / "comments.xml"
    if comments_path.is_file():
        cdoc = parseString(comments_path.read_bytes())
        cdoc.documentElement.appendChild(_comment_el(cdoc, cid, author, date, text))
        comments_path.write_bytes(cdoc.toxml(encoding="UTF-8"))
    else:
        comments_path.write_bytes(comments_part(cid, author, date, text).encode("utf-8"))
    content_types_add_override(unpacked, "word/comments.xml", COMMENTS_CT)

    rels_path = unpacked / "word" / "_rels" / "document.xml.rels"
    rels = RelsFile(rels_path)
    if not rels.find_by_type(COMMENTS_REL):
        rels.add(COMMENTS_REL, "comments.xml")
    rels.save()

    if extended:
        ext_path = unpacked / "word" / "commentsExtended.xml"
        if ext_path.is_file():
            edoc = parseString(ext_path.read_bytes())
            ex = edoc.createElementNS(W15, "w15:commentEx")
            ex.setAttribute("w15:paraId", f"{cid + 0x10000000:08X}")
            ex.setAttribute("w15:paraIdParent", "00000000")
            ex.setAttribute("w15:done", "0")
            edoc.documentElement.appendChild(ex)
            ext_path.write_bytes(edoc.toxml(encoding="UTF-8"))
        else:
            ext_path.write_bytes(comments_extended_part(cid).encode("utf-8"))
        content_types_add_override(unpacked, "word/commentsExtended.xml", COMMENTS_EXT_CT)
        if not rels.find_by_type(COMMENTS_EXT_REL):
            rels.add(COMMENTS_EXT_REL, "commentsExtended.xml")
        rels.save()

    doc_path.write_bytes(doc.toxml(encoding="UTF-8"))
    return cid


def _comment_el(doc, cid, author, date, text):
    c = doc.createElementNS(W, "w:comment")
    c.setAttribute("w:id", str(cid))
    c.setAttribute("w:author", author)
    c.setAttribute("w:date", date)
    p = doc.createElementNS(W, "w:p")
    ppr = doc.createElementNS(W, "w:pPr")
    pstyle = doc.createElementNS(W, "w:pStyle")
    pstyle.setAttribute("w:val", "CommentText")
    ppr.appendChild(pstyle)
    p.appendChild(ppr)
    r1 = doc.createElementNS(W, "w:r")
    r1pr = doc.createElementNS(W, "w:rPr")
    rstyle = doc.createElementNS(W, "w:rStyle")
    rstyle.setAttribute("w:val", "CommentReference")
    r1pr.appendChild(rstyle)
    ref = doc.createElementNS(W, "w:commentReference")
    ref.setAttribute("w:id", str(cid))
    r1.appendChild(r1pr)
    r1.appendChild(ref)
    p.appendChild(r1)
    r2 = doc.createElementNS(W, "w:r")
    t = doc.createElementNS(W, "w:t")
    t.appendChild(doc.createTextNode(text))
    r2.appendChild(t)
    p.appendChild(r2)
    c.appendChild(p)
    return c


def main() -> int:
    ap = argparse.ArgumentParser(description="Add a comment to a docx.")
    ap.add_argument("target", help="unpacked directory or packed .docx/.dotx")
    ap.add_argument("text", help="comment text")
    ap.add_argument("--find", help="anchor substring locating the paragraph to annotate")
    ap.add_argument("--paragraph", type=int, help="1-based paragraph index to annotate")
    ap.add_argument("--author", default="docx skill")
    ap.add_argument("--extended", action="store_true", help="also write word/commentsExtended.xml")
    ap.add_argument("--output", help="packed output path (requires a packed input)")
    args = ap.parse_args()

    if not args.find and not args.paragraph:
        args.paragraph = 1

    target = Path(args.target)
    if target.is_dir():
        cid = apply(target, args.text, args.author, args.find, args.paragraph, args.extended)
        print(f"Added comment {cid} to {target}")
        print("Marker snippet inserted in word/document.xml:")
        print("  " + marker_snippet(cid))
        return 0

    if target.suffix.lower() not in OOXML_FAMILY:
        print(f"Error: unsupported file type {target.suffix!r}", file=sys.stderr)
        return 2
    out = Path(args.output) if args.output else target
    tmp_ctx = tempfile.TemporaryDirectory()
    unpacked = Path(tmp_ctx.name) / "pkg"
    unpacked.mkdir(parents=True)
    with zipfile.ZipFile(target) as zf:
        safe_extract(zf, unpacked)
    cid = apply(unpacked, args.text, args.author, args.find, args.paragraph, args.extended)
    rezip(unpacked, out)
    tmp_ctx.cleanup()
    print(f"Added comment {cid} to {out}")
    print("Marker snippet inserted in word/document.xml:")
    print("  " + marker_snippet(cid))
    return 0


if __name__ == "__main__":
    sys.exit(main())
