from __future__ import annotations

from PySide6.QtCore import QSize
from PySide6.QtGui import QFont, Qt, QPalette, QColor
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
)

from utils.cover import load_cover_pixmap


class BaseItemWidget(QWidget):
    def __init__(
        self,
        cover_id: str,
        cover_size: int = 640,
        cover_display_size: int = 92,
    ) -> None:
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(0, 4, 0, 4)

        self._cover_label = QLabel()
        self._cover_label.setFixedSize(QSize(cover_display_size, cover_display_size))
        pixmap = load_cover_pixmap(cover_id, cover_size, cover_display_size)
        if pixmap:
            self._cover_label.setPixmap(pixmap)
        layout.addWidget(self._cover_label)

        self._text_container = QWidget()
        self._text_container.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        text_layout = QVBoxLayout(self._text_container)
        text_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)

        self._title_label: QLabel | None = None
        self._subtitle_label: QLabel | None = None
        self._info_label: QLabel | None = None

        self._text_layout = text_layout
        layout.addWidget(self._text_container)

        self._base_title_color: QColor | None = None
        self._subtitle_default_color = QColor("#7a7a7a")
        self._info_default_color = QColor("#7a7a7a")
        self._is_selected = False

    def _create_title_label(self, text: str) -> QLabel:
        label = QLabel(text)
        font = QFont()
        font.setBold(True)
        label.setFont(font)
        self._title_label = label
        self._base_title_color = label.palette().color(QPalette.ColorRole.WindowText)
        self._text_layout.addWidget(label)
        return label

    def _create_subtitle_label(self, text: str, word_wrap: bool = False) -> QLabel:
        label = QLabel(text)
        if word_wrap:
            label.setWordWrap(True)
        self._subtitle_label = label
        self._text_layout.addWidget(label)
        return label

    def _create_info_label(self, text: str) -> QLabel:
        label = QLabel(text)
        self._info_label = label
        self._text_layout.addWidget(label)
        return label

    def set_selected_state(self, selected: bool) -> None:
        if self._is_selected == selected:
            return
        self._is_selected = selected
        self._apply_selection_palette(selected)

    def _apply_selection_palette(self, selected: bool) -> None:
        app_palette = QApplication.palette()
        fg_role = (
            QPalette.ColorRole.HighlightedText
            if selected
            else QPalette.ColorRole.Text
        )

        title_color = (
            app_palette.color(fg_role) if selected else self._base_title_color
        )
        subtitle_color = (
            app_palette.color(fg_role) if selected else self._subtitle_default_color
        )
        info_color = (
            app_palette.color(fg_role) if selected else self._info_default_color
        )

        labels_colors = [
            (self._title_label, title_color),
            (self._subtitle_label, subtitle_color),
            (self._info_label, info_color),
        ]

        for label, color in labels_colors:
            if label and color:
                palette = label.palette()
                palette.setColor(QPalette.ColorRole.WindowText, color)
                palette.setColor(QPalette.ColorRole.Text, color)
                label.setPalette(palette)

