from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Iterable

import requests

from utils.cover import build_tidal_image_url

logger = logging.getLogger(__name__)


class FfmpegUnavailableError(RuntimeError):
    """Raised when ffmpeg binary is not available on PATH."""


# noinspection PyUnresolvedReferences,PyDeprecation
def embed_metadata_with_ffmpeg(
    source: Path,
    *,
    title: str,
    album: str | None,
    artists: Iterable[str],
    cover_id: str | None,
) -> None:
    if not source.exists():
        raise FileNotFoundError(f"Audio file {source} does not exist")
    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        raise FfmpegUnavailableError("ffmpeg binary not found on PATH")
    cover_path = _download_cover_art(cover_id)
    output_path = _temp_output_path(source)
    metadata_fields = {
        "title": title,
        "album": album,
        "artist": ", ".join(artists) if artists else None,
        "album_artist": artists[0] if artists else None,
    }
    cmd = [
        ffmpeg_bin,
        "-y",
        "-loglevel",
        "error",
        "-i",
        str(source),
    ]
    if cover_path:
        cmd += [
            "-i",
            str(cover_path),
            "-map",
            "0:a",
            "-map",
            "1:v",
            "-c:a",
            "copy",
            "-c:v",
            "mjpeg",
            "-disposition:v:0",
            "attached_pic",
        ]
    else:
        cmd += [
            "-map",
            "0:a",
            "-c",
            "copy",
        ]
    for key, value in metadata_fields.items():
        if value:
            cmd.extend(["-metadata", f"{key}={value}"])
    cmd.append(str(output_path))
    try:
        subprocess.run(cmd, check=True)
        output_path.replace(source)
    finally:
        _cleanup_temp_file(output_path)
        if cover_path:
            _cleanup_temp_file(cover_path)


def _download_cover_art(cover_id: str | None) -> Path | None:
    if not cover_id:
        return None
    url = build_tidal_image_url(cover_id, size=640)
    if not url:
        return None
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.debug("cover art download failed for %s", cover_id, exc_info=exc)
        return None
    with tempfile.NamedTemporaryFile(prefix="cover_", suffix=".jpg", delete=False) as tmp:
        tmp.write(resp.content)
        temp_path = Path(tmp.name)
    return temp_path


def _temp_output_path(source: Path) -> Path:
    fd, tmp_path = tempfile.mkstemp(
        prefix="ffmpeg_tag_",
        suffix=source.suffix,
        dir=str(source.parent),
    )
    os.close(fd)
    temp_path = Path(tmp_path)
    temp_path.unlink(missing_ok=True)
    return temp_path


def _cleanup_temp_file(path: Path | None) -> None:
    if not path:
        return
    try:
        path.unlink(missing_ok=True)
    except OSError:
        logger.debug("failed to cleanup temp file %s", path)
