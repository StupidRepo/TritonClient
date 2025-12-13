from __future__ import annotations

from typing import Iterable

from PySide6.QtWidgets import QListWidget, QListWidgetItem

from models.track import Track
from widgets.album_track_item import AlbumTrackItem

class TrackListWidget(QListWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.setUniformItemSizes(True)
        self.setSpacing(0)

    def load_tracks(self, tracks: Iterable[Track]) -> None:
        self.clear()
        for track in tracks:
            item = QListWidgetItem()
            widget = AlbumTrackItem(track)
            widget.setFixedHeight(max(widget.sizeHint().height(), 64))
            item.setSizeHint(widget.sizeHint())
            self.addItem(item)
            self.setItemWidget(item, widget)
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
