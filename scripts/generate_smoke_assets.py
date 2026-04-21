"""
Generate synthetic DOCX/PDF under datasets/raw/ for Tier A rows.
Run from repo root:  pip install -r scripts/requirements.txt && python scripts/generate_smoke_assets.py
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from docx import Document
from pypdf import PdfReader, PdfWriter

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW = REPO_ROOT / "datasets" / "raw"
MANIFEST = REPO_ROOT / "datasets" / "manifest.json"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def pdf_page_count(p: Path) -> int:
    return len(PdfReader(str(p)).pages)


def write_minimal_docx(path: Path, paragraphs: list[str]) -> None:
    doc = Document()
    for text in paragraphs:
        doc.add_paragraph(text)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(path))


def write_pdf_pages(path: Path, num_pages: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=612, height=792)
    with path.open("wb") as f:
        writer.write(f)


def update_manifest_entry(
    mid: str,
    rel_path: str,
    sha: str,
    nbytes: int,
    pages: int | None,
    *,
    license_note: str = "synthetic",
    mark_synthetic: bool = True,
) -> None:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for row in data:
        if row["id"] == mid:
            row["sha256"] = sha
            row["bytes"] = nbytes
            if pages is not None:
                row["pages"] = pages
            row["source"] = f"file:datasets/raw/{rel_path}"
            row["license"] = license_note
            if mark_synthetic:
                row["synthetic"] = True
            break
    else:
        raise SystemExit(f"id {mid} not in manifest")
    MANIFEST.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)

    def u(mid: str, filename: str, pages: int | None = None, **kw) -> None:
        p = RAW / filename
        update_manifest_entry(mid, filename, sha256_file(p), p.stat().st_size, pages, **kw)

    # DOCX
    write_minimal_docx(RAW / "docx_smoke_001.docx", ["Smoke test document for Group 259.", "Line two."])
    u("docx_smoke_001", "docx_smoke_001.docx")

    write_minimal_docx(RAW / "docx_baseline_small.docx", ["Baseline small.", "Short content."])
    u("docx_baseline_small", "docx_baseline_small.docx")

    write_minimal_docx(
        RAW / "docx_baseline_medium.docx",
        [f"Medium baseline paragraph {i}." for i in range(40)],
    )
    u("docx_baseline_medium", "docx_baseline_medium.docx")

    write_minimal_docx(
        RAW / "docx_baseline_large.docx",
        [f"Large baseline paragraph {i} with more text." for i in range(80)],
    )
    u("docx_baseline_large", "docx_baseline_large.docx")

    write_minimal_docx(RAW / "docx_large_001.docx", [f"Large doc line {i}." for i in range(200)])
    u("docx_large_001", "docx_large_001.docx")

    write_minimal_docx(RAW / "docx_large_002.docx", [f"Second large doc line {i}." for i in range(200)])
    u("docx_large_002", "docx_large_002.docx")

    # PDFs
    write_pdf_pages(RAW / "pdf_smoke_001.pdf", 1)
    u("pdf_smoke_001", "pdf_smoke_001.pdf", pdf_page_count(RAW / "pdf_smoke_001.pdf"))

    write_pdf_pages(RAW / "pdf_baseline_small.pdf", 2)
    u("pdf_baseline_small", "pdf_baseline_small.pdf", pdf_page_count(RAW / "pdf_baseline_small.pdf"))

    write_pdf_pages(RAW / "pdf_baseline_medium.pdf", 8)
    u("pdf_baseline_medium", "pdf_baseline_medium.pdf", pdf_page_count(RAW / "pdf_baseline_medium.pdf"))

    write_pdf_pages(RAW / "pdf_baseline_multipage.pdf", 15)
    u("pdf_baseline_multipage", "pdf_baseline_multipage.pdf", pdf_page_count(RAW / "pdf_baseline_multipage.pdf"))

    write_pdf_pages(RAW / "pdf_large_001.pdf", 40)
    u("pdf_large_001", "pdf_large_001.pdf", pdf_page_count(RAW / "pdf_large_001.pdf"))

    write_pdf_pages(RAW / "pdf_stress_001.pdf", 120)
    u("pdf_stress_001", "pdf_stress_001.pdf", pdf_page_count(RAW / "pdf_stress_001.pdf"))

    print("Wrote assets under", RAW)
    print("Updated manifest.json for all Tier A ids.")


if __name__ == "__main__":
    main()
