from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


def resolve_project_path(raw_path: str, default: str) -> Path:
    path = Path(raw_path or default)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


@dataclass(slots=True)
class Settings:
    app_title: str = os.getenv("APP_TITLE", "EcoSort AI")
    host: str = os.getenv("APP_HOST", "0.0.0.0")
    port: int = int(os.getenv("APP_PORT", "8000"))

    vision_backend: str = os.getenv("VISION_BACKEND", "ultralytics").strip().lower()
    vision_model_path: str = os.getenv("VISION_MODEL_PATH", "").strip()
    vision_model_name: str = os.getenv(
        "VISION_MODEL_NAME", "hrutik_waste_detection_yolov8_best.pt"
    ).strip()
    vision_model_url: str = os.getenv(
        "VISION_MODEL_URL",
        "https://huggingface.co/HrutikAdsare/waste-detection-yolov8/resolve/main/best.pt",
    ).strip()
    vision_confidence: float = float(os.getenv("VISION_CONFIDENCE", "0.25"))
    vision_imgsz: int = int(os.getenv("VISION_IMGSZ", "640"))

    upload_dir: Path = resolve_project_path(os.getenv("UPLOAD_DIR", "./uploads"), "./uploads")
    artifact_dir: Path = resolve_project_path(os.getenv("ARTIFACT_DIR", "./artifacts"), "./artifacts")

    llm_api_base: str = os.getenv("LLM_API_BASE", "https://api.openai.com/v1/chat/completions").strip()
    llm_api_key: str = os.getenv("LLM_API_KEY", "").strip()
    llm_model: str = os.getenv("LLM_MODEL", "gpt-4o-mini").strip()

    vision_api_base: str = os.getenv("VISION_API_BASE", "").strip()
    vision_api_key: str = os.getenv("VISION_API_KEY", "").strip()
    vision_api_model: str = os.getenv("VISION_API_MODEL", "qwen3-vl-plus").strip()

    def ensure_dirs(self) -> None:
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        (self.artifact_dir / "weights").mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()
