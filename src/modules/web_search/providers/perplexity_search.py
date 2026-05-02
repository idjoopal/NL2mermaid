"""
Perplexity Search SDK implementation.

Primary path:
    from perplexity import Perplexity
    client = Perplexity()
    client.search.create(...)
"""
import asyncio
import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from .base import BaseSearchService, SearchResult
from ..constants import (
    DEFAULT_TIMEOUT,
    ENV_PERPLEXITY_API_KEY,
    ERROR_API_KEY_REQUIRED,
    ERROR_EMPTY_QUERY,
)
from ..exceptions import APIKeyMissingError

logger = logging.getLogger(__name__)

_ALLOWED_SEARCH_RECENCY_FILTERS = {"hour", "day", "week", "month", "year"}
_UNSUPPORTED_PARAM_REGEX = re.compile(r"([a-zA-Z_][a-zA-Z0-9_]*)\s+is not supported")


class PerplexitySearchService(BaseSearchService):
    """
    Perplexity Search SDK implementation.

    동작 기본값은 services_config.yaml의 perplexity 블록에서 조정하세요.
    API 키는 web_search.env의 PERPLEXITY_API_KEY 환경변수로 설정하세요.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Args:
            config: services_config.yaml에서 로드된 서비스 설정 딕셔너리

        Raises:
            APIKeyMissingError: API 키가 없을 때
        """
        super().__init__("perplexity", config)

        api_key = self.config.get("api_key", "")
        if not api_key:
            raise APIKeyMissingError(
                ERROR_API_KEY_REQUIRED.format(
                    service_name="Perplexity",
                    env_var=ENV_PERPLEXITY_API_KEY,
                )
            )
        self.api_key = api_key

        self.timeout = self.config.get("timeout", DEFAULT_TIMEOUT)
        self.max_results = self.config.get("max_results", 10)
        self.max_tokens = self.config.get("max_tokens", 10000)
        self.max_tokens_per_page = self.config.get("max_tokens_per_page", 4096)
        self.search_domain_filter = self.config.get("search_domain_filter", [])
        self.search_language_filter = self.config.get("search_language_filter", [])
        self.country = self.config.get("country")
        self.search_recency_filter = self.config.get("search_recency_filter")
        self.search_after_date_filter = self.config.get("search_after_date_filter")
        self.search_before_date_filter = self.config.get("search_before_date_filter")
        self.last_updated_after_filter = self.config.get("last_updated_after_filter")
        self.last_updated_before_filter = self.config.get("last_updated_before_filter")
        self.display_server_time = self.config.get("display_server_time", False)

        self.sdk_client = self._create_sdk_client()

    @staticmethod
    def _load_sdk_class():
        try:
            from perplexity import Perplexity  # type: ignore

            return Perplexity, "perplexity"
        except ImportError:
            pass

        try:
            from perplexityai import Perplexity  # type: ignore

            return Perplexity, "perplexityai"
        except ImportError as exc:
            raise ImportError(
                "Perplexity SDK is not installed. Install `perplexityai` "
                "(module import path: `from perplexity import Perplexity`)."
            ) from exc

    def _create_sdk_client(self):
        sdk_class, sdk_module_name = self._load_sdk_class()

        # perplexityai 배포판은 `from perplexity import Perplexity` 경로를 제공합니다.
        try:
            client = sdk_class(api_key=self.api_key)
            logger.info("Initialized Perplexity SDK client via `%s`", sdk_module_name)
            return client
        except TypeError:
            # 일부 버전은 생성자 인자를 받지 않으므로 환경변수 기반 초기화로 폴백
            os.environ[ENV_PERPLEXITY_API_KEY] = self.api_key
            client = sdk_class()
            logger.info(
                "Initialized Perplexity SDK client via `%s` using environment API key",
                sdk_module_name,
            )
            return client

    @staticmethod
    def _sanitize_query(query: Union[str, List[str]]) -> Union[str, List[str]]:
        if isinstance(query, str):
            if not query.strip():
                raise ValueError(ERROR_EMPTY_QUERY)
            return query.strip()

        if isinstance(query, list):
            filtered = [q.strip() for q in query if isinstance(q, str) and q.strip()]
            if not filtered:
                raise ValueError(ERROR_EMPTY_QUERY)
            return filtered

        raise ValueError(ERROR_EMPTY_QUERY)

    @staticmethod
    def _validate_enum(value: Optional[str], allowed: set[str], field_name: str) -> None:
        if value and value not in allowed:
            allowed_text = ", ".join(sorted(allowed))
            raise ValueError(f"Invalid {field_name}: '{value}'. Allowed: {allowed_text}")

    @staticmethod
    def _get_value(container: Any, key: str, default: Any = None) -> Any:
        if container is None:
            return default
        if isinstance(container, dict):
            return container.get(key, default)
        return getattr(container, key, default)

    @classmethod
    def _extract_unsupported_param_from_error(cls, exc: Exception) -> Optional[str]:
        text = str(exc) or ""
        match = _UNSUPPORTED_PARAM_REGEX.search(text)
        if not match:
            return None
        return match.group(1)

    @staticmethod
    def _as_list(value: Any) -> List[Any]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, tuple):
            return list(value)
        return [value]

    async def _sdk_search_create(self, params: Dict[str, Any]) -> Any:
        search_api = getattr(self.sdk_client, "search", None)
        if search_api is None:
            raise RuntimeError("Perplexity SDK client does not expose `search` namespace.")

        create_fn = getattr(search_api, "create", None)
        if not callable(create_fn):
            raise RuntimeError("Perplexity SDK client does not expose `search.create(...)`.")

        return await asyncio.to_thread(create_fn, **params)

    async def search(self, query: Union[str, List[str]], **kwargs) -> List[SearchResult]:
        """
        Perform search using Perplexity Search SDK.
        query는 string 또는 string[] 모두 지원합니다.
        """
        sanitized_query = self._sanitize_query(query)

        search_params: Dict[str, Any] = {
            "query": sanitized_query,
            "max_results": kwargs.get("max_results", self.max_results),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "max_tokens_per_page": kwargs.get("max_tokens_per_page", self.max_tokens_per_page),
            "search_domain_filter": kwargs.get(
                "search_domain_filter", self.search_domain_filter
            ),
            "search_language_filter": kwargs.get(
                "search_language_filter", self.search_language_filter
            ),
            "country": kwargs.get("country", self.country),
            "search_recency_filter": kwargs.get(
                "search_recency_filter", self.search_recency_filter
            ),
            "search_after_date_filter": kwargs.get(
                "search_after_date_filter", self.search_after_date_filter
            ),
            "search_before_date_filter": kwargs.get(
                "search_before_date_filter", self.search_before_date_filter
            ),
            "last_updated_after_filter": kwargs.get(
                "last_updated_after_filter", self.last_updated_after_filter
            ),
            "last_updated_before_filter": kwargs.get(
                "last_updated_before_filter", self.last_updated_before_filter
            ),
            "display_server_time": kwargs.get(
                "display_server_time", self.display_server_time
            ),
        }

        self._validate_enum(
            search_params.get("search_recency_filter"),
            _ALLOWED_SEARCH_RECENCY_FILTERS,
            "search_recency_filter",
        )

        request_params = {
            k: v for k, v in search_params.items() if v is not None and v != "" and v != []
        }

        last_error: Optional[Exception] = None
        for _ in range(8):
            try:
                response = await self._sdk_search_create(request_params)
                return self._convert_results(response)
            except Exception as exc:
                last_error = exc
                unsupported_param = self._extract_unsupported_param_from_error(exc)
                if (
                    unsupported_param
                    and unsupported_param in request_params
                    and unsupported_param != "query"
                ):
                    logger.warning(
                        "Perplexity parameter '%s' is unsupported by this endpoint/account. "
                        "Retrying without it.",
                        unsupported_param,
                    )
                    request_params.pop(unsupported_param, None)
                    continue
                break

        error_msg = f"Perplexity SDK error: {last_error}" if last_error else "Unknown SDK error"
        logger.error(error_msg)
        raise Exception(error_msg) from last_error

    def _convert_results(self, sdk_response: Any) -> List[SearchResult]:
        """Convert Perplexity SDK response to SearchResult objects."""
        raw_results = self._as_list(self._get_value(sdk_response, "results", []))
        response_references = (
            self._get_value(sdk_response, "references")
            or self._get_value(sdk_response, "sources")
            or self._get_value(sdk_response, "citations")
        )

        server_time = self._get_value(sdk_response, "server_time")
        usage = self._get_value(sdk_response, "usage")
        converted: List[SearchResult] = []

        for idx, item in enumerate(raw_results):
            try:
                title = (
                    self._get_value(item, "title")
                    or self._get_value(item, "name")
                    or self._get_value(item, "source_title")
                    or "No title"
                )
                url = (
                    self._get_value(item, "url")
                    or self._get_value(item, "link")
                    or self._get_value(item, "source_url")
                    or ""
                )
                snippet = (
                    self._get_value(item, "snippet")
                    or self._get_value(item, "content")
                    or self._get_value(item, "text")
                    or ""
                )

                if not url:
                    logger.warning("Perplexity result %s missing URL, skipping", idx)
                    continue

                metadata: Dict[str, Any] = {}
                for key in ("score", "date", "published_date", "last_updated", "author"):
                    value = self._get_value(item, key)
                    if value is not None:
                        metadata[key] = value

                if server_time is not None:
                    metadata["server_time"] = server_time
                if usage is not None:
                    metadata["usage"] = usage
                if response_references:
                    metadata["references"] = response_references

                converted.append(
                    SearchResult(
                        title=str(title),
                        url=str(url),
                        snippet=str(snippet),
                        source="perplexity",
                        timestamp=datetime.now(),
                        metadata=metadata if metadata else None,
                    )
                )
            except Exception as exc:
                logger.warning(
                    "Error converting Perplexity result %s: %s",
                    idx,
                    exc,
                    exc_info=False,
                )
                continue

        return converted

    async def health_check(self) -> bool:
        """Check if Perplexity Search SDK is available and working."""
        try:
            results = await self.search("test", max_results=1)
            return isinstance(results, list)
        except Exception as exc:
            logger.error("Perplexity Search SDK health check failed: %s", exc)
            return False

    async def aclose(self) -> None:
        """SDK client close hook (no-op for sync SDK client)."""
        return None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.aclose()
