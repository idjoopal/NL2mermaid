"""
Schemas for web search module.

각 검색 서비스가 받는 파라미터를 Pydantic 모델로 정의합니다.
"""
from typing import List, Literal, Optional, Union
from pydantic import BaseModel, Field

from .constants import MIN_MAX_RESULTS, MAX_MAX_RESULTS
from .prompts import PARAM_DESCRIPTIONS


class SearchBusinessInfoParams_Tavily(BaseModel):
    """Parameters for tavily_search tool."""

    query: str = Field(..., description=PARAM_DESCRIPTIONS["query"])
    max_results: int = Field(
        3,
        ge=MIN_MAX_RESULTS,
        le=MAX_MAX_RESULTS,
        description=PARAM_DESCRIPTIONS["max_results"],
    )
    search_depth: str = Field(
        "basic",
        description=PARAM_DESCRIPTIONS["search_depth"],
    )
    include_answer: bool = Field(
        True,
        description=PARAM_DESCRIPTIONS["include_answer"],
    )
    include_domains: List[str] = Field(
        default_factory=list,
        description=PARAM_DESCRIPTIONS["include_domains"],
    )
    exclude_domains: List[str] = Field(
        default_factory=list,
        description=PARAM_DESCRIPTIONS["exclude_domains"],
    )


class SearchBusinessInfoParams_Perplexity(BaseModel):
    """Parameters for perplexity_search tool."""

    query: Union[str, List[str]] = Field(
        ...,
        description=PARAM_DESCRIPTIONS["query_perplexity"],
    )
    max_results: int = Field(
        3,
        ge=MIN_MAX_RESULTS,
        le=MAX_MAX_RESULTS,
        description=PARAM_DESCRIPTIONS["max_results"],
    )
    max_tokens: int = Field(
        10000,
        ge=1,
        description=PARAM_DESCRIPTIONS["max_tokens"],
    )
    max_tokens_per_page: int = Field(
        4096,
        ge=1,
        description=PARAM_DESCRIPTIONS["max_tokens_per_page"],
    )
    country: str = Field(
        "",
        description=PARAM_DESCRIPTIONS["country"],
    )
    search_domain_filter: List[str] = Field(
        default_factory=list,
        description=PARAM_DESCRIPTIONS["search_domain_filter"],
    )
    search_language_filter: List[str] = Field(
        default_factory=list,
        description=PARAM_DESCRIPTIONS["search_language_filter"],
    )
    search_recency_filter: Optional[Literal["hour", "day", "week", "month", "year"]] = Field(
        default=None,
        description=PARAM_DESCRIPTIONS["search_recency_filter"],
    )
    search_after_date_filter: str = Field(
        "",
        description=PARAM_DESCRIPTIONS["search_after_date_filter"],
    )
    search_before_date_filter: str = Field(
        "",
        description=PARAM_DESCRIPTIONS["search_before_date_filter"],
    )
    last_updated_after_filter: str = Field(
        "",
        description=PARAM_DESCRIPTIONS["last_updated_after_filter"],
    )
    last_updated_before_filter: str = Field(
        "",
        description=PARAM_DESCRIPTIONS["last_updated_before_filter"],
    )
    display_server_time: bool = Field(
        False,
        description=PARAM_DESCRIPTIONS["display_server_time"],
    )


# service.py에서 공통 타입으로 사용
SearchBusinessInfoParams = Union[
    SearchBusinessInfoParams_Tavily,
    SearchBusinessInfoParams_Perplexity,
]
