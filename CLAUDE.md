# NL2Mermaid 프로젝트

자연어 질의를 받아 Mermaid 다이어그램 이미지를 생성하는 MCP Agent.

---

## 아키텍처 원칙

`prebuilt_base` 구조를 준수한다.

```
main.py  →  agents  →  modules  →  utils
```

- `main.py`: MCP Tool 등록만
- `agents/`: Module 조합 + I/O 변환 + 로깅
- `modules/`: 기능별 독립 비즈니스 로직
- `utils/`: 공통 인프라 (llm_manager, db_manager, config_loader, logger)

---

## 브랜치 전략

```
main          ← 배포용 (명시적 요청 시에만 반영)
  └── dev     ← 개발 베이스
        └── feat/{기능명}  ← 기능 개발 후 dev에 PR 머지
```

---

## 구현 계획

### Agent: nl2mermaid_agent

```
nl2mermaid_agent(query, diagram_type, theme)
    ├─ nl2mermaid_service.execute(query, diagram_type) → mermaid_code
    ├─ mermaid_renderer_service.execute(code, theme)   → image_bytes
    ├─ 렌더링 실패 시 → 에러 피드백 → nl2mermaid 재시도 (최대 2회)
    └─ 출력: FastMCP Image 객체 + 파일 저장
```

### Module 1: `nl2mermaid` — 자연어 → Mermaid 코드 생성

```
src/modules/nl2mermaid/
├── __init__.py
├── service.py          execute(query, diagram_type) → str
├── prompts.py          다이어그램 타입별 few-shot 포함 LLM 프롬프트
├── types.py            DiagramType enum, GenerationResult
├── constants.py
└── config/
    ├── config.py
    └── config.yaml     기본 모델, 다이어그램 타입 설정
```

- LLM: `gpt-4o-mini` 우선 (agent_env: `NL2MERMAID_MODEL_ID=openai:gpt-4o-mini`)
- diagram_type 미지정 시 LLM이 query를 보고 자동 결정 (하이브리드)
- 출력 전처리: ` ```mermaid ` 마커 제거, 공백 정리

### Module 2: `mermaid_renderer` — Mermaid 코드 → 이미지 렌더링

```
src/modules/mermaid_renderer/
├── __init__.py
├── service.py          execute(code, theme, fmt) → bytes
├── types.py            ImageFormat, RenderResult
├── constants.py
├── providers/
│   ├── base.py         BaseRendererProvider
│   ├── mermaid_ink.py  mermaid.ink (기본, pako 인코딩)
│   └── kroki.py        Kroki (선택, POST)
└── config/
    ├── config.py
    └── services_config.yaml   provider URL, timeout, 기본 theme 등
```

- 기본 provider: `mermaid_ink`
- 한글 렌더링: Noto Sans KR 폰트 init 디렉티브 자동 삽입
- 배경: 흰색 (`bgColor=white`)
- 출력: PNG bytes → FastMCP `Image` 반환 + `./output/` 디렉토리에 파일 저장

### Agent 파일

```
src/agents/
├── nl2mermaid_agent.py
└── agent_env/
    └── nl2mermaid.env.example
        NL2MERMAID_MODEL_ID=openai:gpt-4o-mini
        RENDERER_PROVIDER=mermaid_ink
        RENDERER_OUTPUT_DIR=./output
```

### main.py 등록

```python
@mcp.tool(name="NL2Mermaid")
async def nl2mermaid_tool(
    query: str,
    diagram_type: str = "auto",   # auto | flowchart | sequence | gantt | timeline | mindmap
    theme: str = "default",       # default | neutral | dark | forest
) -> Image:
    return await nl2mermaid_agent(query=query, diagram_type=diagram_type, theme=theme)
```

---

## 지원 다이어그램 타입

| 타입 | Mermaid 문법 | 용도 |
|------|-------------|------|
| flowchart | `flowchart TD/LR` | 프로세스 흐름도 (핵심) |
| sequence | `sequenceDiagram` | 시스템·팀 간 상호작용 |
| gantt | `gantt` | 프로젝트 일정 |
| timeline | `timeline` | 시계열 이벤트 |
| mindmap | `mindmap` | 개념 구조도 |

---

## 개발 순서

1. `feat/poc-rendering` — mermaid.ink / Kroki 한글 렌더링 검증 (POC)
2. `feat/mermaid-renderer-module` — renderer 모듈 (provider 패턴)
3. `feat/nl2mermaid-module` — nl2mermaid 모듈 (LLM + 프롬프트 + few-shot)
4. `feat/nl2mermaid-agent` — agent + retry 로직 + main.py 등록
