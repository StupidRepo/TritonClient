from __future__ import annotations

import logging

import requests

from models.album import Album
from models.playlist import Playlist, PlaylistTrack
from models.track import Track

logger = logging.getLogger(__name__)


class SearchService:
    BASE_URL = "https://triton.squid.wtf/search"
    PLAYLIST_DETAILS_URL = "https://triton.squid.wtf/playlist"
    ALBUM_DETAILS_URL = "https://triton.squid.wtf/album"
    MODE_MAP = {
        "Tracks": "s",
        "Artists": "a",
        "Albums": "al",
        "Playlists": "p",
    }

    def available_categories(self) -> tuple[str, ...]:
        return tuple(self.MODE_MAP.keys())

    def search(self, category: str, query: str) -> list[Playlist] | list[Track] | list[Album]:
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
        if category == "Albums":
            album_items = payload.get("data", {}).get("albums", {}).get("items", [])
            return [Album.from_search_payload(item) for item in album_items]
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

    def fetch_album_detail(self, album_id: str) -> tuple[Album, list[Track]]:
        try:
            resp = requests.get(f"{self.ALBUM_DETAILS_URL}/?id={album_id}", timeout=10)
            resp.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("album detail fetch failed for %s", album_id, exc_info=exc)
            return Album(album_id, "", 0, None, 0, "", [], False), []
        payload = resp.json()
        data = payload.get("data", {})
        items = data.get("items", [])

        album_info = {}
        if items:
            first_item = items[0].get("item", {})
            album_data = first_item.get("album", {})
            album_info = {
                "id": album_data.get("id"),
                "title": album_data.get("title", ""),
                "cover": album_data.get("cover"),
                "numberOfTracks": len(items),
                "duration": sum(item.get("item", {}).get("duration", 0) for item in items),
                "releaseDate": "",
                "artists": first_item.get("artists", []),
                "explicit": first_item.get("explicit", False),
            }

        album = Album.from_search_payload(album_info)
        tracks = [Track.from_payload(item.get("item", {})) for item in items]
        return album, tracks

