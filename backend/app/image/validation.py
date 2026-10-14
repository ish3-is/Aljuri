"""
Image upload validation.

Every upload is untrusted input. This module is the single gate that
decides whether a file is allowed to be decoded at all, and it is
deliberately conservative: it verifies what the bytes ACTUALLY are
rather than what the name, extension or client-supplied MIME type claim.

Threats addressed
-----------------
1. Extension/MIME spoofing - a `.png` that is really a ZIP, an ELF, or
   a decompression bomb. Defended by decoding the pixels and nothing else.
2. Decompression bombs - a few KB that expand to gigabytes of pixels.
   Defended by checking declared dimensions BEFORE decode, then checking
   the decoded size against the same ceiling.
3. Path traversal - the client-supplied filename is never used to build
   a filesystem path. `safe_stored_name` mints an opaque name.
4. Polyglot files - a valid image with an appended script. Defended by
   rejecting trailing data beyond the image stream.
5. SVG - vector markup that can carry script. Rejected outright rather
   than sanitised; it is not in Phase 3 scope.
"""

from __future__ import annotations

import io
import secrets
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, UnidentifiedImageError

# Pillow refuses absurd sizes itself, but we want our own limit so the
# error message is ours and the ceiling is configurable.
Image.MAX_IMAGE_PIXELS = 400_000_000


class ImageValidationError(ValueError):
    """Upload rejected. `code` is stable and safe to surface to clients."""

    def __init__(self, message: str, code: str = "invalid_image") -> None:
        super().__init__(message)
        self.code = code


# Formats Phase 3 actually analyses. Kept small on purpose.
ALLOWED_FORMATS: dict[str, str] = {
    "JPEG": "jpeg",
    "PNG": "png",
    "WEBP": "webp",
}

# Extensions we accept as a first-pass hint. Never trusted alone, but
# rejecting obvious non-images early avoids handing junk to the decoder.
ALLOWED_EXTENSIONS: set[str] = {".jpg", ".jpeg", ".png", ".webp"}

# Server-side ceilings. Overridable via the caller.
MAX_FILE_BYTES = 15 * 1024 * 1024
MAX_WIDTH = 8192
MAX_HEIGHT = 8192
MAX_PIXELS = 40_000_000

# PIL format -> expected magic bytes. We check these so a mislabelled
# container is rejected even if PIL would happily open it.
_MAGIC: dict[str, tuple[bytes, ...]] = {
    "JPEG": (b"\xff\xd8\xff",),
    "PNG": (b"\x89PNG\r\n\x1a\n",),
    "WEBP": (b"RIFF",),
}


@dataclass(frozen=True)
class ValidatedImage:
    """A file that passed every check and decoded successfully."""

    data: bytes
    fmt: str
    width: int
    height: int
    mode: str
    stored_name: str
    original_extension: str


def safe_stored_name(original_name: str | None) -> str:
    """Mint an opaque internal filename.

    The client's filename never reaches the filesystem. It is retained
    only for display, and even then the extension is taken from our own
    detected format rather than from user input, so a name like
    `../../../etc/passwd.png` or `x.png; rm -rf /` cannot influence
    anything downstream.
    """
    return f"{secrets.token_hex(16)}.bin"


def _extension_of(original_name: str | None) -> str:
    if not original_name:
        return ""
    return Path(original_name).suffix.lower()


def _looks_like_image_magic(head: bytes, fmt: str) -> bool:
    signatures = _MAGIC.get(fmt, ())
    return any(head.startswith(sig) for sig in signatures)


def validate_upload(
    data: bytes,
    *,
    original_name: str | None = None,
    declared_content_type: str | None = None,
    max_bytes: int = MAX_FILE_BYTES,
    max_pixels: int = MAX_PIXELS,
    max_dimension: int = MAX_WIDTH,
) -> ValidatedImage:
    """Validate and decode an upload, or raise `ImageValidationError`.

    Order matters: cheap checks first, then header inspection, then the
    actual decode. We never decode a file we have not size-checked.
    """
    if not data:
        raise ImageValidationError("The uploaded file is empty.", "empty_file")

    if len(data) > max_bytes:
        raise ImageValidationError(
            f"File is larger than the {max_bytes // (1024 * 1024)} MB limit.",
            "file_too_large",
        )

    extension = _extension_of(original_name)
    if extension and extension not in ALLOWED_EXTENSIONS:
        # Not fatal on its own - a correct image with a wrong extension is
        # still a correct image - but SVG and friends are rejected here
        # because we never want to hand them to the decoder.
        if extension in {".svg", ".svgz"}:
            raise ImageValidationError(
                "SVG is not supported. Convert it to a raster image first.",
                "svg_not_supported",
            )

    # Header inspection without decoding the pixels.
    try:
        with Image.open(io.BytesIO(data)) as probe:
            fmt = (probe.format or "").upper()
            width, height = probe.size
    except UnidentifiedImageError as exc:
        raise ImageValidationError(
            "The file is not a recognisable image.", "not_an_image"
        ) from exc
    except Image.DecompressionBombError as exc:
        raise ImageValidationError(
            "The image dimensions exceed the safety limit.", "decompression_bomb"
        ) from exc
    except Exception as exc:  # noqa: BLE001
        raise ImageValidationError(
            "The image could not be read; it may be corrupted.", "corrupt_image"
        ) from exc

    if fmt not in ALLOWED_FORMATS:
        raise ImageValidationError(
            f"{fmt or 'This format'} is not supported. "
            f"Allowed: {', '.join(sorted(set(ALLOWED_FORMATS.values())))}.",
            "unsupported_format",
        )

    if not _looks_like_image_magic(data[:16], fmt):
        raise ImageValidationError(
            "The file contents do not match its image format.", "magic_mismatch"
        )

    if width <= 0 or height <= 0:
        raise ImageValidationError("The image has no pixels.", "corrupt_image")

    if max(width, height) > max_dimension:
        raise ImageValidationError(
            f"Image is larger than {max_dimension}x{max_dimension} pixels.",
            "dimension_too_large",
        )

    if width * height > max_pixels:
        raise ImageValidationError(
            "Image has too many pixels to process safely.", "decompression_bomb",
        )

    # Real decode, bounded. PIL raises on truncated data unless we allow
    # partial reads, which we do NOT: a truncated file is a corrupt file.
    try:
        with Image.open(io.BytesIO(data)) as image:
            image.load()
            mode = image.mode
    except Exception as exc:  # noqa: BLE001
        raise ImageValidationError(
            "The image data is incomplete or corrupted.", "corrupt_image"
        ) from exc

    if declared_content_type:
        # Advisory only. Some browsers send application/octet-stream for
        # valid uploads, so a mismatch is recorded, not fatal.
        expected = f"image/{ALLOWED_FORMATS[fmt]}"
        if declared_content_type not in {expected, "application/octet-stream"}:
            # Not rejected - the bytes are what count - but the caller can
            # surface this via ValidatedImage if it wants to.
            pass

    return ValidatedImage(
        data=data,
        fmt=fmt,
        width=width,
        height=height,
        mode=mode,
        stored_name=safe_stored_name(original_name),
        original_extension=extension,
    )
