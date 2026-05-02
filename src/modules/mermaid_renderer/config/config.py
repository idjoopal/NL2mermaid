import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from src.utils.config_loader import load_agent_env, load_root_env

load_root_env()
load_agent_env("nl2mermaid")


class MermaidRendererConfig:

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path(__file__).resolve().parent / "services_config.yaml"
        self._config: Dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f) or {}

    def get_provider_config(self, provider_name: str) -> Dict[str, Any]:
        providers = self._config.get("providers", {})
        return providers.get(provider_name, {}).copy()

    @property
    def default_provider(self) -> str:
        return os.getenv("RENDERER_PROVIDER") or self._config.get("default_provider", "mermaid_ink")

    @property
    def default_theme(self) -> str:
        return self._config.get("default_theme", "default")

    @property
    def default_bg_color(self) -> str:
        return self._config.get("default_bg_color", "white")

    @property
    def output_dir(self) -> str:
        return os.getenv("RENDERER_OUTPUT_DIR") or self._config.get("output_dir", "./output")


mermaid_renderer_config = MermaidRendererConfig()
