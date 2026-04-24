"""Inference service for produce freshness detection."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
from PIL import Image

from .policies import build_explanation, derive_grade

MODEL_DIR = Path(__file__).resolve().parent.parent / "model"
MODEL_PATH = MODEL_DIR / "freshness_model.joblib"
METADATA_PATH = MODEL_DIR / "freshness_model_metadata.json"


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


def predict_quality(*, image_path: str | None = None, image_file=None, product_type: str | None = None) -> dict:
    if not image_path and image_file is None:
        raise ValueError("Either image_path or image_file must be provided.")

    metadata = load_metadata()
    model = load_model()
    target_size = tuple(metadata.get("image_size", [224, 224]))

    if image_path:
        image = Image.open(image_path)
    else:
        image_file.seek(0)
        image = Image.open(image_file)

    batch = _prepare_array(image, target_size)

    if hasattr(model, "predict_proba"):
        class_index = list(model.classes_).index(1)
        probability_fresh = float(model.predict_proba(batch)[0][class_index])
    else:
        raw_prediction = int(model.predict(batch)[0])
        probability_fresh = 1.0 if raw_prediction == 1 else 0.0

    if probability_fresh >= 0.5:
        freshness = "Fresh"
        confidence = probability_fresh
        quality_status = "FRESH"
    else:
        freshness = "Rotten"
        confidence = 1.0 - probability_fresh
        quality_status = "ROTTEN"

    grade = derive_grade(freshness=freshness, confidence=confidence)
    explanation = build_explanation(
        freshness=freshness,
        confidence=confidence,
        grade=grade,
        product_type=product_type,
    )

    return {
        "freshness": freshness,
        "confidence": round(confidence, 4),
        "grade": grade,
        "quality_status": quality_status,
        "explanation": explanation,
        "product_type": product_type,
    }
