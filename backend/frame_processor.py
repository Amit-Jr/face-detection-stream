"""
frame_processor.py — Draw axis-aligned ROI bounding box using Pillow ONLY.
No OpenCV used anywhere in this module.
"""

from __future__ import annotations

import io
import base64
import logging
from typing import Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

from face_detector import DetectionResult

logger = logging.getLogger(__name__)

# Box visual config
BOX_COLOR = (255, 50, 50)       # Red
BOX_WIDTH = 3                   # px
LABEL_COLOR = (255, 255, 255)   # White text
LABEL_BG = (255, 50, 50)        # Red label background
FONT_SIZE = 14


def draw_roi(
    pil_image: Image.Image,
    detection: Optional[DetectionResult],
) -> Tuple[Image.Image, bool]:
    """
    Draw an axis-aligned minimal bounding box on *pil_image* in-place.

    Parameters
    ----------
    pil_image  : source PIL Image (will be modified)
    detection  : DetectionResult from face_detector, or None

    Returns
    -------
    (annotated_image, face_found)
    """
    draw = ImageDraw.Draw(pil_image)
    face_found = detection is not None

    if face_found:
        # Draw bounding rectangle — Pillow rectangle = axis-aligned bounding box ✓
        draw.rectangle(
            [detection.x1, detection.y1, detection.x2, detection.y2],
            outline=BOX_COLOR,
            width=BOX_WIDTH,
        )

        # Confidence label
        label = f"Face {detection.confidence:.0%}"
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", FONT_SIZE)
        except OSError:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), label, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        label_x = detection.x1
        label_y = max(0, detection.y1 - text_h - 6)

        draw.rectangle(
            [label_x, label_y, label_x + text_w + 6, label_y + text_h + 6],
            fill=LABEL_BG,
        )
        draw.text((label_x + 3, label_y + 3), label, fill=LABEL_COLOR, font=font)
    else:
        # Overlay "No Face" text so the frontend knows detection ran
        draw.text((10, 10), "No face detected", fill=(200, 200, 200))

    return pil_image, face_found


def pil_to_jpeg_bytes(pil_image: Image.Image, quality: int = 80) -> bytes:
    """Encode PIL Image → JPEG bytes (no OpenCV)."""
    buf = io.BytesIO()
    pil_image.save(buf, format="JPEG", quality=quality, optimize=True)
    return buf.getvalue()


def pil_to_base64_jpeg(pil_image: Image.Image, quality: int = 80) -> str:
    """Encode PIL Image → base64 JPEG string for WebSocket transport."""
    return base64.b64encode(pil_to_jpeg_bytes(pil_image, quality)).decode()


def bytes_to_pil(raw: bytes) -> Image.Image:
    """Decode raw image bytes (JPEG/PNG) → PIL Image."""
    return Image.open(io.BytesIO(raw)).convert("RGB")
