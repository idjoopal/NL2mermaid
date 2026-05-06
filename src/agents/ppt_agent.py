"""
PPT Agent

MCP에 등록되는 단위입니다.
ppt_content, ppt_generator 두 모듈을 조합하여 자연어 → PPTX 파일 변환을 수행합니다.

REQUIRED MODULES:
- modules/ppt_content/   : LLM 기반 슬라이드 내용 구조화
- modules/ppt_generator/ : python-pptx 기반 PPTX 파일 생성

환경 설정: agents/agent_env/ppt.env
"""
import json
import time

from src.modules.ppt_content import ppt_content_service
from src.modules.ppt_content.types import SlideSpec
from src.modules.ppt_generator import ppt_generator_service
from src.utils.logger import get_logger

logger = get_logger("ppt_agent")


async def ppt_agent(
    query: str,
    template_name: str = "business",
    language: str = "ko",
) -> str:
    start = time.time()
    logger.info(
        "[REQUEST] ppt_agent, template=%s, language=%s, query=%s",
        template_name, language, query[:100],
    )

    try:
        # 1. 템플릿 로드 후 SlideSpec 변환
        template_def = ppt_generator_service.get_template(template_name)
        slide_specs = [
            SlideSpec(
                slide_id=s.id,
                slide_type=s.type,
                placeholders=[p.name for p in s.placeholders],
                chart_type=s.chart_type,
            )
            for s in template_def.slides
        ]

        # 2. LLM 슬라이드 내용 구조화
        content = await ppt_content_service.execute(
            query=query,
            slide_specs=slide_specs,
            template_name=template_name,
            language=language,
        )

        # 3. PPTX 파일 생성
        result = await ppt_generator_service.execute(
            content=content,
            template_name=template_name,
            save_to_file=True,
        )

        elapsed = round((time.time() - start) * 1000, 2)
        logger.info(
            "[RESPONSE] status=success, elapsed_time_ms=%s, slides=%s, file=%s",
            elapsed, result.slide_count, result.file_path,
        )

        summary = "\n".join(
            f"{i + 1}. {s.title}" for i, s in enumerate(content.slides)
        )
        return json.dumps(
            {
                "file_path": result.file_path,
                "slide_count": result.slide_count,
                "template": template_name,
                "title": content.title,
                "summary": summary,
            },
            ensure_ascii=False,
        )

    except Exception as e:
        elapsed = round((time.time() - start) * 1000, 2)
        logger.error(
            "[RESPONSE] status=error, elapsed_time_ms=%s, error=%s", elapsed, str(e)
        )
        return json.dumps({"error": str(e)}, ensure_ascii=False)
