from pathlib import Path

from pdf_accessibility import audit_pdf


def write_pdf(path: Path, body: bytes) -> None:
    path.write_bytes(b"%PDF-1.7\n" + body + b"\n%%EOF")


def test_detects_accessible_markers(tmp_path: Path) -> None:
    sample = tmp_path / "good.pdf"
    write_pdf(
        sample,
        b"""
        1 0 obj << /Type /Catalog /Lang (en-US) /StructTreeRoot 2 0 R /MarkInfo << /Marked true >> >> endobj
        3 0 obj << /Title (Accessible Doc) >> endobj
        """,
    )

    report = audit_pdf(sample)
    assert report.failed_checks == 0
    assert report.score_percent == 100.0


def test_flags_missing_markers(tmp_path: Path) -> None:
    sample = tmp_path / "bad.pdf"
    write_pdf(sample, b"1 0 obj << /Type /Catalog >> endobj")

    report = audit_pdf(sample)
    assert report.failed_checks >= 3
    failed_names = {c.name for c in report.checks if not c.passed}
    assert "tagged_pdf" in failed_names
    assert "document_language" in failed_names


def test_alt_text_comparison(tmp_path: Path) -> None:
    sample = tmp_path / "image.pdf"
    write_pdf(
        sample,
        b"""
        1 0 obj << /Subtype /Image >> endobj
        2 0 obj << /MarkInfo << /Marked true >> /StructTreeRoot 3 0 R /Lang (en-US) /Title (Doc) >> endobj
        """,
    )

    report = audit_pdf(sample)
    alt_check = next(c for c in report.checks if c.name == "images_alt_text")
    assert not alt_check.passed
