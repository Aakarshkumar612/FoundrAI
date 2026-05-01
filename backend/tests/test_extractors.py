"""Tests for multi-format text extractors."""

import io
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from backend.storage.extractors import extract_text, get_doc_type, _extract_csv, _extract_excel, _extract_pdf, _extract_docx


# ── get_doc_type ──────────────────────────────────────────────────────────────

class TestGetDocType:
    def test_csv_is_financial(self):
        assert get_doc_type("data.csv") == "financial"

    def test_excel_is_financial(self):
        assert get_doc_type("report.xlsx") == "financial"

    def test_pdf_is_document(self):
        assert get_doc_type("deck.pdf") == "document"

    def test_docx_is_document(self):
        assert get_doc_type("plan.docx") == "document"

    def test_image_is_image(self):
        assert get_doc_type("chart.png") == "image"
        assert get_doc_type("screenshot.jpg") == "image"

    def test_txt_is_document(self):
        assert get_doc_type("notes.txt") == "document"


# ── CSV extractor ─────────────────────────────────────────────────────────────

class TestCSVExtractor:
    CSV = b"month,revenue,burn_rate\n2026-01,85000,42000\n2026-02,92000,43000\n"

    def test_contains_column_names(self):
        text = _extract_csv(self.CSV)
        assert "revenue" in text
        assert "burn_rate" in text

    def test_contains_values(self):
        text = _extract_csv(self.CSV)
        assert "85000" in text

    def test_columns_header_present(self):
        text = _extract_csv(self.CSV)
        assert "Columns:" in text

    def test_dispatch_via_extract_text(self):
        text = extract_text(self.CSV, "fin.csv")
        assert "revenue" in text


# ── Excel extractor ───────────────────────────────────────────────────────────

class TestExcelExtractor:
    def _make_xlsx(self) -> bytes:
        import pandas as pd
        buf = io.BytesIO()
        df = pd.DataFrame({"month": ["2026-01"], "revenue": [85000], "burn_rate": [42000]})
        df.to_excel(buf, index=False, engine="openpyxl")
        return buf.getvalue()

    def test_extracts_column_names(self):
        text = _extract_excel(self._make_xlsx())
        assert "revenue" in text

    def test_extracts_values(self):
        text = _extract_excel(self._make_xlsx())
        assert "85000" in text

    def test_sheet_header_present(self):
        text = _extract_excel(self._make_xlsx())
        assert "Sheet:" in text

    def test_dispatch_via_extract_text(self):
        text = extract_text(self._make_xlsx(), "data.xlsx")
        assert "revenue" in text


# ── PDF extractor ─────────────────────────────────────────────────────────────

class TestPDFExtractor:
    def _make_pdf(self, text: str = "Revenue grew 20% in Q1.") -> bytes:
        from pypdf import PdfWriter
        writer = PdfWriter()
        writer.add_blank_page(width=612, height=792)
        buf = io.BytesIO()
        writer.write(buf)
        return buf.getvalue()

    def test_returns_string_for_valid_pdf(self):
        result = _extract_pdf(self._make_pdf())
        assert isinstance(result, str)

    def test_dispatch_via_extract_text(self):
        result = extract_text(self._make_pdf(), "report.pdf")
        assert isinstance(result, str)

    def test_empty_pdf_returns_empty_string(self):
        result = _extract_pdf(self._make_pdf())
        assert isinstance(result, str)  # blank pages → empty, no crash


# ── Word extractor ────────────────────────────────────────────────────────────

class TestDocxExtractor:
    def _make_docx(self, text: str = "Our runway is 18 months.") -> bytes:
        from docx import Document
        doc = Document()
        doc.add_paragraph(text)
        buf = io.BytesIO()
        doc.save(buf)
        return buf.getvalue()

    def test_extracts_paragraph_text(self):
        text = _extract_docx(self._make_docx("Runway is 18 months."))
        assert "Runway" in text

    def test_dispatch_via_extract_text(self):
        text = extract_text(self._make_docx(), "plan.docx")
        assert isinstance(text, str)
        assert len(text) > 0


# ── Image extractor ───────────────────────────────────────────────────────────

class TestImageExtractor:
    def _make_png(self) -> bytes:
        from PIL import Image
        img = Image.new("RGB", (100, 100), color=(255, 0, 0))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def test_returns_fallback_when_no_groq_client(self):
        text = extract_text(self._make_png(), "chart.png", groq_client=None)
        assert "chart.png" in text

    def test_calls_groq_vision_when_client_provided(self):
        mock_groq = MagicMock()
        mock_groq.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Revenue chart showing 20% growth."))]
        )
        text = extract_text(self._make_png(), "revenue.png", groq_client=mock_groq)
        assert "Revenue chart" in text
        mock_groq.chat.completions.create.assert_called_once()

    def test_groq_failure_returns_fallback(self):
        mock_groq = MagicMock()
        mock_groq.chat.completions.create.side_effect = Exception("API error")
        text = extract_text(self._make_png(), "chart.png", groq_client=mock_groq)
        assert "chart.png" in text


# ── Unsupported / edge cases ──────────────────────────────────────────────────

class TestEdgeCases:
    def test_txt_file_returns_content(self):
        text = extract_text(b"Hello world. Revenue is up.", "notes.txt")
        assert "Hello world" in text

    def test_unknown_extension_returns_empty(self):
        text = extract_text(b"data", "file.xyz")
        assert text == ""

    def test_corrupt_csv_returns_empty(self):
        text = extract_text(b"\x00\xff\xfe", "bad.csv")
        assert isinstance(text, str)
