"""
Tavily Search API implementation.
Uses Tavily's Search API for AI-powered web search results.
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

import httpx

from .base import BaseSearchService, SearchResult
from ..constants import (
    TAVILY_MAX_RESULTS,
    TAVILY_MAX_INCLUDE_DOMAINS,
    TAVILY_MAX_EXCLUDE_DOMAINS,
    TAVILY_MIN_CHUNKS_PER_SOURCE,
    TAVILY_MAX_CHUNKS_PER_SOURCE,
    DEFAULT_TIMEOUT,
    HEALTH_CHECK_TIMEOUT,
    SEARCH_DEPTH_ADVANCED,
    TOPIC_GENERAL,
    CONTENT_TYPE_JSON,
    ENV_TAVILY_API_KEY,
    ERROR_API_KEY_REQUIRED,
    ERROR_EMPTY_QUERY,
)
from ..exceptions import APIKeyMissingError

logger = logging.getLogger(__name__)

_DEFAULT_API_BASE_URL = "https://api.tavily.com"


class TavilySearchService(BaseSearchService):
    """
    Tavily Search API implementation.

    Provides AI-powered search results using Tavily's Search API.
    동작 기본값은 services_config.yaml의 tavily_search 블록에서 조정하세요.
    API 키는 web_search.env의 TAVILY_API_KEY 환경변수로 설정하세요.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Args:
            config: services_config.yaml에서 로드된 서비스 설정 딕셔너리

        Raises:
            APIKeyMissingError: API 키가 없을 때
        """
        super().__init__("tavily_search", config)

        api_key = self.config.get("api_key", "")
        if not api_key:
            raise APIKeyMissingError(
                ERROR_API_KEY_REQUIRED.format(
                    service_name="Tavily",
                    env_var=ENV_TAVILY_API_KEY,
                )
            )
        self.api_key = api_key

        # api_base_url은 services_config.yaml에서 읽음 (기본값 fallback 유지)
        api_base_url = self.config.get("api_base_url", _DEFAULT_API_BASE_URL).rstrip("/")
        self.search_endpoint = f"{api_base_url}/search"

        self.max_results = min(self.config.get("max_results", 5), TAVILY_MAX_RESULTS)
        self.timeout = self.config.get("timeout", DEFAULT_TIMEOUT)
        self.search_depth = self.config.get("search_depth")
        self.chunks_per_source = self.config.get("chunks_per_source")
        self.topic = self.config.get("topic", TOPIC_GENERAL)
        self.time_range = self.config.get("time_range")
        self.start_date = self.config.get("start_date")
        self.end_date = self.config.get("end_date")
        self.include_answer = self.config.get("include_answer", False)
        self.include_raw_content = self.config.get("include_raw_content", False)
        self.include_images = self.config.get("include_images", False)
        self.include_image_descriptions = self.config.get("include_image_descriptions", False)
        self.include_favicon = self.config.get("include_favicon", False)
        self.include_domains = self.config.get("include_domains", [])
        self.exclude_domains = self.config.get("exclude_domains", [])
        self.country = self.config.get("country")
        self.auto_parameters = self.config.get("auto_parameters", False)
        self.include_usage = self.config.get("include_usage", False)

        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            headers={"Content-Type": CONTENT_TYPE_JSON},
        )

    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        """
        Perform search using Tavily Search API.
        """
        if not query:
            raise ValueError(ERROR_EMPTY_QUERY)

        try:
            # auto_parameters가 True면 Tavily에게 모든 파라미터 최적화 위임
            auto_mode = kwargs.get("auto_parameters", self.auto_parameters)

            if auto_mode is True:
                search_params: Dict[str, Any] = {
                    "query": query,
                    "auto_parameters": True,
                }
                if "search_depth" in kwargs and kwargs.get("search_depth"):
                    search_params["search_depth"] = kwargs["search_depth"]
                if "max_results" in kwargs and kwargs.get("max_results") is not None:
                    search_params["max_results"] = min(
                        kwargs["max_results"], TAVILY_MAX_RESULTS
                    )
                if "include_answer" in kwargs and kwargs.get("include_answer") is not None:
                    search_params["include_answer"] = kwargs["include_answer"]
                if "include_domains" in kwargs and kwargs.get("include_domains"):
                    search_params["include_domains"] = kwargs["include_domains"][:TAVILY_MAX_INCLUDE_DOMAINS]
                if "exclude_domains" in kwargs and kwargs.get("exclude_domains"):
                    search_params["exclude_domains"] = kwargs["exclude_domains"][:TAVILY_MAX_EXCLUDE_DOMAINS]
            else:
                # 수동 모드: services_config.yaml 기본값 + LLM kwargs 오버라이드
                date_filter_type = kwargs.pop("date_filter_type", None)

                search_params = {
                    "query": query,
                    "max_results": kwargs.get("max_results", self.max_results),
                    "search_depth": kwargs.get("search_depth", self.search_depth),
                    "topic": kwargs.get("topic", self.topic),
                    "include_answer": kwargs.get("include_answer", self.include_answer),
                    "include_raw_content": kwargs.get("include_raw_content", self.include_raw_content),
                    "include_images": kwargs.get("include_images", self.include_images),
                    "include_domains": kwargs.get("include_domains", self.include_domains),
                    "exclude_domains": kwargs.get("exclude_domains", self.exclude_domains),
                    "country": kwargs.get("country", self.country),
                }

                if date_filter_type == "time_range" or kwargs.get("time_range"):
                    search_params["time_range"] = kwargs.get("time_range", self.time_range)
                elif date_filter_type == "date_range" or kwargs.get("start_date") or kwargs.get("end_date"):
                    search_params["start_date"] = kwargs.get("start_date", self.start_date)
                    search_params["end_date"] = kwargs.get("end_date", self.end_date)

                if search_params.get("search_depth") == SEARCH_DEPTH_ADVANCED:
                    chunks = kwargs.get("chunks_per_source", self.chunks_per_source)
                    if chunks and TAVILY_MIN_CHUNKS_PER_SOURCE <= chunks <= TAVILY_MAX_CHUNKS_PER_SOURCE:
                        search_params["chunks_per_source"] = chunks

                search_params["max_results"] = min(
                    search_params["max_results"], TAVILY_MAX_RESULTS
                )
                search_params = {
                    k: v for k, v in search_params.items()
                    if v is not None and v != "" and v != []
                }

            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = await self.client.post(
                self.search_endpoint,
                json=search_params,
                headers=headers,
            )
            response.raise_for_status()

            data = response.json()
            return self._convert_results(data.get("results", []), query, data)

        except httpx.HTTPStatusError as exc:
            error_msg = f"Tavily API HTTP error: {exc.response.status_code} - {exc.response.text}"
            logger.error(error_msg)
            raise Exception(error_msg) from exc
        except httpx.RequestError as exc:
            error_msg = f"Tavily API request error: {exc}"
            logger.error(error_msg)
            raise Exception(error_msg) from exc
        except Exception as exc:
            logger.error("Error in Tavily search: %s", exc, exc_info=True)
            raise

    def _convert_results(
        self,
        tavily_results: List[Dict[str, Any]],
        query: str,
        response_data: Dict[str, Any],
    ) -> List[SearchResult]:
        """Convert Tavily API results to SearchResult objects."""
        converted: List[SearchResult] = []
        response_references = (
            response_data.get("references")
            or response_data.get("sources")
            or response_data.get("citations")
        )

        for idx, item in enumerate(tavily_results):
            try:
                title = item.get("title", "No title")
                url = item.get("url", "")
                content = item.get("content", "")
                score = item.get("score")
                raw_content = item.get("raw_content")
                favicon = item.get("favicon")

                timestamp = datetime.now()

                metadata: Dict[str, Any] = {"score": score}
                if favicon:
                    metadata["favicon"] = favicon
                if raw_content:
                    metadata["raw_content"] = raw_content
                if "answer" in response_data and response_data["answer"]:
                    metadata["answer"] = response_data["answer"]
                if "usage" in response_data:
                    metadata["usage"] = response_data["usage"]
                if "auto_parameters" in response_data:
                    metadata["auto_parameters"] = response_data["auto_parameters"]
                if response_references:
                    metadata["references"] = response_references

                if not url:
                    logger.warning("Result %s missing URL, skipping", idx)
                    continue

                converted.append(
                    SearchResult(
                        title=title or "No title",
                        url=url,
                        snippet=content or "",
                        source="tavily_search",
                        timestamp=timestamp,
                        metadata=metadata if metadata else None,
                    )
                )
            except Exception as exc:
                logger.warning("Error converting result %s: %s", idx, exc, exc_info=False)
                continue

        return converted

    async def health_check(self) -> bool:
        """Check if Tavily Search API is available and working."""
        try:
            test_params = {
                "query": "test",
                "max_results": 1,
                "search_depth": "basic",
            }
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = await asyncio.wait_for(
                self.client.post(
                    self.search_endpoint,
                    json=test_params,
                    headers=headers,
                ),
                timeout=HEALTH_CHECK_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()
            if "results" in data or "error" not in data:
                return True
            logger.warning("Tavily health check API error: %s", data.get("error", {}))
            return False
        except asyncio.TimeoutError:
            logger.error("Tavily Search API health check timed out")
            return False
        except Exception as exc:
            logger.error("Tavily Search API health check failed: %s", exc)
            return False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
