"""
Lightweight image-forensic signals.

Discipline applied throughout: **a signal may only claim what it can
actually establish.** Every signal below carries a `meaning` and a
`does_not_mean`, and the explanation layer is required to surface both.
The project's Phase 2 arc was spent learning that a measurable signal can
encode collection methodology rather than the thing it appears to
measure; these are written to be checkable rather than impressive.

What is deliberately NOT here
------------------------------
**ELA (Error Level Analysis).** ELA is widely circulated as an AI-image
detector. It is not one. ELA visualises the difference between a
re-encoded image and its reconstruction, which reflects *any* re-
compression - including ordinary JPEG recompression by a messaging app -
and has been repeatedly shown to misclassify heavily compressed genuine
photographs as manipulated. Including it would put a visually striking
signal in the UI that confidently indicates the wrong thing. It is
excluded, and the exclusion is documented rather than silent.

Similarly excluded: any claim about anatomy (hands, fingers, teeth),
object counting, or "AI tells". Those need validated object-level models.
Without one, "the hands look wrong" is an anecdote, not evidence.

Signals included, and what each genuinely establishes:

``compression_anomaly``
    Quantisation-table structure. Establishes how the file was encoded.
    Does NOT establish whether the content is synthetic.

``high_frequency_energy``
    Share of energy above the Nyquist half of the spectrum. Establishes
    how sharp the image is. Saturated synthetic images often differ here,
    but so does any in-focus camera photograph - weak evidence alone.

``noise_floor_estimate``
    Variance in near-flat regions. Establishes sensor/processing noise.
    Heavy denoising, upscaling and compression all suppress it.

``spectral_slope``
    Rate at which energy decays with frequency. Establishes the overall
    texture statistics of the pipeline that produced the file.
"""

from __future__ import annotations

import io
import math
from dataclasses import dataclass, asdict, field
from typing import Any

import numpy as np
from PIL import Image

from app.image.validation import ValidatedImage


@dataclass
class ForensicSignal:
    name: str
    value: float | None
    meaning: str
    does_not_mean: str
    #: How much weight this signal may carry in fusion. All are weak;
    #: the model is the primary evidence channel by design.
    weight: str = "weak"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ForensicReport:
    signals: list[ForensicSignal] = field(default_factory=list)
    excluded: list[dict[str, str]] = field(default_factory=list)

    def as_dicts(self) -> list[dict[str, Any]]:
        return [s.to_dict() for s in self.signals]

    def get(self, name: str) -> float | None:
        for signal in self.signals:
            if signal.name == name:
                return signal.value
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "signals": self.as_dicts(),
            "excluded": self.excluded,
            "ela_excluded_reason": (
                "Error Level Analysis is not used. ELA responds to any "
                "re-compression, including ordinary messaging-app "
                "recompression of a genuine photograph, so it cannot "
                "distinguish synthetic media from a compressed camera "
                "photo. It is misleading rather than merely weak."
            ),
        }


# Signals that are deliberately not computed, recorded so the omission is
# visible in the API response instead of being invisible to a reader.
_EXCLUDED = [
    {
        "name": "error_level_analysis",
        "reason": "Not a synthetic-media detector; misclassifies recompressed genuine photos.",
    },
    {
        "name": "anatomy_or_object_checks",
        "reason": "Requires a validated object-level model; none is implemented.",
    },
]


def _to_gray_array(image: ValidatedImage, limit: int = 1024) -> np.ndarray:
    """Grayscale float array, optionally downscaled for speed.

    Downscaling for *analysis only* is fine and is not the same as the
    preprocessing the model sees.
    """
    with Image.open(io.BytesIO(image.data)) as opened:
        gray = opened.convert("L")
        if max(gray.size) > limit:
            ratio = limit / max(gray.size)
            gray = gray.resize(
                (max(1, int(gray.width * ratio)), max(1, int(gray.height * ratio))),
                Image.BILINEAR,
            )
        return np.asarray(gray, dtype=np.float64)


def compression_anomaly(image: ValidatedImage) -> float | None:
    """Estimate blockiness from the JPEG quantisation table.

    Higher = stronger 8x8 block structure. This measures ENCODING, not
    authorship. A genuine camera JPEG has strong block structure; so does
    a synthetic image that was exported as JPEG. The signal is retained
    because it is a useful covariate for the model, not because it
    separates real from synthetic on its own.
    """
    if image.fmt != "JPEG":
        return None
    try:
        with Image.open(io.BytesIO(image.data)) as opened:
            table = opened.quantization
        if not table:
            return None
        first = table.get(0) if 0 in table else next(iter(table.values()))
        values = [v for v in first if v > 0]
        if not values:
            return None
        # Low average quantiser => aggressive compression => high blockiness.
        return round(1.0 - (sum(values) / len(values)) / 255.0, 5)
    except Exception:  # noqa: BLE001
        return None


def frequency_stats(array: np.ndarray) -> tuple[float | None, float | None]:
    """(high-frequency energy fraction, spectral slope)."""
    if array.size < 64:
        return None, None
    try:
        spectrum = np.abs(np.fft.fftshift(np.fft.fft2(array)))
        total = spectrum.sum()
        if total <= 0:
            return None, None

        rows, cols = spectrum.shape
        cy, cx = rows // 2, cols // 2
        yy, xx = np.ogrid[:rows, :cols]
        radius = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
        max_radius = radius.max() or 1.0

        high_mask = radius > 0.5 * max_radius
        high_fraction = float(spectrum[high_mask].sum() / total)

        # Radial profile -> linear fit in log-log space for a slope.
        radii = radius.astype(int).ravel()
        energy = spectrum.ravel()
        bins = 24
        radial = np.bincount(
            (radii / max_radius * (bins - 1)).astype(int), weights=energy, minlength=bins
        )
        counts = np.bincount(
            (radii / max_radius * (bins - 1)).astype(int), minlength=bins
        )
        valid = (counts > 0) & (radial > 0)
        if valid.sum() < 4:
            return round(high_fraction, 6), None
        x = np.log10(np.arange(bins)[valid] + 1)
        y = np.log10(radial[valid])
        slope = float(np.polyfit(x, y, 1)[0])
        return round(high_fraction, 6), round(slope, 6)
    except Exception:  # noqa: BLE001
        return None, None


def noise_floor(array: np.ndarray) -> float | None:
    """Variance in locally flat regions - a proxy for sensor noise.

    High values mean an unprocessed capture. Low values mean denoising,
    upscaling or heavy compression. AI generators typically produce very
    low noise, but so does any image that has been through a messaging
    app, so this is corroborating evidence at best.
    """
    try:
        # Laplacian response; noise shows up as high-frequency residue.
        lap = (
            -4 * array[1:-1, 1:-1]
            + array[:-2, 1:-1]
            + array[2:, 1:-1]
            + array[1:-1, :-2]
            + array[1:-1, 2:]
        )
        # Use the lower quartile so edges and detail do not dominate.
        threshold = np.percentile(np.abs(lap), 25)
        flat = np.abs(lap)[np.abs(lap) <= threshold]
        if flat.size == 0:
            return None
        return round(float(np.var(flat)), 5)
    except Exception:  # noqa: BLE001
        return None


def colour_stats(image: ValidatedImage, array: np.ndarray) -> dict[str, float] | None:
    try:
        with Image.open(io.BytesIO(image.data)) as opened:
            rgb = np.asarray(opened.convert("RGB"), dtype=np.float64)
            if max(rgb.shape[:2]) > 512:
                small = Image.fromarray(rgb.astype("uint8")).resize((256, 256))
                rgb = np.asarray(small, dtype=np.float64)
        return {
            "channel_std_mean": round(float(rgb.reshape(-1, rgb.shape[-1]).std(axis=0).mean()), 4),
            "saturated_fraction": round(
                float(((rgb > 250).any(axis=-1) | (rgb < 5).any(axis=-1)).mean()), 5
            ),
            "unique_colours_estimate": round(float(len(np.unique(rgb.astype("uint8")))), 2),
        }
    except Exception:  # noqa: BLE001
        return None


def analyze(image: ValidatedImage) -> ForensicReport:
    """Compute every forensic signal. Returns None-valued signals too, so
    the API response shows what was and was not measurable."""
    report = ForensicReport(excluded=list(_EXCLUDED))

    array = _to_gray_array(image)
    high_fraction, slope = frequency_stats(array)
    noise = noise_floor(array)

    blockiness = compression_anomaly(image)

    report.signals = [
        ForensicSignal(
            name="compression_anomaly",
            value=blockiness,
            meaning=(
                "8x8 block structure from JPEG quantisation. Non-JPEG "
                "formats return null."
            ),
            does_not_mean=(
                "Does not indicate synthetic origin. Both camera JPEGs "
                "and JPEG-exported synthetic images show strong block "
                "structure."
            ),
        ),
        ForensicSignal(
            name="high_frequency_energy",
            value=high_fraction,
            meaning="Share of spectral energy above the Nyquist half.",
            does_not_mean=(
                "Does not distinguish synthetic from real on its own. Any "
                "sharply focused photograph also carries high-frequency "
                "energy."
            ),
        ),
        ForensicSignal(
            name="noise_floor",
            value=noise,
            meaning=(
                "Variance in locally flat regions. Lower means a smoother, "
                "more processed image."
            ),
            does_not_mean=(
                "Low noise is not proof of synthesis: denoising, upscaling "
                "and messaging-app compression all reduce it."
            ),
        ),
        ForensicSignal(
            name="spectral_slope",
            value=slope,
            meaning="Rate of energy decay across the radial frequency profile.",
            does_not_mean=(
                "A summary of processing history, not authorship. It cannot "
                "identify a generator."
            ),
        ),
    ]

    return report
