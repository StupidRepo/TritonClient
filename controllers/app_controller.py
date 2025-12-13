from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Sequence

from models.download_queue import DownloadQueue
from models.playlist import Playlist
from models.track import Track
from services.download_service import DownloadService, ProgressCallback
from services.search_service import SearchService

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class DownloadCallbacks:
    track_started: Callable[[Track, int, int], None] | None = None
    track_progress: ProgressCallback | None = None
    track_completed: Callable[[int, int], None] | None = None


class AppController:
    def __init__(
        self,
        search_service: SearchService | None = None,
        download_service: DownloadService | None = None,
        queue: DownloadQueue | None = None,
        download_dir: Path | None = None,
    ) -> None:
        self._search_service = search_service or SearchService()
        self._download_service = download_service or DownloadService()
        self._queue = queue or DownloadQueue()
        self._download_dir = download_dir or (Path.home() / "Downloads")

    @property
    def download_dir(self) -> Path:
        return self._download_dir

    def set_download_dir(self, folder: Path) -> None:
        self._download_dir = folder

    def categories(self) -> tuple[str, ...]:
        return tuple(self._search_service.available_categories())

    def search(self, category: str, query: str) -> Sequence[Playlist | Track]:
        return self._search_service.search(category, query)

    def fetch_playlist_detail(self, playlist_uuid: str) -> tuple[Playlist, list[Track]]:
        return self._search_service.fetch_playlist_detail(playlist_uuid)

    def queue_size(self) -> int:
        return self._queue.size()

    def queue_is_empty(self) -> bool:
        return self._queue.is_empty()

    def queue_tracks(self) -> list[Track]:
        return self._queue.all_tracks()

    def add_to_queue(self, tracks: Iterable[Track]) -> int:
        return self._queue.add_tracks(tracks)

    def remove_from_queue(self, tracks: Iterable[Track]) -> int:
        return self._queue.remove_tracks(tracks)

    def clear_queue(self) -> None:
        self._queue.clear()

    def download_queue(self, callbacks: DownloadCallbacks | None = None) -> None:
        tracks = self._queue.all_tracks()
        if not tracks:
            return
        callbacks = callbacks or DownloadCallbacks()
        total = len(tracks)
        completed = 0
        for track in tracks:
            if callbacks.track_started:
                callbacks.track_started(track, completed, total)
            # noinspection PyBroadException
            try:
                self._download_service.download_track(
                    track,
                    self._download_dir,
                    progress_callback=callbacks.track_progress,
                )
            except Exception:
                logger.exception("failed to download track %s", track.title)
            finally:
                completed += 1
                if callbacks.track_completed:
                    callbacks.track_completed(completed, total)
        self._queue.clear()
