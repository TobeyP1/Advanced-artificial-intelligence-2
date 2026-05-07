"""Inference service for produce freshness detection."""

from __future__ import annotations

import base64
import io
import json
import os
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
from PIL import Image, ImageDraw, ImageOps

from .policies import build_explanation, derive_grade

MODEL_DIR = Path(__file__).resolve().parent.parent / "model"
MODEL_PATH = MODEL_DIR / "freshness_model.joblib"
METADATA_PATH = MODEL_DIR / "freshness_model_metadata.json"
FRESHNESS_FRESH_THRESHOLD = float(os.getenv("FRESHNESS_FRESH_THRESHOLD", "0.45"))


class QualityModelNotReady(Exception):
    """Raised when the ML model has not been trained or is missing."""


@lru_cache(maxsize=1)
def load_model():
    if not MODEL_PATH.exists():
        raise QualityModelNotReady(
            f"Model not found at {MODEL_PATH}. Place freshness_model.joblib in the model directory."
        )
    return joblib.load(MODEL_PATH)


@lru_cache(maxsize=1)
def load_metadata() -> dict:
    if not METADATA_PATH.exists():
        return {
            "class_names": ["Rotten", "Fresh"],
            "image_size": [224, 224],
        }

    return json.loads(METADATA_PATH.read_text(encoding="utf-8"))


def _prepare_array(image: Image.Image, target_size: tuple[int, int]) -> np.ndarray:
    image = image.convert("RGB").resize(target_size)
    array = np.asarray(image, dtype=np.float32) / 255.0
    return array.flatten().reshape(1, -1)


def _resolve_fresh_class_value(model, metadata: dict):
    classes = list(getattr(model, "classes_", []))
    if not classes:
        return 1

    class_names = metadata.get("class_names", [])
    if isinstance(class_names, list) and len(class_names) == len(classes):
        for idx, label in enumerate(class_names):
            if str(label).strip().lower() == "fresh":
                return classes[idx]

    for candidate in (1, "1", True):
        if candidate in classes:
            return candidate

    return classes[-1]


def _predict_fresh_probability(model, batch: np.ndarray, metadata: dict) -> float:
    if hasattr(model, "predict_proba"):
        classes = list(getattr(model, "classes_", []))
        fresh_class = _resolve_fresh_class_value(model, metadata)
        class_index = classes.index(fresh_class) if fresh_class in classes else len(classes) - 1
        return float(model.predict_proba(batch)[0][class_index])

    raw_prediction = model.predict(batch)[0]
    fresh_class = _resolve_fresh_class_value(model, metadata)
    return 1.0 if raw_prediction == fresh_class else 0.0


def _extract_defect_mask(image: Image.Image) -> np.ndarray:
    hsv = np.asarray(image.convert("HSV"), dtype=np.uint8)
    h = hsv[:, :, 0].astype(np.int16)
    s = hsv[:, :, 1].astype(np.int16)
    v = hsv[:, :, 2].astype(np.int16)

    dark_spot_mask = (v < 90) & (s > 30)
    brownish_mask = (h >= 6) & (h <= 26) & (s >= 70) & (v <= 180)
    candidate = dark_spot_mask | brownish_mask

    # Remove isolated pixels so the mask focuses on coherent defect regions.
    neighborhood = candidate.copy()
    for y_shift in (-1, 0, 1):
        for x_shift in (-1, 0, 1):
            if y_shift == 0 and x_shift == 0:
                continue
            neighborhood = neighborhood + np.roll(np.roll(candidate, y_shift, axis=0), x_shift, axis=1)

    return neighborhood >= 3


def _extract_bounding_boxes(mask: np.ndarray, max_boxes: int = 3, min_area: int = 120) -> list[tuple[int, int, int, int]]:
    height, width = mask.shape
    visited = np.zeros_like(mask, dtype=bool)
    boxes: list[tuple[int, int, int, int, int]] = []

    for y in range(height):
        for x in range(width):
            if not mask[y, x] or visited[y, x]:
                continue

            stack = [(y, x)]
            visited[y, x] = True
            min_y = max_y = y
            min_x = max_x = x
            area = 0

            while stack:
                cy, cx = stack.pop()
                area += 1
                if cy < min_y:
                    min_y = cy
                if cy > max_y:
                    max_y = cy
                if cx < min_x:
                    min_x = cx
                if cx > max_x:
                    max_x = cx

                for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                    if 0 <= ny < height and 0 <= nx < width and mask[ny, nx] and not visited[ny, nx]:
                        visited[ny, nx] = True
                        stack.append((ny, nx))

            if area >= min_area:
                boxes.append((area, min_x, min_y, max_x, max_y))

    boxes.sort(key=lambda item: item[0], reverse=True)
    return [(left, top, right, bottom) for _, left, top, right, bottom in boxes[:max_boxes]]


def _derive_defect_severity(defect_area_ratio: float) -> str:
    if defect_area_ratio >= 0.18:
        return "High"
    if defect_area_ratio >= 0.08:
        return "Medium"
    return "Low"


def _build_overlay_base64(image: Image.Image, mask: np.ndarray, boxes: list[tuple[int, int, int, int]]) -> str:
    preview = image.convert("RGB").resize((320, 320))
    preview_rgba = preview.convert("RGBA")

    mask_image = Image.fromarray((mask.astype(np.uint8) * 115), mode="L").resize(preview.size, Image.NEAREST)
    red_layer = Image.new("RGBA", preview.size, (220, 55, 55, 0))
    red_layer.putalpha(mask_image)
    composite = Image.alpha_composite(preview_rgba, red_layer)

    draw = ImageDraw.Draw(composite)
    scale_x = preview.width / float(mask.shape[1])
    scale_y = preview.height / float(mask.shape[0])
    for left, top, right, bottom in boxes:
        draw.rectangle(
            [
                left * scale_x,
                top * scale_y,
                (right + 1) * scale_x,
                (bottom + 1) * scale_y,
            ],
            outline=(255, 232, 84, 255),
            width=3,
        )

    buffer = io.BytesIO()
    composite.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def predict_quality(*, image_path: str | None = None, image_file=None, product_type: str | None = None) -> dict:
    if not image_path and image_file is None:
        raise ValueError("Either image_path or image_file must be provided.")

    metadata = load_metadata()
    model = load_model()
    target_size = tuple(metadata.get("image_size", [224, 224]))
    fresh_threshold = float(metadata.get("fresh_probability_threshold", FRESHNESS_FRESH_THRESHOLD))

    if image_path:
        image = Image.open(image_path)
    else:
        image_file.seek(0)
        image = Image.open(image_file)

    image = ImageOps.exif_transpose(image).convert("RGB")

    batch = _prepare_array(image, target_size)

    probability_fresh = _predict_fresh_probability(model, batch, metadata)

    if probability_fresh >= fresh_threshold:
        freshness = "Fresh"
        confidence = probability_fresh
        quality_status = "FRESH"
    else:
        freshness = "Rotten"
        confidence = 1.0 - probability_fresh
        quality_status = "ROTTEN"

    analysis_image = image.resize((224, 224))
    defect_mask = _extract_defect_mask(analysis_image)
    defect_boxes = _extract_bounding_boxes(defect_mask)
    defect_area_ratio = float(np.mean(defect_mask))
    defect_severity = _derive_defect_severity(defect_area_ratio)

    grade = derive_grade(freshness=freshness, confidence=confidence, defect_area_ratio=defect_area_ratio)
    explanation = build_explanation(
        freshness=freshness,
        confidence=confidence,
        grade=grade,
        product_type=product_type,
        defect_area_ratio=defect_area_ratio,
        defect_severity=defect_severity,
    )
    defect_boxes_payload = [
        {"left": left, "top": top, "right": right, "bottom": bottom}
        for left, top, right, bottom in defect_boxes
    ]
    defect_overlay_base64 = _build_overlay_base64(analysis_image, defect_mask, defect_boxes)

    return {
        "freshness": freshness,
        "confidence": round(confidence, 4),
        "grade": grade,
        "quality_status": quality_status,
        "explanation": explanation,
        "product_type": product_type,
        "defect_area_ratio": round(defect_area_ratio, 4),
        "defect_severity": defect_severity,
        "defect_boxes": defect_boxes_payload,
        "defect_overlay_base64": defect_overlay_base64,
    }
