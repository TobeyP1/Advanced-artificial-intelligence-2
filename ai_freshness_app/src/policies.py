"""Quality policy rules for grading, actions, and textual explanations."""

from __future__ import annotations

GRADE_A_MIN_CONFIDENCE = 0.9
GRADE_B_MIN_CONFIDENCE = 0.7


def derive_grade(freshness: str, confidence: float) -> str:
    if freshness == "Rotten":
        return "C"
    if confidence >= GRADE_A_MIN_CONFIDENCE:
        return "A"
    if confidence >= GRADE_B_MIN_CONFIDENCE:
        return "B"
    return "C"


def derive_suggested_action(quality_status: str, grade: str) -> str:
    if quality_status == "ROTTEN" or grade == "C":
        return "Remove"
    if grade == "B":
        return "Discount"
    return "Sell"


def build_explanation(freshness: str, confidence: float, grade: str, product_type: str | None = None) -> str:
    product_context = f" ({product_type})" if product_type else ""
    if freshness == "Fresh" and confidence >= 0.9:
        return f"Predicted Fresh with high confidence ({confidence:.2f}){product_context}; assigned grade {grade}."
    if freshness == "Fresh":
        return f"Predicted Fresh with moderate confidence ({confidence:.2f}){product_context}; assigned grade {grade}."
    return f"Predicted Rotten with confidence ({confidence:.2f}){product_context}; assigned grade {grade} for caution."
