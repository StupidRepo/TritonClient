from __future__ import annotations

from typing import Iterable

from models.track import Track


def _key(track: Track) -> str:
    if track.track_id:
        return track.track_id
    # since track.artists is a list of TrackArtist, we need to extract their names
    artist_key = "-".join(artist.name for artist in track.artists) if track.artists else ""
    return f"{track.title}-{artist_key}".strip()


class DownloadQueue:
    def __init__(self) -> None:
        self._tracks: list[Track] = []
        self._seen_keys: set[str] = set()

    def add_tracks(self, tracks: Iterable[Track]) -> int:
        added = 0
        for track in tracks:
            key = _key(track)
            if not key or key in self._seen_keys:
                continue
            self._tracks.append(track)
            self._seen_keys.add(key)
            added += 1
        return added

    def remove_tracks(self, tracks: Iterable[Track]) -> int:
        to_remove = {_key(track) for track in tracks if _key(track)}
        if not to_remove:
            return 0
        original = len(self._tracks)
        self._tracks = [track for track in self._tracks if _key(track) not in to_remove]
        self._seen_keys = {_key(track) for track in self._tracks}
        return original - len(self._tracks)

    def clear(self) -> None:
        self._tracks.clear()
        self._seen_keys.clear()

    def size(self) -> int:
        return len(self._tracks)

    def all_tracks(self) -> list[Track]:
        """Return a copy of all tracks in the queue."""
        return list(self._tracks)

    def is_empty(self) -> bool:
        """Check if the queue is empty."""
        return not self._tracks

    def peek(self, count: int | None = None) -> list[Track]:
        """Return the first 'count' tracks without removing them. If count is None, return all."""
        if count is None:
            return list(self._tracks)
        return list(self._tracks[:count])

