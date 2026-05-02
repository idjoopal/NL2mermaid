"""
NL2Mermaid Module - Service

자연어 질의를 Mermaid 다이어그램 코드로 변환합니다.
LLMManager를 통해 OpenAI / Cohere 모델을 사용합니다.
"""
import logging
import re

from src.utils.llm_manager import LLMManager

from .config.config import NL2MERMAID_MODEL_ID
from .constants import (
    DEFAULT_DIAGRAM_TYPE,
    DIAGRAM_TYPE_AUTO,
    ERROR_EMPTY_QUERY,
    ERROR_GENERATION_FAILED,
    SUPPORTED_DIAGRAM_TYPES,
)
from .exceptions import GenerationFailedError, InvalidQueryError
from .prompts import GENERATION_PROMPTS, SYSTEM_PROMPT, TYPE_DETECTION_PROMPT
from .types import GenerationResult

logger = logging.getLogger(__name__)


class NL2MermaidService:

    def __init__(self) -> None:
        self._llm = LLMManager()

    async def execute(
        self,
        query: str,
        diagram_type: str = DEFAULT_DIAGRAM_TYPE,
    ) -> GenerationResult:
        """
        자연어 질의를 Mermaid 코드로 변환합니다. (모듈 진입점)

        Args:
            query: 다이어그램으로 표현할 자연어 설명
            diagram_type: 다이어그램 타입 (auto | flowchart | sequence | gantt | timeline | mindmap)

        Returns:
            GenerationResult (mermaid_code, diagram_type, model_used)
        """
        if not query or not query.strip():
            raise InvalidQueryError(ERROR_EMPTY_QUERY)

        dtype = diagram_type.strip().lower()
        if dtype not in SUPPORTED_DIAGRAM_TYPES:
            dtype = DIAGRAM_TYPE_AUTO

        # auto이면 타입 먼저 결정
        if dtype == DIAGRAM_TYPE_AUTO:
            dtype = await self._detect_type(query)

        mermaid_code = await self._generate(query, dtype)

        return GenerationResult(
            mermaid_code=mermaid_code,
            diagram_type=dtype,
            model_used=NL2MERMAID_MODEL_ID,
        )

    async def _detect_type(self, query: str) -> str:
        """질의를 보고 적합한 다이어그램 타입을 결정합니다."""
        prompt = TYPE_DETECTION_PROMPT.format(query=query)
        try:
            result = await self._llm.ainvoke(
                f"{SYSTEM_PROMPT}\n\n{prompt}",
                model_name=NL2MERMAID_MODEL_ID,
            )
            detected = result["content"].strip().lower()
            # 유효한 타입만 허용
            for dtype in SUPPORTED_DIAGRAM_TYPES:
                if dtype != DIAGRAM_TYPE_AUTO and dtype in detected:
                    logger.info("Auto-detected diagram type: %s", dtype)
                    return dtype
        except Exception as e:
            logger.warning("Type detection failed, defaulting to flowchart: %s", e)
        return "flowchart"

    async def _generate(self, query: str, diagram_type: str) -> str:
        """지정된 타입으로 Mermaid 코드를 생성합니다."""
        template = GENERATION_PROMPTS.get(diagram_type, GENERATION_PROMPTS["flowchart"])
        prompt = f"{SYSTEM_PROMPT}\n\n{template.format(query=query)}"

        try:
            result = await self._llm.ainvoke(prompt, model_name=NL2MERMAID_MODEL_ID)
            code = self._clean_code(result["content"])
            logger.info("Generated %s diagram (%d chars)", diagram_type, len(code))
            return code
        except Exception as e:
            raise GenerationFailedError(ERROR_GENERATION_FAILED.format(error=e)) from e

    @staticmethod
    def _clean_code(raw: str) -> str:
        """LLM 응답에서 순수 Mermaid 코드만 추출합니다."""
        # 코드 블록 마커 제거
        raw = re.sub(r"^```(?:mermaid)?\s*", "", raw.strip(), flags=re.IGNORECASE)
        raw = re.sub(r"\s*```$", "", raw.strip())
        return raw.strip()


nl2mermaid_service = NL2MermaidService()
