"""Render every slide of a PPTX as a labeled thumbnail grid.

Prefers LibreOffice (soffice -> PDF -> pdftoppm) when available; on
Windows with Microsoft Office installed but no LibreOffice, falls back
to PowerPoint COM automation for the PDF step (still needs pdftoppm for
rasterizing — on a machine without it, only the PDF is produced and its
path is printed).

Cells are labeled with the slide's XML part name (slide1.xml, ...) —
the name you need when editing the unpacked package. Hidden slides are
marked. This is a template-analysis tool: it shows which layout each
slide uses so you can pick one to duplicate. For full-resolution visual
QA convert at 150 dpi instead (see SKILL.md).

Usage:
    python thumbnail.py deck.pptx [prefix] [--cols N]

Always pass a prefix named after the deck: the default 'thumbnails'
silently overwrites the grids of any other deck thumbnailed in the same
directory.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from office.pkg import (  # noqa: E402
    NS_P,
    NS_R,
    part_text,
    target_part_path,
)

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

CELL_W = 320
CELL_H = 200
PAD = 16
LABEL_H = 26
JPEG_QUALITY = 90
MAX_COLS = 6
DEFAULT_COLS = 3
ROWS_PER_GRID = 4  # grids split vertically beyond this many rows
HIDDEN_COLOR = (235, 235, 235)


def fail(msg: str):
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(2)


def which(cmd: str) -> str:
    from shutil import which as _which

    p = _which(cmd)
    if not p:
        fail(f"{cmd} not found on PATH — install LibreOffice (soffice) / Poppler (pdftoppm)")
    return p


def slide_parts_in_order(pptx: Path) -> list[str]:
    """Package paths of slides in <p:sldIdLst> order."""
    with zipfile.ZipFile(pptx) as zf:
        pres = parse_xml_part(zf, "ppt/presentation.xml")
        entries = [
            dict(el.attributes.items())
            for el in parse_xml_part(zf, "ppt/_rels/presentation.xml.rels")
            .getElementsByTagName("Relationship")
        ]
    by_rid = {e["Id"]: e["Target"] for e in entries if "Id" in e}
    out = []
    for e in pres.getElementsByTagName("p:sldId"):
        rid = e.getAttribute("r:id") or e.getAttributeNS(NS_R, "id")
        target = by_rid.get(rid)
        if target:
            out.append(target_part_path("ppt/presentation.xml", target))
    return out


def parse_xml_part(zf: zipfile.ZipFile, name: str):
    from defusedxml.minidom import parseString

    return parseString(part_text(zf.read(name)))


def hidden_slides(pptx: Path) -> set[int]:
    """1-based positions of slides marked show='0' in the sldIdLst."""
    with zipfile.ZipFile(pptx) as zf:
        pres = parse_xml_part(zf, "ppt/presentation.xml")
    return {
        idx
        for idx, e in enumerate(pres.getElementsByTagName("p:sldId"), start=1)
        if e.getAttribute("show") == "0"
    }


def soffice_on_path() -> str | None:
    from shutil import which

    return which("soffice")


def render_pdf(pptx: Path, out_dir: Path) -> Path:
    pdf = out_dir / (pptx.stem + ".pdf")
    soffice = soffice_on_path()
    if soffice:
        profile = out_dir / "lo_profile"
        cmd = [
            soffice,
            f"-env:UserInstallation={profile.as_uri()}",
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(out_dir),
            str(pptx),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if pdf.is_file():
            return pdf
        print(f"LibreOffice conversion failed, falling back to PowerPoint COM:\n{proc.stderr}", file=sys.stderr)
    return render_pdf_com(pptx, pdf)


def render_pdf_com(pptx: Path, pdf: Path) -> Path:
    """Windows/Office fallback: export PDF via PowerPoint COM automation."""
    try:
        import win32com.client  # type: ignore[import-not-found]
    except ImportError:
        fail(
            "no renderer available: install LibreOffice (soffice) or, on Windows "
            "with Office, pywin32 (python -m pip install pywin32)"
        )
    abs_pptx = pptx.resolve()
    abs_pdf = pdf.resolve()
    app = win32com.client.Dispatch("PowerPoint.Application")
    try:
        pres = app.Presentations.Open(str(abs_pptx), ReadOnly=True, WithWindow=False)
        pres.SaveAs(str(abs_pdf), 32)  # ppSaveAsPDF
        pres.Close()
    finally:
        app.Quit()
    if not pdf.is_file():
        fail("PowerPoint COM export did not produce a PDF")
    return pdf


def pdf_pages(pdf: Path, out_dir: Path) -> list[Path]:
    """Rasterize PDF pages to JPEGs. Uses pdftoppm (Poppler) when on PATH,
    otherwise PyMuPDF."""
    from shutil import which

    pdftoppm = which("pdftoppm")
    if pdftoppm:
        prefix = out_dir / "page"
        subprocess.run(
            [pdftoppm, "-jpeg", "-r", "60", str(pdf), str(prefix)],
            check=True,
            capture_output=True,
        )
        return sorted(out_dir.glob("page-*.jpg"))
    try:
        import pymupdf
    except ImportError:
        fail("no PDF rasterizer: install poppler (pdftoppm) or PyMuPDF (python -m pip install pymupdf)")
    doc = pymupdf.open(pdf)
    pages = []
    for i, page in enumerate(doc, start=1):
        pix = page.get_pixmap(dpi=60)
        out = out_dir / f"page-{i:02d}.jpg"
        pix.save(str(out), jpg_quality=JPEG_QUALITY)
        pages.append(out)
    doc.close()
    return pages


def load_font(size: int):
    for name in ("arial.ttf", "segoeui.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def make_grid(images: list[Path], labels: list[str], hidden: set[int],
              out_prefix: Path, cols: int) -> list[Path]:
    rows_per_grid = ROWS_PER_GRID
    per_grid = cols * rows_per_grid
    grids = [images[i : i + per_grid] for i in range(0, len(images), per_grid)]
    label_batches = [labels[i : i + per_grid] for i in range(0, len(labels), per_grid)]

    font = load_font(14)
    outputs = []
    for gi, (batch, labels_b) in enumerate(zip(grids, label_batches)):
        rows = (len(batch) + cols - 1) // cols
        W = cols * (CELL_W + PAD) + PAD
        H = rows * (CELL_H + LABEL_H + PAD) + PAD
        board = Image.new("RGB", (W, H), "white")
        draw = ImageDraw.Draw(board)
        for i, img_path in enumerate(batch):
            r, c = divmod(i, cols)
            x = PAD + c * (CELL_W + PAD)
            y = PAD + r * (CELL_H + LABEL_H + PAD)
            img = Image.open(img_path)
            img.thumbnail((CELL_W, CELL_H))
            board.paste(img, (x + (CELL_W - img.width) // 2, y + (CELL_H - img.height) // 2))
            label = labels_b[i]
            # label i corresponds to slide i+1 (1-based) in this grid batch
            slide_idx = gi * per_grid + i + 1
            if slide_idx in hidden:
                draw.text((x, y + CELL_H + 4), f"{label} (hidden)", fill=(200, 60, 60), font=font)
            else:
                draw.text((x, y + CELL_H + 4), label, fill=(60, 60, 60), font=font)
        suffix = "" if len(grids) == 1 else f"-{gi + 1}"
        out = out_prefix.with_name(f"{out_prefix.name}{suffix}.jpg")
        board.save(out, quality=JPEG_QUALITY)
        outputs.append(out)
    return outputs


def main() -> int:
    ap = argparse.ArgumentParser(description="Labeled thumbnail grid of a PPTX's slides.")
    ap.add_argument("pptx", help="input .pptx file")
    ap.add_argument("prefix", nargs="?", default="thumbnails",
                    help="output file prefix (default: thumbnails)")
    ap.add_argument("--cols", type=int, default=DEFAULT_COLS,
                    help=f"grid columns, 1-{MAX_COLS} (default: {DEFAULT_COLS})")
    args = ap.parse_args()

    pptx = Path(args.pptx)
    if not pptx.is_file():
        fail(f"{pptx} does not exist")
    if pptx.suffix.lower() != ".pptx":
        fail("thumbnail.py only accepts .pptx (copy a .potx to a .pptx name first)")
    cols = max(1, min(MAX_COLS, args.cols))

    order = slide_parts_in_order(pptx)
    if not order:
        fail("no slides found in presentation.xml")
    hidden = hidden_slides(pptx)

    with tempfile.TemporaryDirectory(prefix="pptx_thumbs_") as td:
        out_dir = Path(td)
        pdf = render_pdf(pptx, out_dir)
        pages = pdf_pages(pdf, out_dir)
        if len(pages) != len(order):
            print(
                f"Note: {len(pages)} rendered pages vs {len(order)} slides; "
                "labeling by page order.",
                file=sys.stderr,
            )
        labels = [
            Path(p).name if i < len(order) else f"page{i + 1}"
            for i, p in enumerate(pages)
        ]
        outputs = make_grid(pages, labels, hidden, Path(args.prefix).resolve(), cols)

    for o in outputs:
        print(o)
    return 0


if __name__ == "__main__":
    sys.exit(main())
