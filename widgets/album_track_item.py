from __future__ import annotations

from models.track import Track
from utils.formatting import format_track_subtitle
from widgets.base_item_widget import BaseItemWidget


class AlbumTrackItem(BaseItemWidget):
    def __init__(self, track: Track) -> None:
        super().__init__(track.cover_id, cover_size=160, cover_display_size=92)
        self.track = track

        self._create_title_label(track.title)
        self._create_subtitle_label(format_track_subtitle(track))

        self._apply_selection_palette(False)

    @property
    def subtitle_text(self) -> str:
        return format_track_subtitle(self.track)
