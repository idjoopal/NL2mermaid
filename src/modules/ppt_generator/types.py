from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class PlaceholderSpec:
    name: str
    type: str = "text"  # text | list
    required: bool = False


@dataclass
class SlideDefinition:
    id: str
    type: str  # title_slide | content_slide | chart_slide | table_slide | two_column
    placeholders: list[PlaceholderSpec] = field(default_factory=list)
    chart_type: str | None = None  # bar | line | pie | column


@dataclass
class ThemeDefinition:
    primary_color: str = "2B4E9E"
    secondary_color: str = "E8EEF8"
    accent_color: str = "F0A500"
    font_family: str = "맑은 고딕"
    font_size_title: int = 36
    font_size_subtitle: int = 24
    font_size_heading: int = 24
    font_size_body: int = 18


@dataclass
class TemplateDefinition:
    name: str
    description: str
    slides: list[SlideDefinition]
    theme: ThemeDefinition = field(default_factory=ThemeDefinition)


@dataclass
class PptResult:
    pptx_bytes: bytes
    file_path: str | None
    slide_count: int
    template_name: str
