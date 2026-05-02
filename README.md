# NL2Mermaid MCP Server

자연어 설명을 Mermaid 다이어그램 이미지(PNG)로 변환하는 MCP 서버입니다.  
`NL2Mermaid` Tool 하나로 자연어 → LLM → Mermaid 코드 → PNG 이미지 파이프라인을 제공합니다.

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

### 전체 흐름 (NL2Mermaid)

```
NL2Mermaid tool
  └── nl2mermaid_agent(query, diagram_type, theme)
        ├── nl2mermaid_service.execute()       → mermaid_code
        ├── mermaid_renderer_service.execute() → image_bytes
        ├── 렌더링 실패 시 에러 피드백 → 재시도 (최대 2회)
        └── Image(data=image_bytes, format="png") 반환
```

### 레이어 간 의존 방향

```
main.py  →  agents  →  modules  →  utils
```

- 역방향 의존 금지: `modules`는 `agents`를 모르고, `utils`는 `modules`를 모릅니다.
- `agents`끼리 서로를 직접 호출하지 않습니다.
- `modules`끼리 서로를 직접 호출하지 않습니다. 조합은 `agents`에서 수행합니다.

### 프로젝트 구조

```
src/
├── agents/
│   ├── nl2mermaid_agent.py           ← NL2Mermaid Agent (Module 2개 조합 + retry)
│   └── agent_env/
│       └── nl2mermaid.env.example    ← Agent별 환경변수 예시
├── modules/
│   ├── nl2mermaid/                   ← 자연어 → Mermaid 코드 생성
│   │   ├── service.py
│   │   ├── prompts.py
│   │   ├── types.py
│   │   └── config/
│   └── mermaid_renderer/             ← Mermaid 코드 → PNG 렌더링
│       ├── service.py
│       ├── providers/
│       │   ├── mermaid_ink.py        ← 기본 provider (mermaid.ink)
│       │   └── kroki.py              ← 선택 provider (Kroki)
│       └── config/
└── utils/
    ├── llm_manager.py
    ├── db_manager.py
    ├── config_loader.py
    └── logger.py
```

---

## 2. 레이어별 역할과 규칙

### 2-1. `main.py` — MCP Tool 등록

**역할:** MCP 서버를 생성하고 Agent를 Tool로 등록합니다.

```python
from fastmcp import FastMCP
from fastmcp.utilities.types import Image
from src.agents.nl2mermaid_agent import nl2mermaid_agent

mcp = FastMCP("NL2Mermaid MCP Server")

@mcp.tool(name="NL2Mermaid", description="...")
async def nl2mermaid_tool(query: str, diagram_type: str = "auto", theme: str = "default") -> Image:
    return await nl2mermaid_agent(query=query, diagram_type=diagram_type, theme=theme)

app = mcp.http_app
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
# src/agents/nl2mermaid_agent.py
async def nl2mermaid_agent(query: str, diagram_type: str = "auto", theme: str = "default") -> Image:
    # nl2mermaid + mermaid_renderer 두 모듈 조합
    # 렌더링 실패 시 에러 피드백 → LLM 재시도 (최대 2회 self-correction)
    ...
```

**Agent가 해야 할 일:**

| 단계 | 내용 |
|------|------|
| 1. 로깅 | `[REQUEST]` 로그 — 입력값 기록 |
| 2. Input 변환 | MCP 입력 → 각 Module의 `execute()`가 받는 형태로 변환 |
| 3. Module 조합 호출 | `module_a_service.execute(...)`, `module_b_service.execute(...)` 순서대로 호출 |
| 4. Output 변환 | Module 결과 → MCP Tool 반환 형태로 변환 |
| 5. 에러 처리 | 예외 catch → 사용자 친화적 메시지 반환 |
| 6. 로깅 | `[RESPONSE]` 로그 — elapsed_time_ms 기록 |

**규칙:**
- Agent는 **MCP에 등록되는 유일한 단위**입니다. Module은 MCP에 직접 노출하지 않습니다.
- Module 간 직접 호출은 금지입니다. 조합은 Agent에서 수행합니다.

---

### 2-3. `modules/` — 기능의 모든 비즈니스 로직

**역할:** 하나의 기능에 필요한 모든 로직을 담는 독립 단위입니다.

**디렉토리 구조:**
```
src/modules/{모듈명}/
├── __init__.py          # service 싱글톤 인스턴스를 외부에 export
├── service.py           # 핵심 로직 + 외부 진입점: execute()
├── types.py             # Pydantic 모델, 타입 정의
├── constants.py         # 상수
├── prompts.py           # LLM 프롬프트 (있을 경우)
├── config/
│   ├── __init__.py
│   ├── config.py        # 환경변수 로드 + 설정값 관리
│   └── *.yaml           # 서비스별 설정 파일 (있을 경우)
└── providers/           # 외부 서비스 구현체 (있을 경우)
    ├── __init__.py
    ├── base.py
    └── {provider}.py
```

**`service.py`의 핵심 패턴 — `execute()`가 유일한 진입점:**

```python
class MyModuleService:
    async def execute(self, query: str) -> str:
        """Agent에서 호출하는 유일한 진입점."""
        ...

my_module_service = MyModuleService()
```

**`__init__.py` — 외부에 service 인스턴스만 노출:**

```python
from .service import my_module_service

__all__ = ["my_module_service"]
```

**규칙:**
- 해당 기능의 로직은 **Module 디렉토리 안에 전부** 있어야 합니다.
- Agent에서는 `execute()` 하나만 호출합니다. 내부 메서드를 직접 호출하지 않습니다.
- Module은 `agents/`, `main.py`를 import하지 않습니다.
- LLM 호출은 `utils/llm_manager`를, DB 접속은 `utils/db_manager`를 사용합니다.

**Provider 패턴 — 외부 API 구현체가 여럿일 때:**

```python
# providers/base.py
class BaseRendererProvider(ABC):
    @abstractmethod
    async def render(self, code: str, **kwargs) -> bytes: ...
```

새 Provider 추가 시 `service.py`의 레지스트리에 1줄만 추가합니다.

---

### 2-4. `utils/` — 공통 인프라

| 파일 | 역할 |
|------|------|
| `llm_manager.py` | **LLM 연결** — Cohere / OpenAI 라우팅 클라이언트 |
| `db_manager.py` | **DB 연결** — PostgreSQL / MariaDB 연결 관리 |
| `config_loader.py` | `.env` 파일 로드 + 환경변수 조회 헬퍼 |
| `logger.py` | JSON 형식 stdout 로거 |

**규칙:**
- LLM 호출은 반드시 `utils/llm_manager`를 사용합니다. 직접 LLM SDK를 import하지 않습니다.
- DB 접속은 반드시 `utils/db_manager`를 사용합니다.
- `utils`에는 특정 Module에 종속된 로직을 두지 않습니다.

---

## 3. 환경변수 설정 구조

```
[루트 .env]                              ← 서버 전체 공통 (LLM API 키, APP_ENV 등)
[src/agents/agent_env/{이름}.env]        ← Agent별 독립 설정
```

### 루트 `.env`

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

# OpenAI (nl2mermaid 기본 모델에 사용)
OPENAI_API_KEY=your-openai-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
```

### Agent별 `.env` (`nl2mermaid.env`)

```bash
cp src/agents/agent_env/nl2mermaid.env.example src/agents/agent_env/nl2mermaid.env
```

```ini
NL2MERMAID_MODEL_ID=openai:gpt-4o-mini
RENDERER_PROVIDER=mermaid_ink        # mermaid_ink | kroki
RENDERER_OUTPUT_DIR=./output
```

> `.env.example` 파일은 Git에 포함, 실제 `.env` 파일은 `.gitignore`에 의해 제외됩니다.

---

## 4. 공통 유틸리티

### 4-1. `llm_manager` — LLM 연결 (Cohere / OpenAI)

```python
from src.utils.llm_manager import LLMManager

llm = LLMManager()
result = await llm.ainvoke(prompt, model_name="openai:gpt-4o-mini")  # → OpenAI
result = await llm.ainvoke(prompt, model_name="command-r-plus")      # → Cohere

content = result["content"]
usage   = result["usage"]  # {"input_tokens": ..., "output_tokens": ..., "elapsed_time": ...}
```

**모델명 라우팅 규칙:**

| 입력 | Provider | 사용 모델 |
|------|----------|-----------|
| `"command-r-plus"` | Cohere | 입력값 그대로 |
| `"gpt-4o-mini"` | OpenAI | 입력값 그대로 |
| `"openai"` | OpenAI | `OPENAI_MODEL` env 값 |
| `"openai:gpt-4o"` | OpenAI | `gpt-4o` |
| `"cohere:command-r"` | Cohere | `command-r` |

### 4-2. `config_loader` — 환경변수 로드 & 조회

```python
from src.utils.config_loader import load_root_env, load_agent_env, get_env, get_env_int

load_root_env()
load_agent_env("nl2mermaid")  # src/agents/agent_env/nl2mermaid.env 로드

api_key = get_env("OPENAI_API_KEY", default="")
timeout  = get_env_int("TIMEOUT", default=30)
```

### 4-3. `get_logger` — JSON 구조화 로그

```python
from src.utils.logger import get_logger

logger = get_logger("nl2mermaid_agent")
logger.info("[REQUEST] nl2mermaid, query=%s", query)
logger.info("[RESPONSE] status=success, elapsed_time_ms=%s", elapsed_ms)
logger.error("[RESPONSE] status=error, elapsed_time_ms=%s, error=%s", elapsed_ms, str(e))
```

출력 형식 (JSON, stdout):
```json
{
  "timestamp": "2026-03-25T10:00:00.000000",
  "level": "INFO",
  "name": "nl2mermaid_agent",
  "message": "[REQUEST] nl2mermaid, query=...",
  "source": { "function": "nl2mermaid_agent", "line": 42 }
}
```

---

## 5. 새 Agent / Module 추가하기

### Step 1. Module 디렉토리 생성

```bash
mkdir -p src/modules/my_module/config
touch src/modules/my_module/__init__.py
touch src/modules/my_module/service.py
touch src/modules/my_module/config/__init__.py
touch src/modules/my_module/config/config.py
```

### Step 2. `config/config.py` 작성

```python
from src.utils.config_loader import load_root_env, load_agent_env, get_env

load_root_env()
load_agent_env("my_module")

MY_API_KEY = get_env("MY_API_KEY", "")
```

### Step 3. `service.py` 작성

```python
from src.utils.llm_manager import LLMManager
from .config.config import MY_API_KEY

class MyModuleService:
    def __init__(self):
        self.llm = LLMManager()

    async def execute(self, query: str) -> str:
        result = await self.llm.ainvoke(query)
        return result["content"]

my_module_service = MyModuleService()
```

### Step 4. `__init__.py` 작성

```python
from .service import my_module_service

__all__ = ["my_module_service"]
```

### Step 5. Agent 파일 생성

```python
# src/agents/my_module_agent.py
import time
from src.modules.my_module import my_module_service
from src.utils.logger import get_logger

logger = get_logger("my_module_agent")

async def my_module_agent(input: str) -> str:
    start_time = time.time()
    logger.info("[REQUEST] my_module, input=%s", input)
    try:
        result = await my_module_service.execute(query=input)
        elapsed = round((time.time() - start_time) * 1000, 2)
        logger.info("[RESPONSE] status=success, elapsed_time_ms=%s", elapsed)
        return result
    except Exception as e:
        elapsed = round((time.time() - start_time) * 1000, 2)
        logger.error("[RESPONSE] status=error, elapsed_time_ms=%s, error=%s", elapsed, str(e))
        return f"죄송합니다. 요청을 처리하는 중 오류가 발생했습니다: {e}"
```

### Step 6. `main.py`에 등록

```python
from src.agents.my_module_agent import my_module_agent

@mcp.tool(name="My_Module", description="...")
async def my_module_tool(input: str) -> str:
    return await my_module_agent(input=input)
```

### Step 7. `.env.example` 작성

```ini
# src/agents/agent_env/my_module.env.example
MY_API_KEY=your-api-key-here
```

### 체크리스트

```
[ ] src/modules/my_module/config/config.py   — load_root_env() + load_agent_env() 호출
[ ] src/modules/my_module/service.py         — execute() 구현
[ ] src/modules/my_module/__init__.py        — service 인스턴스 export
[ ] src/agents/my_module_agent.py            — Module 조합 + I/O 변환 + 로깅
[ ] src/agents/agent_env/my_module.env.example
[ ] main.py                                  — @mcp.tool() 등록
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

cp src/agents/agent_env/nl2mermaid.env.example src/agents/agent_env/nl2mermaid.env
# NL2MERMAID_MODEL_ID, RENDERER_PROVIDER 설정
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

## 지원 다이어그램 타입

| 타입 | Mermaid 문법 | 용도 |
|------|-------------|------|
| auto | LLM 자동 결정 | - |
| flowchart | `flowchart TD/LR` | 프로세스 흐름도 |
| sequence | `sequenceDiagram` | 시스템·팀 간 상호작용 |
| gantt | `gantt` | 프로젝트 일정 |
| timeline | `timeline` | 시계열 이벤트 |
| mindmap | `mindmap` | 개념 구조도 |

## 렌더링 Provider

| Provider | 방식 | 특징 |
|----------|------|------|
| mermaid_ink (기본) | GET + pako 인코딩 | 설치 불필요, 한글 지원 |
| kroki (선택) | POST | 자체 호스팅 시 사용 |
