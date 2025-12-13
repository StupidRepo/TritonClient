from __future__ import annotations

from typing import Iterable

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QListWidgetItem

from models.playlist import Playlist
from utils.formatting import format_duration
from widgets.base_item_widget import BaseItemWidget
from widgets.base_list_widget import BaseListWidget


class _PlaylistItemWidget(BaseItemWidget):
    def __init__(self, playlist: Playlist) -> None:
        super().__init__(playlist.cover_id, cover_size=640, cover_display_size=92)
        self.playlist = playlist

        # Create labels using base class methods
        self._create_title_label(playlist.title.strip())
        self._create_subtitle_label(
            playlist.description.strip() or "No description", word_wrap=True
        )
        self._create_info_label(
            f"{playlist.number_of_tracks} tracks • {format_duration(playlist.duration, long=True)}"
        )

        # Apply initial palette
        self._apply_selection_palette(False)


class PlaylistListWidget(BaseListWidget):
    playlist_activated = Signal(Playlist)

    def __init__(self) -> None:
        super().__init__()
        self.itemDoubleClicked.connect(self._on_item_activated)

    def load_playlists(self, playlists: Iterable[Playlist]) -> None:
        self.clear()
        for playlist in playlists:
            widget = _PlaylistItemWidget(playlist)
            item = QListWidgetItem()
            self.addItem(item)
            self.setItemWidget(item, widget)
            # Let the item size based on widget's size hint
            item.setSizeHint(widget.sizeHint())
        self._sync_item_widget_selection()

    def _on_item_activated(self, item: QListWidgetItem) -> None:
        widget = self.itemWidget(item)
        if widget and hasattr(widget, "playlist"):
            self.playlist_activated.emit(widget.playlist)
