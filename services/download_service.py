from __future__ import annotations

import base64
import json
import logging
import re
from pathlib import Path
from typing import Any, Callable

import requests

import config
from models.track import Track
from utils.media import embed_metadata_with_ffmpeg, FfmpegUnavailableError

logger = logging.getLogger(__name__)
ProgressCallback = Callable[[int, int], None]


class DownloadService:
    TRACK_ENDPOINT = "https://triton.squid.wtf/track"
    _INVALID_FILENAME_RE = re.compile(r"[\\/:*?\"<>|]+")

    def download_track(
        self,
        track: Track,
        destination: Path,
        progress_callback: ProgressCallback | None = None,
    ) -> Path:
        track_id = track.track_id
        if not track_id:
            raise ValueError(f"Track '{track.title}' does not have an identifier")

        try:
            payload = self._fetch_manifest(track_id)
        except Exception as e:
            logger.error("Failed to fetch manifest for track %s: %s", track.title, e)
            raise ValueError(f"Could not fetch manifest for '{track.title}'") from e

        manifest_b64 = payload.get("data", {}).get("manifest")
        if not manifest_b64:
            raise ValueError(f"Manifest payload missing for '{track.title}'")

        try:
            manifest_json = json.loads(base64.b64decode(manifest_b64))
        except (json.JSONDecodeError, Exception) as e:
            logger.error("Failed to decode manifest for track %s: %s", track.title, e)
            raise ValueError(f"Invalid manifest format for '{track.title}'") from e

        urls = manifest_json.get("urls") or []
        if not urls:
            raise ValueError(f"No download URLs in manifest for '{track.title}'")

        first_entry = urls[0]
        download_url = first_entry if isinstance(first_entry, str) else first_entry.get("url")
        if not download_url:
            raise ValueError(f"Download URL is missing for '{track.title}'")

        # Prepare destination
        destination.mkdir(parents=True, exist_ok=True)
        target_file = destination / self._build_filename(track)

        # Download the file
        try:
            with requests.get(download_url, stream=True, timeout=30) as resp:
                resp.raise_for_status()
                total_bytes = int(resp.headers.get("Content-Length") or 0)
                downloaded = 0

                if progress_callback:
                    progress_callback(0, total_bytes)

                with target_file.open("wb") as handle:
                    for chunk in resp.iter_content(chunk_size=config.DOWNLOAD_CHUNK_SIZE):
                        if chunk:
                            handle.write(chunk)
                            downloaded += len(chunk)
                            if progress_callback:
                                progress_callback(downloaded, total_bytes)

                if progress_callback:
                    progress_callback(downloaded, total_bytes)
        except requests.RequestException as e:
            logger.error("Download failed for track %s: %s", track.title, e)
            # Clean up partial download
            if target_file.exists():
                target_file.unlink()
            raise ValueError(f"Download failed for '{track.title}'") from e

        # Embed metadata
        try:
            embed_metadata_with_ffmpeg(
                target_file,
                track = track,
                cover_id=track.cover_id,
            )
        except FfmpegUnavailableError:
            logger.debug("ffmpeg not available; skipping metadata embedding")
        except Exception as e:
            logger.warning("Metadata embedding failed for %s: %s", target_file, e)

        return target_file

    def _fetch_manifest(self, track_id: str) -> dict[str, Any]:
        resp = requests.get(self.TRACK_ENDPOINT, params={"id": track_id, "quality":"LOSSLESS"}, timeout=15)
        resp.raise_for_status()
        return resp.json()

    def _build_filename(self, track: Track) -> str:
        artist = track.artists[0] if track.artists else "Unknown Artist"
        candidate = f"{artist.name if hasattr(artist, "name") else str(artist)} - {track.title}".strip()
        safe_name = self._INVALID_FILENAME_RE.sub("", candidate)
        safe_name = safe_name.strip() or "track"
        return f"{safe_name}.flac"
