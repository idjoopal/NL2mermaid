"""
NL2Mermaid MCP Server

아키텍처:
1. main.py - MCP 서버 (Agents만 Tool로 등록)
2. agents/ - Modules를 불러오고 input/output 변환만 수행
3. modules/ - 기존 tool의 핵심 비즈니스 로직
4. utils/ - 다른 Modules가 공통으로 활용할만한 부분

"""
from fastmcp import FastMCP
from fastmcp.utilities.types import Image

from src.agents.nl2mermaid_agent import nl2mermaid_agent
from src.agents.ppt_agent import ppt_agent


# =============================================================================
# MCP 서버 생성
# =============================================================================
mcp = FastMCP("NL2Mermaid MCP Server")


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
# NL2PPT Tool
# =============================================================================
_NL2PPT_DESCRIPTION = """\
자연어 설명을 PPTX 프레젠테이션 파일로 자동 생성합니다.

LLM이 입력 내용을 슬라이드별로 구조화하고 선택한 템플릿에 맞게 PPTX 파일을 생성합니다.

▸ 입력: query (자연어 내용), template_name (템플릿), language (언어)
▸ 출력: JSON (파일 경로, 슬라이드 수, 요약)

내장 템플릿:
- business : 비즈니스 보고 (커버/목차/내용/차트/표/마무리)
- pitch    : 스타트업 피치덱 (문제/솔루션/시장/팀/요청)
- report   : 분석 보고서 (커버/요약/배경/분석/결론)
커스텀: ./custom_templates/*.yaml 자동 탐색

슬라이드 타입: 제목, 텍스트, 표, 차트(bar/line/pie), 2컨럼
"""

@mcp.tool(
    name="NL2PPT",
    description=_NL2PPT_DESCRIPTION,
)
async def nl2ppt_tool(
    query: str,
    template_name: str = "business",
    language: str = "ko",
) -> str:
    """
    자연어를 PPTX 프레젠테이션 파일로 변환합니다.

    Args:
        query: PPT에 담을 자연어 내용
        template_name: 템플릿 이름 (business | pitch | report | 커스텀명)
        language: 언어 코드 (ko | en)

    Returns:
        JSON 문자열 {file_path, slide_count, template, title, summary}
    """
    return await ppt_agent(query=query, template_name=template_name, language=language)


# =============================================================================
# Gunicorn용 앱 노출
# =============================================================================
app = mcp.http_app
