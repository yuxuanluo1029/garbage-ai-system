from __future__ import annotations

from typing import Iterable

import requests

from app.config import settings
from app.schemas import AnalyzeRequest


class AgentService:
    def __init__(self) -> None:
        self.api_base = settings.llm_api_base
        self.api_key = settings.llm_api_key
        self.model = settings.llm_model

    def _detections_to_text(self, labels: Iterable[tuple[str, str, float, str]]) -> str:
        lines = []
        for label, category, confidence, source in labels:
            lines.append(
                f"- 目标：{label} | 建议分类：{category} | 置信度：{confidence:.2%} | 识别来源：{source}"
            )
        return "\n".join(lines) if lines else "- 当前没有稳定的识别目标，请结合图片内容谨慎判断。"

    def analyze(self, request: AnalyzeRequest) -> tuple[str, str]:
        if not self.api_key:
            fallback = (
                "当前还没有配置大模型 API Key，所以我先根据识别结果给出规则化分析。\n\n"
                f"主要识别对象：{request.summary_label or '未识别到明确对象'}\n"
                f"综合类别：{request.summary_category}\n"
                f"识别链路：{request.recognition_mode or '本地规则'}\n"
                f"判断原因：{request.summary_reason}\n\n"
                "建议：如果图片里有多个物体，尽量拆分后分别拍照；如果物品被油污、液体或食物残渣严重污染，"
                "要优先考虑它是否已经失去回收价值，再决定是否按其他垃圾处理。"
            )
            return fallback, "local-rule-based"

        prompt = (
            "你是一名中文垃圾分类与环保问答助手。请基于识别结果回答用户问题，"
            "输出要简洁、准确、可操作，并尽量分成四部分："
            "1. 主要判断 2. 判断依据 3. 投放建议 4. 注意事项。\n\n"
            f"主要识别对象：{request.summary_label or '未识别到明确对象'}\n"
            f"综合类别：{request.summary_category}\n"
            f"判断原因：{request.summary_reason}\n"
            f"识别链路：{request.recognition_mode or '未提供'}\n"
            "检测明细：\n"
            f"{self._detections_to_text((item.label, item.waste_category, item.confidence, item.source) for item in request.detections)}\n\n"
            f"用户问题：{request.question}"
        )

        response = requests.post(
            self.api_base,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一名负责垃圾分类解答与环保建议的中文助手。",
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
            },
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        answer = payload["choices"][0]["message"]["content"].strip()
        return answer, self.model


agent_service = AgentService()

