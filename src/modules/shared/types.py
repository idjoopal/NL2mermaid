from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class ChartData:
    categories: list[str]
    series: list[dict]  # [{"name": str, "values": list[float]}]
    chart_type: str = "bar"  # bar | line | pie | column


@dataclass
class SlideContent:
    slide_id: str
    title: str = ""
    subtitle: str | None = None
    bullets: list[str] = field(default_factory=list)
    body: str | None = None
    table_data: list[list[str]] | None = None
    chart_data: ChartData | None = None


@dataclass
class PptContent:
    slides: list[SlideContent]
    title: str
    template_name: str
