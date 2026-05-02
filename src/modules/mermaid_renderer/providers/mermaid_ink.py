import base64
import json
import zlib
from typing import Any, Dict, Optional

import httpx

from ..constants import DEFAULT_TIMEOUT, MERMAID_INK_BASE_URL
from ..exceptions import RenderFailedError
from ..types import ImageFormat, RenderResult
from .base import BaseRendererProvider


class MermaidInkProvider(BaseRendererProvider):
    """
    mermaid.ink 공개 API를 이용한 렌더링 프로바이더.
    pako(deflate+base64) 인코딩으로 한글 및 긴 코드 처리.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("mermaid_ink", config)
        self.base_url = self.config.get("api_base_url", MERMAID_INK_BASE_URL).rstrip("/")
        self.timeout = self.config.get("timeout", DEFAULT_TIMEOUT)

    @staticmethod
    def _encode_pako(code: str, theme: str) -> str:
        payload = json.dumps({"code": code, "mermaid": {"theme": theme}})
        compressed = zlib.compress(payload.encode("utf-8"), 9)
        encoded = base64.b64encode(compressed).decode()
        return "pako:" + encoded.replace("+", "-").replace("/", "_")

    async def render(
        self,
        mermaid_code: str,
        image_format: ImageFormat,
        theme: str,
        bg_color: str,
    ) -> RenderResult:
        token = self._encode_pako(mermaid_code, theme)
        fmt = image_format.value

        if fmt == "svg":
            url = f"{self.base_url}/svg/{token}"
        else:
            url = f"{self.base_url}/img/{token}?type=png&bgColor={bg_color}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise RenderFailedError(f"mermaid.ink HTTP {e.response.status_code}: {e.response.text[:200]}") from e
        except Exception as e:
            raise RenderFailedError(f"mermaid.ink 요청 실패: {e}") from e

        return RenderResult(
            image_bytes=response.content,
            image_format=image_format,
            provider=self.provider_name,
            mermaid_code=mermaid_code,
        )
