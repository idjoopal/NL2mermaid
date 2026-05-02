from dataclasses import dataclass
from enum import Enum


class ImageFormat(str, Enum):
    PNG = "png"
    SVG = "svg"


class DiagramTheme(str, Enum):
    DEFAULT = "default"
    NEUTRAL = "neutral"
    DARK = "dark"
    FOREST = "forest"


@dataclass
class RenderResult:
    image_bytes: bytes
    image_format: ImageFormat
    provider: str
    mermaid_code: str
