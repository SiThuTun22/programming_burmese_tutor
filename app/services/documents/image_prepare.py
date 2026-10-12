from __future__ import annotations

import fitz

from app.lib.config import get_vision_max_image_edge


def _detect_image_filetype(image_bytes: bytes) -> str:
    if len(image_bytes) >= 8 and image_bytes[:8] == b'\x89PNG\r\n\x1a\n':
        return 'png'
    if len(image_bytes) >= 2 and image_bytes[0] == 0xFF and image_bytes[1] == 0xD8:
        return 'jpeg'
    if len(image_bytes) >= 12 and image_bytes[:4] == b'RIFF' and image_bytes[8:12] == b'WEBP':
        return 'webp'
    return 'png'


def _prepare_image_bytes(image_bytes: bytes, max_edge: int) -> bytes:
    filetype = _detect_image_filetype(image_bytes)
    document = fitz.open(stream=image_bytes, filetype=filetype)
    page = document.load_page(0)

    page_width = page.rect.width
    page_height = page.rect.height
    longest_edge = page_width
    if page_height > longest_edge:
        longest_edge = page_height

    scale = 1.0
    if longest_edge > max_edge:
        scale = max_edge / longest_edge

    matrix = fitz.Matrix(scale, scale)
    pixmap = page.get_pixmap(matrix=matrix, alpha=False)
    prepared = pixmap.tobytes('jpeg', jpg_quality=85)
    document.close()
    return prepared


def prepare_image_bytes_for_vision(image_bytes: bytes) -> bytes:
    if len(image_bytes) == 0:
        return image_bytes

    max_edge = get_vision_max_image_edge()
    prepared = _prepare_image_bytes(image_bytes, max_edge)
    return prepared


def prepare_image_bytes_for_vision_small(image_bytes: bytes) -> bytes:
    if len(image_bytes) == 0:
        return image_bytes

    max_edge = get_vision_max_image_edge()
    smaller_edge = int(max_edge * 0.75)
    if smaller_edge < 512:
        smaller_edge = 512
    prepared = _prepare_image_bytes(image_bytes, smaller_edge)
    return prepared
