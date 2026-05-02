"""
Web Search 설정 관리

환경변수 우선, 없으면 기본값 사용
prebuilt-mcp 프로젝트 구조에 맞게 config_loader를 활용합니다.
"""
import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from src.utils.config_loader import load_agent_env, load_root_env

logger = logging.getLogger(__name__)

# .env 파일 로드
load_root_env()
load_agent_env("web_search")

# 서비스명 → API 키 환경변수 매핑
_SERVICE_API_KEY_ENVS: Dict[str, str] = {
    "tavily_search": "TAVILY_API_KEY",
    "tavily": "TAVILY_API_KEY",
    "perplexity": "PERPLEXITY_API_KEY",
    "perplexity_search": "PERPLEXITY_API_KEY",
}


class WebSearchConfig:
    """
    Web Search 설정 관리자.

    - services_config.yaml 로드 → 서비스별 기본값 제공
    - web_search.env에서 API 키를 읽어 서비스 설정에 주입
    """

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = (
            config_path or Path(__file__).resolve().parent / "services_config.yaml"
        )
        self._config: Dict[str, Any] = {}
        self._load_config()

    def _load_config(self) -> None:
        """services_config.yaml을 로드합니다."""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self._config = yaml.safe_load(f) or {}
                logger.debug("Loaded web_search config from %s", self.config_path)
            except Exception as exc:
                logger.error("Failed to load config from %s: %s", self.config_path, exc)
                self._config = {}
        else:
            logger.warning("Configuration file not found: %s", self.config_path)
            self._config = {}

    def get_service_config(self, service_name: str) -> Dict[str, Any]:
        """
        서비스 설정을 반환합니다.

        우선순위:
          1. services_config.yaml의 해당 서비스 블록
          2. API 키는 web_search.env 환경변수에서 주입 (yaml에 api_key가 비어 있을 때)

        Args:
            service_name: 서비스 이름 (예: "tavily_search", "perplexity")

        Returns:
            서비스 설정 딕셔너리
        """
        services = self._config.get("services", {})
        service_config = services.get(service_name, {}).copy()

        # API 키가 yaml에 없으면 환경변수에서 주입
        env_var = _SERVICE_API_KEY_ENVS.get(service_name)
        if env_var and not service_config.get("api_key"):
            service_config["api_key"] = os.getenv(env_var, "")

        return service_config


web_search_config = WebSearchConfig()
