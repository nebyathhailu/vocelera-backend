"""
File parsing layer.

Each parser returns a plain dict:
  {
    "text":       str,   # full extracted text for the AI prompt
    "row_count":  int | None,
    "page_count": int | None,
    "preview":    str,   # first ~500 chars for logging / debug
  }

Parsers are stateless — no Django imports, no models. Easy to unit-test.
"""

import io
import logging
from typing import BinaryIO

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------

def parse_csv(file_obj: BinaryIO) -> dict:
    """
    Parse a CSV file into structured text for AI consumption.
    Handles encoding detection and truncates large files to 5000 rows.
    """
    import chardet
    import pandas as pd

    raw = file_obj.read()
    detected = chardet.detect(raw)
    encoding = detected.get("encoding") or "utf-8"

    df = pd.read_csv(io.BytesIO(raw), encoding=encoding, nrows=5000)
    df = df.dropna(how="all")

    row_count  = len(df)
    col_names  = list(df.columns)

    # Build a text block: column names + sample rows
    sample     = df.head(100).to_string(index=False)
    stats_text = df.describe(include="all").to_string()

    text = (
        f"=== CSV DOCUMENT ===\n"
        f"Total rows: {row_count}\n"
        f"Columns ({len(col_names)}): {', '.join(str(c) for c in col_names)}\n\n"
        f"=== STATISTICAL SUMMARY ===\n{stats_text}\n\n"
        f"=== SAMPLE DATA (first 100 rows) ===\n{sample}"
    )

    return {
        "text":       text,
        "row_count":  row_count,
        "page_count": None,
        "preview":    text[:500],
    }


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------

def parse_pdf(file_obj: BinaryIO) -> dict:
    """
    Extract text from all pages of a PDF using pdfplumber.
    Caps at 50 pages for token safety.
    """
    import pdfplumber

    MAX_PAGES = 50
    pages_text = []
    page_count = 0

    with pdfplumber.open(file_obj) as pdf:
        page_count = len(pdf.pages)
        pages_to_read = pdf.pages[:MAX_PAGES]

        for i, page in enumerate(pages_to_read, start=1):
            extracted = page.extract_text()
            if extracted and extracted.strip():
                pages_text.append(f"--- Page {i} ---\n{extracted.strip()}")

    full_text = "\n\n".join(pages_text)

    truncation_note = ""
    if page_count > MAX_PAGES:
        truncation_note = f"\n[Note: Document has {page_count} pages. Analysis covers first {MAX_PAGES} pages.]"

    text = (
        f"=== PDF DOCUMENT ===\n"
        f"Total pages: {page_count}{truncation_note}\n\n"
        f"=== EXTRACTED TEXT ===\n{full_text}"
    )

    return {
        "text":       text,
        "row_count":  None,
        "page_count": page_count,
        "preview":    text[:500],
    }


# ---------------------------------------------------------------------------
# Excel
# ---------------------------------------------------------------------------

def parse_excel(file_obj: BinaryIO) -> dict:
    """
    Parse an Excel file (xlsx or xls).
    Processes all sheets, capped at 5000 rows per sheet.
    """
    import pandas as pd

    xl     = pd.ExcelFile(file_obj)
    sheets = xl.sheet_names
    parts  = []
    total_rows = 0

    for sheet_name in sheets:
        df = pd.read_excel(xl, sheet_name=sheet_name, nrows=5000)
        df = df.dropna(how="all")

        row_count = len(df)
        total_rows += row_count

        sample     = df.head(100).to_string(index=False)
        stats_text = df.describe(include="all").to_string()
        col_names  = list(df.columns)

        parts.append(
            f"=== SHEET: {sheet_name} ===\n"
            f"Rows: {row_count} | Columns: {', '.join(str(c) for c in col_names)}\n\n"
            f"Statistical summary:\n{stats_text}\n\n"
            f"Sample data:\n{sample}"
        )

    text = f"=== EXCEL DOCUMENT ===\nSheets: {', '.join(sheets)}\n\n" + "\n\n".join(parts)

    return {
        "text":       text,
        "row_count":  total_rows,
        "page_count": None,
        "preview":    text[:500],
    }


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

def parse_document(file_obj: BinaryIO, document_type: str) -> dict:
    """
    Route to the correct parser based on document_type string.

    Args:
        file_obj:      File-like object (Django InMemoryUploadedFile or similar)
        document_type: One of "csv", "pdf", "xlsx"

    Returns:
        dict with text, row_count, page_count, preview keys.

    Raises:
        ValueError: If document_type is unsupported.
    """
    parsers = {
        "csv":  parse_csv,
        "pdf":  parse_pdf,
        "xlsx": parse_excel,
        "xls":  parse_excel,
    }

    parser = parsers.get(document_type.lower())
    if not parser:
        raise ValueError(
            f"Unsupported document type: '{document_type}'. "
            f"Supported: {', '.join(parsers.keys())}"
        )

    logger.info("Parsing document [type=%s]", document_type)
    return parser(file_obj)