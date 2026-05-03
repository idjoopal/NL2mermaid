from pathlib import Path

import yaml

from src.utils.config_loader import get_env, load_agent_env, load_root_env
from src.modules.ppt_generator.constants import (
    CUSTOM_TEMPLATES_DIR,
    DEFAULT_TEMPLATE,
    FONT_FALLBACK,
    OUTPUT_DIR,
)

load_root_env()
load_agent_env("ppt")


class PptGeneratorConfig:
    def __init__(self):
        cfg_path = Path(__file__).parent / "services_config.yaml"
        with open(cfg_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        self.default_template: str = get_env("PPT_DEFAULT_TEMPLATE") or data.get("default_template", DEFAULT_TEMPLATE)
        self.output_dir: str = get_env("PPT_OUTPUT_DIR") or data.get("output_dir", OUTPUT_DIR)
        self.custom_templates_dir: str = get_env("PPT_CUSTOM_TEMPLATES_DIR") or data.get("custom_templates_dir", CUSTOM_TEMPLATES_DIR)
        self.font_fallback: str = data.get("font_fallback", FONT_FALLBACK)


ppt_generator_config = PptGeneratorConfig()
