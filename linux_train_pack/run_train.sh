#!/usr/bin/env bash
set -euo pipefail

DATASET_ROOT="${1:-./garbage_dataset}"
WORKDIR="${2:-./workdir}"

MODEL="${MODEL:-yolov8s.pt}"
EPOCHS="${EPOCHS:-50}"
IMGSZ="${IMGSZ:-640}"
BATCH="${BATCH:-16}"
WORKERS="${WORKERS:-8}"
DEVICE="${DEVICE:-0}"
NAME="${NAME:-garbage4_yolov8s}"

echo "[1/2] Prepare dataset split and dataset.yaml"
python prepare_garbage4_dataset.py \
  --dataset-root "${DATASET_ROOT}" \
  --output-dir "${WORKDIR}/dataset"

echo "[2/2] Start training"
python train_yolo_garbage.py \
  --data "${WORKDIR}/dataset/dataset.yaml" \
  --model "${MODEL}" \
  --epochs "${EPOCHS}" \
  --imgsz "${IMGSZ}" \
  --device "${DEVICE}" \
  --batch "${BATCH}" \
  --workers "${WORKERS}" \
  --project "${WORKDIR}/runs" \
  --name "${NAME}"

echo "Training finished. Best weights should be under ${WORKDIR}/runs/${NAME}/weights/best.pt"
