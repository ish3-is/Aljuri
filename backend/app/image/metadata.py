"""
Safe image metadata extraction.

Two rules govern this module:

1. **Metadata is supporting evidence, never a verdict.** The absence of
   EXIF does not indicate a synthetic image - it indicates the image was
   stripped, which is common for screenshots, social media, messaging
   apps and every AI generator. The presence of EXIF does not indicate a
   camera either, since software writes EXIF too. `evidence_weight` is
   deliberately `weak` for every metadata signal.

2. **Privacy is the default.** Precise GPS coordinates are never
   returned. `gps_present` is reported as a boolean; the coordinates
   themselves are reduced to nothing. A user who uploads a photo taken at
   their home should not have the location handed back to them through a
   trust tool, least of all one that then displays it.

Nothing here executes, resolves, or fetches anything. EXIF values are
read as inert bytes and never passed to a shell, an import, or a URL
resolver.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field, asdict
from typing import Any

from PIL import Image
from PIL.ExifTags import TAGS

from app.image.validation import ValidatedImage


@dataclass
class MetadataResult:
    """What we are willing to say about an image's embedded metadata."""

    format: str
    width: int
    height: int
    color_mode: str
    exif_present: bool
    camera_make: str | None = None
    camera_model: str | None = None
    software: str | None = None
    orientation: int | None = None
    created: str | None = None
    modified: str | None = None
    #: Boolean only. Coordinates are deliberately discarded.
    gps_present: bool = False
    #: Human-readable note about what EXIF presence does and does not mean.
    exif_interpretation: str = ""
    #: Always "weak" - metadata corroborates, it never decides.
    evidence_weight: str = "weak"
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# GPS IFD tags. We detect presence and then deliberately drop the values.
_GPS_TAG_IDS = {0x8825}


def _clean(value: Any) -> str | None:
    """Coerce an EXIF value to a safe, displayable string.

    EXIF is attacker-controlled. We never return bytes, never resolve
    anything, and truncate aggressively so a multi-kilobyte blob cannot
    bloat a response.
    """
    if value is None:
        return None
    if isinstance(value, bytes):
        # Often holds a maker note or thumbnail. Do not surface it.
        return None
    try:
        text = str(value).strip()
    except Exception:  # noqa: BLE001
        return None
    if not text:
        return None
    # Strip control characters that could corrupt log or terminal output.
    text = "".join(ch for ch in text if ch.isprintable())
    return text[:120] or None


def _format_datetime(value: Any) -> str | None:
    if not value:
        return None
    raw = _clean(value)
    if not raw:
        return None
    # EXIF datetimes look like "2024:01:31 12:00:00". ISO-8601 is friendlier.
    try:
        date_part, time_part = raw.split(" ", 1)
        return f"{date_part.replace(':', '-')}T{time_part}"
    except ValueError:
        return raw


def extract_metadata(image: ValidatedImage) -> MetadataResult:
    """Read metadata without ever exposing location or executing content."""
    result = MetadataResult(
        format=image.fmt,
        width=image.width,
        height=image.height,
        color_mode=image.mode,
        exif_present=False,
    )

    try:
        with Image.open(io.BytesIO(image.data)) as opened:
            exif = None
            try:
                exif = opened.getexif()
            except Exception as exc:  # noqa: BLE001
                result.warnings.append(f"EXIF unreadable: {type(exc).__name__}")

            if exif:
                result.exif_present = True
                for tag_id, value in exif.items():
                    name = TAGS.get(tag_id, str(tag_id))
                    if tag_id in _GPS_TAG_IDS:
                        # Presence only. The coordinates are never read out.
                        result.gps_present = True
                        continue
                    if name == "Make":
                        result.camera_make = _clean(value)
                    elif name == "Model":
                        result.camera_model = _clean(value)
                    elif name == "Software":
                        result.software = _clean(value)
                    elif name == "Orientation":
                        try:
                            result.orientation = int(value)
                        except (TypeError, ValueError):
                            pass
                    elif name == "DateTime":
                        result.created = _format_datetime(value)
                    elif name == "DateTimeOriginal":
                        result.created = _format_datetime(value) or result.created
                    elif name == "DateTimeDigitized":
                        result.modified = _format_datetime(value)

                # Sub-IFDs can hold GPS even when the top level does not.
                try:
                    for ifd_id in (0x8825,):
                        if ifd_id in getattr(exif, "keys", lambda: [])():
                            result.gps_present = True
                except Exception:  # noqa: BLE001
                    pass
    except Exception as exc:  # noqa: BLE001
        result.warnings.append(f"metadata read failed: {type(exc).__name__}")

    if result.exif_present:
        if result.camera_make or result.camera_model:
            result.exif_interpretation = (
                "Camera EXIF is present. This is consistent with a camera "
                "capture but does not confirm one - editing software also "
                "writes EXIF."
            )
        else:
            result.exif_interpretation = (
                "EXIF is present but carries no camera identification. "
                "This is typical of software-written metadata."
            )
    else:
        result.exif_interpretation = (
            "No EXIF metadata. This is NOT evidence of synthetic origin - "
            "screenshots, social platforms and messaging apps all strip it."
        )

    return result
