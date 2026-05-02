"""
NL2Mermaid Agent

MCP에 등록되는 Agent 단위입니다.
nl2mermaid + mermaid_renderer 두 모듈을 조합하고,
렌더링 실패 시 에러 피드백으로 최대 2회 재시도합니다.

================================================================================
REQUIRED MODULES
================================================================================
1. modules/nl2mermaid/   : 자연어 → Mermaid 코드 생성 (LLM)
2. modules/mermaid_renderer/ : Mermaid 코드 → 이미지 렌더링
환경 설정: agents/agent_env/nl2mermaid.env
================================================================================
"""
import time

from fastmcp.utilities.types import Image

from src.modules.mermaid_renderer import mermaid_renderer_service
from src.modules.mermaid_renderer.exceptions import RenderFailedError
from src.modules.nl2mermaid import nl2mermaid_service
from src.utils.logger import get_logger

logger = get_logger("nl2mermaid_agent")

MAX_RETRY = 2


async def nl2mermaid_agent(
    query: str,
    diagram_type: str = "auto",
    theme: str = "default",
) -> Image:
    """
    자연어 질의를 Mermaid 다이어그램 이미지로 변환합니다.

    Args:
        query: 다이어그램으로 표현할 자연어 설명
        diagram_type: 다이어그램 타입 (auto | flowchart | sequence | gantt | timeline | mindmap)
        theme: 다이어그램 테마 (default | neutral | dark | forest)

    Returns:
        FastMCP Image 객체 (PNG)
    """
    start_time = time.time()
    logger.info("[REQUEST] nl2mermaid, query=%s, diagram_type=%s, theme=%s", query, diagram_type, theme)

    error_feedback = ""

    for attempt in range(1, MAX_RETRY + 1):
        try:
            # 1. 자연어 → Mermaid 코드 생성
            generation_query = query if not error_feedback else f"{query}\n\n[이전 시도 오류: {error_feedback}]"
            gen_result = await nl2mermaid_service.execute(
                query=generation_query,
                diagram_type=diagram_type,
            )

            logger.info(
                "[STEP] code_generated, attempt=%d, type=%s, length=%d",
                attempt, gen_result.diagram_type, len(gen_result.mermaid_code),
            )

            # 2. Mermaid 코드 → 이미지 렌더링
            render_result = await mermaid_renderer_service.execute(
                mermaid_code=gen_result.mermaid_code,
                theme=theme,
                save_to_file=True,
            )

            elapsed = round((time.time() - start_time) * 1000, 2)
            logger.info(
                "[RESPONSE] status=success, attempt=%d, elapsed_time_ms=%s, provider=%s, size=%d",
                attempt, elapsed, render_result.provider, len(render_result.image_bytes),
            )

            return Image(data=render_result.image_bytes, format="png")

        except RenderFailedError as e:
            error_feedback = str(e)
            logger.warning("[RETRY] attempt=%d, render_error=%s", attempt, error_feedback)
            if attempt == MAX_RETRY:
                break

        except Exception as e:
            elapsed = round((time.time() - start_time) * 1000, 2)
            logger.error("[RESPONSE] status=error, elapsed_time_ms=%s, error=%s", elapsed, str(e))
            raise

    elapsed = round((time.time() - start_time) * 1000, 2)
    logger.error("[RESPONSE] status=error, elapsed_time_ms=%s, error=render_failed_after_retry", elapsed)
    raise RuntimeError(f"렌더링에 {MAX_RETRY}회 실패했습니다. 마지막 오류: {error_feedback}")
