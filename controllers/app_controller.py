from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Callable, Iterable, Sequence

from config import MAX_CONCURRENT_DOWNLOADS
from models.album import Album
from models.download_queue import DownloadQueue
from models.playlist import Playlist
from models.track import Track
from services.download_service import DownloadService, ProgressCallback
from services.search_service import SearchService

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class DownloadCallbacks:
    track_started: Callable[[Track, int, int, int], None] | None = None  # track, completed, total, worker_id
    track_progress: Callable[[int, int, int], None] | None = None  # downloaded, total, worker_id
    track_completed: Callable[[int, int, int], None] | None = None  # completed, total, worker_id
    is_cancelled: Callable[[], bool] | None = None  # check if cancellation requested


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

    def search(self, category: str, query: str) -> Sequence[Playlist | Track | Album]:
        return self._search_service.search(category, query)

    def fetch_playlist_detail(self, playlist_uuid: str) -> tuple[Playlist, list[Track]]:
        return self._search_service.fetch_playlist_detail(playlist_uuid)

    def fetch_album_detail(self, album_id: str) -> tuple[Album, list[Track]]:
        return self._search_service.fetch_album_detail(album_id)

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
        worker_id = 0  # Single-threaded downloads use worker 0
        for track in tracks:
            # Check for cancellation
            if callbacks.is_cancelled and callbacks.is_cancelled():
                break

            if callbacks.track_started:
                callbacks.track_started(track, completed, total, worker_id)

            def progress_wrapper(downloaded: int, total_bytes: int) -> None:
                if callbacks.track_progress:
                    callbacks.track_progress(downloaded, total_bytes, worker_id)

            # noinspection PyBroadException
            try:
                self._download_service.download_track(
                    track,
                    self._download_dir,
                    progress_callback=progress_wrapper,
                )
            except Exception:
                logger.exception("failed to download track %s", track.title)
            finally:
                completed += 1
                if callbacks.track_completed:
                    callbacks.track_completed(completed, total, worker_id)
        self._queue.clear()

    def download_tracks_parallel(
        self,
        tracks: list[Track],
        destination: Path,
        callbacks: DownloadCallbacks | None = None,
        max_workers: int = MAX_CONCURRENT_DOWNLOADS,
    ) -> None:
        if not tracks:
            return

        callbacks = callbacks or DownloadCallbacks()
        total = len(tracks)
        completed = 0
        lock = Lock()
        worker_id_counter = 0
        cancelled = False

        def download_single(track: Track, track_index: int) -> bool:
            nonlocal completed, worker_id_counter, cancelled

            # Check for cancellation before starting
            if callbacks.is_cancelled and callbacks.is_cancelled():
                with lock:
                    cancelled = True
                return False

            # assign worker ID
            with lock:
                if cancelled:
                    return False
                worker_id = worker_id_counter % max_workers
                worker_id_counter += 1
                current_completed = completed

            # notify track started
            if callbacks.track_started:
                callbacks.track_started(track, current_completed, total, worker_id)

            # dl the track with progress callback that includes worker_id
            def progress_wrapper(downloaded: int, total_bytes: int) -> None:
                if callbacks.track_progress:
                    callbacks.track_progress(downloaded, total_bytes, worker_id)

            # noinspection PyBroadException
            try:
                self._download_service.download_track(
                    track,
                    destination,
                    progress_callback=progress_wrapper,
                )
            except Exception:
                logger.exception("failed to download track %s", track.title)

            # notify track completed
            with lock:
                completed += 1
                current_completed = completed
            if callbacks.track_completed:
                callbacks.track_completed(current_completed, total, worker_id)

            return True

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(download_single, track, idx) for idx, track in enumerate(tracks)]
            # wait for all dls to complete
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception:
                    logger.exception("download task failed")

    def download_queue_parallel(self, callbacks: DownloadCallbacks | None = None, max_workers: int = MAX_CONCURRENT_DOWNLOADS) -> None:
        tracks = self._queue.all_tracks()
        if not tracks:
            return
        self.download_tracks_parallel(tracks, self._download_dir, callbacks, max_workers)
        self._queue.clear()

