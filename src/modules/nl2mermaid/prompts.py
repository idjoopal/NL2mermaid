SYSTEM_PROMPT = """\
당신은 자연어 설명을 Mermaid 다이어그램 코드로 변환하는 전문가입니다.

## 규칙
1. Mermaid 코드만 출력합니다. 설명, 마크다운 코드 블록(```), 부가 텍스트는 절대 포함하지 않습니다.
2. 한국어 텍스트를 그대로 사용합니다.
3. 노드 텍스트에 특수문자(괄호, 따옴표 등)가 필요하면 큰따옴표로 감싸거나 이스케이프합니다.
4. PPT에 사용할 수 있도록 간결하고 명확하게 작성합니다.
5. 노드는 최대 15개를 넘지 않도록 합니다.

## 다이어그램 타입별 규칙
- flowchart: `flowchart TD` 또는 `flowchart LR` 사용. 프로세스 흐름에는 TD 권장.
- sequence: `sequenceDiagram` 사용. participant 이름은 한글 가능.
- gantt: `gantt` 사용. dateFormat YYYY-MM-DD 명시.
- timeline: `timeline` 사용. 연도/기간 기준으로 구분.
- mindmap: `mindmap` 사용. 루트 노드는 가장 핵심 개념.
"""

TYPE_DETECTION_PROMPT = """\
다음 질의를 보고 가장 적합한 Mermaid 다이어그램 타입을 하나만 답하세요.
선택지: flowchart, sequence, gantt, timeline, mindmap

질의: {query}

답변 형식: 타입명만 (예: flowchart)
"""

GENERATION_PROMPTS = {
    "flowchart": """\
다음 내용을 Mermaid flowchart 다이어그램으로 표현하세요.

질의: {query}

예시:
flowchart TD
    A[고객 주문] --> B{{재고 확인}}
    B -->|재고 있음| C[결제 처리]
    B -->|재고 없음| D[입고 예정 안내]
    C --> E[배송 시작]
    C -->|결제 실패| F[주문 취소]
""",

    "sequence": """\
다음 내용을 Mermaid sequenceDiagram으로 표현하세요.

질의: {query}

예시:
sequenceDiagram
    participant 고객
    participant 쇼핑몰
    participant 결제사
    고객->>쇼핑몰: 주문 요청
    쇼핑몰->>결제사: 결제 승인 요청
    결제사-->>쇼핑몰: 승인 완료
    쇼핑몰-->>고객: 주문 확인서 발송
""",

    "gantt": """\
다음 내용을 Mermaid gantt 차트로 표현하세요.

질의: {query}

예시:
gantt
    title 프로젝트 일정
    dateFormat YYYY-MM-DD
    section 기획
        요구사항 분석 : 2024-01-01, 14d
        설계 : 2024-01-15, 7d
    section 개발
        백엔드 개발 : 2024-01-22, 21d
        프론트엔드 개발 : 2024-01-29, 14d
    section 테스트
        QA 테스트 : 2024-02-19, 7d
        배포 : 2024-02-26, 3d
""",

    "timeline": """\
다음 내용을 Mermaid timeline으로 표현하세요.

질의: {query}

예시:
timeline
    title 회사 성장 히스토리
    2020 : 법인 설립
         : 첫 제품 출시
    2021 : 시리즈 A 투자 유치
         : 해외 진출
    2022 : 매출 100억 달성
    2023 : 코스닥 상장
""",

    "mindmap": """\
다음 내용을 Mermaid mindmap으로 표현하세요.

질의: {query}

예시:
mindmap
  root((마케팅 전략))
    디지털 마케팅
      SNS 광고
      검색 광고
      콘텐츠 마케팅
    오프라인 마케팅
      이벤트
      옥외 광고
    파트너십
      제휴 마케팅
      인플루언서
""",
}
