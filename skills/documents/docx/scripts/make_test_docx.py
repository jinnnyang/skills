"""Generate a minimal valid docx for testing (no external writers needed).

Builds a small WordprocessingML document from scratch: word/document.xml,
styles, core/application properties, content types and relationships.
Used as a fixture for merge_runs.py / accept_changes.py / comment.py /
validate.py. Output opens in python-docx and passes office/validate.py.

The fixture deliberately includes one paragraph whose text is split across
several runs with identical formatting, so merge_runs.py has something to
merge, and one paragraph marked as a redline delete so accept_changes.py
has a change to accept.
"""

from __future__ import annotations

import sys
from pathlib import Path
from xml.dom.minidom import Document

sys.path.insert(0, str(Path(__file__).resolve().parent))

from office.pkg import rezip  # noqa: E402

RNS = "http://schemas.openxmlformats.org/package/2006/relationships"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

DOC_CT = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
)
STYLES_CT = "application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"
CORE_CT = "application/vnd.openxmlformats-package.core-properties+xml"
APP_CT = "application/vnd.openxmlformats-officedocument.extended-properties+xml"


def rels(*pairs):
    doc = Document()
    root = doc.createElement("Relationships")
    root.setAttribute("xmlns", RNS)
    for rid, rtype, target in pairs:
        el = doc.createElement("Relationship")
        el.setAttribute("Id", rid)
        el.setAttribute("Type", rtype)
        el.setAttribute("Target", target)
        root.appendChild(el)
    doc.appendChild(root)
    return doc.toxml(encoding="UTF-8")


DOC_XML = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="{W}" xmlns:r="{R}">
  <w:body>
    <w:p>
      <w:pPr><w:pStyle w:val="Title"/></w:pPr>
      <w:r><w:t>Docx Skill Test</w:t></w:r>
    </w:p>
    <w:p>
      <w:r><w:t>Hello from a minimal valid test document.</w:t></w:r>
    </w:p>
    <w:p>
      <w:r><w:rPr><w:b/></w:rPr><w:t>This sentence is</w:t></w:r>
      <w:r><w:rPr><w:b/></w:rPr><w:t xml:space="preserve"> split across </w:t></w:r>
      <w:r><w:rPr><w:b/></w:rPr><w:t>three runs.</w:t></w:r>
    </w:p>
    <w:p>
      <w:r><w:t>Please review this paragraph before publishing.</w:t></w:r>
    </w:p>
    <w:p>
      <w:r><w:t xml:space="preserve">Track this sentence for deletion: </w:t></w:r>
      <w:del w:id="1" w:author="docx skill" w:date="2026-01-01T00:00:00Z">
        <w:r><w:delText>it must vanish.</w:delText></w:r>
      </w:del>
    </w:p>
    <w:sectPr>
      <w:pgSz w:w="12240" w:h="15840"/>
      <w:cols w:space="708"/>
      <w:docGrid w:linePitch="360"/>
    </w:sectPr>
  </w:body>
</w:document>
"""

STYLES_XML = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="{W}">
  <w:docDefaults>
    <w:rPrDefault><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:sz w:val="22"/></w:rPr></w:rPrDefault>
    <w:pPrDefault><w:pPr><w:spacing w:after="160" w:line="259" w:lineRule="auto"/></w:pPr></w:pPrDefault>
  </w:docDefaults>
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Title">
    <w:name w:val="Title"/>
    <w:pPr><w:spacing w:after="300"/></w:pPr>
    <w:rPr><w:b/><w:sz w:val="36"/></w:rPr>
  </w:style>
</w:styles>
"""

CORE_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
 xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/"
 xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>Docx Skill Test</dc:title>
  <dc:creator>docx skill</dc:creator>
  <cp:lastModifiedBy>docx skill</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">2026-01-01T00:00:00Z</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">2026-01-01T00:00:00Z</dcterms:modified>
</cp:coreProperties>
"""

APP_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
 xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>docx skill test</Application>
  <Pages>1</Pages>
  <Words>10</Words>
</Properties>
"""


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0 if len(sys.argv) > 1 else 2
    out = Path(sys.argv[1])
    root = Path(out.parent / (out.stem + "_build"))
    root.mkdir(parents=True, exist_ok=True)

    (root / "[Content_Types].xml").write_bytes(f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="{DOC_CT}"/>
  <Override PartName="/word/styles.xml" ContentType="{STYLES_CT}"/>
  <Override PartName="/docProps/core.xml" ContentType="{CORE_CT}"/>
  <Override PartName="/docProps/app.xml" ContentType="{APP_CT}"/>
</Types>
""".encode())

    (root / "_rels").mkdir(parents=True, exist_ok=True)
    (root / "_rels" / ".rels").write_bytes(rels(
        ("rId1", f"{R}/officeDocument", "word/document.xml"),
        ("rId2", "http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties", "docProps/core.xml"),
        ("rId3", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties", "docProps/app.xml"),
    ))

    (root / "word" / "_rels").mkdir(parents=True, exist_ok=True)
    (root / "word" / "_rels" / "document.xml.rels").write_bytes(rels(
        ("rId1", f"{R}/styles", "styles.xml"),
    ))

    (root / "word" / "document.xml").write_text(DOC_XML, encoding="utf-8")
    (root / "word" / "styles.xml").write_text(STYLES_XML, encoding="utf-8")
    (root / "docProps").mkdir(parents=True, exist_ok=True)
    (root / "docProps" / "core.xml").write_text(CORE_XML, encoding="utf-8")
    (root / "docProps" / "app.xml").write_text(APP_XML, encoding="utf-8")

    rezip(root, out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
