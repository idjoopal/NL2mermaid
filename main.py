"""
Prebuilt MCP Server

아키텍처:
1. main.py - MCP 서버 (Agents만 Tool로 등록)
2. agents/ - Modules를 불러오고 input/output 변환만 수행
3. modules/ - 기존 tool의 핵심 비즈니스 로직
4. utils/ - 다른 Modules가 공통으로 활용할만한 부분

"""
from fastmcp import FastMCP
from fastmcp.utilities.types import Image

from src.agents.nl2mermaid_agent import nl2mermaid_agent
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
# NL2Mermaid Tool
# =============================================================================
_NL2MERMAID_DESCRIPTION = """\
자연어 설명을 Mermaid 다이어그램 이미지(PNG)로 변환합니다. PPT용 프로세스 도식화에 최적화.

▸ 입력: query (자연어), diagram_type (선택), theme (선택)
▸ 출력: PNG 이미지

지원 다이어그램 타입:
- auto      : LLM이 자동 결정 (기본값)
- flowchart : 프로세스 흐름도
- sequence  : 시스템·팀 간 상호작용
- gantt     : 프로젝트 일정
- timeline  : 시계열 이벤트
- mindmap   : 개념 구조도

지원 테마: default | neutral | dark | forest
"""

@mcp.tool(
    name="NL2Mermaid",
    description=_NL2MERMAID_DESCRIPTION,
)
async def nl2mermaid_tool(
    query: str,
    diagram_type: str = "auto",
    theme: str = "default",
) -> Image:
    """
    자연어를 Mermaid 다이어그램 이미지로 변환합니다.

    Args:
        query: 다이어그램으로 표현할 자연어 설명
        diagram_type: 다이어그램 타입 (auto | flowchart | sequence | gantt | timeline | mindmap)
        theme: 테마 (default | neutral | dark | forest)

    Returns:
        PNG 이미지
    """
    return await nl2mermaid_agent(query=query, diagram_type=diagram_type, theme=theme)


# =============================================================================
# Gunicorn용 앱 노출
# =============================================================================
app = mcp.http_app
