from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from ..types import ImageFormat, RenderResult


class BaseRendererProvider(ABC):

    def __init__(self, provider_name: str, config: Optional[Dict[str, Any]] = None):
        self.provider_name = provider_name
        self.config = config or {}

    @abstractmethod
    async def render(
        self,
        mermaid_code: str,
        image_format: ImageFormat,
        theme: str,
        bg_color: str,
    ) -> RenderResult:
        """Mermaid 코드를 이미지로 렌더링한다."""

    def get_provider_name(self) -> str:
        return self.provider_name
