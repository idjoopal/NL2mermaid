# NL2Mermaid MCP Server

자연어를 **Mermaid 다이어그램(PNG)** 또는 **PPTX 프레젠테이션**으로 변환하는 MCP 서버입니다.  
두 가지 Tool을 제공하며, LLM이 내용을 구조화한 뒤 각 포맷으로 출력합니다.

---

## 제공 Tool

| Tool | 입력 | 출력 | 설명 |
|------|------|------|------|
| `NL2Mermaid` | 자연어 | PNG 이미지 | 자연어 → Mermaid 코드 → PNG |
| `NL2PPT` | 자연어 | PPTX 파일 | 자연어 → 슬라이드 구조화 → PPTX |

---

## 목차

1. [NL2Mermaid — 사용 예시](#1-nl2mermaid--사용-예시)
2. [NL2PPT — 사용 예시](#2-nl2ppt--사용-예시)
3. [아키텍처 개요](#3-아키텍처-개요)
4. [환경변수 설정](#4-환경변수-설정)
5. [NL2PPT 템플릿](#5-nl2ppt-템플릿)
6. [공통 유틸리티](#6-공통-유틸리티)
7. [새 Agent / Module 추가하기](#7-새-agent--module-추가하기)
8. [서버 실행](#8-서버-실행)

---

## 1. NL2Mermaid — 사용 예시

### 기본 사용법

```
Tool: NL2Mermaid
query: "사용자가 로그인하면 JWT를 발급하고, 만료 시 리프레시 토큰으로 재발급하는 흐름"
diagram_type: "sequence"
theme: "default"
```

**LLM이 생성한 Mermaid 코드:**
```
sequenceDiagram
    participant U as User
    participant A as AuthServer
    participant R as ResourceServer
    U->>A: POST /login (id, pw)
    A-->>U: 200 OK (JWT + RefreshToken)
    U->>R: GET /api/data (Bearer JWT)
    R-->>U: 200 OK (data)
    Note over U,R: JWT 만료 후
    U->>A: POST /refresh (RefreshToken)
    A-->>U: 200 OK (new JWT)
```

**출력:** PNG 이미지 (MCP Image 타입으로 반환)

---

### 예시 2 — 플로우차트

```
Tool: NL2Mermaid
query: "주문이 들어오면 재고 확인 후 있으면 결제 처리, 없으면 입고 대기 알림을 보낸다"
diagram_type: "flowchart"
theme: "neutral"
```

**생성된 Mermaid 코드:**
```
flowchart TD
    A([주문 접수]) --> B{재고 확인}
    B -->|재고 있음| C[결제 처리]
    B -->|재고 없음| D[입고 대기 알림]
    C --> E[배송 준비]
    D --> F([대기 상태 저장])
    E --> G([완료])
```

**출력:** PNG 이미지

---

### 예시 3 — 간트 차트

```
Tool: NL2Mermaid
query: "앱 개발 프로젝트. 요구사항 분석 2주, 설계 2주, 개발 6주, QA 2주, 배포 1주"
diagram_type: "gantt"
```

**생성된 Mermaid 코드:**
```
gantt
    title 앱 개발 프로젝트
    dateFormat YYYY-MM-DD
    section 분석·설계
        요구사항 분석 : 2026-05-01, 2w
        시스템 설계   : 2026-05-15, 2w
    section 개발
        기능 개발     : 2026-05-29, 6w
    section 검증·배포
        QA 테스트     : 2026-07-10, 2w
        배포          : 2026-07-24, 1w
```

**출력:** PNG 이미지

### 지원 다이어그램 타입

| diagram_type | Mermaid 문법 | 용도 |
|---|---|---|
| `auto` | LLM 자동 결정 | 기본값 |
| `flowchart` | `flowchart TD/LR` | 프로세스 흐름도 |
| `sequence` | `sequenceDiagram` | 시스템·팀 간 상호작용 |
| `gantt` | `gantt` | 프로젝트 일정 |
| `timeline` | `timeline` | 시계열 이벤트 |
| `mindmap` | `mindmap` | 개념 구조도 |

### 지원 테마

| theme | 특징 |
|-------|------|
| `default` | 파란색 계열 기본 테마 |
| `neutral` | 회색 계열 문서 친화적 |
| `dark` | 어두운 배경 |
| `forest` | 초록 계열 |

---

## 2. NL2PPT — 사용 예시

### 예시 1 — 비즈니스 보고서 (`business` 템플릿)

**입력:**
```
Tool: NL2PPT
query: "2026년 상반기 마케팅 성과 보고서.
        SNS 광고비 5천만원, 전환율 3.2%, 매출 기여 2억원.
        채널별로는 인스타그램 45%, 유튜브 30%, 네이버 25%.
        하반기 예산 증액 건의."
template_name: "business"
language: "ko"
```

**LLM이 구조화한 슬라이드 내용:**
```json
[
  {"slide_id": "cover",      "title": "2026 상반기 마케팅 성과 보고서", "subtitle": "마케팅팀"},
  {"slide_id": "agenda",     "title": "목차", "bullets": ["1. 성과 요약", "2. 채널별 분석", "3. 예산 현황", "4. 하반기 건의사항"]},
  {"slide_id": "analysis",   "title": "성과 요약", "body": "광고비 5천만원 집행 / 전환율 3.2% / 매출 기여 2억원"},
  {"slide_id": "data_chart", "title": "채널별 비중",
   "chart_data": {"chart_type": "pie", "categories": ["인스타그램", "유튜브", "네이버"],
                  "series": [{"name": "비중(%)", "values": [45, 30, 25]}]}},
  {"slide_id": "data_table", "title": "채널별 상세 현황",
   "table_data": [["채널", "예산(만원)", "전환율", "매출기여(만원)"],
                  ["인스타그램", "2,250", "4.1%", "9,000"],
                  ["유튜브",     "1,500", "2.8%", "6,000"],
                  ["네이버",     "1,250", "2.2%", "5,000"]]},
  {"slide_id": "closing",    "title": "하반기 예산 증액 건의", "subtitle": "감사합니다"}
]
```

**출력 (JSON):**
```json
{
  "file_path": "./output/20260503_141022.pptx",
  "slide_count": 6,
  "template": "business",
  "title": "2026 상반기 마케팅 성과 보고서",
  "summary": "1. 2026 상반기 마케팅 성과 보고서\n2. 목차\n3. 성과 요약\n4. 채널별 비중\n5. 채널별 상세 현황\n6. 하반기 예산 증액 건의"
}
```

**생성된 PPTX 구성:**
| 슬라이드 | 타입 | 내용 |
|----------|------|------|
| 1 | 커버 | 제목 + 부제 (컬러 배경) |
| 2 | 텍스트 | 목차 (글머리 기호) |
| 3 | 텍스트 | 성과 요약 |
| 4 | 파이 차트 | 채널별 비중 |
| 5 | 표 | 채널별 상세 현황 (헤더 강조) |
| 6 | 마무리 | 건의사항 + 감사 |

---

### 예시 2 — 스타트업 피치덱 (`pitch` 템플릿)

**입력:**
```
Tool: NL2PPT
query: "AI 기반 재고 최적화 SaaS.
        문제: 중소 유통업체 재고 손실 연 15%.
        솔루션: 실시간 수요 예측 ML 모델.
        시장: 국내 2조원 (TAM), SAM 5천억, SOM 500억.
        팀: CEO 전커머스 10년, CTO KAIST 박사.
        내년 MAU 1만, ARR 10억 목표. 시드 5억 투자 요청."
template_name: "pitch"
language: "ko"
```

**출력 (JSON):**
```json
{
  "file_path": "./output/20260503_141523.pptx",
  "slide_count": 6,
  "template": "pitch",
  "title": "AI 재고 최적화 SaaS",
  "summary": "1. AI 재고 최적화 SaaS\n2. 문제\n3. 솔루션\n4. 시장 규모\n5. 팀 소개\n6. 투자 요청"
}
```

**생성된 PPTX 구성:**
| 슬라이드 | 타입 | 내용 |
|----------|------|------|
| 1 | 커버 | 회사명 + 한줄 소개 |
| 2 | 텍스트 | 문제 (재고 손실 15%, 기존 한계) |
| 3 | 텍스트 | 솔루션 (ML 모델, 차별점) |
| 4 | 컬럼 차트 | 시장 규모 (TAM/SAM/SOM) |
| 5 | 텍스트 | 팀 소개 |
| 6 | 마무리 | 목표 지표 + 투자 요청 금액 |

---

### 예시 3 — 분석 보고서 (`report` 템플릿)

**입력:**
```
Tool: NL2PPT
query: "국내 SaaS 시장 분석 보고서.
        2022년 1.2조 → 2023년 1.6조 → 2024년 2.1조 → 2025년 2.8조 성장.
        성장 동인: 클라우드 전환 가속, 구독 모델 확산, 중소기업 디지털화.
        리스크: 데이터 보안 규제 강화, 글로벌 빅테크 진입.
        결론: 2026년 3.5조 전망, HR/ERP/CRM 분야 집중 투자 권고."
template_name: "report"
language: "ko"
```

**출력 (JSON):**
```json
{
  "file_path": "./output/20260503_142200.pptx",
  "slide_count": 7,
  "template": "report",
  "title": "국내 SaaS 시장 분석 보고서",
  "summary": "1. 국내 SaaS 시장 분석\n2. 핵심 요약\n3. 시장 배경\n4. 연도별 성장 추이\n5. 분야별 현황\n6. 결론 및 시사점\n7. 마무리"
}
```

**생성된 PPTX 구성:**
| 슬라이드 | 타입 | 내용 |
|----------|------|------|
| 1 | 커버 | 제목 + 날짜 |
| 2 | 텍스트 | 핵심 요약 (3줄 요약) |
| 3 | 텍스트 | 시장 배경 |
| 4 | 라인 차트 | 연도별 시장 규모 성장 추이 |
| 5 | 표 | HR/ERP/CRM 분야별 현황 |
| 6 | 텍스트 | 결론 및 시사점 |
| 7 | 마무리 | 결론 메시지 |

---

### 예시 4 — 커스텀 템플릿

`./custom_templates/dev_retrospective.yaml` 파일을 직접 만들면 자동으로 탐색됩니다.

```yaml
# ./custom_templates/dev_retrospective.yaml
name: dev_retrospective
description: "개발팀 분기 회고 템플릿"
slides:
  - id: cover
    type: title_slide
    placeholders: [{name: title}, {name: subtitle}]
  - id: done
    type: content_slide
    placeholders: [{name: title}, {name: bullets, type: list}]
  - id: issues
    type: content_slide
    placeholders: [{name: title}, {name: bullets, type: list}]
  - id: metrics
    type: chart_slide
    chart_type: bar
    placeholders: [{name: title}, {name: chart_data}]
  - id: next_quarter
    type: content_slide
    placeholders: [{name: title}, {name: bullets, type: list}]
theme:
  primary_color: "1A6B3C"
  font_family: "맑은 고딕"
```

**입력:**
```
Tool: NL2PPT
query: "분기 개발팀 회고. 완료: 결제 모듈 v2, API 성능 30% 개선.
        이슈: 테스트 커버리지 부족. 다음 분기: 커버리지 80%, 신규 기능 3건."
template_name: "dev_retrospective"
```

**출력:** `./output/20260503_142011.pptx` (5슬라이드, 초록 테마)

---

## 3. 아키텍처 개요

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

### NL2Mermaid 흐름

```
NL2Mermaid tool
  └── nl2mermaid_agent(query, diagram_type, theme)
        ├── nl2mermaid_service.execute()       → mermaid_code
        ├── mermaid_renderer_service.execute() → image_bytes
        ├── 렌더링 실패 시 에러 피드백 → 재시도 (최대 2회)
        └── Image(data=image_bytes, format="png") 반환
```

### NL2PPT 흐름

```
NL2PPT tool
  └── ppt_agent(query, template_name, language)
        ├── ppt_generator_service.get_template()  → TemplateDefinition
        ├── ppt_content_service.execute()         → PptContent  (LLM 슬라이드 구조화)
        ├── ppt_generator_service.execute()       → PptResult   (PPTX bytes 생성)
        │     ├── title_slide   → 컬러 배경 + 제목/부제
        │     ├── content_slide → 글머리 기호 또는 본문
        │     ├── table_slide   → python-pptx Table API
        │     ├── chart_slide   → python-pptx Chart API (bar/column/line/pie)
        │     └── two_column    → 좌우 2컬럼 레이아웃
        └── ./output/{timestamp}.pptx 저장 + JSON 반환
```

### 레이어 간 의존 방향

```
main.py  →  agents  →  modules  →  utils
```

- 역방향 의존 금지 (`modules`는 `agents`를 모름)
- `agents`끼리, `modules`끼리 서로 직접 호출 금지. 조합은 `agents`에서만.

### 프로젝트 구조

```
src/
├── agents/
│   ├── nl2mermaid_agent.py           ← NL2Mermaid Agent (Module 2개 조합 + retry)
│   ├── ppt_agent.py                  ← NL2PPT Agent (ppt_content + ppt_generator 조합)
│   └── agent_env/
│       ├── nl2mermaid.env.example
│       └── ppt.env.example
├── modules/
│   ├── shared/
│   │   └── types.py                  ← 모듈 간 공유 타입 (ChartData, SlideContent 등)
│   ├── nl2mermaid/                   ← 자연어 → Mermaid 코드 생성
│   │   ├── service.py
│   │   ├── prompts.py
│   │   └── config/
│   ├── mermaid_renderer/             ← Mermaid 코드 → PNG 렌더링
│   │   ├── service.py
│   │   ├── providers/
│   │   │   ├── mermaid_ink.py        ← 기본 provider
│   │   │   └── kroki.py             ← 선택 provider
│   │   └── config/
│   ├── ppt_content/                  ← 자연어 → 슬라이드 내용 구조화 (LLM)
│   │   ├── service.py
│   │   ├── prompts.py
│   │   ├── types.py
│   │   └── config/
│   └── ppt_generator/               ← 슬라이드 내용 → PPTX 생성 (python-pptx)
│       ├── service.py
│       ├── types.py
│       ├── exceptions.py
│       ├── templates/                ← 내장 YAML 템플릿
│       │   ├── business.yaml
│       │   ├── pitch.yaml
│       │   └── report.yaml
│       └── config/
└── utils/
    ├── llm_manager.py
    ├── config_loader.py
    └── logger.py
```

---

## 4. 환경변수 설정

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

# OpenAI
OPENAI_API_KEY=your-openai-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
```

### NL2Mermaid `.env`

```bash
cp src/agents/agent_env/nl2mermaid.env.example src/agents/agent_env/nl2mermaid.env
```

```ini
NL2MERMAID_MODEL_ID=openai:gpt-4o-mini
RENDERER_PROVIDER=mermaid_ink   # mermaid_ink | kroki
RENDERER_OUTPUT_DIR=./output
```

### NL2PPT `.env`

```bash
cp src/agents/agent_env/ppt.env.example src/agents/agent_env/ppt.env
```

```ini
PPT_CONTENT_MODEL_ID=openai:gpt-4o-mini
PPT_OUTPUT_DIR=./output
PPT_DEFAULT_TEMPLATE=business
PPT_CUSTOM_TEMPLATES_DIR=./custom_templates
```

> `.env.example` 파일은 Git에 포함, 실제 `.env` 파일은 `.gitignore`에 의해 제외됩니다.

---

## 5. NL2PPT 템플릿

### 내장 템플릿 3종

| 이름 | 설명 | 슬라이드 구성 |
|------|------|---------------|
| `business` | 비즈니스 보고 | 커버 / 목차 / 내용×2 / 차트 / 표 / 마무리 |
| `pitch` | 스타트업 피치덱 | 커버 / 문제 / 솔루션 / 시장(차트) / 팀 / 요청 |
| `report` | 분석 보고서 | 커버 / 요약 / 배경 / 추이(차트) / 표 / 결론 / 마무리 |

### 지원 슬라이드 타입

| type | 내용 |
|------|------|
| `title_slide` | 커버·마무리 — 컬러 배경 + 제목 + 부제 |
| `content_slide` | 제목 + 글머리 기호 또는 본문 텍스트 |
| `table_slide` | 제목 + 표 (헤더 자동 강조) |
| `chart_slide` | 제목 + 차트 (bar / column / line / pie) |
| `two_column` | 제목 + 좌우 2컬럼 레이아웃 |

### 커스텀 템플릿 YAML 구조

```yaml
name: my_template
description: "커스텀 템플릿 설명"
slides:
  - id: cover
    type: title_slide
    placeholders:
      - {name: title, required: true}
      - {name: subtitle}
  - id: main
    type: content_slide
    placeholders:
      - {name: title}
      - {name: bullets, type: list}
  - id: chart
    type: chart_slide
    chart_type: bar          # bar | column | line | pie
    placeholders:
      - {name: title}
      - {name: chart_data}
  - id: summary
    type: table_slide
    placeholders:
      - {name: title}
      - {name: table_data}
theme:
  primary_color: "2B4E9E"   # 헥스 코드
  secondary_color: "E8EEF8"
  font_family: "맑은 고딕"
  font_size_title: 36
  font_size_body: 18
```

커스텀 YAML을 `./custom_templates/` 디렉터리에 저장하면 `template_name`으로 자동 탐색됩니다.

---

## 6. 공통 유틸리티

### `llm_manager` — LLM 연결

```python
from src.utils.llm_manager import LLMManager

llm = LLMManager()
result = await llm.ainvoke(prompt, model_name="openai:gpt-4o-mini")
content = result["content"]
usage   = result["usage"]  # {input_tokens, output_tokens, elapsed_time}
```

**모델명 라우팅:**

| 입력 | Provider |
|------|----------|
| `"gpt-4o-mini"` | OpenAI |
| `"openai:gpt-4o"` | OpenAI (`gpt-4o`) |
| `"command-r-plus"` | Cohere |
| `"cohere:command-r"` | Cohere (`command-r`) |

### `config_loader` — 환경변수 로드

```python
from src.utils.config_loader import load_root_env, load_agent_env, get_env

load_root_env()
load_agent_env("ppt")  # src/agents/agent_env/ppt.env 로드

api_key = get_env("OPENAI_API_KEY", default="")
```

### `get_logger` — JSON 구조화 로그

```python
from src.utils.logger import get_logger

logger = get_logger("ppt_agent")
logger.info("[REQUEST] ppt_agent, template=%s, query=%s", template, query)
logger.info("[RESPONSE] status=success, elapsed_time_ms=%s", elapsed_ms)
```

출력 형식 (JSON, stdout):
```json
{
  "timestamp": "2026-05-03T14:10:22.000000",
  "level": "INFO",
  "name": "ppt_agent",
  "message": "[REQUEST] ppt_agent, template=business, query=..."
}
```

---

## 7. 새 Agent / Module 추가하기

### Step 1. Module 디렉토리 생성

```bash
mkdir -p src/modules/my_module/config
touch src/modules/my_module/{__init__,service,types,constants}.py
touch src/modules/my_module/config/{__init__,config}.py
```

### Step 2. `config/config.py`

```python
from src.utils.config_loader import load_root_env, load_agent_env, get_env

load_root_env()
load_agent_env("my_module")

MY_MODEL_ID = get_env("MY_MODEL_ID", "openai:gpt-4o-mini")
```

### Step 3. `service.py`

```python
from src.utils.llm_manager import LLMManager
from .config.config import MY_MODEL_ID

class MyModuleService:
    def __init__(self):
        self.llm = LLMManager()

    async def execute(self, query: str) -> str:
        result = await self.llm.ainvoke(query, model_name=MY_MODEL_ID)
        return result["content"]

my_module_service = MyModuleService()
```

### Step 4. `__init__.py`

```python
from .service import my_module_service

__all__ = ["my_module_service"]
```

### Step 5. Agent 파일

```python
# src/agents/my_module_agent.py
import time
from src.modules.my_module import my_module_service
from src.utils.logger import get_logger

logger = get_logger("my_module_agent")

async def my_module_agent(query: str) -> str:
    start = time.time()
    logger.info("[REQUEST] my_module, query=%s", query)
    try:
        result = await my_module_service.execute(query=query)
        elapsed = round((time.time() - start) * 1000, 2)
        logger.info("[RESPONSE] status=success, elapsed_time_ms=%s", elapsed)
        return result
    except Exception as e:
        elapsed = round((time.time() - start) * 1000, 2)
        logger.error("[RESPONSE] status=error, elapsed_time_ms=%s, error=%s", elapsed, str(e))
        return f"오류가 발생했습니다: {e}"
```

### Step 6. `main.py` 등록

```python
from src.agents.my_module_agent import my_module_agent

@mcp.tool(name="MyTool", description="...")
async def my_tool(query: str) -> str:
    return await my_module_agent(query=query)
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

## 8. 서버 실행

### 의존성 설치

```bash
uv sync
```

### 환경변수 설정

```bash
cp .env.example .env
# LLM API 키 및 endpoint 입력

cp src/agents/agent_env/nl2mermaid.env.example src/agents/agent_env/nl2mermaid.env
cp src/agents/agent_env/ppt.env.example        src/agents/agent_env/ppt.env
```

### 개발 모드 (Hot Reload)

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 9101 --reload
```

### 운영 모드

```bash
uv run gunicorn -b 0.0.0.0:9101 -k uvicorn.workers.UvicornWorker main:app
```

### MCP 접속 확인

```
http://0.0.0.0:9101/mcp
```

### 렌더링 Provider (NL2Mermaid)

| Provider | 방식 | 특징 |
|----------|------|------|
| `mermaid_ink` (기본) | GET + pako 인코딩 | 설치 불필요, 한글 지원 |
| `kroki` (선택) | POST | 자체 호스팅 시 사용 |
