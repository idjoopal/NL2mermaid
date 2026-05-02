# Prebuilt MCP - 개발자 사용 가이드

> `web_search`는 아키텍처 구조를 보여주는 샘플 구현입니다.
> 이 가이드를 참고해 새로운 Agent / Module을 동일한 패턴으로 추가하세요.

---

## 목차

1. [아키텍처 개요](#1-아키텍처-개요)
2. [레이어별 역할과 규칙](#2-레이어별-역할과-규칙)
3. [환경변수 설정 구조](#3-환경변수-설정-구조)
4. [공통 유틸리티](#4-공통-유틸리티)
5. [새 Agent / Module 추가하기](#5-새-agent--module-추가하기)
6. [서버 실행](#6-서버-실행)

---

## 1. 아키텍처 개요

```
[MCP Client]
     │
     ▼
[main.py]  ← FastMCP 서버. Agent를 MCP Tool로 등록하는 유일한 진입점
     │
     ▼
[agents/]  ← MCP에 등록되는 단위. 여러 Module을 조합하고 I/O를 변환
     │
     ▼
[modules/] ← 해당 기능의 모든 비즈니스 로직을 담는 독립 단위
     │
     ▼
[utils/]   ← LLM/DB 연결, 설정 로드, 로깅 — 공통 인프라
```

### 레이어 간 의존 방향

```
main.py  →  agents  →  modules  →  utils
```

- 역방향 의존 금지: `modules`는 `agents`를 모르고, `utils`는 `modules`를 모릅니다.
- `agents`끼리 서로를 직접 호출하지 않습니다.
- `modules`끼리 서로를 직접 호출하지 않습니다. 조합은 `agents`에서 수행합니다.

---

## 2. 레이어별 역할과 규칙

### 2-1. `main.py` — MCP Tool 등록

**역할:** MCP 서버를 생성하고 Agent를 Tool로 등록합니다.

```python
from fastmcp import FastMCP
from src.agents.web_search_agent import web_search_agent

mcp = FastMCP("Prebuilt MCP Server")

@mcp.tool(name="Web_Search", description="...")
async def web_search_tool(input: str) -> str:
    return await web_search_agent(query=input)

app = mcp.http_app  # Gunicorn/uvicorn용 ASGI 앱
```

**규칙:**
- MCP Tool로 등록하는 대상은 **Agent**입니다. Module을 직접 등록하지 않습니다.
- Tool 함수 본체는 **Agent 호출 1줄**만 작성합니다. 비즈니스 로직을 두지 않습니다.
- `app = mcp.http_app`은 항상 파일 하단에 유지합니다.

---

### 2-2. `agents/` — MCP 등록 단위 + Module 조합

**역할:** 하나 이상의 Module을 조합하고, MCP의 Input/Output 형식에 맞게 변환합니다.

**파일 위치:** `src/agents/{이름}_agent.py`

```python
# src/agents/web_search_agent.py
import time
from src.modules.web_search import web_search_service
from src.utils.logger import get_logger

logger = get_logger("web_search_agent")

async def web_search_agent(query: str) -> str:
    start_time = time.time()
    logger.info("[REQUEST] web_search, query=%s", query)

    try:
        result = await web_search_service.execute(query=query)
        elapsed = round((time.time() - start_time) * 1000, 2)
        logger.info("[RESPONSE] status=success, elapsed_time_ms=%s", elapsed)
        return result
    except Exception as e:
        elapsed = round((time.time() - start_time) * 1000, 2)
        logger.error("[RESPONSE] status=error, elapsed_time_ms=%s, error=%s", elapsed, str(e))
        return f"죄송합니다. 요청을 처리하는 중 오류가 발생했습니다: {e}"
```

**Agent가 해야 할 일:**

| 단계 | 내용 |
|------|------|
| 1. 로깅 | `[REQUEST]` 로그 — 입력값 기록 |
| 2. Input 변환 | MCP 입력 → 각 Module의 `execute()`가 받는 형태로 변환 |
| 3. Module 조합 호출 | `module_a_service.execute(...)`, `module_b_service.execute(...)` 순서대로 호출 |
| 4. Output 변환 | Module 결과 → MCP Tool 반환 형태(str)로 변환 |
| 5. 에러 처리 | 예외 catch → 사용자 친화적 메시지 반환 |
| 6. 로깅 | `[RESPONSE]` 로그 — elapsed_time_ms 기록 |

**규칙:**
- Agent는 **MCP에 등록되는 유일한 단위**입니다. Module은 MCP에 직접 노출하지 않습니다.
- (1개 혹은 여러 개의) Module은 Agent에서 호출한 뒤, input/output을 변환하여 사용합니다.
- Module 간 직접 호출은 금지되어있습니다. Module은 독립적인 Task를 진행할 수 있는 Prebuilt 기능입니다.
- LLM 호출이나 DB 접속이 필요할 경우 `utils/llm_manager`, `utils/db_manager`를 사용합니다.

---

### 2-3. `modules/` — 기능의 모든 비즈니스 로직

**역할:** 하나의 기능에 필요한 모든 로직을 담는 독립 단위입니다.
Module 디렉토리 안에서 해당 기능이 완결되어야 합니다.

**디렉토리 구조:**
```
src/modules/{모듈명}/
├── __init__.py          # service 싱글톤 인스턴스를 외부에 export
├── service.py           # 핵심 로직 + 외부 진입점: execute()
├── types.py             # Pydantic 모델, 타입 정의
├── constants.py         # 상수
├── exceptions.py        # 커스텀 예외
├── prompts.py           # LLM 프롬프트 (있을 경우)
├── config/
│   ├── __init__.py
│   ├── config.py        # 환경변수 로드 + 설정값 관리
│   └── *.yaml           # 서비스별 설정 파일 (있을 경우)
└── providers/           # 외부 서비스 구현체 (있을 경우)
    ├── __init__.py
    ├── base.py           # 추상 베이스 클래스
    └── {provider}.py     # 구현체
```

**`service.py`의 핵심 패턴 — `execute()`가 유일한 진입점:**

```python
class MyModuleService:
    async def execute(self, query: str) -> str:
        """
        Agent에서 호출하는 유일한 진입점.
        이 메서드 하나로 해당 모듈의 기능 전체를 사용할 수 있어야 합니다.
        """
        # 이 module의 기능이 전부 여기에 구현됩니다
        ...

# 싱글톤 인스턴스 — __init__.py에서 이것만 export
my_module_service = MyModuleService()
```

**`__init__.py` — 외부에 service 인스턴스만 노출:**

```python
# src/modules/my_module/__init__.py
from .service import my_module_service

__all__ = ["my_module_service"]
```

**규칙:**
- 해당 기능의 로직은 **Module 디렉토리 안에 전부** 있어야 합니다.
- Agent에서는 `execute()` 하나만 호출합니다. 내부 메서드를 직접 호출하지 않습니다.
- Module은 `agents/`, `main.py`를 import하지 않습니다.
- LLM 호출이 필요하면 `utils/llm_manager`를, DB 접속이 필요하면 `utils/db_manager`를 사용합니다.

**Provider 패턴 — 외부 API 구현체가 여럿일 때:**

```python
# providers/base.py — 공통 인터페이스 정의
class BaseSearchService(ABC):
    @abstractmethod
    async def search(self, query: str, **kwargs) -> List[SearchResult]: ...

    @abstractmethod
    async def health_check(self) -> bool: ...
```

새 Provider 추가 시 `service.py`의 레지스트리에 1줄만 추가하면 됩니다:

```python
_SERVICE_REGISTRY: Dict[str, Type[BaseSearchService]] = {
    "tavily":     TavilySearchService,
    "perplexity": PerplexitySearchService,
    "my_new":     MyNewSearchService,   # ← 이 줄만 추가
}
```

---

### 2-4. `utils/` — 공통 인프라

**역할:** 여러 Module이 공통으로 사용하는 연결/설정/로깅 기능을 제공합니다.

| 파일 | 역할 |
|------|------|
| `llm_manager.py` | **LLM 연결** — Cohere / OpenAI 라우팅 클라이언트 |
| `db_manager.py` | **DB 연결** — PostgreSQL / MariaDB 연결 관리 |
| `config_loader.py` | `.env` 파일 로드 + 환경변수 조회 헬퍼 |
| `logger.py` | JSON 형식 stdout 로거 |

**규칙:**
- LLM을 호출해야 할 때는 반드시 `utils/llm_manager`를 사용합니다. 직접 LLM SDK를 import하지 않습니다.
- DB에 접속해야 할 때는 반드시 `utils/db_manager`를 사용합니다. 직접 DB 드라이버를 연결하지 않습니다.
- `utils`에는 특정 Module에 종속된 로직을 두지 않습니다. 범용적인 기능만 위치합니다.
- 해당 기능이 수정되면 모든 Prebuilt 프로젝트에 영향이 있습니다. 반드시 입고시 확인 절차가 요구됩니다.

---

## 3. 환경변수 설정 구조

```
[루트 .env]                              ← 서버 전체 공통 (LLM API 키, APP_ENV 등)
[src/agents/agent_env/{이름}.env]        ← Agent별 독립 설정 (DB 접속, 검색 API 키 등)
```

### 루트 `.env` 주요 항목

```bash
cp .env.example .env
```

```ini
APP_ENV=dev
SERVER_HOST=0.0.0.0
SERVER_PORT=9101

# Cohere (기본 LLM)
CLIENT_NAME=prebuilt-mcp
API_KEY=your-cohere-api-key
BASE_URL=http://your-cohere-endpoint
MODEL=command
TEMPERATURE=0.0
TIMEOUT=120
MAX_TOKENS=2048

# OpenAI (선택)
OPENAI_API_KEY=your-openai-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
```

### Agent별 `.env` (예: `web_search.env`)

```bash
cp src/agents/agent_env/web_search.env.example src/agents/agent_env/web_search.env
```

```ini
TAVILY_API_KEY=your-tavily-key
PERPLEXITY_API_KEY=your-perplexity-key
```

### Module의 `config.py`에서 환경변수 로드

```python
# src/modules/my_module/config/config.py
from src.utils.config_loader import load_root_env, load_agent_env, get_env

# 모듈 import 시 1회 실행
load_root_env()              # 루트 .env
load_agent_env("my_module")  # src/agents/agent_env/my_module.env

MY_API_KEY = get_env("MY_API_KEY", "")
```

> `.env.example` 파일은 Git에 포함, 실제 `.env` 파일은 `.gitignore`에 의해 제외됩니다.

---

## 4. 공통 유틸리티

### 4-1. `llm_manager` — LLM 연결 (Cohere / OpenAI)

LLM을 호출해야 하는 모든 곳에서 직접 SDK를 사용하지 않고 `LLMManager`를 사용합니다.

```python
from src.utils.llm_manager import LLMManager

llm = LLMManager()

# 모델명으로 Provider 자동 선택
result = await llm.ainvoke(prompt, model_name="command-r-plus")  # → Cohere
result = await llm.ainvoke(prompt, model_name="gpt-4o-mini")     # → OpenAI
result = await llm.ainvoke(prompt, model_name="openai:gpt-4o")   # → OpenAI (명시적)
result = await llm.ainvoke(prompt, model_name="openai")          # → OPENAI_MODEL env 사용

# 반환값
content = result["content"]  # str
usage   = result["usage"]    # {"input_tokens": ..., "output_tokens": ..., "elapsed_time": ...}
```

**모델명 라우팅 규칙:**

| 입력 | Provider | 사용 모델 |
|------|----------|-----------|
| `"command-r-plus"` | Cohere | 입력값 그대로 |
| `"gpt-4o-mini"` | OpenAI | 입력값 그대로 |
| `"openai"` | OpenAI | `OPENAI_MODEL` env 값 |
| `"cohere"` | Cohere | `COHERE_MODEL` env 값 |
| `"openai:gpt-4o"` | OpenAI | `gpt-4o` |
| `"cohere:command-r"` | Cohere | `command-r` |

### 4-2. `db_manager` — DB 연결 (PostgreSQL / MariaDB)

DB에 접속해야 하는 모든 곳에서 직접 드라이버를 연결하지 않고 `db_manager`를 사용합니다.

```python
from src.utils.db_manager import get_db_manager

db = get_db_manager()  # 환경변수에서 접속 정보를 읽어 연결 관리
rows = await db.execute_query("SELECT * FROM my_table WHERE id = $1", [id])
```

DB 접속 정보는 해당 Agent의 `.env`에 설정합니다 (예: `TEXT2SQL_DB_HOST`, `TEXT2SQL_DB_PORT` 등).

### 4-3. `config_loader` — 환경변수 로드 & 조회

```python
from src.utils.config_loader import (
    load_root_env,
    load_agent_env,
    get_env,
    get_env_int,
    get_env_float,
    get_env_bool,
)

load_root_env()
load_agent_env("my_module")

api_key = get_env("MY_API_KEY", default="")
timeout  = get_env_int("TIMEOUT", default=30)
ratio    = get_env_float("RATIO", default=0.5)
debug    = get_env_bool("DEBUG", default=False)
```

### 4-4. `get_logger` — JSON 구조화 로그

```python
from src.utils.logger import get_logger

logger = get_logger("my_agent")
```

출력 형식 (JSON, stdout):
```json
{
  "timestamp": "2026-03-25T10:00:00.000000",
  "level": "INFO",
  "name": "my_agent",
  "message": "[REQUEST] input=hello",
  "source": { "function": "my_agent", "line": 42, "pathname": "..." }
}
```

**로그 컨벤션:**

```python
# 요청 시작 (Agent 진입)
logger.info("[REQUEST] {operation}, {key}={value}, ...")

# 성공 응답
logger.info("[RESPONSE] status=success, elapsed_time_ms=%s, ...", elapsed_ms)

# 에러 응답
logger.error("[RESPONSE] status=error, elapsed_time_ms=%s, error=%s", elapsed_ms, str(e))
```

---

## 5. 새 Agent / Module 추가하기

아래 순서대로 파일을 만들고 내용을 채웁니다.

### Step 1. Module 디렉토리 생성

```bash
mkdir -p src/modules/my_module/config
touch src/modules/my_module/__init__.py
touch src/modules/my_module/service.py
touch src/modules/my_module/config/__init__.py
touch src/modules/my_module/config/config.py
```

### Step 2. `config/config.py` 작성 — 환경변수 로드

```python
# src/modules/my_module/config/config.py
from src.utils.config_loader import load_root_env, load_agent_env, get_env

load_root_env()
load_agent_env("my_module")   # src/agents/agent_env/my_module.env 로드

MY_API_KEY = get_env("MY_API_KEY", "")
```

### Step 3. `service.py` 작성 — 기능의 모든 비즈니스 로직

```python
# src/modules/my_module/service.py
from src.utils.llm_manager import LLMManager   # LLM 호출이 필요한 경우
# from src.utils.db_manager import get_db_manager  # DB 접속이 필요한 경우
from .config.config import MY_API_KEY


class MyModuleService:
    def __init__(self):
        self.llm = LLMManager()  # LLM 연결은 llm_manager 사용

    async def execute(self, query: str) -> str:
        """
        Agent에서 호출하는 유일한 진입점.
        이 module의 기능이 여기에 전부 구현됩니다.
        """
        # 비즈니스 로직 구현
        result = await self.llm.ainvoke(query)
        return result["content"]


my_module_service = MyModuleService()
```

### Step 4. `__init__.py` 작성 — service 인스턴스 export

```python
# src/modules/my_module/__init__.py
from .service import my_module_service

__all__ = ["my_module_service"]
```

### Step 5. Agent 파일 생성

```bash
touch src/agents/my_module_agent.py
touch src/agents/agent_env/my_module.env.example
```

### Step 6. `my_module_agent.py` 작성 — Module 조합 + I/O 변환

```python
"""
My Module Agent

MCP에 등록되는 단위입니다.
Module을 조합하고 MCP의 input/output 형식에 맞게 변환합니다.

REQUIRED MODULES:
- modules/my_module/   : 핵심 비즈니스 로직
환경 설정: agents/agent_env/my_module.env
"""
import time
from src.modules.my_module import my_module_service
from src.utils.logger import get_logger

logger = get_logger("my_module_agent")


async def my_module_agent(input: str) -> str:
    start_time = time.time()
    logger.info("[REQUEST] my_module, input=%s", input)

    try:
        # 1. Input 변환 (필요 시)
        # 2. Module 호출 — 여러 모듈을 조합할 수 있음
        result = await my_module_service.execute(query=input)

        # 3. Output 변환 (필요 시)
        elapsed = round((time.time() - start_time) * 1000, 2)
        logger.info("[RESPONSE] status=success, elapsed_time_ms=%s", elapsed)
        return result

    except Exception as e:
        elapsed = round((time.time() - start_time) * 1000, 2)
        logger.error("[RESPONSE] status=error, elapsed_time_ms=%s, error=%s", elapsed, str(e))
        return f"죄송합니다. 요청을 처리하는 중 오류가 발생했습니다: {e}"
```

여러 Module을 조합하는 예시:

```python
async def my_combined_agent(input: str) -> str:
    # Step 1: 첫 번째 module로 데이터 가져오기
    raw_data = await module_a_service.execute(query=input)

    # Step 2: 두 번째 module로 결과 가공
    final_result = await module_b_service.execute(data=raw_data)

    return final_result
```

### Step 7. `main.py`에 Agent를 MCP Tool로 등록

```python
# main.py에 추가
from src.agents.my_module_agent import my_module_agent

_MY_MODULE_DESCRIPTION = """\
(MCP Client에 표시될 Tool 설명을 작성합니다.)

▸ 입력: user_query
▸ 출력: 처리 결과
"""

@mcp.tool(
    name="My_Module",
    description=_MY_MODULE_DESCRIPTION,
)
async def my_module_tool(input: str) -> str:
    return await my_module_agent(input=input)
```

### Step 8. `.env.example` 작성

```ini
# src/agents/agent_env/my_module.env.example
MY_API_KEY=your-api-key-here
```

### 체크리스트

```
[ ] src/modules/my_module/config/config.py   — load_root_env() + load_agent_env() 호출
[ ] src/modules/my_module/service.py         — execute() 구현, 기능 전체가 여기에 담김
[ ] src/modules/my_module/__init__.py        — service 인스턴스 export
[ ] src/agents/my_module_agent.py            — Module 조합 + I/O 변환 + 로깅
[ ] src/agents/agent_env/my_module.env.example  — 환경변수 예시
[ ] src/agents/agent_env/my_module.env          — 실제 값 입력 (gitignore됨)
[ ] main.py                                  — Agent를 @mcp.tool()로 등록
```

---

## 6. 서버 실행

### 의존성 설치

```bash
uv sync
```

### 환경변수 설정

```bash
cp .env.example .env
# .env 편집 후 LLM API 키, endpoint 입력

cp src/agents/agent_env/web_search.env.example src/agents/agent_env/web_search.env
# 필요한 agent env 파일도 동일하게 준비
```

### 개발 모드 (Hot Reload)

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 9101 --reload
```

### 운영 모드 (Gunicorn)

```bash
uv run gunicorn -b 0.0.0.0:9101 -k uvicorn.workers.UvicornWorker main:app
```

### MCP 접속 확인

```
http://0.0.0.0:9101/mcp
```

---

## 참고: `web_search` 샘플 전체 흐름 요약

```
main.py
  └── @mcp.tool("Web_Search")
        └── web_search_agent(query)              # agents/ — MCP 등록 단위
              └── web_search_service.execute()   # modules/ — 기능 전체 담당
                    ├── config.py                #   load_root_env() + load_agent_env()
                    ├── TavilySearchService      #   providers/ — 외부 API 구현체
                    └── PerplexitySearchService  #   providers/ — 외부 API 구현체
```

**이 샘플에서 확인할 수 있는 패턴:**

| 규칙 | web_search 샘플에서 |
|------|---------------------|
| Agent가 MCP 등록 단위 | `web_search_agent`가 `@mcp.tool`로 등록됨 |
| Module이 기능 전체 담당 | 검색 로직 전체가 `modules/web_search/` 안에 있음 |
| `execute()`가 유일한 진입점 | Agent는 `web_search_service.execute(query)`만 호출 |
| LLM/DB는 utils 사용 | (이 모듈은 외부 검색 API 사용이므로 llm_manager 미사용) |
| 환경변수 분리 | 루트 `.env`(공통) + `web_search.env`(검색 API 키) |
