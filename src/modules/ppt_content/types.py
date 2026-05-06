from __future__ import annotations
from dataclasses import dataclass

from src.modules.shared.types import ChartData, PptContent, SlideContent

__all__ = ["ChartData", "PptContent", "SlideContent", "SlideSpec"]


@dataclass
class SlideSpec:
    """Agent에서 ppt_content로 전달하는 슬라이드 명세"""
    slide_id: str
    slide_type: str  # title_slide | content_slide | chart_slide | table_slide | two_column
    placeholders: list[str]
    chart_type: str | None = None
