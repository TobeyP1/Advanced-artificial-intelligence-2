# ai_freshness_app

Standalone mini web app for fruit/vegetable freshness prediction.

This app is extracted from the DESD AI component and runs independently using Flask.

## Features
- Image upload with safe validation
- Fresh/Rotten prediction
- Confidence score
- Grade A/B/C
- Suggested action (Sell/Discount/Remove)
- Human-readable explanation

## Project structure
- `app.py` - Flask app entrypoint
- `templates/` - HTML templates
- `static/css/` - Basic styling
- `model/` - Trained model artifacts
- `src/` - AI inference and grading logic
- `requirements.txt` - Python dependencies

## Quick start
1. Open terminal in `ai_freshness_app`.
2. Create and activate a virtual environment.
3. Install dependencies:
   - `pip install -r requirements.txt`
4. Run app:
   - `python app.py`
5. Open:
   - `http://127.0.0.1:5000/`

## Notes for markers
- No DESD database, Django auth, or marketplace dependencies are required.
- AI logic is isolated in `src/inference.py` and `src/policies.py`.
- Model files expected in `model/freshness_model.joblib` and `model/freshness_model_metadata.json`.
- Invalid uploads are handled with:
  - extension checks
  - image decoding checks
  - max upload size limit (5 MB)

## Troubleshooting
- If model file is missing, place the two model files in `model/`.
- If package install fails, use Python 3.10+ and retry dependency install.
