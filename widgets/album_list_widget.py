from __future__ import annotations

from datetime import datetime
from typing import Iterable

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QListWidgetItem

from models.album import Album
from utils.formatting import format_duration
from widgets.base_item_widget import BaseItemWidget
from widgets.base_list_widget import BaseListWidget


class _AlbumItemWidget(BaseItemWidget):
    def __init__(self, album: Album) -> None:
        super().__init__(album.cover_id, cover_size=640, cover_display_size=92)
        self.album = album

        self._create_title_label(album.title)
        artist_text = ", ".join(artist.name for artist in album.artists)
        self._create_subtitle_label(artist_text, word_wrap=True)

        release_year = datetime.strptime(album.release_date, "%Y-%m-%d").year
        self._create_info_label(
            f"{album.number_of_tracks} tracks • {format_duration(album.duration, long=True)} • {release_year}"
        )

        self._apply_selection_palette(False)

class AlbumListWidget(BaseListWidget):
    album_activated = Signal(Album)

    def __init__(self) -> None:
        super().__init__()
        self.itemDoubleClicked.connect(self._on_item_activated)

    def _on_item_activated(self, item: QListWidgetItem) -> None:
        widget = self.itemWidget(item)
        if widget and hasattr(widget, "album"):
            self.album_activated.emit(widget.album)

    def load_albums(self, albums: Iterable[Album]) -> None:
        self.clear()
        for album in albums:
            widget = _AlbumItemWidget(album)
            item = QListWidgetItem()
            self.addItem(item)
            self.setItemWidget(item, widget)
            # Let the item size based on widget's size hint
            item.setSizeHint(widget.sizeHint())
        self._sync_item_widget_selection()

