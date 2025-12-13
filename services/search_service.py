from __future__ import annotations

import logging

import requests

from models.playlist import Playlist, PlaylistTrack
from models.track import Track

logger = logging.getLogger(__name__)


class SearchService:
    BASE_URL = "https://triton.squid.wtf/search"
    PLAYLIST_DETAILS_URL = "https://triton.squid.wtf/playlist"
    MODE_MAP = {
        "Tracks": "s",
        "Artists": "a",
        "Albums": "al",
        "Playlists": "p",
    }

    def available_categories(self) -> tuple[str, ...]:
        return tuple(self.MODE_MAP.keys())

    def search(self, category: str, query: str) -> list[Playlist] | list[Track]:
        if not query or category not in self.MODE_MAP:
            return []
        params = {self.MODE_MAP[category]: query}
        try:
            resp = requests.get(self.BASE_URL, params=params, timeout=10)
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.warning("search request failed for %s / %s", category, query, exc_info=e)
            return []
        payload = resp.json()
        items = payload.get("data", {}).get("items", [])
        if category == "Tracks":
            return [Track.from_payload(item) for item in items]
        if category == "Playlists":
            playlist_items = payload.get("data", {}).get("playlists", {}).get("items", [])
            return [Playlist.from_search_payload(item) for item in playlist_items]
        return items

    def fetch_playlist_detail(self, playlist_uuid: str) -> tuple[Playlist, list[Track]]:
        try:
            resp = requests.get(f"{self.PLAYLIST_DETAILS_URL}/?id={playlist_uuid}", timeout=10)
            resp.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("playlist detail fetch failed for %s", playlist_uuid, exc_info=exc)
            return Playlist(playlist_uuid, "", "", 0, None, 0, []), []
        payload = resp.json()
        playlist = Playlist.from_search_payload(payload)
        tracks = [PlaylistTrack.from_detail_payload(item).track for item in payload.get("items", [])]
        return playlist, tracks
