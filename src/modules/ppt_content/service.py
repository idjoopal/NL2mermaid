import json
import re

from src.utils.llm_manager import LLMManager
from src.utils.logger import get_logger
from .types import PptContent, SlideContent, ChartData, SlideSpec
from .prompts import SYSTEM_PROMPT, USER_PROMPT
from .config.config import PPT_CONTENT_MODEL_ID

logger = get_logger("ppt_content")


class PptContentService:
    def __init__(self):
        self.llm = LLMManager()

    async def execute(
        self,
        query: str,
        slide_specs: list[SlideSpec],
        template_name: str = "business",
        language: str = "ko",
    ) -> PptContent:
        if not query.strip():
            raise ValueError("query가 비어있습니다.")

        lang_str = "한국어" if language == "ko" else "English"
        system_prompt = SYSTEM_PROMPT.format(language=lang_str)
        user_prompt = USER_PROMPT.format(
            query=query,
            slide_specs=self._format_specs(slide_specs),
        )

        result = await self.llm.ainvoke(
            f"{system_prompt}\n\n{user_prompt}",
            model_name=PPT_CONTENT_MODEL_ID,
        )
        slides_data = self._parse_json(result["content"])
        slides = self._build_slides(slides_data, slide_specs)
        title = slides[0].title if slides else "프레젠테이션"

        return PptContent(slides=slides, title=title, template_name=template_name)

    def _format_specs(self, specs: list[SlideSpec]) -> str:
        lines = []
        for s in specs:
            line = f"- slide_id={s.slide_id}, type={s.slide_type}, placeholders={s.placeholders}"
            if s.chart_type:
                line += f", chart_type={s.chart_type}"
            lines.append(line)
        return "\n".join(lines)

    def _parse_json(self, content: str) -> list[dict]:
        content = re.sub(r"```json\s*", "", content)
        content = re.sub(r"```\s*", "", content)
        content = content.strip()
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error("JSON 파싱 실패: %s, content=%s", str(e), content[:300])
            raise ValueError(f"LLM 응답 JSON 파싱 실패: {e}")

    def _build_slides(
        self, data: list[dict], specs: list[SlideSpec]
    ) -> list[SlideContent]:
        spec_map = {s.slide_id: s for s in specs}
        slides = []

        for item in data:
            slide_id = item.get("slide_id", "")
            spec = spec_map.get(slide_id)

            chart_data = None
            if item.get("chart_data"):
                cd = item["chart_data"]
                chart_data = ChartData(
                    categories=cd.get("categories", []),
                    series=cd.get("series", []),
                    chart_type=cd.get(
                        "chart_type",
                        getattr(spec, "chart_type", None) or "bar",
                    ),
                )

            slides.append(
                SlideContent(
                    slide_id=slide_id,
                    title=item.get("title", ""),
                    subtitle=item.get("subtitle"),
                    bullets=item.get("bullets", []),
                    body=item.get("body"),
                    table_data=item.get("table_data"),
                    chart_data=chart_data,
                )
            )

        return slides


ppt_content_service = PptContentService()
