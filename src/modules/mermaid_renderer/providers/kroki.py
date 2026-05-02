from typing import Any, Dict, Optional

import httpx

from ..constants import DEFAULT_TIMEOUT, KROKI_BASE_URL
from ..exceptions import RenderFailedError
from ..types import ImageFormat, RenderResult
from .base import BaseRendererProvider


class KrokiProvider(BaseRendererProvider):
    """
    Kroki API를 이용한 렌더링 프로바이더.
    POST 방식으로 코드 길이 제한 없음. 자체 호스팅 가능.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("kroki", config)
        self.base_url = self.config.get("api_base_url", KROKI_BASE_URL).rstrip("/")
        self.timeout = self.config.get("timeout", DEFAULT_TIMEOUT)

    async def render(
        self,
        mermaid_code: str,
        image_format: ImageFormat,
        theme: str,
        bg_color: str,
    ) -> RenderResult:
        fmt = image_format.value
        url = f"{self.base_url}/mermaid/{fmt}"

        # Kroki는 theme init 디렉티브를 코드에 직접 삽입
        code_with_theme = f"%%{{init: {{'theme':'{theme}'}}}}%%\n{mermaid_code}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    content=code_with_theme.encode("utf-8"),
                    headers={"Content-Type": "text/plain"},
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise RenderFailedError(f"Kroki HTTP {e.response.status_code}: {e.response.text[:200]}") from e
        except Exception as e:
            raise RenderFailedError(f"Kroki 요청 실패: {e}") from e

        return RenderResult(
            image_bytes=response.content,
            image_format=image_format,
            provider=self.provider_name,
            mermaid_code=mermaid_code,
        )
