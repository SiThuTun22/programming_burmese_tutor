from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fitz


@dataclass
class PdfWord:
    page: int
    text: str
    x: float
    y: float
    width: float
    height: float


def extract_pdf_words(storage_path: Path) -> tuple[str, list[PdfWord]]:
    document = fitz.open(storage_path)
    words: list[PdfWord] = []
    text_parts: list[str] = []

    page_index = 0
    for page in document:
        page_number = page_index + 1
        page_text = page.get_text('text')
        text_parts.append(page_text)
        raw_words = page.get_text('words')
        for raw_word in raw_words:
            if len(raw_word) < 5:
                continue
            word_text = str(raw_word[4]).strip()
            if len(word_text) == 0:
                continue
            x0 = float(raw_word[0])
            y0 = float(raw_word[1])
            x1 = float(raw_word[2])
            y1 = float(raw_word[3])
            width = x1 - x0
            height = y1 - y0
            pdf_word = PdfWord(page_number, word_text, x0, y0, width, height)
            words.append(pdf_word)
        page_index = page_index + 1

    document.close()
    extracted_text = '\n'.join(text_parts)
    return extracted_text, words


def render_pdf_pages_as_png(storage_path: Path, max_pages: int) -> list[bytes]:
    document = fitz.open(storage_path)
    images: list[bytes] = []
    page_count = document.page_count
    limit = max_pages
    if page_count < limit:
        limit = page_count

    page_index = 0
    while page_index < limit:
        page = document.load_page(page_index)
        pixmap = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
        png_bytes = pixmap.tobytes('png')
        images.append(png_bytes)
        page_index = page_index + 1

    document.close()
    return images
