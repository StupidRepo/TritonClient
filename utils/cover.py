from __future__ import annotations

from typing import Optional

import requests
from PySide6.QtCore import QSize
from PySide6.QtGui import QPixmap


def build_tidal_image_url(image_id: str, size: int = 160) -> Optional[str]:
    if not image_id:
        return None
    parts = image_id.split("-")
    return f"https://resources.tidal.com/images/{'/'.join(parts)}/{size}x{size}.jpg"


def load_cover_pixmap(image_id: str, size: int, resize: int) -> QPixmap:
    url = build_tidal_image_url(image_id, size)
    if not url:
        return make_placeholder_gray_pixmap(resize)
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(e)
        return make_placeholder_gray_pixmap(resize)
    pixmap = QPixmap()
    return pixmap.scaled(QSize(resize, resize)) if pixmap.loadFromData(resp.content) else make_placeholder_gray_pixmap(resize)

def make_placeholder_gray_pixmap(size: int) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill("#CCCCCC")
    return pixmap