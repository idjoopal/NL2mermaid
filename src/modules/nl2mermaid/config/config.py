import os
from src.utils.config_loader import load_agent_env, load_root_env

load_root_env()
load_agent_env("nl2mermaid")

NL2MERMAID_MODEL_ID = os.getenv("NL2MERMAID_MODEL_ID", "openai:gpt-4o-mini")
