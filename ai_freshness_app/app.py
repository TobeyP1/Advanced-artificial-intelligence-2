from __future__ import annotations

from http import HTTPStatus

from flask import Flask, flash, render_template, request
from PIL import UnidentifiedImageError
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

from src.inference import QualityModelNotReady, predict_quality
from src.policies import derive_suggested_action

# Allowed file types for upload safety.
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "bmp"}
# Keep uploads small so the app stays responsive and safer to run.
MAX_UPLOAD_MB = 5

app = Flask(__name__)
# Needed for flash messages shown in the template.
app.config["SECRET_KEY"] = "dev-freshness-key-change-in-production"
# Flask will reject any file bigger than this size.
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024


def _is_allowed_filename(filename: str) -> bool:
    # Quick extension check before we try to open/process the file.
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS


@app.errorhandler(RequestEntityTooLarge)
def file_too_large(_error):
    # Friendly message when file size exceeds MAX_CONTENT_LENGTH.
    flash(f"Upload rejected: file exceeds {MAX_UPLOAD_MB} MB.", "error")
    return render_template("index.html", result=None), HTTPStatus.REQUEST_ENTITY_TOO_LARGE


@app.route("/", methods=["GET", "POST"])
def index():
    # Nothing to show at first load; result is filled after successful prediction.
    result = None

    if request.method == "POST":
        # Read uploaded image and optional product type from the form.
        uploaded = request.files.get("image")
        product_type = request.form.get("product_type", "").strip()

        # Validate that a file was actually selected.
        if uploaded is None or not uploaded.filename:
            flash("Please choose an image to upload.", "error")
            return render_template("index.html", result=None), HTTPStatus.BAD_REQUEST

        # Sanitize name and allow only expected image extensions.
        filename = secure_filename(uploaded.filename)
        if not filename or not _is_allowed_filename(filename):
            flash("Invalid file type. Use PNG, JPG, JPEG, WEBP, or BMP.", "error")
            return render_template("index.html", result=None), HTTPStatus.BAD_REQUEST

        try:
            # Run model inference from in-memory file stream (no DB/filesystem dependency).
            prediction = predict_quality(image_file=uploaded.stream, product_type=product_type or None)

            # Build display values for the result panel.
            result = {
                "freshness": prediction["freshness"],
                "confidence": prediction["confidence"],
                "grade": prediction["grade"],
                "suggested_action": derive_suggested_action(
                    quality_status=prediction["quality_status"],
                    grade=prediction["grade"],
                ),
                "explanation": prediction["explanation"],
                "product_type": prediction.get("product_type") or "-",
            }
        except QualityModelNotReady as exc:
            # Model file missing/corrupt or otherwise unavailable.
            flash(str(exc), "error")
            return render_template("index.html", result=None), HTTPStatus.SERVICE_UNAVAILABLE
        except UnidentifiedImageError:
            # Pillow could not decode file as an image.
            flash("Uploaded file is not a valid image.", "error")
            return render_template("index.html", result=None), HTTPStatus.BAD_REQUEST
        except Exception:
            # Generic safety net for unexpected processing failures.
            flash("Image processing failed. Please upload a clear fruit/vegetable image.", "error")
            return render_template("index.html", result=None), HTTPStatus.BAD_REQUEST

    return render_template("index.html", result=result)


if __name__ == "__main__":
    # Local development server entrypoint.
    app.run(debug=True)
