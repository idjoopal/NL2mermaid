"""
Mermaid Renderer Module - Service

Mermaid 코드를 이미지(PNG/SVG)로 렌더링합니다.
mermaid.ink (기본) 또는 Kroki provider를 사용합니다.
"""
import logging
import re
from pathlib import Path
from typing import Dict, Optional, Type

from .config.config import mermaid_renderer_config
from .constants import (
    DEFAULT_BG_COLOR,
    DEFAULT_IMAGE_FORMAT,
    DEFAULT_THEME,
    ERROR_INVALID_CODE,
    PROVIDER_KROKI,
    PROVIDER_MERMAID_INK,
)
from .exceptions import InvalidMermaidCodeError, RenderFailedError
from .providers.base import BaseRendererProvider
from .providers.kroki import KrokiProvider
from .providers.mermaid_ink import MermaidInkProvider
from .types import ImageFormat, RenderResult

logger = logging.getLogger(__name__)

_PROVIDER_REGISTRY: Dict[str, Type[BaseRendererProvider]] = {
    PROVIDER_MERMAID_INK: MermaidInkProvider,
    PROVIDER_KROKI: KrokiProvider,
}


class MermaidRendererService:

    def __init__(self) -> None:
        self._providers: Dict[str, BaseRendererProvider] = {}
        self._initialize_providers()

    def _initialize_providers(self) -> None:
        for name, cls in _PROVIDER_REGISTRY.items():
            config = mermaid_renderer_config.get_provider_config(name)
            if not config.get("enabled", True):
                continue
            try:
                self._providers[name] = cls(config=config)
                logger.info("Initialized renderer provider: %s", name)
            except Exception as e:
                logger.warning("Failed to initialize renderer provider %s: %s", name, e)

    @staticmethod
    def _sanitize_code(code: str) -> str:
        """코드 블록 마커 제거 및 공백 정리."""
        code = re.sub(r"^```(?:mermaid)?\s*", "", code.strip(), flags=re.IGNORECASE)
        code = re.sub(r"\s*```$", "", code.strip())
        return code.strip()

    async def execute(
        self,
        mermaid_code: str,
        image_format: str = DEFAULT_IMAGE_FORMAT,
        theme: str = DEFAULT_THEME,
        bg_color: str = DEFAULT_BG_COLOR,
        provider_name: Optional[str] = None,
        save_to_file: bool = True,
    ) -> RenderResult:
        """
        Mermaid 코드를 이미지로 렌더링합니다. (모듈 진입점)

        Args:
            mermaid_code: Mermaid 다이어그램 코드
            image_format: 출력 형식 (png | svg)
            theme: 다이어그램 테마 (default | neutral | dark | forest)
            bg_color: 배경색 (white | transparent)
            provider_name: 렌더링 프로바이더 (기본: config 설정값)
            save_to_file: True면 ./output/ 디렉토리에 파일 저장

        Returns:
            RenderResult (image_bytes, image_format, provider, mermaid_code)
        """
        code = self._sanitize_code(mermaid_code)
        if not code:
            raise InvalidMermaidCodeError(ERROR_INVALID_CODE)

        fmt = ImageFormat(image_format)
        selected = provider_name or mermaid_renderer_config.default_provider

        provider = self._providers.get(selected)
        if provider is None:
            fallback = next(iter(self._providers), None)
            if fallback is None:
                raise RenderFailedError("사용 가능한 렌더링 프로바이더가 없습니다.")
            logger.warning("Provider '%s' not available, falling back to '%s'", selected, fallback)
            provider = self._providers[fallback]

        result = await provider.render(code, fmt, theme, bg_color)

        if save_to_file:
            self._save_file(result)

        return result

    @staticmethod
    def _save_file(result: RenderResult) -> None:
        import hashlib
        import time

        output_dir = Path(mermaid_renderer_config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        ts = int(time.time())
        code_hash = hashlib.md5(result.mermaid_code.encode()).hexdigest()[:6]
        filename = f"diagram_{ts}_{code_hash}.{result.image_format.value}"
        path = output_dir / filename
        path.write_bytes(result.image_bytes)
        logger.info("Saved diagram to %s", path)


mermaid_renderer_service = MermaidRendererService()
