"""Train a Fresh/Rotten classifier from an image dataset folder.

Expected dataset organization: any nested folders are allowed as long as the
path for each image includes a label keyword.

Fresh labels (mapped to "Fresh"):
- healthy
- fresh

Rotten labels (mapped to "Rotten"):
- rotten
- spoil(ed)
- bad
- diseas(ed/e)

Example usage:
python train_model.py --dataset-dir "C:/data/fruit-and-vegetable-disease-healthy-vs-rotten"
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
from PIL import Image, ImageOps
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
FRESH_KEYWORDS = ("healthy", "fresh")
ROTTEN_KEYWORDS = ("rotten", "spoiled", "spoilt", "bad", "diseased")


@dataclass
class Example:
    path: Path
    label: int  # 0 = Rotten, 1 = Fresh
    product_type: str


def _infer_label(path: Path, dataset_root: Path) -> int | None:
    rel = path.relative_to(dataset_root)
    searchable = [part.lower() for part in rel.parts]
    searchable.append(path.stem.lower())

    has_fresh = any(any(word in token for word in FRESH_KEYWORDS) for token in searchable)
    has_rotten = any(any(word in token for word in ROTTEN_KEYWORDS) for token in searchable)

    if has_rotten:
        return 0
    if has_fresh:
        return 1
    return None


def _infer_product_type(path: Path, dataset_root: Path) -> str:
    rel = path.relative_to(dataset_root)
    tokens = [part for part in rel.parts[:-1] if part]
    for token in tokens:
        lower = token.lower()
        if any(k in lower for k in FRESH_KEYWORDS + ROTTEN_KEYWORDS):
            continue
        clean = token.replace("_", " ").replace("-", " ").strip()
        if clean:
            return clean.title()
    return "Unknown"


def _collect_examples(dataset_root: Path) -> tuple[list[Example], int]:
    examples: list[Example] = []
    skipped = 0

    for path in dataset_root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue

        label = _infer_label(path, dataset_root)
        if label is None:
            skipped += 1
            continue

        product_type = _infer_product_type(path, dataset_root)
        examples.append(Example(path=path, label=label, product_type=product_type))

    return examples, skipped


def _prepare_image(path: Path, image_size: tuple[int, int]) -> np.ndarray:
    with Image.open(path) as image:
        image = ImageOps.exif_transpose(image).convert("RGB").resize(image_size)
        arr = np.asarray(image, dtype=np.float32) / 255.0
    return arr.flatten()


def _build_dataset(examples: list[Example], image_size: tuple[int, int]) -> tuple[np.ndarray, np.ndarray]:
    features = np.asarray([_prepare_image(ex.path, image_size) for ex in examples], dtype=np.float32)
    labels = np.asarray([ex.label for ex in examples], dtype=np.int32)
    return features, labels


def train(dataset_dir: Path, output_dir: Path, image_size: tuple[int, int], test_size: float, random_state: int) -> dict:
    examples, skipped = _collect_examples(dataset_dir)
    if len(examples) < 20:
        raise ValueError(
            f"Not enough labeled images found in {dataset_dir}. Found {len(examples)} labeled files; at least 20 are required."
        )

    X, y = _build_dataset(examples, image_size)
    class_counts = {
        "Rotten": int(np.sum(y == 0)),
        "Fresh": int(np.sum(y == 1)),
    }
    if class_counts["Rotten"] == 0 or class_counts["Fresh"] == 0:
        raise ValueError(
            "Dataset labeling produced a single class. "
            f"Counts: {class_counts}. Check folder naming for healthy/fresh and rotten labels."
        )

    X_train, X_val, y_train, y_val = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=random_state,
        stratify=y,
    )

    model_rf = RandomForestClassifier(
        n_estimators=300,
        random_state=random_state,
        class_weight="balanced",
        n_jobs=-1,
    )
    model_rf.fit(X_train, y_train)
    rf_acc = float(accuracy_score(y_val, model_rf.predict(X_val)))

    model_lr = LogisticRegression(max_iter=1000)
    model_lr.fit(X_train, y_train)
    lr_acc = float(accuracy_score(y_val, model_lr.predict(X_val)))

    if rf_acc >= lr_acc:
        best_model = model_rf
        best_name = "random_forest"
        best_acc = rf_acc
    else:
        best_model = model_lr
        best_name = "logistic_regression"
        best_acc = lr_acc

    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = output_dir / "freshness_model.joblib"
    metadata_path = output_dir / "freshness_model_metadata.json"

    joblib.dump(best_model, model_path)

    metadata = {
        "model_name": model_path.name,
        "backend": "sklearn",
        "best_model_type": best_name,
        "class_names": ["Rotten", "Fresh"],
        "image_size": [image_size[0], image_size[1]],
        "val_accuracy": best_acc,
        "samples": {
            "train": int(len(X_train)),
            "validation": int(len(X_val)),
            "total_labeled": int(len(examples)),
            "skipped_unlabeled": int(skipped),
            "class_counts": class_counts,
        },
        "model_comparison_accuracy": {
            "random_forest": rf_acc,
            "logistic_regression": lr_acc,
        },
        "unique_product_types": sorted({ex.product_type for ex in examples}),
        "source_dataset_dir": str(dataset_dir.resolve()),
    }

    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


def download_dataset_via_kagglehub(dataset_ref: str) -> Path:
    try:
        import kagglehub
    except ImportError as exc:
        raise RuntimeError(
            "kagglehub is not installed. Install it with: pip install kagglehub"
        ) from exc

    dataset_path = kagglehub.dataset_download(dataset_ref)
    return Path(dataset_path).expanduser().resolve()


def main() -> None:
    parser = argparse.ArgumentParser(description="Train Fresh vs Rotten model from a dataset directory.")
    parser.add_argument("--dataset-dir", type=Path, help="Root folder of the dataset.")
    parser.add_argument(
        "--use-kagglehub",
        action="store_true",
        help="Download dataset with kagglehub when --dataset-dir is not provided.",
    )
    parser.add_argument(
        "--kaggle-dataset",
        default="muhammad0subhan/fruit-and-vegetable-disease-healthy-vs-rotten",
        help="Kaggle dataset reference used with --use-kagglehub.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "model",
        help="Directory to write freshness_model.joblib and metadata JSON.",
    )
    parser.add_argument("--image-size", type=int, default=32, help="Image width/height used for model input.")
    parser.add_argument("--test-size", type=float, default=0.2, help="Validation split size.")
    parser.add_argument("--random-state", type=int, default=42, help="Random seed for reproducibility.")
    args = parser.parse_args()

    if args.dataset_dir:
        dataset_dir = args.dataset_dir.expanduser().resolve()
    elif args.use_kagglehub:
        dataset_dir = download_dataset_via_kagglehub(args.kaggle_dataset)
        print(f"Dataset downloaded to: {dataset_dir}")
    else:
        raise ValueError("Provide --dataset-dir or use --use-kagglehub.")

    if not dataset_dir.exists() or not dataset_dir.is_dir():
        raise ValueError(f"Dataset directory does not exist: {dataset_dir}")

    metadata = train(
        dataset_dir=dataset_dir,
        output_dir=args.output_dir.expanduser().resolve(),
        image_size=(args.image_size, args.image_size),
        test_size=args.test_size,
        random_state=args.random_state,
    )

    print("Training complete.")
    print(f"Best model: {metadata['best_model_type']}")
    print(f"Validation accuracy: {metadata['val_accuracy']:.4f}")
    print(f"Labeled samples: {metadata['samples']['total_labeled']}")
    print(f"Skipped samples (unlabeled path): {metadata['samples']['skipped_unlabeled']}")


if __name__ == "__main__":
    main()
