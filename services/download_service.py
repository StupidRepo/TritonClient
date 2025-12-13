from __future__ import annotations

import base64
import json
import re
from pathlib import Path
from typing import Any, Callable

import requests

from models.track import Track
from utils.media import embed_metadata_with_ffmpeg, FfmpegUnavailableError

ProgressCallback = Callable[[int, int], None]


class DownloadService:
    TRACK_ENDPOINT = "https://triton.squid.wtf/track"
    DOWNLOAD_CHUNK_SIZE = 64 * 1024
    _INVALID_FILENAME_RE = re.compile(r"[\\/:*?\"<>|]+")

    def download_track(
        self,
        track: Track,
        destination: Path,
        progress_callback: ProgressCallback | None = None,
    ) -> Path:
        track_id = track.track_id
        if not track_id:
            raise ValueError("Track does not have an identifier")
        payload = self._fetch_manifest(track_id)
        manifest_b64 = payload.get("data", {}).get("manifest")
        if not manifest_b64:
            raise ValueError("Manifest payload missing")
        # print("Manifest (base64):")
        # print(manifest_b64)
        manifest_json = json.loads(base64.b64decode(manifest_b64))
        urls = manifest_json.get("urls") or []
        if not urls:
            raise ValueError("No download urls in manifest")
        first_entry = urls[0]
        download_url = first_entry if isinstance(first_entry, str) else first_entry.get("url")
        if not download_url:
            raise ValueError("Download url is missing")
        destination.mkdir(parents=True, exist_ok=True)
        target_file = destination / self._build_filename(track)
        with requests.get(download_url, stream=True, timeout=60) as resp:
            resp.raise_for_status()
            total_bytes = int(resp.headers.get("Content-Length") or 0)
            downloaded = 0
            if progress_callback:
                progress_callback(0, total_bytes)
            with target_file.open("wb") as handle:
                for chunk in resp.iter_content(self.DOWNLOAD_CHUNK_SIZE):
                    if chunk:
                        handle.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback:
                            progress_callback(downloaded, total_bytes)
        if progress_callback:
            progress_callback(downloaded, total_bytes)
        try:
            embed_metadata_with_ffmpeg(
                target_file,
                title=track.title,
                album=track.album_title,
                artists=track.artists,
                cover_id=track.cover_id,
            )
        except FfmpegUnavailableError:
            print("ffmpeg not available; skipping metadata embedding")
        except Exception as e:
            print(e)
            print("metadata embedding failed for %s", target_file)
        return target_file

    def _fetch_manifest(self, track_id: str) -> dict[str, Any]:
        resp = requests.get(self.TRACK_ENDPOINT, params={"id": track_id, "quality":"LOSSLESS"}, timeout=15)
        resp.raise_for_status()
        return resp.json()

    def _build_filename(self, track: Track) -> str:
        artist = track.artists[0] if track.artists else "Unknown Artist"
        candidate = f"{artist} - {track.title}".strip()
        safe_name = self._INVALID_FILENAME_RE.sub("", candidate)
        safe_name = safe_name.strip() or "track"
        return f"{safe_name}.flac"

