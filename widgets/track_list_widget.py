from __future__ import annotations

from typing import Iterable

from PySide6.QtWidgets import QListWidget, QListWidgetItem

from models.track import Track
from widgets.album_track_item import AlbumTrackItem
from widgets.base_list_widget import BaseListWidget

class TrackListWidget(BaseListWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)

    def load_tracks(self, tracks: Iterable[Track]) -> None:
        self.clear()
        for track in tracks:
            item = QListWidgetItem()
            widget = AlbumTrackItem(track)
            self.addItem(item)
            self.setItemWidget(item, widget)
            # Let the item size based on widget's size hint
            item.setSizeHint(widget.sizeHint())
        self._sync_item_widget_selection()


    def selected_track(self) -> Track | None:
        item = self.currentItem()
        if not item:
            return None
        widget = self.itemWidget(item)
        return getattr(widget, "track", None)

    def selected_tracks(self) -> list[Track]:
        tracks: list[Track] = []
        for item in self.selectedItems():
            widget = self.itemWidget(item)
            track = getattr(widget, "track", None)
            if track:
                tracks.append(track)
        return tracks
