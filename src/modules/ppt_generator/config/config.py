from pathlib import Path

import yaml

from src.utils.config_loader import get_env, load_agent_env, load_root_env

load_root_env()
load_agent_env("ppt")


class PptGeneratorConfig:
    def __init__(self):
        cfg_path = Path(__file__).parent / "services_config.yaml"
        with open(cfg_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        self.default_template: str = get_env("PPT_DEFAULT_TEMPLATE") or data.get("default_template", "business")
        self.output_dir: str = get_env("PPT_OUTPUT_DIR") or data.get("output_dir", "./output")
        self.custom_templates_dir: str = get_env("PPT_CUSTOM_TEMPLATES_DIR") or data.get("custom_templates_dir", "./custom_templates")
        self.font_fallback: str = data.get("font_fallback", "맑은 고딕")


ppt_generator_config = PptGeneratorConfig()
