from __future__ import annotations

from typing import Any

def extract_artist_names(artists_data: list[dict[str, Any]]) -> list[str]:
    """Extract artist names from API payload data."""
    return [
        artist.get("name")
        for artist in artists_data
        if artist.get("name")
    ]


def safe_str_id(value: Any) -> str:
    """Convert a value to a string ID, returning empty string if None."""
    return str(value) if value is not None else ""

