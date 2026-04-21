from __future__ import annotations

import argparse
import random
from collections import Counter, defaultdict
from pathlib import Path


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def read_classes(classes_path: Path) -> list[str]:
    text = classes_path.read_text(encoding="utf-8", errors="ignore")
    return [line.strip() for line in text.splitlines() if line.strip()]


def dominant_class(label_path: Path) -> int:
    counts: Counter[int] = Counter()
    for line in label_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        parts = line.strip().split()
        if parts:
            counts[int(float(parts[0]))] += 1
    return counts.most_common(1)[0][0] if counts else -1


def build_entries(dataset_root: Path) -> list[tuple[Path, Path, int]]:
    image_dir = dataset_root / "images"
    label_dir = dataset_root / "labels"
    entries: list[tuple[Path, Path, int]] = []

    for image_path in sorted(image_dir.iterdir()):
        if not image_path.is_file() or image_path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        label_path = label_dir / f"{image_path.stem}.txt"
        if label_path.exists():
            entries.append((image_path.resolve(), label_path.resolve(), dominant_class(label_path)))
    return entries


def stratified_split(
    entries: list[tuple[Path, Path, int]],
    val_ratio: float,
    test_ratio: float,
    seed: int,
) -> tuple[list[Path], list[Path], list[Path]]:
    rng = random.Random(seed)
    grouped: defaultdict[int, list[tuple[Path, Path, int]]] = defaultdict(list)
    for entry in entries:
        grouped[entry[2]].append(entry)

    train_images: list[Path] = []
    val_images: list[Path] = []
    test_images: list[Path] = []

    for items in grouped.values():
        rng.shuffle(items)
        total = len(items)
        test_count = max(1, round(total * test_ratio)) if total >= 10 else 0
        val_count = max(1, round(total * val_ratio)) if total >= 10 else (1 if total >= 3 else 0)
        if val_count + test_count >= total:
            test_count = 0
            val_count = min(val_count, max(1, total - 1))

        val_slice = items[:val_count]
        test_slice = items[val_count : val_count + test_count]
        train_slice = items[val_count + test_count :]

        train_images.extend(image for image, _, _ in train_slice)
        val_images.extend(image for image, _, _ in val_slice)
        test_images.extend(image for image, _, _ in test_slice)

    rng.shuffle(train_images)
    rng.shuffle(val_images)
    rng.shuffle(test_images)
    return train_images, val_images, test_images


def write_list(paths: list[Path], target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(str(path) for path in paths), encoding="utf-8")


def write_yaml(classes: list[str], train_txt: Path, val_txt: Path, test_txt: Path, yaml_path: Path) -> None:
    lines = [
        f"train: {train_txt.as_posix()}",
        f"val: {val_txt.as_posix()}",
        f"test: {test_txt.as_posix()}",
        "",
        f"nc: {len(classes)}",
        f"names: {classes!r}",
        "",
    ]
    yaml_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare train/val/test splits and dataset.yaml for a 4-class garbage YOLO dataset.")
    parser.add_argument("--dataset-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--val-ratio", type=float, default=0.1)
    parser.add_argument("--test-ratio", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    dataset_root = Path(args.dataset_root).resolve()
    output_dir = Path(args.output_dir).resolve()
    classes = read_classes(dataset_root / "labels" / "classes.txt")
    entries = build_entries(dataset_root)
    if not entries:
        raise RuntimeError("No valid image/label pairs were found in the dataset.")

    train_images, val_images, test_images = stratified_split(entries, args.val_ratio, args.test_ratio, args.seed)
    train_txt = output_dir / "train.txt"
    val_txt = output_dir / "val.txt"
    test_txt = output_dir / "test.txt"
    yaml_path = output_dir / "dataset.yaml"

    write_list(train_images, train_txt)
    write_list(val_images, val_txt)
    write_list(test_images, test_txt)
    write_yaml(classes, train_txt, val_txt, test_txt, yaml_path)

    print(f"dataset_root={dataset_root}")
    print(f"total_images={len(entries)}")
    print(f"train_images={len(train_images)}")
    print(f"val_images={len(val_images)}")
    print(f"test_images={len(test_images)}")
    print(f"yaml_path={yaml_path}")
    print(f"classes={classes}")


if __name__ == "__main__":
    main()
