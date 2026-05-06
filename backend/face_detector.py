"""
face_detector.py — Face detection via MediaPipe (NO OpenCV).

MediaPipe's FaceDetection model returns relative bounding boxes
(fractions of frame width/height).  This module converts them to
absolute pixel coordinates and returns a typed dataclass.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import mediapipe as mp
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# Initialise once at module load — thread-safe for reading
_mp_face_detection = mp.solutions.face_detection


@dataclass
class DetectionResult:
    x1: int
    y1: int
    x2: int
    y2: int
    confidence: float
    frame_width: int
    frame_height: int


def detect_face(pil_image: Image.Image) -> Optional[DetectionResult]:
    """
    Run MediaPipe short-range face detection on a PIL Image.

    Parameters
    ----------
    pil_image : PIL.Image.Image
        RGB image (any size).

    Returns
    -------
    DetectionResult | None
        Absolute pixel bounding box + confidence, or None if no face found.
    """
    w, h = pil_image.size
    # MediaPipe expects a uint8 RGB numpy array
    img_rgb = np.array(pil_image.convert("RGB"), dtype=np.uint8)

    try:
        with _mp_face_detection.FaceDetection(
            model_selection=0,          # 0 = short range (≤2 m), 1 = full range
            min_detection_confidence=0.5,
        ) as detector:
            results = detector.process(img_rgb)
    except Exception as exc:
        logger.error("MediaPipe inference error: %s", exc)
        return None

    if not results.detections:
        return None

    # Task specifies only one face — take the highest-confidence detection
    best = max(results.detections, key=lambda d: d.score[0])
    box = best.location_data.relative_bounding_box
    score = float(best.score[0])

    # Clamp to [0, 1] to guard against MediaPipe returning slightly OOB values
    xmin = max(0.0, box.xmin)
    ymin = max(0.0, box.ymin)
    xmax = min(1.0, box.xmin + box.width)
    ymax = min(1.0, box.ymin + box.height)

    return DetectionResult(
        x1=int(xmin * w),
        y1=int(ymin * h),
        x2=int(xmax * w),
        y2=int(ymax * h),
        confidence=score,
        frame_width=w,
        frame_height=h,
    )
