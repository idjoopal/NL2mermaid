"""
자동화된 설정 로더 유틸리티

각 agent의 .env 파일을 자동으로 로드합니다.
agents 디렉토리 구조를 스캔하여 자동으로 처리하므로,
agent 추가/제거 시 별도 작업이 필요 없습니다.
"""
import os
import logging
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv, dotenv_values

logger = logging.getLogger("config_loader")

# 민감 정보로 간주할 키워드 (대소문자 무시)
_SENSITIVE_KEYWORDS = ("KEY", "SECRET", "TOKEN", "PASSWORD", "PASSWD", "CREDENTIAL")


def _mask_value(key: str, value: str) -> str:
    """민감 정보가 포함된 키의 값을 마스킹합니다."""
    key_upper = key.upper()
    if any(keyword in key_upper for keyword in _SENSITIVE_KEYWORDS):
        if len(value) <= 4:
            return "****"
        return value[:2] + "*" * (len(value) - 4) + value[-2:]
    return value


def _log_env_variables(env_path: Path, label: str) -> None:
    """env 파일의 변수들을 로깅합니다."""
    variables = dotenv_values(env_path)
    if not variables:
        return

    lines = [f"  {k} = {_mask_value(k, v)}" for k, v in variables.items() if v is not None]
    if lines:
        logger.info(f"[ENV 로드] {label} ({env_path.name})\n" + "\n".join(lines))


def load_agent_env(agent_name: str) -> None:
    """
    특정 agent의 .env 파일을 로드합니다.

    Args:
        agent_name: agent 이름 (예: 'nl2sql')

    파일 위치: src/agents/env/{agent_name}.env
    예: src/agents/env/nl2sql.env
    """
    utils_dir = Path(__file__).parent
    src_dir = utils_dir.parent
    agents_dir = src_dir / "agents" / "agent_env"
    agent_env_path = agents_dir / f"{agent_name}.env"

    if agent_env_path.exists():
        _log_env_variables(agent_env_path, f"Agent={agent_name}")
        load_dotenv(agent_env_path, override=False)
    else:
        logger.warning(f"[ENV 로드] Agent={agent_name} env 파일 없음: {agent_env_path}")


def load_root_env() -> None:
    """
    루트 .env 파일을 로드합니다 (서버 레벨 설정).

    파일 위치: 프로젝트 루트/.env
    """
    # 프로젝트 루트 찾기 (src/utils/config_loader.py -> 프로젝트 루트)
    root_dir = Path(__file__).parent.parent.parent
    root_env_path = root_dir / ".env"

    if root_env_path.exists():
        _log_env_variables(root_env_path, "Root(전체 공통)")
        load_dotenv(root_env_path, override=False)
    else:
        logger.warning(f"[ENV 로드] Root .env 파일 없음: {root_env_path}")


def get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    """환경 변수를 가져옵니다."""
    return os.getenv(key, default)


def get_env_int(key: str, default: int = 0) -> int:
    """환경 변수를 정수로 가져옵니다."""
    value = os.getenv(key)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def get_env_float(key: str, default: float = 0.0) -> float:
    """환경 변수를 실수로 가져옵니다."""
    value = os.getenv(key)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def get_env_bool(key: str, default: bool = False) -> bool:
    """환경 변수를 불린으로 가져옵니다."""
    value = os.getenv(key)
    if value is None:
        return default
    return value.lower() in ("true", "1", "yes", "on")
