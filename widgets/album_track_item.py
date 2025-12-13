from __future__ import annotations

from PySide6.QtCore import QSize
from PySide6.QtGui import QFont, Qt, QPalette, QColor
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from models.track import Track
from utils.cover import load_cover_pixmap
from utils.formatting import format_track_subtitle

class AlbumTrackItem(QWidget):
    def __init__(self, track: Track) -> None:
        super().__init__()
        self.track = track
        self.setLayout(QHBoxLayout())
        self.layout().setSpacing(10)
        self.layout().setContentsMargins(0, 4, 0, 4)

        cover_label = QLabel()
        cover_label.setFixedSize(QSize(92, 92))
        pixmap = load_cover_pixmap(track.cover_id, 160, 92)
        if pixmap:
            cover_label.setPixmap(pixmap)
        self.layout().addWidget(cover_label)

        text_container = QWidget()
        text_layout = QVBoxLayout(text_container)
        text_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)

        title_label = QLabel(track.title)
        font = QFont()
        font.setBold(True)
        title_label.setFont(font)
        subtitle_label = QLabel(format_track_subtitle(track))
        self._title_label = title_label
        self._subtitle_label = subtitle_label
        self._base_title_color = title_label.palette().color(QPalette.ColorRole.WindowText)
        self._subtitle_base_color = QColor("#7a7a7a")

        # quality_label = QLabel(track.audio_quality or "")
        # quality_label.setStyleSheet("color: gray; font-size: 10pt;")

        text_layout.addWidget(title_label)
        text_layout.addWidget(subtitle_label)
        self.layout().addWidget(text_container)
        self._text_container = text_container
        self._is_selected = False
        self._apply_selection_palette(False)

    def set_selected_state(self, selected: bool) -> None:
        if self._is_selected == selected:
            return
        self._is_selected = selected
        self._apply_selection_palette(selected)

    def _apply_selection_palette(self, selected: bool) -> None:
        app_palette = QApplication.palette()
        bg_role = QPalette.ColorRole.Highlight if selected else QPalette.ColorRole.Base
        fg_role = QPalette.ColorRole.HighlightedText if selected else QPalette.ColorRole.Text
        title_color = app_palette.color(fg_role) if selected else self._base_title_color
        subtitle_color = app_palette.color(fg_role) if selected else self._subtitle_base_color
        for widget in (self, self._text_container):
            palette = widget.palette()
            palette.setColor(QPalette.ColorRole.Window, app_palette.color(bg_role))
            palette.setColor(QPalette.ColorRole.Base, app_palette.color(bg_role))
            widget.setPalette(palette)
        for label, color in ((self._title_label, title_color), (self._subtitle_label, subtitle_color)):
            label_palette = label.palette()
            label_palette.setColor(QPalette.ColorRole.WindowText, color)
            label_palette.setColor(QPalette.ColorRole.Text, color)
            label.setPalette(label_palette)

    @property
    def subtitle_text(self) -> str:  # kept for backwards compatibility if referenced elsewhere
        return format_track_subtitle(self.track)
