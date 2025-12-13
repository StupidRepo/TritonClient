from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from utils.payload_helpers import extract_artist_names, safe_str_id


@dataclass
class Album:
    album_id: str
    title: str
    duration: int
    cover_id: Optional[str]
    number_of_tracks: int
    release_date: str
    artists: List[str]
    explicit: bool

    @classmethod
    def from_search_payload(cls, payload: Dict[str, Any]) -> "Album":
        """Parse album from search results"""
        artists = extract_artist_names(payload.get("artists", []))
        album_id = safe_str_id(payload.get("id"))

        return cls(
            album_id=album_id,
            title=payload.get("title", "Untitled Album"),
            duration=payload.get("duration", 0),
            cover_id=payload.get("cover"),
            number_of_tracks=payload.get("numberOfTracks", 0),
            release_date=payload.get("releaseDate", ""),
            artists=artists,
            explicit=payload.get("explicit", False),
        )

