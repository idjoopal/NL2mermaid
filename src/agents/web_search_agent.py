"""
Web Search Agent

Main.py에서 Tool로 등록되는 Agent 단위입니다.
- Modules (web_search)를 불러와서 사용
- Input/Output 변환만 담당
- 비즈니스 로직은 Modules에 위임

================================================================================
REQUIRED MODULES (필수 의존성)
================================================================================
이 Agent가 실행되기 위해 필요한 Module 목록:

1. modules/web_search/
   - service.py : 핵심 비즈니스 로직 (Perplexity/Tavily API 호출)
   - config/    : 설정 (services_config.yaml)

2. utils/
   - config_loader.py : 환경변수 로더
   - logger.py        : JSON 형식 로거

환경 설정 파일 (agents/agent_env/ 폴더에 위치):
   - agents/agent_env/web_search.env : Web Search Agent 전용 환경변수
================================================================================
"""
import time

from src.modules.web_search import web_search_service
from src.utils.logger import get_logger

logger = get_logger("web_search_agent")


async def web_search_agent(query: str) -> str:
    """
    Web Search Agent - 외부 웹 검색을 수행합니다.

    [역할]
    - Input: 사용자로부터 받은 검색 질의 (str)
    - Output: 검색 결과 텍스트 (str)
    - 비즈니스 로직: modules/web_search의 service에 위임

    Args:
        query: 사용자의 검색 질의

    Returns:
        검색 결과 문자열
    """
    start_time = time.time()
    logger.info("[REQUEST] web_search, query=%s", query)

    try:
        result = await web_search_service.execute(query=query)
        elapsed_time = time.time() - start_time
        logger.info(
            "[RESPONSE] status=success, elapsed_time_ms=%s, result_length=%s",
            round(elapsed_time * 1000, 2),
            len(result),
        )
        return result
    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(
            "[RESPONSE] status=error, elapsed_time_ms=%s, error=%s",
            round(elapsed_time * 1000, 2),
            str(e),
        )
        return _format_error(str(e))


def _format_error(error_message: str) -> str:
    """에러 메시지를 포맷팅합니다."""
    return f"죄송합니다. 요청을 처리하는 중 오류가 발생했습니다: {error_message}"
