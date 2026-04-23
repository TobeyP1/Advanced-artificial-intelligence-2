from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
from django.conf import settings
from PIL import Image

from .policies import build_explanation, derive_grade


class QualityModelNotReady(Exception):
    """Raised when the ML model has not been trained or is missing."""


def _configured_model_dir() -> Path | None:
    configured = getattr(settings, "FRESHNESS_MODEL_DIR", "")
    if not configured:
        return None
    return Path(configured).expanduser().resolve()


def _fallback_model_dir() -> Path:
    return Path(getattr(settings, "BASE_DIR")) / "freshness_model"


def _model_dir() -> Path:
    configured = _configured_model_dir()
    if configured:
        return configured
    return _fallback_model_dir()


def _model_path() -> Path:
    return _model_dir() / "freshness_model.joblib"


def _metadata_path() -> Path:
    return _model_dir() / "freshness_model_metadata.json"


@lru_cache(maxsize=1)
def load_model():
    model_path = _model_path()
    if not model_path.exists():
        raise QualityModelNotReady(
            f"Model not found at {model_path}. Set FRESHNESS_MODEL_DIR in settings.py to the folder that contains freshness_model.joblib."
        )
    return joblib.load(model_path)


@lru_cache(maxsize=1)
def load_metadata() -> dict:
    metadata_path = _metadata_path()
    if not metadata_path.exists():
        return {
            "class_names": ["Rotten", "Fresh"],
            "image_size": [224, 224],
        }

    return json.loads(metadata_path.read_text(encoding="utf-8"))


def _prepare_array(image: Image.Image, target_size: tuple[int, int]) -> np.ndarray:
    image = image.convert("RGB").resize(target_size)
    array = np.asarray(image, dtype=np.float32) / 255.0
    return array.flatten().reshape(1, -1)


def predict_quality(*, image_file, product_type: str | None = None) -> dict:
    metadata = load_metadata()
    model = load_model()
    target_size = tuple(metadata.get("image_size", [224, 224]))

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
