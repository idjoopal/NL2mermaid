"""
Prebuilt MCP Server

아키텍처:
1. main.py - MCP 서버 (Agents만 Tool로 등록)
2. agents/ - Modules를 불러오고 input/output 변환만 수행
3. modules/ - 기존 tool의 핵심 비즈니스 로직
4. utils/ - 다른 Modules가 공통으로 활용할만한 부분

"""
from fastmcp import FastMCP

from src.agents.web_search_agent import web_search_agent


# =============================================================================
# MCP 서버 생성
# =============================================================================
mcp = FastMCP("Prebuilt MCP Server")


# =============================================================================
# Web Search Tool
# =============================================================================
_WEB_SEARCH_DESCRIPTION = """\
실시간 외부 웹 검색으로 뉴스·시장 동향·트렌드 등 최신 정보를 조회합니다.

▸ 입력: user_query
▸ 출력: 웹 검색 결과 (Tavily / Perplexity 기반)
"""

@mcp.tool(
    name="Web_Search",
    description=_WEB_SEARCH_DESCRIPTION,
)

async def web_search_tool(input: str) -> str:
    """
    외부 웹 검색 도구입니다.
    사용자 질의를 받아 Perplexity/Tavily 검색 API를 호출합니다.

    Args:
        input: 사용자 검색 질의

    Returns:
        검색 결과 텍스트
    """
    return await web_search_agent(query=input)


# =============================================================================
# Gunicorn용 앱 노출
# =============================================================================
app = mcp.http_app
