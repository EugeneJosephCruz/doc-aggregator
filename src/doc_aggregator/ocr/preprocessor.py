"""Image preprocessing for OCR."""

from __future__ import annotations

import cv2
import numpy as np


def preprocess_for_ocr(image: np.ndarray) -> np.ndarray:
    """Apply grayscale, denoise, and deskew transforms."""
    if image is None or image.size == 0:
        raise ValueError("Invalid image for OCR preprocessing")

    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    denoised = cv2.fastNlMeansDenoising(gray)
    _, binary = cv2.threshold(
        denoised, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU
    )

    angle = _estimate_skew_angle(binary)
    if abs(angle) > 0.1:
        denoised = _rotate_image(denoised, angle)
    return denoised


def _estimate_skew_angle(binary: np.ndarray) -> float:
    coords = np.column_stack(np.where(binary > 0))
    if coords.shape[0] < 100:
        return 0.0

    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    # Hard safety cap to avoid aggressive accidental rotations.
    return float(max(min(angle, 15.0), -15.0))


def _rotate_image(image: np.ndarray, angle: float) -> np.ndarray:
    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(
        image,
        matrix,
        (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )
