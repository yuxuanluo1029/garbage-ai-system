from __future__ import annotations

import base64
import io
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps

from app.config import settings
from app.schemas import DetectionItem, PredictionResponse, WasteCategory


CATEGORY_COLORS: dict[WasteCategory, str] = {
    "可回收垃圾": "#1f7a4d",
    "厨余垃圾": "#cf7c19",
    "有害垃圾": "#c94242",
    "其他垃圾": "#586073",
    "待确认": "#6e675a",
}


@dataclass(frozen=True, slots=True)
class LabelSpec:
    zh_label: str
    waste_category: WasteCategory
    rationale: str


LABEL_SPECS: dict[str, LabelSpec] = {
    "recyclable waste": LabelSpec("可回收垃圾", "可回收垃圾", "模型将该目标识别为可回收垃圾。"),
    "hazardous waste": LabelSpec("有害垃圾", "有害垃圾", "模型将该目标识别为有害垃圾。"),
    "kitchen waste": LabelSpec("厨余垃圾", "厨余垃圾", "模型将该目标识别为厨余垃圾。"),
    "other waste": LabelSpec("其他垃圾", "其他垃圾", "模型将该目标识别为其他垃圾。"),
    "cardboard": LabelSpec("纸箱", "可回收垃圾", "干燥、洁净的纸箱通常属于可回收垃圾。"),
    "paper": LabelSpec("纸张", "可回收垃圾", "纸张类物品通常可以作为可回收垃圾处理。"),
    "glass": LabelSpec("玻璃制品", "可回收垃圾", "玻璃瓶、玻璃罐等通常属于可回收垃圾。"),
    "metal": LabelSpec("金属制品", "可回收垃圾", "金属类物品通常属于可回收垃圾。"),
    "plastic": LabelSpec("塑料制品", "可回收垃圾", "干净的塑料制品通常可以作为可回收垃圾处理。"),
    "organic waste": LabelSpec("厨余残渣", "厨余垃圾", "食物残渣、果皮菜叶等通常属于厨余垃圾。"),
    "organic": LabelSpec("厨余残渣", "厨余垃圾", "食物残渣、果皮菜叶等通常属于厨余垃圾。"),
    "e-waste": LabelSpec("电子废弃物", "有害垃圾", "电子废弃物建议单独回收或按有害垃圾规范处理。"),
    "ewaste": LabelSpec("电子废弃物", "有害垃圾", "电子废弃物建议单独回收或按有害垃圾规范处理。"),
    "medical": LabelSpec("医疗废弃物", "有害垃圾", "医疗废弃物具有潜在风险，建议按有害垃圾规范处理。"),
    "medical waste": LabelSpec("医疗废弃物", "有害垃圾", "医疗废弃物具有潜在风险，建议按有害垃圾规范处理。"),
    "medical-waste": LabelSpec("医疗废弃物", "有害垃圾", "医疗废弃物具有潜在风险，建议按有害垃圾规范处理。"),
}

UNKNOWN_SPEC = LabelSpec(
    zh_label="未映射物体",
    waste_category="待确认",
    rationale="模型识别到了目标，但当前还没有更细的中文分类映射，请人工确认。",
)


def image_to_data_url(image: Image.Image, fmt: str = "PNG") -> str:
    buffer = io.BytesIO()
    image.save(buffer, format=fmt)
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/{fmt.lower()};base64,{encoded}"


def load_normalized_image(image_path: Path) -> Image.Image:
    with Image.open(io.BytesIO(image_path.read_bytes())) as raw_image:
        return ImageOps.exif_transpose(raw_image).convert("RGB")


def save_temp_inference_image(image: Image.Image) -> Path:
    temp_dir = Path(tempfile.gettempdir()) / "ecosort_inference"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / f"{uuid.uuid4().hex}.png"
    image.save(temp_path, format="PNG")
    return temp_path


def clamp_bbox(bbox: list[float], width: int, height: int) -> list[float]:
    x1, y1, x2, y2 = bbox
    x1 = max(0.0, min(float(width), x1))
    y1 = max(0.0, min(float(height), y1))
    x2 = max(0.0, min(float(width), x2))
    y2 = max(0.0, min(float(height), y2))
    return [x1, y1, x2, y2]


def bbox_iou(box_a: list[float], box_b: list[float]) -> float:
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b
    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)
    inter_w = max(0.0, inter_x2 - inter_x1)
    inter_h = max(0.0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union_area = area_a + area_b - inter_area
    return inter_area / union_area if union_area > 0 else 0.0


def normalize_label(label: str) -> str:
    return " ".join(label.strip().lower().replace("_", " ").split())


def find_font(size: int) -> ImageFont.ImageFont:
    candidates = [
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
        Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            try:
                return ImageFont.truetype(str(candidate), size=size)
            except OSError:
                continue
    return ImageFont.load_default()


class UltralyticsGarbageDetector:
    def __init__(self, model_path: str, confidence: float) -> None:
        from ultralytics import YOLO

        self.confidence = confidence
        self.imgsz = settings.vision_imgsz
        self.model_path = self._resolve_model_path(model_path)
        self.model = YOLO(str(self.model_path))
        self.model_name = self.model_path.name
        self.used_custom_weights = True
        if "garbage4" in self.model_name or self.model_name == "best.pt":
            self.source_name = "自训练垃圾模型"
            self.recognition_mode = "自训练4类垃圾检测模型"
        else:
            self.source_name = "HrutikAdsare 现成权重"
            self.recognition_mode = "现成垃圾检测权重"

    def _resolve_model_path(self, model_path: str) -> Path:
        if model_path:
            if model_path.startswith(("http://", "https://")):
                target_name = Path(model_path.split("?")[0]).name or settings.vision_model_name
                target = settings.artifact_dir / "weights" / target_name
                self._download_weight(model_path, target)
                return target

            candidate = Path(model_path)
            if candidate.exists():
                return candidate.resolve()
            raise FileNotFoundError(f"未找到识别模型文件：{model_path}")

        target = settings.artifact_dir / "weights" / settings.vision_model_name
        if target.exists():
            return target

        if not settings.vision_model_url:
            raise FileNotFoundError("没有提供可下载的垃圾检测模型地址。")

        self._download_weight(settings.vision_model_url, target)
        return target

    def _download_weight(self, url: str, target: Path) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp_target = target.with_suffix(target.suffix + ".part")
        if target.exists() and target.stat().st_size > 1_000_000:
            tmp_target.unlink(missing_ok=True)
            return

        response = requests.get(url, stream=True, timeout=180)
        response.raise_for_status()
        with tmp_target.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)

        if tmp_target.stat().st_size <= 1_000_000:
            tmp_target.unlink(missing_ok=True)
            raise RuntimeError("下载到的模型文件异常，文件体积过小。")

        tmp_target.replace(target)

    def _spec_for_label(self, raw_label: str) -> LabelSpec:
        normalized = normalize_label(raw_label)
        return LABEL_SPECS.get(normalized, UNKNOWN_SPEC)

    def _parse_detections(self, result, image_size: tuple[int, int]) -> list[DetectionItem]:
        width, height = image_size
        boxes = getattr(result, "boxes", None)
        if boxes is None:
            return []

        names = result.names
        parsed: list[DetectionItem] = []
        for box in boxes:
            confidence = float(box.conf.item())
            cls_id = int(box.cls.item())
            raw_label = names[cls_id] if isinstance(names, list) else names.get(cls_id, str(cls_id))
            spec = self._spec_for_label(raw_label)
            bbox = clamp_bbox([float(v) for v in box.xyxy[0].tolist()], width, height)
            parsed.append(
                DetectionItem(
                    label=spec.zh_label,
                    confidence=round(confidence, 4),
                    waste_category=spec.waste_category,
                    rationale=f"{spec.rationale} 模型原始类别为 {raw_label}。",
                    bbox=[round(value, 1) for value in bbox],
                    source=self.source_name,
                )
            )

        parsed.sort(key=lambda item: item.confidence, reverse=True)
        deduplicated: list[DetectionItem] = []
        for item in parsed:
            if any(item.label == chosen.label and bbox_iou(item.bbox, chosen.bbox) > 0.6 for chosen in deduplicated):
                continue
            deduplicated.append(item)
            if len(deduplicated) >= 6:
                break
        return deduplicated

    def _pick_summary(self, detections: list[DetectionItem]) -> tuple[str, WasteCategory, str]:
        if not detections:
            return (
                "未识别到明确物体",
                "待确认",
                "模型暂时没有识别到稳定目标，建议换一张主体更清晰、更近距离的图片。",
            )

        top = detections[0]
        if self._is_ambiguous(detections):
            labels_text = "、".join(f"{item.label}({item.confidence:.0%})" for item in detections[:3])
            return (
                "待确认",
                "待确认",
                f"当前几个候选结果过于接近或整体置信度偏低：{labels_text}。这张图建议人工确认，或更换更清晰的单主体图片。",
            )

        top_categories = {item.waste_category for item in detections[:3]}
        unique_labels: list[str] = []
        for item in detections:
            if item.label not in unique_labels:
                unique_labels.append(item.label)

        if len(top_categories) > 1:
            labels_text = "、".join(unique_labels[:4])
            return (
                "混合垃圾",
                "待确认",
                f"图中同时识别到 {labels_text} 等不同类别对象，建议拆分后分别投放。",
            )

        if len(unique_labels) > 1:
            labels_text = "、".join(unique_labels[1:4])
            return (
                top.label,
                top.waste_category,
                f"当前主要识别对象为“{top.label}”，同时还检测到 {labels_text}，它们大多属于 {top.waste_category}。",
            )

        return (
            top.label,
            top.waste_category,
            f"系统当前最稳定的识别结果是“{top.label}”，建议按 {top.waste_category} 处理。",
        )

    def _is_ambiguous(self, detections: list[DetectionItem]) -> bool:
        top = detections[0]
        second = detections[1] if len(detections) > 1 else None

        if top.confidence < 0.45:
            return True

        if second is None:
            return False

        iou = bbox_iou(top.bbox, second.bbox)
        confidence_gap = top.confidence - second.confidence
        same_region = iou > 0.75

        if same_region and confidence_gap < 0.12:
            return True

        if top.confidence < 0.6 and second.confidence > 0.25 and confidence_gap < 0.18:
            return True

        third = detections[2] if len(detections) > 2 else None
        if third is not None:
            if same_region and top.confidence - third.confidence < 0.16:
                return True
            if top.confidence < 0.7 and third.confidence > 0.22:
                return True

        return False

    def _draw_annotations(
        self,
        image: Image.Image,
        detections: list[DetectionItem],
        summary_label: str,
        summary_category: WasteCategory,
    ) -> Image.Image:
        annotated = image.copy()
        draw = ImageDraw.Draw(annotated)
        font = find_font(18)
        header_font = find_font(22)

        for item in detections:
            if len(item.bbox) != 4:
                continue
            left, top, right, bottom = item.bbox
            color = CATEGORY_COLORS[item.waste_category]
            draw.rounded_rectangle((left, top, right, bottom), radius=10, outline=color, width=4)

            caption = f"{item.label} | {item.confidence:.0%}"
            text_box = draw.textbbox((0, 0), caption, font=font)
            text_width = text_box[2] - text_box[0]
            text_height = text_box[3] - text_box[1]
            text_left = left
            text_top = max(0.0, top - text_height - 14)
            text_right = min(float(annotated.width), text_left + text_width + 18)
            draw.rounded_rectangle((text_left, text_top, text_right, top), radius=8, fill=color)
            draw.text((text_left + 9, text_top + 6), caption, fill="white", font=font)

        header = f"{summary_label} / {summary_category}"
        header_box = draw.textbbox((0, 0), header, font=header_font)
        header_width = min(float(annotated.width) - 12, float(header_box[2] - header_box[0] + 28))
        draw.rounded_rectangle((12, 12, 12 + header_width, 54), radius=12, fill=(31, 42, 31))
        draw.text((24, 21), header, fill="white", font=header_font)
        return annotated

    def predict(self, image_path: Path) -> PredictionResponse:
        image = load_normalized_image(image_path)
        temp_path = save_temp_inference_image(image)
        try:
            results = self.model.predict(
                source=str(temp_path),
                conf=self.confidence,
                imgsz=self.imgsz,
                verbose=False,
                max_det=20,
            )
        finally:
            temp_path.unlink(missing_ok=True)

        detections = self._parse_detections(results[0], image.size)
        summary_label, summary_category, summary_reason = self._pick_summary(detections)
        annotated = self._draw_annotations(image, detections, summary_label, summary_category)

        return PredictionResponse(
            source_image=image_to_data_url(image),
            annotated_image=image_to_data_url(annotated),
            detections=detections,
            summary_label=summary_label,
            summary_category=summary_category,
            summary_reason=summary_reason,
            recognition_mode=self.recognition_mode,
            model_name=self.model_name,
            used_custom_weights=self.used_custom_weights,
        )


_detector: UltralyticsGarbageDetector | None = None


def get_detector() -> UltralyticsGarbageDetector:
    global _detector
    if _detector is None:
        _detector = UltralyticsGarbageDetector(settings.vision_model_path, settings.vision_confidence)
    return _detector


def save_upload(content: bytes, suffix: str) -> Path:
    filename = f"{uuid.uuid4().hex}{suffix}"
    target = settings.upload_dir / filename
    target.write_bytes(content)
    return target

