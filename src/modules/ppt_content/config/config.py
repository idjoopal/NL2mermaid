from src.utils.config_loader import get_env, load_agent_env, load_root_env
from src.modules.ppt_content.constants import DEFAULT_MODEL

load_root_env()
load_agent_env("ppt")

PPT_CONTENT_MODEL_ID: str = get_env("PPT_CONTENT_MODEL_ID", DEFAULT_MODEL)
