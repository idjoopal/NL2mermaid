"""
Tool descriptions for web search module.
These descriptions are used by LLMs when calling tools via MCP protocol.
"""

# ============================================================================
# Parameter Field Descriptions (Pydantic schema용 — types.py에서 import)
# ============================================================================
PARAM_DESCRIPTIONS = {
    # ── 공통 ──────────────────────────────────────────────────────────────
    "query": (
        "검색 핵심 키워드. 날짜 지역 '뉴스' 등 필터 표현은 제외하고 핵심 주제만 작성. "
        "예: '삼성전자 실적', 'AI 시장 트렌드', '테슬라 주가 전망'"
    ),
    "query_perplexity": (
        "Perplexity 검색어. 문자열 1개 또는 문자열 배열(string[]) 모두 허용. "
        "예: 'AI 트렌드 2026' 또는 ['Comet Browser', 'Perplexity AI']"
    ),
    "max_results": "서비스별 최대 결과 수 (1~50, 기본값 3).",

    # ── Tavily 전용 ────────────────────────────────────────────────────────
    "search_depth": '검색 깊이. "basic" | "advanced" | "fast" | "ultra-fast".',
    "include_answer": "Tavily 요약 답변 포함 여부. 기본 true.",
    "include_domains": (
        "포함할 도메인 리스트. 사용자가 특정 출처를 요청할 때만 사용. "
        "예: ['nytimes.com', 'reuters.com']. 프로토콜 제외, 도메인만."
    ),
    "exclude_domains": (
        "제외할 도메인 리스트. 사용자가 특정 출처 제외를 요청할 때만 사용. "
        "예: ['reddit.com']. 프로토콜 제외, 도메인만."
    ),

    # ── Perplexity 전용 ───────────────────────────────────────────────────
    "search_domain_filter": (
        "검색 대상 도메인 필터. 포함할 도메인은 그대로, 제외할 도메인은 '-' 접두사. "
        "예: ['example.com', '-reddit.com']"
    ),
    "search_language_filter": (
        "검색 언어 필터. ISO 639-1 코드 목록. "
        "예: ['en', 'ko']"
    ),
    "country": "검색 대상 국가. ISO 국가 코드 (예: 'KR', 'US', 'JP').",
    "max_tokens": "검색 결과 전체 최대 토큰 수. 기본 10000.",
    "max_tokens_per_page": "개별 페이지당 최대 토큰 수. 기본 4096.",
    "search_recency_filter": "최신성 필터. 'hour' | 'day' | 'week' | 'month' | 'year'.",
    "search_after_date_filter": "해당 날짜 이후 작성 문서만 검색 (YYYY-MM-DD).",
    "search_before_date_filter": "해당 날짜 이전 작성 문서만 검색 (YYYY-MM-DD).",
    "last_updated_after_filter": "해당 날짜 이후 수정 문서만 검색 (YYYY-MM-DD).",
    "last_updated_before_filter": "해당 날짜 이전 수정 문서만 검색 (YYYY-MM-DD).",
    "display_server_time": "응답에 server_time 포함 여부. 기본 false.",
}


# ============================================================================
# Web Search Tool Description (MCP tool 등록 시 사용)
# ============================================================================
WEB_SEARCH_DESCRIPTION = """외부 웹에서 비즈니스 정보를 검색합니다. (Perplexity / Tavily Search)

사용자 질의를 받아 외부 검색 API(Perplexity, Tavily)를 호출하고 결과를 반환합니다.

## 사용 예시
- "삼성전자 최신 실적 뉴스"
- "AI 시장 트렌드 2026"
- "테슬라 주가 전망"

## 응답 형식
검색 결과 요약, 참조 URL, 문서 내용 등을 텍스트로 반환합니다.
"""
