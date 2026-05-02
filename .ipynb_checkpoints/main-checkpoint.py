"""
Prebuilt MCP Server

아키텍처:
1. main.py - MCP 서버 (Agents만 Tool로 등록)
2. agents/ - Modules를 불러오고 input/output 변환만 수행
3. modules/ - 기존 tool의 핵심 비즈니스 로직
4. utils/ - 다른 Modules가 공통으로 활용할만한 부분
"""
from fastmcp import FastMCP
from src.agents.chitchat_agent import chitchat_agent
from src.agents.text2sql_agent import text2sql_agent
from src.agents.dart_search_agent import dart_search_router_agent
from src.agents.query_gateway_agent import query_gateway_agent
from src.agents.release_info_agent import release_info_agent
from src.modules.dart_search.assets.tool_descriptions import (
    DART_SEARCH_ROUTER_DESCRIPTION,
)

# =============================================================================
# MCP 서버 생성
# =============================================================================
mcp = FastMCP("Prebuilt MCP Server")


# =============================================================================
# Agent를 Tool로 등록
# =============================================================================

# @mcp.tool(name="Cohere_Chitchat", description="모델명 기반 자유대화 도구")
# async def chitchat_tool(input: str, model_name: str | None = None) -> str:
#     """
#     모델명을 기반으로 자유대화를 수행합니다.
    
#     Args:
#         input: 사용자의 메시지
#         model_name: 사용할 LLM 모델명 (예: command-r-plus, gpt-4o-mini)
    
#     Returns:
#         LLM 응답 문자열
#     """
#     return await chitchat_agent(input, model_name=model_name)


@mcp.tool(name="Text2SQL", description="자연어를 SQL로 변환하는 도구")
async def text2sql_tool(input: str, model_name: str | None = None) -> str:
    """
    자연어 질문을 SQL로 변환합니다.
    
    Args:
        input: 사용자의 자연어 질문
        model_name: 사용할 LLM 모델명 (예: command-r-plus, gpt-4o-mini)
    
    Returns:
        SQL 변환 결과
    """
    return await text2sql_agent(input, model_name=model_name)


@mcp.tool(
    name="Query_Gateway",
    description="질의를 분석해 엔티티/의도를 추출하고 최종 검색 방향(disclosure/db/web)을 결정하는 도구",
)
async def query_gateway_tool(input: str) -> str:
    """
    질의 게이트웨이 도구입니다.
    질의를 표준화하고 엔티티/의도를 분석한 뒤 검색 방향을 결정합니다.

    Args:
        input: 사용자 자연어 질의

    Returns:
        분석 결과 JSON 문자열
    """
    return await query_gateway_agent(input=input)


# =============================================================================
# Server Info Tool
# =============================================================================

@mcp.tool(
    name="Server_Release_Info",
    description="이 MCP 서버에 등록된 도구 목록과 릴리즈 이력을 확인합니다. 파라미터 없이 호출하면 됩니다.",
)
async def release_info_tool() -> str:
    """
    서버 도구 목록 및 릴리즈 정보를 반환합니다.

    Returns:
        도구 목록, 릴리즈 이력이 포함된 문자열
    """
    return await release_info_agent()


# =============================================================================
# DART Search Tool (Unified Router)
# =============================================================================

@mcp.tool(
    name="DART_Search",
    description=DART_SEARCH_ROUTER_DESCRIPTION,
)
async def dart_search_tool(input: str) -> str:
    """
    DART Search 라우터 도구입니다.
    사용자 질의를 받아 내부에서 적절한 DART 하위 기능으로 라우팅합니다.

    Args:
        input: 사용자 자연어 질의

    Returns:
        DART 조회 결과
    """
    return await dart_search_router_agent(query=input)


# =============================================================================
# Gunicorn용 앱 노출
# =============================================================================
app = mcp.http_app
