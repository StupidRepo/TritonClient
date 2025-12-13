from __future__ import annotations

from typing import Iterable

from PySide6.QtCore import QSize, Signal
from PySide6.QtGui import QFont, Qt, QPalette, QColor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget, QSizePolicy, QApplication,
)

from models.album import Album
from utils.cover import load_cover_pixmap


class _AlbumItemWidget(QWidget):
    def __init__(self, album: Album) -> None:
        super().__init__()
        self.album = album
        layout = QHBoxLayout(self)
        self.layout().setSpacing(10)
        self.layout().setContentsMargins(0, 4, 0, 4)

        cover = QLabel()
        cover.setFixedSize(QSize(92, 92))
        pixmap = load_cover_pixmap(album.cover_id, 640, 92)
        if pixmap:
            cover.setPixmap(pixmap)
        layout.addWidget(cover)

        text_container = QWidget()
        text_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        text_layout = QVBoxLayout(text_container)
        text_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)

        title = QLabel(album.title)
        title_font = QFont()
        title_font.setBold(True)
        title.setFont(title_font)

        artist_text = ", ".join(album.artists) if album.artists else "Unknown Artist"
        artist = QLabel(artist_text)
        artist.setWordWrap(True)
        text_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        stats = QLabel(f"{album.number_of_tracks} tracks • {self._format_duration(album.duration)}")
        text_layout.addWidget(title)
        text_layout.addWidget(artist)
        text_layout.addWidget(stats)
        layout.addWidget(text_container)

        self._labels = (title, artist, stats)
        self._title = title
        self._artist = artist
        self._stats = stats
        self._default_artist_color = QColor("#7a7a7a")
        self._default_stats_color = QColor("#7a7a7a")
        self._base_title_color = title.palette().color(QPalette.ColorRole.WindowText)
        self._apply_selection_palette(False)

    def set_selected_state(self, selected: bool) -> None:
        self._apply_selection_palette(selected)

    def _apply_selection_palette(self, selected: bool) -> None:
        app_palette = QApplication.palette()
        fg_role = QPalette.ColorRole.HighlightedText if selected else QPalette.ColorRole.Text
        title_color = app_palette.color(fg_role) if selected else self._base_title_color
        secondary_color = app_palette.color(fg_role) if selected else self._default_artist_color
        stats_color = app_palette.color(fg_role) if selected else self._default_stats_color

        for label, color in ((self._title, title_color), (self._artist, secondary_color), (self._stats, stats_color)):
            palette = label.palette()
            palette.setColor(QPalette.ColorRole.WindowText, color)
            palette.setColor(QPalette.ColorRole.Text, color)
            label.setPalette(palette)

    @staticmethod
    def _format_duration(seconds: int) -> str:
        mins, secs = divmod(seconds, 60)
        return f"{mins}m {secs:02d}s"


class AlbumListWidget(QListWidget):
    album_activated = Signal(Album)

    def __init__(self) -> None:
        super().__init__()
        self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.itemDoubleClicked.connect(self._on_item_activated)
        self._sync_item_widget_selection()

    def selectionChanged(self, selected, deselected) -> None:
        super().selectionChanged(selected, deselected)
        self._sync_item_widget_selection()

    def _sync_item_widget_selection(self) -> None:
        for index in range(self.count()):
            item = self.item(index)
            widget = self.itemWidget(item)
            if widget and hasattr(widget, "set_selected_state"):
                widget.set_selected_state(item.isSelected())

    def _on_item_activated(self, item: QListWidgetItem) -> None:
        widget = self.itemWidget(item)
        if widget and hasattr(widget, "album"):
            self.album_activated.emit(widget.album)

    def load_albums(self, albums: Iterable[Album]) -> None:
        self.clear()
        for album in albums:
            widget = _AlbumItemWidget(album)
            item = QListWidgetItem()
            item.setSizeHint(widget.sizeHint())
            self.addItem(item)
            self.setItemWidget(item, widget)

