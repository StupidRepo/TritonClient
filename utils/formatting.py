from __future__ import annotations

from models.track import Track


def format_duration(seconds: int | None, *, long: bool = False) -> str:
    if not seconds and seconds != 0:
        return ""
    minutes, remainder = divmod(max(seconds, 0), 60)
    if long:
        return f"{minutes}m {remainder:02d}s"
    return f"{minutes}:{remainder:02d}"


def format_track_listing(track: Track) -> str:
    artists = ", ".join(artist.name for artist in track.artists)
    return f"{track.title} — {artists}" if artists else track.title


def format_track_subtitle(track: Track) -> str:
    duration_label = format_duration(track.duration)
    artist_label = ", ".join(artist.name for artist in track.artists)
    if duration_label and artist_label:
        return f"{duration_label} • {artist_label}"
    return duration_label or artist_label or "unknown artist"

