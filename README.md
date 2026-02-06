# PDF Accessibility Software (`pdf-access`)

A lightweight command-line tool to audit baseline accessibility indicators in PDF files.

## What it checks

- Tagged PDF markers (`/MarkInfo` and `/Marked true`)
- Structure tree presence (`/StructTreeRoot`)
- Document language metadata (`/Lang (...)`)
- Title metadata (`/Title (...)`)
- Encryption marker (`/Encrypt`)
- Approximate image-alt coverage (`/Subtype /Image` vs `/Alt (...)`)

> This is a **heuristic scanner** for fast triage. It does not replace full WCAG/PDF/UA conformance testing.

## Usage

```bash
python3 pdf_accessibility.py ./document.pdf
python3 pdf_accessibility.py ./document.pdf --json
python3 pdf_accessibility.py ./document.pdf --output report.txt
```

## Exit codes

- `0`: all checks passed
- `1`: one or more checks failed
- `2`: file error / invalid input

## Development

Run tests:

```bash
python3 -m pytest -q
```
