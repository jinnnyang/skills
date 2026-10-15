"""Generate a minimal valid PPTX for testing (no pptxgenjs needed).

Builds a 2-slide deck from scratch with the slide parts, layouts,
masters, theme, content types, and relationships a PowerPoint file
needs. Used as a test fixture for add_slide.py / clean.py / validate.py.

Usage: python make_test_pptx.py OUT.pptx
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from office.pkg import rezip  # noqa: E402
from xml.dom.minidom import Document  # noqa: E402

RNS = "http://schemas.openxmlformats.org/package/2006/relationships"
PCT = "application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"
SCT = "application/vnd.openxmlformats-officedocument.presentationml.slide+xml"
LCT = "application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"
MCT = "application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"
THEME_CT = "application/vnd.openxmlformats-officedocument.theme+xml"

A = "http://schemas.openxmlformats.org/drawingml/2006/main"
P = "http://schemas.openxmlformats.org/presentationml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def xml(tag, attrs=None, children=None, text=None):
    doc = Document()
    el = doc.createElement(tag)
    for k, v in (attrs or {}).items():
        el.setAttribute(k, v)
    if text:
        el.appendChild(doc.createTextNode(text))
    for c in children or []:
        el.appendChild(c)
    return el, doc


def slide_xml(title: str, body: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="{A}" xmlns:r="{R}" xmlns:p="{P}">
  <p:cSld>
    <p:spTree>
      <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
      <p:grpSpPr/>
      <p:sp>
        <p:nvSpPr><p:cNvPr id="2" name="Title"/><p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr><p:nvPr><p:ph type="title"/></p:nvPr></p:nvSpPr>
        <p:spPr/>
        <p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:r><a:t>{title}</a:t></a:r></a:p></p:txBody>
      </p:sp>
      <p:sp>
        <p:nvSpPr><p:cNvPr id="3" name="Content"/><p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr><p:nvPr><p:ph type="body" idx="1"/></p:nvPr></p:nvSpPr>
        <p:spPr/>
        <p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:r><a:t>{body}</a:t></a:r></a:p></p:txBody>
      </p:sp>
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sld>
"""


LAYOUT_XML = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldLayout xmlns:a="{A}" xmlns:r="{R}" xmlns:p="{P}" type="obj" preserve="1">
  <p:cSld name="Title and Content">
    <p:spTree>
      <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
      <p:grpSpPr/>
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sldLayout>
"""

MASTER_XML = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldMaster xmlns:a="{A}" xmlns:r="{R}" xmlns:p="{P}">
  <p:cSld><p:spTree>
    <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
    <p:grpSpPr/>
  </p:spTree></p:cSld>
  <p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>
  <p:sldLayoutIdLst>
    <p:sldLayoutId id="2147483649" r:id="rId1"/>
  </p:sldLayoutIdLst>
</p:sldMaster>
"""

THEME_XML = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<a:theme xmlns:a="{A}" name="Test">
  <a:themeElements>
    <a:clrScheme name="Test">
      <a:dk1><a:sysClr val="windowText" lastClr="000000"/></a:dk1>
      <a:lt1><a:sysClr val="window" lastClr="FFFFFF"/></a:lt1>
      <a:dk2><a:srgbClr val="44546A"/></a:dk2>
      <a:lt2><a:srgbClr val="E7E6E6"/></a:lt2>
      <a:accent1><a:srgbClr val="4472C4"/></a:accent1>
      <a:accent2><a:srgbClr val="ED7D31"/></a:accent2>
      <a:accent3><a:srgbClr val="A5A5A5"/></a:accent3>
      <a:accent4><a:srgbClr val="FFC000"/></a:accent4>
      <a:accent5><a:srgbClr val="5B9BD5"/></a:accent5>
      <a:accent6><a:srgbClr val="70AD47"/></a:accent6>
      <a:hlink><a:srgbClr val="0563C1"/></a:hlink>
      <a:folHlink><a:srgbClr val="954F72"/></a:folHlink>
    </a:clrScheme>
    <a:fontScheme name="Test">
      <a:majorFont><a:latin typeface="Calibri Light"/><a:ea typeface=""/><a:cs typeface=""/></a:majorFont>
      <a:minorFont><a:latin typeface="Calibri"/><a:ea typeface=""/><a:cs typeface=""/></a:minorFont>
    </a:fontScheme>
    <a:fmtScheme name="Test">
      <a:fillStyleLst>
        <a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
        <a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
        <a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
      </a:fillStyleLst>
      <a:lnStyleLst>
        <a:ln w="6350"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>
        <a:ln w="12700"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>
        <a:ln w="19050"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>
      </a:lnStyleLst>
      <a:effectStyleLst>
        <a:effectStyle><a:effectLst/></a:effectStyle>
        <a:effectStyle><a:effectLst/></a:effectStyle>
        <a:effectStyle><a:effectLst/></a:effectStyle>
      </a:effectStyleLst>
      <a:bgFillStyleLst>
        <a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
        <a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
        <a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
      </a:bgFillStyleLst>
    </a:fmtScheme>
  </a:themeElements>
</a:theme>
"""

PRES_XML = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:a="{A}" xmlns:r="{R}" xmlns:p="{P}">
  <p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst>
  <p:sldIdLst>
    <p:sldId id="256" r:id="rId2"/>
    <p:sldId id="257" r:id="rId3"/>
  </p:sldIdLst>
  <p:sldSz cx="12192000" cy="6858000"/>
  <p:notesSz cx="6858000" cy="9144000"/>
</p:presentation>
"""


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


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    out = Path(sys.argv[1])
    root = Path(out.parent / (out.stem + "_build"))
    root.mkdir(parents=True, exist_ok=True)

    (root / "[Content_Types].xml").write_bytes(f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/ppt/presentation.xml" ContentType="{PCT}"/>
  <Override PartName="/ppt/slides/slide1.xml" ContentType="{SCT}"/>
  <Override PartName="/ppt/slides/slide2.xml" ContentType="{SCT}"/>
  <Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="{LCT}"/>
  <Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="{MCT}"/>
  <Override PartName="/ppt/theme/theme1.xml" ContentType="{THEME_CT}"/>
</Types>
""".encode())

    (root / "_rels").mkdir(parents=True, exist_ok=True)
    (root / "_rels" / ".rels").write_bytes(rels(
        ("rId1", f"{R}/officeDocument", "ppt/presentation.xml"),
    ))
    (root / "ppt" / "_rels").mkdir(parents=True, exist_ok=True)
    (root / "ppt" / "_rels" / "presentation.xml.rels").write_bytes(rels(
        ("rId1", f"{R}/slideMaster", "slideMasters/slideMaster1.xml"),
        ("rId2", f"{R}/slide", "slides/slide1.xml"),
        ("rId3", f"{R}/slide", "slides/slide2.xml"),
    ))
    (root / "ppt" / "presentation.xml").write_text(PRES_XML, encoding="utf-8")

    for i, (t, b) in enumerate([("First Slide", "Hello world"), ("Second Slide", "Goodbye")], 1):
        (root / "ppt" / "slides").mkdir(parents=True, exist_ok=True)
        (root / "ppt" / "slides" / f"slide{i}.xml").write_text(slide_xml(t, b), encoding="utf-8")
        (root / "ppt" / "slides" / "_rels").mkdir(parents=True, exist_ok=True)
        (root / "ppt" / "slides" / "_rels" / f"slide{i}.xml.rels").write_bytes(rels(
            ("rId1", f"{R}/slideLayout", "../slideLayouts/slideLayout1.xml"),
        ))

    (root / "ppt" / "slideLayouts").mkdir(parents=True, exist_ok=True)
    (root / "ppt" / "slideLayouts" / "slideLayout1.xml").write_text(LAYOUT_XML, encoding="utf-8")
    (root / "ppt" / "slideLayouts" / "_rels").mkdir(parents=True, exist_ok=True)
    (root / "ppt" / "slideLayouts" / "_rels" / "slideLayout1.xml.rels").write_bytes(rels(
        ("rId1", f"{R}/slideMaster", "../slideMasters/slideMaster1.xml"),
    ))

    (root / "ppt" / "slideMasters").mkdir(parents=True, exist_ok=True)
    (root / "ppt" / "slideMasters" / "slideMaster1.xml").write_text(MASTER_XML, encoding="utf-8")
    (root / "ppt" / "slideMasters" / "_rels").mkdir(parents=True, exist_ok=True)
    (root / "ppt" / "slideMasters" / "_rels" / "slideMaster1.xml.rels").write_bytes(rels(
        ("rId1", f"{R}/slideLayout", "../slideLayouts/slideLayout1.xml"),
        ("rId2", f"{R}/theme", "../theme/theme1.xml"),
    ))

    (root / "ppt" / "theme").mkdir(parents=True, exist_ok=True)
    (root / "ppt" / "theme" / "theme1.xml").write_text(THEME_XML, encoding="utf-8")

    rezip(root, out)
    import shutil

    shutil.rmtree(root)
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
