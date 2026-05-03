from src.utils.config_loader import load_root_env, load_agent_env, get_env

load_root_env()
load_agent_env("ppt")

PPT_CONTENT_MODEL_ID: str = get_env("PPT_CONTENT_MODEL_ID", "openai:gpt-4o-mini")
