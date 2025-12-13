from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from models.album import Album
from models.playlist import Playlist
from utils.cover import load_cover_pixmap
from utils.formatting import format_duration


class BaseHeaderWidget(QWidget):
    """Base widget for displaying album/playlist headers with cover art and metadata."""
    download_requested = Signal()

    def __init__(self, default_title: str, download_button_text: str) -> None:
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        # keep items aligned to top
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        # keep fixed height of 160px
        self.setFixedHeight(160)

        self._cover = QLabel()
        self._cover.setFixedSize(160, 160)
        layout.addWidget(self._cover)

        text_container = QVBoxLayout()
        text_container.setSpacing(4)

        # hack: set text container to wrap on vertical height so that the cover and text align at top
        text_container.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._title = QLabel(default_title)
        self._title.setWordWrap(True)
        self._title.setStyleSheet("font-weight: bold; font-size: 18pt;")

        self._meta = QLabel()
        self._meta.setStyleSheet("color: gray;")

        self._download_button = QPushButton(download_button_text)
        self._download_button.clicked.connect(self.download_requested.emit)

        text_container.addWidget(self._title)
        self._add_middle_widgets(text_container)
        text_container.addWidget(self._meta)
        text_container.addStretch()  # Push download button to the bottom
        text_container.addWidget(self._download_button)
        layout.addLayout(text_container)

    def _add_middle_widgets(self, layout: QVBoxLayout) -> None:
        """Override this to add custom widgets between title and meta."""
        pass


class PlaylistHeaderWidget(BaseHeaderWidget):
    def __init__(self) -> None:
        self._desc = QLabel()
        self._desc.setWordWrap(True)
        super().__init__("Select a playlist", "Download Playlist")

    def _add_middle_widgets(self, layout: QVBoxLayout) -> None:
        layout.addWidget(self._desc)

    def render(self, playlist: Playlist, **kwargs) -> None:
        pixmap = load_cover_pixmap(playlist.cover_id, 640, 160)
        self._cover.setPixmap(pixmap)
        self._title.setText(playlist.title)
        duration = format_duration(playlist.duration, long=True)
        artists = ", ".join(playlist.featured_artists) if playlist.featured_artists else "various"
        self._desc.setText(playlist.description or "no description")
        self._meta.setText(f"{playlist.number_of_tracks} tracks • {duration} • {artists}")


class AlbumHeaderWidget(BaseHeaderWidget):
    def __init__(self) -> None:
        self._artist = QLabel()
        self._artist.setWordWrap(True)
        super().__init__("Select an album", "Download Album")

    def _add_middle_widgets(self, layout: QVBoxLayout) -> None:
        layout.addWidget(self._artist)

    def render(self, album: Album, **kwargs) -> None:
        pixmap = load_cover_pixmap(album.cover_id, 640, 160)
        self._cover.setPixmap(pixmap)
        self._title.setText(album.title)
        duration = format_duration(album.duration, long=True)
        self._meta.setText(f"{album.number_of_tracks} tracks • {duration}")
        artists = ", ".join(album.artists) if album.artists else "Unknown Artist"
        year = album.release_date.split("-")[0] if album.release_date else ""
        artist_text = f"{artists}" + (f" • {year}" if year else "")
        self._artist.setText(artist_text)

