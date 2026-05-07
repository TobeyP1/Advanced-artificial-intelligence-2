"""Quality policy rules for grading, actions, and textual explanations."""

from __future__ import annotations

GRADE_A_MIN_CONFIDENCE = 0.9
GRADE_B_MIN_CONFIDENCE = 0.7


def _downgrade_grade_once(grade: str) -> str:
    if grade == "A":
        return "B"
    return "C"


def _derive_defect_severity(defect_area_ratio: float) -> str:
    if defect_area_ratio >= 0.18:
        return "High"
    if defect_area_ratio >= 0.08:
        return "Medium"
    return "Low"


def derive_grade(freshness: str, confidence: float, defect_area_ratio: float = 0.0) -> str:
    if freshness == "Rotten":
        return "C"

    if confidence >= GRADE_A_MIN_CONFIDENCE:
        base_grade = "A"
    elif confidence >= GRADE_B_MIN_CONFIDENCE:
        base_grade = "B"
    else:
        base_grade = "C"

    severity = _derive_defect_severity(defect_area_ratio)
    if severity == "High":
        return "C"
    if severity == "Medium":
        return _downgrade_grade_once(base_grade)
    return base_grade


def derive_suggested_action(quality_status: str, grade: str, defect_severity: str = "Low") -> str:
    if quality_status == "ROTTEN" or grade == "C":
        return "Remove"
    if defect_severity == "High":
        return "Remove"
    if defect_severity == "Medium":
        return "Discount"
    if grade == "B":
        return "Discount"
    return "Sell"


def build_explanation(
    freshness: str,
    confidence: float,
    grade: str,
    product_type: str | None = None,
    defect_area_ratio: float = 0.0,
    defect_severity: str = "Low",
) -> str:
    product_context = f" ({product_type})" if product_type else ""
    defect_summary = f" Defect estimate: {defect_severity} ({defect_area_ratio * 100:.1f}% area)."

    if freshness == "Fresh" and confidence >= 0.9:
        return (
            f"Predicted Fresh with high confidence ({confidence:.2f}){product_context}; "
            f"assigned grade {grade}.{defect_summary}"
        )
    if freshness == "Fresh":
        return (
            f"Predicted Fresh with moderate confidence ({confidence:.2f}){product_context}; "
            f"assigned grade {grade}.{defect_summary}"
        )
    return (
        f"Predicted Rotten with confidence ({confidence:.2f}){product_context}; "
        f"assigned grade {grade} for caution.{defect_summary}"
    )
