from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from models.track import Track
from utils.payload_helpers import extract_artist_names


@dataclass
class Playlist:
    uuid: str
    title: str
    description: str
    duration: int
    cover_id: Optional[str]
    number_of_tracks: int
    featured_artists: List[str]

    # this is used when parsing search results and also when we double-click on a playlist to view its details
    # we use .get("playlist", {}) to handle the /playlist/?id=... structure.
    # couldn't be bothered to duplicate this in two separate methods, so we just do it all here in one.
    # if one field can't be found, assume it's detailed /playlist/?id=... structure, and look under "playlist"
    @classmethod
    def from_search_payload(cls, payload: Dict[str, Any]) -> "Playlist":
        # Extract featured artists from either direct payload or nested playlist
        promoted_artists = (
            extract_artist_names(payload.get("promotedArtists", []))
            or extract_artist_names(payload.get("playlist", {}).get("promotedArtists", []))
        )

        return cls(
            uuid=(payload.get("uuid") or payload.get("playlist", {}).get("uuid", "")),
            title=(
                payload.get("title")
                or payload.get("playlist", {}).get("title", "Untitled Playlist")
            ),
            description=(
                payload.get("description")
                or payload.get("playlist", {}).get("description", "")
            ),
            duration=(payload.get("duration") or payload.get("playlist", {}).get("duration", 0)),
            cover_id=(
                payload.get("squareImage")
                or payload.get("playlist", {}).get("squareImage")
            ),
            number_of_tracks=(
                payload.get("numberOfTracks")
                or payload.get("playlist", {}).get("numberOfTracks", 0)
            ),
            featured_artists=promoted_artists,
        )


@dataclass
class PlaylistTrack:
    track: Track
    index: int

    @classmethod
    def from_detail_payload(cls, payload: Dict[str, Any]) -> "PlaylistTrack":
        item = payload.get("item", {})
        track = Track.from_payload(item)
        return cls(track=track, index=item.get("trackNumber", payload.get("index", 0)))
