#!/usr/bin/env python3
"""PDF accessibility auditor CLI.

This tool performs practical, heuristic checks that are useful for quickly
triaging PDF accessibility quality.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


@dataclass
class CheckResult:
    name: str
    passed: bool
    severity: str
    message: str


@dataclass
class AuditReport:
    file_path: str
    total_checks: int
    passed_checks: int
    failed_checks: int
    score_percent: float
    checks: list[CheckResult]
    notes: list[str]


def _contains_tagged_pdf_markers(pdf_bytes: bytes) -> bool:
    return b"/MarkInfo" in pdf_bytes and (
        b"/Marked true" in pdf_bytes or b"/Marked true\n" in pdf_bytes
    )


def _contains_structure_tree(pdf_bytes: bytes) -> bool:
    return b"/StructTreeRoot" in pdf_bytes


def _contains_document_lang(pdf_bytes: bytes) -> bool:
    # Example: /Lang (en-US)
    return bool(re.search(rb"/Lang\s*\([^)]+\)", pdf_bytes))


def _contains_title_metadata(pdf_bytes: bytes) -> bool:
    # Example: /Title (My PDF)
    return bool(re.search(rb"/Title\s*\([^)]+\)", pdf_bytes))


def _contains_encrypt_dictionary(pdf_bytes: bytes) -> bool:
    return b"/Encrypt" in pdf_bytes


def _image_count(pdf_bytes: bytes) -> int:
    return len(re.findall(rb"/Subtype\s*/Image", pdf_bytes))


def _alt_text_count(pdf_bytes: bytes) -> int:
    # Example in tagged structures: /Alt (Description)
    return len(re.findall(rb"/Alt\s*\([^)]+\)", pdf_bytes))


def _iter_checks(pdf_bytes: bytes) -> Iterable[CheckResult]:
    tagged = _contains_tagged_pdf_markers(pdf_bytes)
    struct = _contains_structure_tree(pdf_bytes)
    lang = _contains_document_lang(pdf_bytes)
    title = _contains_title_metadata(pdf_bytes)
    encrypted = _contains_encrypt_dictionary(pdf_bytes)
    img_count = _image_count(pdf_bytes)
    alt_count = _alt_text_count(pdf_bytes)

    yield CheckResult(
        name="tagged_pdf",
        passed=tagged,
        severity="high",
        message=(
            "Tagged PDF markers were found." if tagged else "No Tagged PDF markers found (/MarkInfo /Marked true)."
        ),
    )
    yield CheckResult(
        name="structure_tree",
        passed=struct,
        severity="high",
        message=(
            "Structure tree root found." if struct else "No /StructTreeRoot found; logical reading structure may be missing."
        ),
    )
    yield CheckResult(
        name="document_language",
        passed=lang,
        severity="medium",
        message="Document language found." if lang else "No /Lang metadata found.",
    )
    yield CheckResult(
        name="title_metadata",
        passed=title,
        severity="medium",
        message="Title metadata found." if title else "No /Title metadata found.",
    )
    yield CheckResult(
        name="not_encrypted",
        passed=not encrypted,
        severity="low",
        message="Document is not encrypted." if not encrypted else "Document appears encrypted (/Encrypt).",
    )

    if img_count == 0:
        yield CheckResult(
            name="images_alt_text",
            passed=True,
            severity="medium",
            message="No images detected; alt-text check skipped.",
        )
    else:
        enough_alt = alt_count >= img_count
        yield CheckResult(
            name="images_alt_text",
            passed=enough_alt,
            severity="medium",
            message=(
                f"Detected {img_count} image markers and {alt_count} /Alt markers."
                if enough_alt
                else f"Detected {img_count} image markers but only {alt_count} /Alt markers."
            ),
        )


def audit_pdf(file_path: Path) -> AuditReport:
    pdf_bytes = file_path.read_bytes()
    checks = list(_iter_checks(pdf_bytes))
    passed = sum(1 for c in checks if c.passed)
    total = len(checks)
    failed = total - passed
    notes = [
        "Heuristic scan only: results are not a substitute for full WCAG/PDF/UA validation.",
        "For production compliance, validate with assistive technology and a dedicated PDF/UA validator.",
    ]

    return AuditReport(
        file_path=str(file_path),
        total_checks=total,
        passed_checks=passed,
        failed_checks=failed,
        score_percent=round((passed / total) * 100, 2) if total else 0.0,
        checks=checks,
        notes=notes,
    )


def _format_text_report(report: AuditReport) -> str:
    lines = [
        f"PDF Accessibility Report: {report.file_path}",
        f"Score: {report.score_percent}% ({report.passed_checks}/{report.total_checks} checks passed)",
        "",
        "Checks:",
    ]
    for check in report.checks:
        icon = "PASS" if check.passed else "FAIL"
        lines.append(f"- [{icon}] {check.name} ({check.severity}): {check.message}")

    lines.append("\nNotes:")
    lines.extend(f"- {note}" for note in report.notes)
    return "\n".join(lines)


def _to_json(report: AuditReport) -> str:
    payload = asdict(report)
    payload["checks"] = [asdict(c) for c in report.checks]
    return json.dumps(payload, indent=2)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="pdf-access",
        description="Audit a PDF for baseline accessibility signals.",
    )
    parser.add_argument("pdf", type=Path, help="Path to a PDF file")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional path to write the report (stdout if omitted)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if not args.pdf.exists() or not args.pdf.is_file():
        print(f"Error: file not found: {args.pdf}", file=sys.stderr)
        return 2

    report = audit_pdf(args.pdf)
    output = _to_json(report) if args.json else _format_text_report(report)

    if args.output:
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output)

    return 1 if report.failed_checks else 0


if __name__ == "__main__":
    raise SystemExit(main())
