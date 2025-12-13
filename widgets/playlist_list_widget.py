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
    QWidget, QSizePolicy, QApplication, )

from models.playlist import Playlist
from utils.cover import load_cover_pixmap


class _PlaylistItemWidget(QWidget):
    def __init__(self, playlist: Playlist) -> None:
        super().__init__()
        self.playlist = playlist
        layout = QHBoxLayout(self)
        self.layout().setSpacing(10)
        self.layout().setContentsMargins(0, 4, 0, 4)

        cover = QLabel()
        cover.setFixedSize(QSize(92, 92))
        pixmap = load_cover_pixmap(playlist.cover_id, 640, 92)
        if pixmap:
            cover.setPixmap(pixmap)
        layout.addWidget(cover)

        text_container = QWidget()
        text_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        text_layout = QVBoxLayout(text_container)
        text_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)

        title = QLabel(playlist.title)
        title_font = QFont()
        title_font.setBold(True)
        title.setFont(title_font)

        desc = QLabel(playlist.description or "No description")
        desc.setWordWrap(True)
        text_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        stats = QLabel(f"{playlist.number_of_tracks} tracks • {self._format_duration(playlist.duration)}")
        text_layout.addWidget(title)
        text_layout.addWidget(desc)
        text_layout.addWidget(stats)
        layout.addWidget(text_container)
        self._labels = (title, desc, stats)
        self._title = title
        self._desc = desc
        self._stats = stats
        self._default_desc_color = QColor("#7a7a7a")
        self._default_stats_color = QColor("#7a7a7a")
        self._base_title_color = title.palette().color(QPalette.ColorRole.WindowText)
        self._apply_selection_palette(False)

    def set_selected_state(self, selected: bool) -> None:
        self._apply_selection_palette(selected)

    def _apply_selection_palette(self, selected: bool) -> None:
        app_palette = QApplication.palette()
        fg_role = QPalette.ColorRole.HighlightedText if selected else QPalette.ColorRole.Text
        title_color = app_palette.color(fg_role) if selected else self._base_title_color
        secondary_color = app_palette.color(fg_role) if selected else self._default_desc_color
        stats_color = app_palette.color(fg_role) if selected else self._default_stats_color
        for label, color in ((self._title, title_color), (self._desc, secondary_color), (self._stats, stats_color)):
            palette = label.palette()
            palette.setColor(QPalette.ColorRole.WindowText, color)
            palette.setColor(QPalette.ColorRole.Text, color)
            label.setPalette(palette)

    @staticmethod
    def _format_duration(seconds: int) -> str:
        mins, secs = divmod(seconds, 60)
        return f"{mins}m {secs:02d}s"


class PlaylistListWidget(QListWidget):
    playlist_activated = Signal(Playlist)

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

    def load_playlists(self, playlists: Iterable[Playlist]) -> None:
        self.clear()
        for playlist in playlists:
            item = QListWidgetItem()
            widget = _PlaylistItemWidget(playlist)
            widget.setFixedHeight(max(widget.sizeHint().height(), 64))
            item.setSizeHint(widget.sizeHint())
            item.setSizeHint(widget.sizeHint())
            self.addItem(item)
            self.setItemWidget(item, widget)
        self._sync_item_widget_selection()

    # noinspection PyUnresolvedReferences
    def _on_item_activated(self, item: QListWidgetItem) -> None:
        widget = self.itemWidget(item)
        if widget:
            self.playlist_activated.emit(widget.playlist)
