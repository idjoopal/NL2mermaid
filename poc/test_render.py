"""
POC: mermaid.ink / Kroki 한글 렌더링 검증

테스트 시나리오:
1. mermaid.ink (base64, pako 인코딩) — flowchart, sequence
2. kroki.io (POST) — flowchart, sequence
"""
import asyncio
import base64
import json
import zlib
from pathlib import Path

import httpx


# ─────────────────────────────────────────────────
# 한글 포함 테스트 다이어그램
# ─────────────────────────────────────────────────
FLOWCHART_KO = """flowchart TD
    A[사용자 요청] --> B{인증 확인}
    B -->|성공| C[데이터 조회]
    B -->|실패| D[에러 응답]
    C --> E[결과 반환]
"""

SEQUENCE_KO = """sequenceDiagram
    participant 사용자
    participant 서버
    participant DB
    사용자->>서버: 로그인 요청
    서버->>DB: 사용자 정보 조회
    DB-->>서버: 정보 반환
    서버-->>사용자: 토큰 발급
"""

# 폰트 지정 init 디렉티브가 도움이 되는지 비교
FLOWCHART_KO_WITH_FONT = """%%{init: {'theme':'default', 'themeVariables': {'fontFamily':'Noto Sans KR, Apple SD Gothic Neo, sans-serif'}}}%%
flowchart TD
    A[사용자 요청] --> B{인증 확인}
    B -->|성공| C[데이터 조회]
    B -->|실패| D[에러 응답]
    C --> E[결과 반환]
"""


# ─────────────────────────────────────────────────
# mermaid.ink — pako 인코딩
# ─────────────────────────────────────────────────
def encode_pako(code: str) -> str:
    payload = json.dumps({"code": code, "mermaid": {"theme": "default"}})
    compressed = zlib.compress(payload.encode(), 9)
    return base64.b64encode(compressed).decode().replace("+", "-").replace("/", "_")


def encode_base64(code: str) -> str:
    return base64.urlsafe_b64encode(code.encode()).decode()


async def render_mermaid_ink(code: str, label: str, *, use_pako: bool = True) -> bytes:
    if use_pako:
        token = "pako:" + encode_pako(code)
    else:
        token = encode_base64(code)
    url = f"https://mermaid.ink/img/{token}?type=png&bgColor=white"
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(url)
        r.raise_for_status()
        out = Path(__file__).parent / f"{label}.png"
        out.write_bytes(r.content)
        print(f"[mermaid.ink] {label}: {len(r.content)} bytes -> {out}")
        return r.content


# ─────────────────────────────────────────────────
# kroki.io — POST
# ─────────────────────────────────────────────────
async def render_kroki(code: str, label: str) -> bytes:
    url = "https://kroki.io/mermaid/png"
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(url, content=code.encode(), headers={"Content-Type": "text/plain"})
        r.raise_for_status()
        out = Path(__file__).parent / f"{label}.png"
        out.write_bytes(r.content)
        print(f"[kroki.io   ] {label}: {len(r.content)} bytes -> {out}")
        return r.content


# ─────────────────────────────────────────────────
# 메인 — 모든 조합 실행
# ─────────────────────────────────────────────────
async def main():
    tasks = [
        # mermaid.ink
        render_mermaid_ink(FLOWCHART_KO, "mermaid_ink_flowchart_ko"),
        render_mermaid_ink(SEQUENCE_KO, "mermaid_ink_sequence_ko"),
        render_mermaid_ink(FLOWCHART_KO_WITH_FONT, "mermaid_ink_flowchart_ko_font"),
        # kroki.io
        render_kroki(FLOWCHART_KO, "kroki_flowchart_ko"),
        render_kroki(SEQUENCE_KO, "kroki_sequence_ko"),
        render_kroki(FLOWCHART_KO_WITH_FONT, "kroki_flowchart_ko_font"),
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for r in results:
        if isinstance(r, Exception):
            print(f"FAIL: {type(r).__name__}: {r}")


if __name__ == "__main__":
    asyncio.run(main())
