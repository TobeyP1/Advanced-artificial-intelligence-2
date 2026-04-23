from __future__ import annotations

from http import HTTPStatus

from django.conf import settings
from django.contrib import messages
from django.shortcuts import render
from PIL import UnidentifiedImageError

from .forms import FreshnessUploadForm
from .services.inference import QualityModelNotReady, predict_quality
from .services.policies import derive_suggested_action


def freshness_index(request):
    result = None
    form = FreshnessUploadForm()

    if request.method == "POST":
        form = FreshnessUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded = form.cleaned_data["image"]
            product_type = form.cleaned_data.get("product_type", "").strip()

            max_upload_mb = getattr(settings, "FRESHNESS_MAX_UPLOAD_MB", 5)
            if uploaded.size > max_upload_mb * 1024 * 1024:
                messages.error(request, f"Upload rejected: file exceeds {max_upload_mb} MB.")
                return render(request, "marketplace_freshness/index.html", {"form": FreshnessUploadForm(), "result": None}, status=HTTPStatus.REQUEST_ENTITY_TOO_LARGE)

            try:
                prediction = predict_quality(image_file=uploaded.file, product_type=product_type or None)
                result = {
                    "freshness": prediction["freshness"],
                    "confidence": prediction["confidence"],
                    "confidence_percent": prediction["confidence"] * 100,
                    "grade": prediction["grade"],
                    "suggested_action": derive_suggested_action(
                        quality_status=prediction["quality_status"],
                        grade=prediction["grade"],
                    ),
                    "explanation": prediction["explanation"],
                    "product_type": prediction.get("product_type") or "-",
                }
            except QualityModelNotReady as exc:
                messages.error(request, str(exc))
                return render(request, "marketplace_freshness/index.html", {"form": FreshnessUploadForm(), "result": None}, status=HTTPStatus.SERVICE_UNAVAILABLE)
            except UnidentifiedImageError:
                messages.error(request, "Uploaded file is not a valid image.")
                return render(request, "marketplace_freshness/index.html", {"form": FreshnessUploadForm(), "result": None}, status=HTTPStatus.BAD_REQUEST)
            except Exception:
                messages.error(request, "Image processing failed. Please upload a clear fruit/vegetable image.")
                return render(request, "marketplace_freshness/index.html", {"form": FreshnessUploadForm(), "result": None}, status=HTTPStatus.BAD_REQUEST)
        else:
            for error in form.non_field_errors():
                messages.error(request, error)
            for field_errors in form.errors.values():
                for error in field_errors:
                    messages.error(request, error)
            return render(request, "marketplace_freshness/index.html", {"form": FreshnessUploadForm(), "result": None}, status=HTTPStatus.BAD_REQUEST)

    return render(request, "marketplace_freshness/index.html", {"form": form, "result": result})
