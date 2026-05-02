"""
Web Search Module - Service

외부 검색 API(Perplexity, Tavily)를 호출하여 웹 검색 결과를 반환합니다.
MCP 라이브러리에 의존하지 않는 순수 Python 구현입니다.

원본: search-mcp/src/tools/SearchAPI/service.py + adapter.py
"""
import asyncio
import logging
import traceback
import hashlib
from typing import Dict, Any, List, Optional, Type, Union

from .types import (
    SearchBusinessInfoParams,
    SearchBusinessInfoParams_Perplexity,
    SearchBusinessInfoParams_Tavily,
)
from .providers.base import BaseSearchService, SearchResult
from .providers.tavily_search import TavilySearchService
from .providers.perplexity_search import PerplexitySearchService
from .constants import (
    SERVICE_PERPLEXITY,
    SERVICE_TAVILY,
    ERROR_NO_SERVICES,
)
from .config.config import web_search_config

logger = logging.getLogger(__name__)


class WebSearchService:
    """Web search service for business logic and API calls."""

    # ── 확장 포인트 ──────────────────────────────────────────────
    # 새 서비스 추가 시 아래 dict에 한 줄씩 추가하세요.
    # ─────────────────────────────────────────────────────────────

    # 정규(canonical) 서비스 이름 → Provider 클래스
    _SERVICE_REGISTRY: Dict[str, Type[BaseSearchService]] = {
        SERVICE_TAVILY: TavilySearchService,
        SERVICE_PERPLEXITY: PerplexitySearchService,
    }

    # 기본 검색 서비스 (execute() 호출 시 target_services 미지정 시 사용)
    DEFAULT_SERVICE = SERVICE_TAVILY

    def __init__(self) -> None:
        self._services: Dict[str, BaseSearchService] = {}
        self._initialize_services()

    def _initialize_services(self) -> None:
        """Initialize enabled services from the registry (canonical names only)."""
        for service_name, service_class in self._SERVICE_REGISTRY.items():
            service_config = web_search_config.get_service_config(service_name)
            if not service_config.get("enabled", True):
                logger.info("Service %s is disabled, skipping", service_name)
                continue
            try:
                self._services[service_name] = service_class(config=service_config)
                logger.info("Initialized service: %s", service_name)
            except Exception as exc:
                logger.error("Failed to initialize service %s: %s", service_name, exc)

    def get_available_service_names(self) -> List[str]:
        """Return list of available (initialized) service names."""
        return list(self._services.keys())

    def get_services(self) -> Dict[str, BaseSearchService]:
        """Expose initialized services for health checks."""
        return self._services

    # ─────────────────────────────────────────────────────────────
    # execute() - 모듈 워크플로우 진입점
    # ─────────────────────────────────────────────────────────────

    async def execute(
        self,
        query: str,
        target_services: Optional[List[str]] = None,
    ) -> str:
        """
        웹 검색을 수행합니다. (모듈 워크플로우 진입점)

        Args:
            query: 검색 질의 문자열
            target_services: 사용할 검색 서비스 목록 (기본: ["perplexity"])

        Returns:
            검색 결과 텍스트
        """
        if not query or not query.strip():
            return "❌ 검색어가 입력되지 않았습니다."

        if target_services is None:
            target_services = [self.DEFAULT_SERVICE]

        # target_services에 따라 적절한 파라미터 모델 선택
        if SERVICE_PERPLEXITY in target_services:
            params = SearchBusinessInfoParams_Perplexity(query=query.strip())
        else:
            params = SearchBusinessInfoParams_Tavily(query=query.strip())

        return await self.search_business_info(params, target_services=target_services)

    # ─────────────────────────────────────────────────────────────
    # 내부 검색 로직
    # ─────────────────────────────────────────────────────────────

    async def search_business_info(
        self,
        params: SearchBusinessInfoParams,
        target_services: Optional[List[str]] = None,
    ) -> str:
        """
        Process search request for business information.
        """
        try:
            if not self._services:
                return f"❌ {ERROR_NO_SERVICES}"

            if target_services:
                services_to_search = [
                    service_name
                    for service_name in target_services
                    if service_name in self._services
                ]
            else:
                services_to_search = list(self._services.keys())

            if not services_to_search:
                return f"❌ {ERROR_NO_SERVICES}"

            # 파라미터는 스키마에 따라 전달 (auto_parameters는 서비스 설정에 따름)
            search_kwargs = params.model_dump(exclude={"query"}, exclude_none=True)

            tasks = [
                self._search_service(self._services[name], params.query, **search_kwargs)
                for name in services_to_search
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            formatted_results = [
                {"service": services_to_search[i], "error": str(r), "results": []}
                if isinstance(r, Exception)
                else r
                for i, r in enumerate(results)
            ]

            # LLM이 reference를 빠르게 확인할 수 있도록 상위 필드로 집계
            aggregated_references: List[Dict[str, Any]] = []
            aggregated_documents: List[Dict[str, Any]] = []
            results_overview: List[Dict[str, Any]] = []
            reference_lines: List[str] = []
            for item in formatted_results:
                if not isinstance(item, dict):
                    continue
                service_name = item.get("service")
                for ref in item.get("references", []) or []:
                    ref_item = dict(ref)
                    if service_name and "service" not in ref_item:
                        ref_item["service"] = service_name
                    aggregated_references.append(ref_item)
                    ref_title = ref_item.get("ref_title") or ref_item.get("source_title") or ""
                    ref_url = ref_item.get("ref_url") or ref_item.get("source_url") or ""
                    ref_snippet = ref_item.get("ref_snippet") or ""
                    parts = []
                    if ref_title:
                        parts.append(str(ref_title))
                    if ref_url:
                        parts.append(str(ref_url))
                    if ref_snippet:
                        parts.append(str(ref_snippet))
                    if parts:
                        prefix = f"[{service_name}] " if service_name else ""
                        reference_lines.append(prefix + " | ".join(parts))
                for doc in item.get("documents", []) or []:
                    doc_item = dict(doc)
                    if service_name and isinstance(doc_item.get("document"), dict):
                        doc_item["document"].setdefault("service", service_name)
                    aggregated_documents.append(doc_item)
                for r in item.get("results", []) or []:
                    results_overview.append(
                        {
                            "service": service_name,
                            "title": r.get("title"),
                            "url": r.get("url"),
                            "snippet": r.get("snippet"),
                            "timestamp": r.get("timestamp"),
                        }
                    )

            response_payload = {
                "query": params.query,
                "services_searched": services_to_search,
                "results_overview": results_overview,
                "references": aggregated_references,
                "reference_text": "\n".join(reference_lines),
                "documents": aggregated_documents,
                "results": formatted_results,
            }
            return self._format_response_text(response_payload)
        except Exception as exc:
            logger.error("Search tool error:\n%s", traceback.format_exc())
            return f"❌ 처리 중 오류가 발생했습니다: {exc}"

    @staticmethod
    def _format_response_text(payload: Dict[str, Any]) -> str:
        """LLM이 읽기 쉬운 텍스트 형태로 검색 결과를 정리합니다."""
        query = payload.get("query", "")
        services = payload.get("services_searched", []) or []
        overview = payload.get("results_overview", []) or []
        references = payload.get("references", []) or []
        results = payload.get("results", []) or []
        documents = payload.get("documents", []) or []

        lines: List[str] = []
        lines.append("Search Results")
        lines.append(f"Query: {query}")
        if services:
            lines.append("Services: " + ", ".join(str(s) for s in services))
        lines.append("")

        lines.append("## Results Overview")
        if not overview:
            lines.append("- (no results)")
        else:
            for idx, item in enumerate(overview, 1):
                title = item.get("title") or ""
                url = item.get("url") or ""
                snippet = item.get("snippet") or ""
                timestamp = item.get("timestamp") or ""
                parts = [p for p in [title, url, snippet] if p]
                line = f"{idx}. " + " | ".join(parts)
                if timestamp:
                    line += f" | {timestamp}"
                lines.append(line)

        lines.append("")
        lines.append("## References (Detailed)")
        if not references:
            lines.append("- (no references)")
        else:
            for idx, ref in enumerate(references, 1):
                title = ref.get("ref_title") or ref.get("source_title") or ""
                url = ref.get("ref_url") or ref.get("source_url") or ""
                snippet = ref.get("ref_snippet") or ""
                service = ref.get("service") or ""
                source = ref.get("ref_source") or ""
                ref_extra = ref.get("ref_extra")
                ref_raw = ref.get("ref_raw")
                src_idx = ref.get("source_result_index")
                src_title = ref.get("source_title") or ""
                src_url = ref.get("source_url") or ""

                header = f"{idx}. Reference"
                if service:
                    header += f" [{service}]"
                lines.append(header)
                if title:
                    lines.append(f"- Title: {title}")
                if url:
                    lines.append(f"- URL: {url}")
                if snippet:
                    lines.append(f"- Snippet: {snippet}")
                if source:
                    lines.append(f"- Source: {source}")
                if src_idx is not None:
                    lines.append(f"- From Result Index: {src_idx}")
                if src_title:
                    lines.append(f"- From Result Title: {src_title}")
                if src_url:
                    lines.append(f"- From Result URL: {src_url}")
                if ref_extra:
                    lines.append(f"- Extra: {ref_extra}")
                if ref_raw is not None:
                    lines.append(f"- Raw: {ref_raw}")
                lines.append("")

        lines.append("## References + Documents (Paired)")
        doc_by_url: Dict[str, Dict[str, Any]] = {}
        for doc in documents:
            doc_data = (doc.get("document") or {}).get("data") or {}
            url = doc_data.get("url")
            if url:
                doc_by_url[str(url)] = doc

        if not references and not documents:
            lines.append("- (no references/documents)")
        else:
            paired = 0
            for idx, ref in enumerate(references, 1):
                title = ref.get("ref_title") or ref.get("source_title") or ""
                url = ref.get("ref_url") or ref.get("source_url") or ""
                snippet = ref.get("ref_snippet") or ""
                service = ref.get("service") or ""
                source = ref.get("ref_source") or ""
                ref_extra = ref.get("ref_extra")
                ref_raw = ref.get("ref_raw")
                src_idx = ref.get("source_result_index")
                src_title = ref.get("source_title") or ""
                src_url = ref.get("source_url") or ""

                header = f"{idx}. Reference"
                if service:
                    header += f" [{service}]"
                lines.append(header)
                if title:
                    lines.append(f"- Title: {title}")
                if url:
                    lines.append(f"- URL: {url}")
                if snippet:
                    lines.append(f"- Snippet: {snippet}")
                if source:
                    lines.append(f"- Source: {source}")
                if src_idx is not None:
                    lines.append(f"- From Result Index: {src_idx}")
                if src_title:
                    lines.append(f"- From Result Title: {src_title}")
                if src_url:
                    lines.append(f"- From Result URL: {src_url}")
                if ref_extra:
                    lines.append(f"- Extra: {ref_extra}")
                if ref_raw is not None:
                    lines.append(f"- Raw: {ref_raw}")

                # Paired document by URL
                if url and url in doc_by_url:
                    doc = doc_by_url.pop(url)
                    doc_data = (doc.get("document") or {}).get("data") or {}
                    doc_id = (doc.get("document") or {}).get("id") or doc_data.get("document_id") or ""
                    lines.append("- Document:")
                    if doc_id:
                        lines.append(f"- ID: {doc_id}")
                    if doc_data.get("url"):
                        lines.append(f"- URL: {doc_data.get('url')}")
                    if doc_data.get("title"):
                        lines.append(f"- Title: {doc_data.get('title')}")
                    if doc_data.get("tool_name"):
                        lines.append(f"- Tool: {doc_data.get('tool_name')}")
                    if doc_data.get("content"):
                        lines.append("- Content:")
                        lines.append("----- DOCUMENT START -----")
                        lines.append(doc_data.get("content"))
                        lines.append("----- DOCUMENT END -----")
                    if doc_data.get("_excludes"):
                        lines.append(f"- Excludes: {doc_data.get('_excludes')}")
                    paired += 1

                lines.append("-" * 80)
                lines.append("")
                lines.append("")

            # Remaining documents not paired by URL
            if doc_by_url:
                lines.append("## Unpaired Documents")
                for idx, doc in enumerate(doc_by_url.values(), 1):
                    doc_data = (doc.get("document") or {}).get("data") or {}
                    doc_id = (doc.get("document") or {}).get("id") or doc_data.get("document_id") or ""
                    lines.append(f"{idx}. Document")
                    if doc_id:
                        lines.append(f"- ID: {doc_id}")
                    if doc_data.get("url"):
                        lines.append(f"- URL: {doc_data.get('url')}")
                    if doc_data.get("title"):
                        lines.append(f"- Title: {doc_data.get('title')}")
                    if doc_data.get("tool_name"):
                        lines.append(f"- Tool: {doc_data.get('tool_name')}")
                    if doc_data.get("content"):
                        lines.append("- Content:")
                        lines.append("----- DOCUMENT START -----")
                        lines.append(doc_data.get("content"))
                        lines.append("----- DOCUMENT END -----")
                    if doc_data.get("_excludes"):
                        lines.append(f"- Excludes: {doc_data.get('_excludes')}")
                    lines.append("-" * 80)
                    lines.append("")
                    lines.append("")

        # 결과별 메타데이터 블록 (reference 외 추가 정보 확인용)
        if results:
            lines.append("## Result Metadata")
            for s_idx, service_block in enumerate(results, 1):
                svc = service_block.get("service", "")
                svc_results = service_block.get("results", []) or []
                if not svc_results:
                    continue
                lines.append(f"### Service: {svc}" if svc else f"### Service #{s_idx}")
                for r_idx, r in enumerate(svc_results, 1):
                    title = r.get("title") or ""
                    url = r.get("url") or ""
                    snippet = r.get("snippet") or ""
                    timestamp = r.get("timestamp") or ""
                    metadata = r.get("metadata") or {}
                    lines.append(f"{r_idx}. Result")
                    if title:
                        lines.append(f"- Title: {title}")
                    if url:
                        lines.append(f"- URL: {url}")
                    if snippet:
                        lines.append(f"- Snippet: {snippet}")
                    if timestamp:
                        lines.append(f"- Timestamp: {timestamp}")
                    if metadata:
                        lines.append(f"- Metadata: {metadata}")
                    lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _normalize_references(results: List[SearchResult]) -> List[Dict[str, Any]]:
        """
        Tavily 응답의 reference 정보를 항목별로 정리해 반환합니다.
        """
        normalized: List[Dict[str, Any]] = []
        for idx, result in enumerate(results):
            metadata = result.metadata or {}
            refs = metadata.get("references")
            if not refs:
                continue
            if isinstance(refs, dict):
                refs = [refs]
            elif not isinstance(refs, list):
                refs = [{"value": refs}]

            for ref in refs:
                item: Dict[str, Any] = {
                    "source_result_index": idx,
                    "source_title": result.title,
                    "source_url": result.url,
                }
                if isinstance(ref, dict):
                    if "title" in ref:
                        item["ref_title"] = ref.get("title")
                    if "url" in ref:
                        item["ref_url"] = ref.get("url")
                    if "snippet" in ref:
                        item["ref_snippet"] = ref.get("snippet")
                    if "source" in ref:
                        item["ref_source"] = ref.get("source")
                    extra = {
                        k: v
                        for k, v in ref.items()
                        if k not in {"title", "url", "snippet", "source"}
                    }
                    if extra:
                        item["ref_extra"] = extra
                else:
                    item["ref_raw"] = ref
                normalized.append(item)

        return normalized

    @staticmethod
    def _build_documents(
        references: List[Dict[str, Any]],
        results: List[SearchResult],
        tool_name: str,
    ) -> List[Dict[str, Any]]:
        """
        참고 문서 목록을 tool output 형식으로 구성합니다.
        """
        documents: List[Dict[str, Any]] = []
        seen_urls: set[str] = set()

        def _doc_id(url: str, title: str) -> str:
            key = f"{url}|{title}".encode("utf-8")
            return hashlib.sha1(key).hexdigest()

        def _append_doc(url: str, title: str, content: str) -> None:
            if not url:
                return
            if url in seen_urls:
                return
            seen_urls.add(url)
            doc_id = _doc_id(url, title)
            documents.append(
                {
                    "type": "document",
                    "document": {
                        "id": doc_id,
                        "data": {
                            "url": url,
                            "title": title or "",
                            "content": content or "",
                            "document_id": doc_id,
                            "_excludes": [
                                "document_id",
                                "tool_call_id",
                                "compass_doc_id",
                                "compass_chunk_sort_id",
                                "doc_text",
                                "tool_name",
                            ],
                            "tool_name": tool_name,
                        },
                    },
                }
            )

        if references:
            for ref in references:
                url = ref.get("ref_url") or ref.get("source_url") or ""
                title = ref.get("ref_title") or ref.get("source_title") or ""
                content = ref.get("ref_snippet") or ""
                _append_doc(url, title, content)
        else:
            for result in results:
                _append_doc(result.url, result.title, result.snippet)

        return documents

    @staticmethod
    async def _search_service(
        service: BaseSearchService,
        query: Union[str, List[str]],
        **kwargs,
    ) -> Dict[str, Any]:
        """Search a single service and format results."""
        try:
            api_params = {"query": query, **{k: v for k, v in kwargs.items() if v is not None}}
            results = await service.search(query, **kwargs)
            num_results = len(results)
            references = WebSearchService._normalize_references(results)
            documents = WebSearchService._build_documents(
                references,
                results,
                tool_name=service.get_service_name(),
            )
            return {
                "service": service.get_service_name(),
                "success": True,
                "num_results": num_results,
                "api_parameters": api_params,
                "references": references,
                "documents": documents,
                "results": [
                    {
                        "title": r.title,
                        "url": r.url,
                        "snippet": r.snippet,
                        "timestamp": r.timestamp.isoformat(),
                        "metadata": r.metadata or {},
                    }
                    for r in results
                ],
            }
        except Exception as exc:
            logger.error("Error searching %s: %s", service.get_service_name(), exc)
            return {
                "service": service.get_service_name(),
                "success": False,
                "error": str(exc),
                "num_results": 0,
                "results": [],
                "api_parameters": {"query": query, **{k: v for k, v in kwargs.items() if v is not None}},
            }


web_search_service = WebSearchService()
