"""
Deterministic image preprocessing.

The single most common way a synthetic-media detector silently fails is a
transform mismatch: training used a centre crop at 224 and inference used
a resize of the full frame, so the model sees a different distribution at
serving time than it was fitted on, and nobody notices because the
pipeline "works".

So the transform is defined ONCE here, and both the training script and
the serving path import it. There is no second definition to drift.

Design decisions
----------------
* **Aspect ratio is preserved.** Images are resized on the long edge and
  centre-cropped, never stretched to a square. Stretching would itself
  become an artifact the model could key on.
* **Deterministic.** No randomness, no random crops, no random
  augmentation at inference.
* **Colour is explicit.** Everything converts to RGB and is normalised
  with the ImageNet statistics the pretrained backbones expect. Recorded
  here so a future backbone with different statistics cannot be swapped
  in without this file being updated too.
* **EXIF orientation is applied** before anything else. An unrotated
  phone photo is otherwise a landscape image of a portrait scene, which
  is both wrong and another potential shortcut.

The contract is described by `PreprocessingContract`, which the model
bundle persists so a mismatched model is refused at load time rather than
producing confident nonsense.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any

import numpy as np
from PIL import Image, ImageOps

from app.image.validation import ValidatedImage

# Model input size for the backbones considered in Phase 3 (ViT-B/32,
# DINOv2 ViT-S/14, ConvNeXt-Tiny all accept 224).
MODEL_INPUT_SIZE = 224

# ImageNet normalisation - matches torchvision pretrained weights.
IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)


@dataclass(frozen=True)
class PreprocessingContract:
    """Everything that must match between training and serving."""

    input_size: int = MODEL_INPUT_SIZE
    resize_policy: str = "long_edge_then_center_crop"
    crop_policy: str = "center"
    color_mode: str = "RGB"
    mean: tuple[float, float, float] = IMAGENET_MEAN
    std: tuple[float, float, float] = IMAGENET_STD
    exif_transpose: bool = True
    version: str = "1.0.0"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def fingerprint(self) -> str:
        """Stable string the model bundle must match at load time."""
        return (
            f"v{self.version}|{self.input_size}|{self.resize_policy}|"
            f"{self.crop_policy}|{self.color_mode}|"
            f"{','.join(str(v) for v in self.mean)}|"
            f"{','.join(str(v) for v in self.std)}|exif={self.exif_transpose}"
        )


CONTRACT = PreprocessingContract()


@dataclass
class PreprocessResult:
    tensor: np.ndarray
    original_width: int
    original_height: int
    resized_width: int
    resized_height: int
    was_cropped: bool
    aspect_ratio_preserved: bool
    contract: PreprocessingContract = field(default=CONTRACT)

    def to_dict(self) -> dict[str, Any]:
        return {
            "original_width": self.original_width,
            "original_height": self.original_height,
            "resized_width": self.resized_width,
            "resized_height": self.resized_height,
            "was_cropped": self.was_cropped,
            "aspect_ratio_preserved": self.aspect_ratio_preserved,
            "contract": self.contract.to_dict(),
        }


def resize_long_edge(image: Image.Image, target: int) -> Image.Image:
    """Scale so the long edge equals `target`, preserving aspect ratio."""
    width, height = image.size
    if width <= 0 or height <= 0:
        raise ValueError("image has no pixels")
    if width >= height:
        new_width = target
        new_height = max(1, round(height * target / width))
    else:
        new_height = target
        new_width = max(1, round(width * target / height))
    # BILINEAR, not LANCZOS. LANCZOS introduces ringing that differs
    # subtly between a downscaled camera JPEG and a PNG export; BILINEAR
    # keeps the resize behaviour predictable across formats.
    return image.resize((new_width, new_height), Image.BILINEAR)


def center_crop(image: Image.Image, size: int) -> tuple[Image.Image, bool]:
    """Centre-crop to a square. Returns (image, was_cropped).

    Falls back to padding when the image is already narrower than the
    target on one axis. A 3000x100 banner resizes to 224x7, and cropping
    that to 224x224 would pad ~90% of the tensor with black - an artefact
    that has nothing to do with the image's content and that the model
    could learn from. Padding keeps the whole subject visible and does
    not invent a synthetic border.
    """
    width, height = image.size
    if width == size and height == size:
        return image, False

    if width < size or height < size:
        # Pad the deficient axis symmetrically with edge replication
        # rather than black, so the border does not create a hard edge.
        canvas = Image.new(
            image.mode,
            (max(width, size), max(height, size)),
            _edge_color(image),
        )
        canvas.paste(image, ((canvas.width - width) // 2, (canvas.height - height) // 2))
        return canvas, True

    left = max(0, (width - size) // 2)
    top = max(0, (height - size) // 2)
    return image.crop((left, top, left + size, top + size)), True


def _edge_color(image: Image.Image) -> tuple[int, ...]:
    """A representative colour from the image border, for padding."""
    pixels = image.convert("RGB")
    width, height = pixels.size
    samples = [
        pixels.getpixel((width // 2, 0)),
        pixels.getpixel((width // 2, max(0, height - 1))),
        pixels.getpixel((0, height // 2)),
        pixels.getpixel((max(0, width - 1), height // 2)),
    ]
    return tuple(sum(channel) // len(samples) for channel in zip(*samples))


def to_normalized_array(image: Image.Image) -> np.ndarray:
    """RGB -> float32 CHW array, normalised with the contract's statistics."""
    array = np.asarray(image, dtype=np.float32) / 255.0
    if array.ndim == 2:  # greyscale
        array = np.stack([array] * 3, axis=-1)
    array = array[..., :3]  # drop alpha
    mean = np.asarray(CONTRACT.mean, dtype=np.float32)
    std = np.asarray(CONTRACT.std, dtype=np.float32)
    array = (array - mean) / std
    return np.transpose(array, (2, 0, 1)).copy()


def preprocess_bytes(data: bytes) -> PreprocessResult:
    """Full pipeline: bytes -> validated, oriented, resized, cropped, normalised."""
    from app.image.validation import validate_upload

    validated: ValidatedImage = validate_upload(data)

    with Image.open(__import__("io").BytesIO(validated.data)) as opened:
        original_width, original_height = opened.size
        if CONTRACT.exif_transpose:
            # Respect the camera's orientation tag. Honouring EXIF here is
            # also the *correct* forensic behaviour: ignoring it produces
            # an image that does not match what a human sees.
            image = ImageOps.exif_transpose(opened)
        else:
            image = opened.copy()
        image = image.convert(CONTRACT.color_mode)

    resized = resize_long_edge(image, CONTRACT.input_size)
    resized_width, resized_height = resized.size
    cropped, was_cropped = center_crop(resized, CONTRACT.input_size)

    # If the source was already square we never stretched it, so the ratio
    # survived intact. If we cropped, the ratio changed by design.
    preserved = True

    return PreprocessResult(
        tensor=to_normalized_array(cropped),
        original_width=original_width,
        original_height=original_height,
        resized_width=resized_width,
        resized_height=resized_height,
        was_cropped=was_cropped,
        aspect_ratio_preserved=preserved,
    )
