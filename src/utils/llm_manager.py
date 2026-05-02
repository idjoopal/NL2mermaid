#!/usr/bin/env python3
"""
LLM Manager Module
LLM 매니저 모듈

환경변수와 모델명을 기준으로 LLM 백엔드(Cohere/OpenAI)를 선택해 호출합니다.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Literal

import cohere
import httpx

try:
    from openai import AsyncOpenAI
except ImportError:  # pragma: no cover - optional dependency fallback
    AsyncOpenAI = None  # type: ignore[assignment]

from src.utils.config_loader import (
    get_env,
    get_env_bool,
    get_env_float,
    get_env_int,
    load_root_env,
)

# .env 파일 로드 (모듈 import 시 1회 실행)
load_root_env()

# 네트워크 관련 예외 (공통)
NETWORK_EXCEPTIONS = (
    httpx.ReadError,
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpx.WriteTimeout,
    httpx.PoolTimeout,
    httpx.NetworkError,
    httpx.TimeoutException,
    ConnectionError,
    TimeoutError,
)

logger = logging.getLogger(__name__)
LLMProvider = Literal["cohere", "openai"]


class LLMManager:
    """Cohere/OpenAI 백엔드를 모델명으로 라우팅하는 LLM 매니저."""

    # 공통 설정 (기존 환경변수 호환)
    BASE_URL: str = get_env("BASE_URL", "https://api.cohere.ai")
    CLIENT_NAME: str = get_env("CLIENT_NAME", "prebuilt-mcp")
    API_KEY: str = get_env("API_KEY", "")
    TIMEOUT: float = get_env_float("TIMEOUT", 120.0)
    MODEL: str = get_env("MODEL", "command-r-plus")
    TEMPERATURE: float = get_env_float("TEMPERATURE", 0.3)
    TOP_K: int = get_env_int("TOP_K", 0)
    MAX_TOKENS: int = get_env_int("MAX_TOKENS", 4096)
    THINKING: bool = get_env_bool("THINKING", False)

    # Cohere 전용 설정
    COHERE_BASE_URL: str = get_env("COHERE_BASE_URL", BASE_URL)
    COHERE_CLIENT_NAME: str = get_env("COHERE_CLIENT_NAME", CLIENT_NAME)
    COHERE_API_KEY: str = get_env("COHERE_API_KEY", API_KEY)
    COHERE_MODEL: str = get_env("COHERE_MODEL", MODEL)

    # OpenAI 전용 설정
    OPENAI_BASE_URL: str = get_env("OPENAI_BASE_URL", "https://api.openai.com/v1")
    OPENAI_API_KEY: str = get_env("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = get_env("OPENAI_MODEL", "gpt-4o-mini")
    OPENAI_TIMEOUT: float = get_env_float("OPENAI_TIMEOUT", TIMEOUT)

    def __init__(self, base_url: str | None = None):
        """
        Args:
            base_url: Cohere base URL override.
        """
        self.cohere_base_url: str = base_url or self.COHERE_BASE_URL
        self.cohere_client: cohere.AsyncClientV2 | None = None
        self.openai_client: Any = None
        self._initialized_providers: set[LLMProvider] = set()

    @property
    def initialized(self) -> bool:
        """기존 코드 호환용 속성."""
        return self.is_initialized()

    def _resolve_provider_and_model(self, model_name: str | None) -> tuple[LLMProvider, str]:
        raw_model = (model_name or "").strip()

        if not raw_model:
            raw_model = (self.COHERE_MODEL or self.OPENAI_MODEL).strip()

        # Provider만 지정된 경우 → 전체 env에서 정의한 모델 사용
        # (예: agent env에서 TEXT2SQL_MODEL_ID=openai → OPENAI_MODEL 값 자동 사용)
        lowered = raw_model.lower()
        if lowered == "openai":
            return "openai", self.OPENAI_MODEL
        if lowered == "cohere":
            return "cohere", self.COHERE_MODEL

        # 명시적 접두사 지원: openai:gpt-4o-mini / cohere:command-r-plus
        for separator in (":", "/"):
            if separator in raw_model:
                provider_prefix, model_part = raw_model.split(separator, 1)
                provider_prefix = provider_prefix.strip().lower()
                model_part = model_part.strip()
                if provider_prefix in {"cohere", "openai"} and model_part:
                    return provider_prefix, model_part

        if lowered.startswith(("gpt-", "o1", "o3", "o4", "chatgpt")):
            provider: LLMProvider = "openai"
        else:
            provider = "cohere"

        final_model = raw_model.strip()
        if not final_model:
            final_model = self.OPENAI_MODEL if provider == "openai" else self.COHERE_MODEL

        if not final_model:
            raise ValueError("모델명이 비어 있습니다. MODEL 또는 모델 인자를 설정하세요.")

        return provider, final_model

    async def initialize(self, model_name: str | None = None) -> None:
        """모델명 기준으로 필요한 provider 클라이언트를 초기화합니다."""
        provider, resolved_model = self._resolve_provider_and_model(model_name)
        if provider in self._initialized_providers:
            return

        try:
            if provider == "cohere":
                await self._initialize_cohere()
            else:
                await self._initialize_openai()

            self._initialized_providers.add(provider)
            logger.debug("LLM Manager initialized (provider=%s, model=%s)", provider, resolved_model)
        except NETWORK_EXCEPTIONS as e:
            error_msg = f"LLM 연결 실패 ({type(e).__name__}): {e or 'Connection failed'}"
            logger.error("[LLM] %s", error_msg)
            raise ConnectionError(error_msg) from e
        except Exception:
            logger.exception("Failed to initialize LLM Manager (provider=%s)", provider)
            raise

    async def _initialize_cohere(self) -> None:
        if not self.COHERE_API_KEY:
            raise ConnectionError("COHERE_API_KEY(API_KEY)가 설정되지 않았습니다.")

        self.cohere_client = cohere.AsyncClientV2(
            base_url=self.cohere_base_url,
            client_name=self.COHERE_CLIENT_NAME,
            api_key=self.COHERE_API_KEY,
            timeout=self.TIMEOUT,
        )

    async def _initialize_openai(self) -> None:
        if AsyncOpenAI is None:
            raise ImportError("openai 패키지가 설치되지 않았습니다. `uv sync` 또는 `pip install openai`를 실행하세요.")

        if not self.OPENAI_API_KEY:
            raise ConnectionError("OPENAI_API_KEY가 설정되지 않았습니다.")

        self.openai_client = AsyncOpenAI(
            api_key=self.OPENAI_API_KEY,
            base_url=self.OPENAI_BASE_URL,
            timeout=self.OPENAI_TIMEOUT,
        )

    async def ainvoke(self, msg: str, model_name: str | None = None) -> dict[str, Any]:
        """
        모델명을 기준으로 provider를 선택해 LLM을 호출합니다.

        Args:
            msg: 사용자 입력 프롬프트
            model_name: 모델명 (예: command-r-plus, gpt-4o-mini, openai:gpt-4o-mini)
        """
        provider, resolved_model = self._resolve_provider_and_model(model_name)
        if provider not in self._initialized_providers:
            await self.initialize(model_name=resolved_model)

        try:
            if provider == "cohere":
                return await self._ainvoke_cohere(msg, resolved_model)
            return await self._ainvoke_openai(msg, resolved_model)
        except NETWORK_EXCEPTIONS as e:
            error_msg = (
                f"LLM API network error ({provider}, {type(e).__name__}): "
                f"{e or 'Connection failed'}"
            )
            logger.error("[LLM] %s", error_msg)
            raise RuntimeError(error_msg) from e
        except Exception:
            logger.exception("[LLM] Error (provider=%s, model=%s)", provider, resolved_model)
            raise

    async def _ainvoke_cohere(self, msg: str, model_name: str) -> dict[str, Any]:
        if self.cohere_client is None:
            raise RuntimeError("Cohere client is None after initialization")

        thinking_type = "enabled" if self.THINKING else "disabled"
        thinking = {"type": thinking_type}

        start_time = time.perf_counter()
        response = await self.cohere_client.chat(
            model=model_name,
            messages=[{"role": "user", "content": msg}],
            temperature=self.TEMPERATURE,
            k=self.TOP_K,
            thinking=thinking,
            max_tokens=self.MAX_TOKENS,
        )
        elapsed_time = time.perf_counter() - start_time

        return {
            "content": self._extract_cohere_text(response),
            "usage": self._extract_cohere_usage(response, elapsed_time),
            "raw": response,
        }

    async def _ainvoke_openai(self, msg: str, model_name: str) -> dict[str, Any]:
        if self.openai_client is None:
            raise RuntimeError("OpenAI client is None after initialization")

        lowered_model = model_name.lower()
        use_max_completion_tokens = lowered_model.startswith(("gpt-5", "o1", "o3", "o4"))

        request_kwargs: dict[str, Any] = {
            "model": model_name,
            "messages": [{"role": "user", "content": msg}],
        }

        # gpt-5/o-series는 max_completion_tokens만 허용
        if use_max_completion_tokens:
            request_kwargs["max_completion_tokens"] = self.MAX_TOKENS
        else:
            request_kwargs["max_tokens"] = self.MAX_TOKENS

        # 일부 최신 모델(gpt-5/o-series)은 temperature 미지원일 수 있어 제외
        if (lowered_model.startswith("gpt-") or lowered_model.startswith("chatgpt")) and not use_max_completion_tokens:
            request_kwargs["temperature"] = self.TEMPERATURE

        start_time = time.perf_counter()
        response = await self.openai_client.chat.completions.create(**request_kwargs)
        elapsed_time = time.perf_counter() - start_time

        return {
            "content": self._extract_openai_text(response),
            "usage": self._extract_openai_usage(response, elapsed_time),
            "raw": response,
        }

    def _extract_cohere_usage(self, response: Any, elapsed_time: float) -> dict[str, Any]:
        try:
            usage = getattr(response, "usage", None)
            if usage is not None:
                tokens = getattr(usage, "tokens", None)
                if tokens is not None:
                    input_tokens = getattr(tokens, "input_tokens", None)
                    output_tokens = getattr(tokens, "output_tokens", None)
                    if input_tokens is not None:
                        input_tokens = int(input_tokens)
                    if output_tokens is not None:
                        output_tokens = int(output_tokens)
                    return {
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "elapsed_time": elapsed_time,
                    }
        except Exception as e:
            logger.warning("Failed to extract usage from Cohere response: %s", e)

        return {
            "input_tokens": None,
            "output_tokens": None,
            "elapsed_time": elapsed_time,
        }

    def _extract_openai_usage(self, response: Any, elapsed_time: float) -> dict[str, Any]:
        try:
            usage = getattr(response, "usage", None)
            if usage is not None:
                return {
                    "input_tokens": getattr(usage, "prompt_tokens", None),
                    "output_tokens": getattr(usage, "completion_tokens", None),
                    "elapsed_time": elapsed_time,
                }
        except Exception as e:
            logger.warning("Failed to extract usage from OpenAI response: %s", e)

        return {
            "input_tokens": None,
            "output_tokens": None,
            "elapsed_time": elapsed_time,
        }

    def _extract_cohere_text(self, response: Any) -> str:
        try:
            content = response.message.content
            if isinstance(content, list) and content:
                first = content[0]
                return str(getattr(first, "text", first))
            return str(content)
        except Exception as e:
            logger.warning("Failed to extract text from Cohere response: %s", e)
            return f"Error: {e}"

    def _extract_openai_text(self, response: Any) -> str:
        try:
            choices = getattr(response, "choices", None)
            if not choices:
                return ""
            message = getattr(choices[0], "message", None)
            if message is None:
                return ""
            content = getattr(message, "content", "")
            if content is None:
                return ""
            return content if isinstance(content, str) else str(content)
        except Exception as e:
            logger.warning("Failed to extract text from OpenAI response: %s", e)
            return f"Error: {e}"

    def is_initialized(self, model_name: str | None = None) -> bool:
        """초기화 여부를 반환합니다."""
        if model_name is None:
            return bool(self._initialized_providers)

        provider, _ = self._resolve_provider_and_model(model_name)
        return provider in self._initialized_providers

    async def cleanup(self) -> None:
        """HTTP 클라이언트 리소스를 정리합니다."""
        if self.cohere_client is not None:
            try:
                if hasattr(self.cohere_client, "_client") and self.cohere_client._client is not None:
                    await self.cohere_client._client.aclose()
                    logger.debug("Cohere HTTP client closed successfully")
            except Exception as e:
                logger.warning("Error closing Cohere HTTP client: %s", e)
            finally:
                self.cohere_client = None

        if self.openai_client is not None:
            try:
                await self.openai_client.close()
                logger.debug("OpenAI HTTP client closed successfully")
            except Exception as e:
                logger.warning("Error closing OpenAI HTTP client: %s", e)
            finally:
                self.openai_client = None

        self._initialized_providers.clear()
