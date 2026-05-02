from __future__ import annotations

PROVIDER_MERMAID_INK = "mermaid_ink"
PROVIDER_KROKI = "kroki"

DEFAULT_PROVIDER = PROVIDER_MERMAID_INK
DEFAULT_THEME = "default"
DEFAULT_IMAGE_FORMAT = "png"
DEFAULT_BG_COLOR = "white"
DEFAULT_TIMEOUT = 30

SUPPORTED_THEMES = ("default", "neutral", "dark", "forest")
SUPPORTED_FORMATS = ("png", "svg")

MERMAID_INK_BASE_URL = "https://mermaid.ink"
KROKI_BASE_URL = "https://kroki.io"

OUTPUT_DIR = "./output"

ERROR_RENDER_FAILED = "Mermaid 렌더링에 실패했습니다: {error}"
ERROR_INVALID_CODE = "Mermaid 코드가 비어 있습니다."
ERROR_UNSUPPORTED_FORMAT = "지원하지 않는 이미지 형식입니다: {fmt}"
