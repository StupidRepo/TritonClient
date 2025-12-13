from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class Track:
    track_id: Optional[str]
    title: str
    duration: int | None
    artists: List[str]
    cover_id: str | None
    audio_tags: str | None
    album_title: str | None

    @classmethod
    def from_payload(cls, payload: Dict[str, Any]) -> "Track":
        artists = [artist.get("name") for artist in payload.get("artists", []) if artist.get("name")]
        album = payload.get("album", {})
        cover_id = album.get("cover")
        track_id = payload.get("id")
        return cls(
            track_id=str(track_id) if track_id is not None else None,
            title=payload.get("title", "Untitled Track"),
            duration=payload.get("duration"),
            artists=artists,
            cover_id=cover_id,
            audio_tags=payload.get("mediaMetadata", {}).get("tags", []),
            album_title=album.get("title"),
        )
