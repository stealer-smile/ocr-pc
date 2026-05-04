"""
pdf_processor.py — PDF to PIL Images
"""
import logging
import pypdfium2 as pdfium
from PIL import Image
from pathlib import Path
from typing import Generator

log = logging.getLogger("pdf_processor")


def pdf_to_images(
  pdf_path: str | Path,
  scale: float = 2.77,
  max_longest_dim: int = 1540,
) -> Generator[tuple[int, Image.Image], None, None]:
  doc = pdfium.PdfDocument(str(pdf_path))
  total = len(doc)
  log.info("PDF opened: %d pages | scale=%.1f | max_dim=%d", total, scale, max_longest_dim)

  for i in range(total):
    page = doc[i]
    pil_img: Image.Image = page.render(scale=scale).to_pil()
    w, h = pil_img.size
    longest = max(w, h)
    if longest > max_longest_dim:
      ratio = max_longest_dim / longest
      pil_img = pil_img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
    yield i, pil_img

  doc.close()


def get_page_count(pdf_path: str | Path) -> int:
  doc = pdfium.PdfDocument(str(pdf_path))
  count = len(doc)
  doc.close()
  return count
