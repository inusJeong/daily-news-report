"""4단계 · 요약: 카테고리별 후보를 Gemini에게 주고 "고르기 + 구조화 요약"을 한 번에 맡긴다.

규칙 점수(3단계)는 빠르지만 보도자료·광고성 기사를 못 거른다. 마지막 선택은
맥락을 읽을 수 있는 LLM이 하고, 규칙은 후보를 좁히는 역할만 한다.
Gemini API 무료 등급을 쓴다 (하루 5회 호출이라 무료 한도 안).
카테고리별 호출이 서로 독립이라 병렬로 돌리고, 하나가 실패해도 그 카테고리만
"제목+링크"로 대체된다.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from .config import env
from .models import Cluster, Story

SYSTEM = """당신은 한 사람만을 위한 아침 뉴스 브리핑 에디터입니다.

독자: {about}

할 일: 한 카테고리의 후보 이슈 목록을 받아, 독자가 오늘 알아야 할 이슈를 최대 {pick}개 고르고 구조화 요약을 씁니다.

고르는 기준
- 실질적인 정보가 있는 뉴스를 고릅니다. 보도자료성 행사 소식, 단순 수상·협약·홍보, 광고성 기사는 고르지 않습니다.
- 여러 매체가 다룬 이슈는 무게가 있다는 신호지만, 홍보 기사가 여러 곳에 뿌려진 경우와 구별하세요.
- 서로 같은 사건을 다루는 후보는 하나만 고릅니다.
- 가치 있는 후보가 {pick}개보다 적으면 적게 고르세요. 억지로 채우지 않습니다.

쓰는 규칙 (모두 한국어, 영어 기사도 한국어로)
- headline: 사건의 핵심을 담은 제목, 40자 이내. 원문 제목을 그대로 베끼지 말고 새로 씁니다.
- short: 카카오톡 미리보기용 초압축 제목, 18자 이내.
- what: 무슨 일이 있었는지 한 문장, "~했다" 체.
- points: 핵심 포인트 2~3개. 각 50자 이내의 명사형 종결("~함", "~음", "~ 전망")로 통일. 숫자·고유명사·원인과 결과를 담습니다. 여러 매체가 다르게 강조하면 그 차이도 포인트로 씁니다.
- why: 한두 문장, 100자 이내. 반드시 "~다"로 끝나는 평서문("~입니다" 금지). 관점: {why}
  "중요하다", "주목할 만하다" 같은 일반론은 쓰지 않습니다.
- 주어진 텍스트에 있는 사실만 씁니다. 추측으로 수치나 사실을 만들지 않습니다.
- 원문 문장을 인용하지 말고 자신의 말로 요약합니다."""


# 카테고리에 why가 없을 때: 전공에 억지로 연결하지 않는 교양 관점
DEFAULT_WHY = ("세상을 이해하는 데 왜 알아둘 만한지(배경, 파장, 논쟁점). "
               "독자의 전공(SCM·산업공학)에 억지로 연결하지 않는다.")


class Pick(BaseModel):
    candidate: int = Field(description="고른 후보의 번호")
    headline: str
    short: str
    what: str
    points: list[str]
    why: str


class Picks(BaseModel):
    picks: list[Pick]


def _candidate_text(i: int, cl: Cluster, tz) -> str:
    lead = cl.lead
    when = cl.latest.astimezone(tz).strftime("%m/%d %H:%M") if cl.latest else "시각 미상"
    content = lead.body or max((a.summary for a in cl.articles), key=len) or "(본문 없음 — 제목만 참고)"
    others = [a.title for a in cl.articles if a.title != lead.title][:3]
    lines = [
        f"[{i}] {lead.title}",
        f"매체 {len(cl.sources)}곳: {', '.join(cl.sources[:6])} · {when}",
        f"내용: {content}",
    ]
    if others:
        lines.append("다른 매체 제목: " + " / ".join(others))
    return "\n".join(lines)


def summarize_category(client: genai.Client, cfg: dict, cat: dict, clusters: list[Cluster]) -> list[Story]:
    candidates = "\n\n".join(_candidate_text(i, cl, cfg["tz"]) for i, cl in enumerate(clusters, 1))
    response = client.models.generate_content(
        model=cfg["llm"]["model"],
        contents=f"카테고리: {cat['name']}\n\n후보 이슈:\n\n{candidates}",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM.format(about=cfg["profile"]["about"].strip(), pick=cat["pick"],
                                             why=cat.get("why", DEFAULT_WHY).strip()),
            response_mime_type="application/json",
            response_schema=Picks,     # 이 구조의 JSON만 돌려받는다
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        ),
    )
    parsed = response.parsed
    if not isinstance(parsed, Picks):
        reason = response.candidates[0].finish_reason if response.candidates else "응답 없음"
        raise RuntimeError(f"요약 실패 ({reason})")

    stories = []
    for p in parsed.picks[: cat["pick"]]:
        if not 1 <= p.candidate <= len(clusters):
            continue
        cl = clusters[p.candidate - 1]
        stories.append(Story(category=cat["id"], headline=p.headline, short=p.short, what=p.what,
                             points=p.points[:3], why=p.why, url=cl.lead.url, sources=cl.sources,
                             lead_title=cl.lead.title))
    return stories


def fallback(cat: dict, clusters: list[Cluster]) -> list[Story]:
    """요약이 실패한 카테고리는 점수 상위 이슈를 제목+링크로만 보여준다."""
    return [Story(category=cat["id"], headline=cl.lead.title, short=cl.lead.title[:18], what="", points=[],
                  why="", url=cl.lead.url, sources=cl.sources, lead_title=cl.lead.title, summarized=False)
            for cl in clusters[: cat["pick"]]]


def summarize(cfg: dict, shortlists: dict[str, list[Cluster]]) -> tuple[dict[str, list[Story]], list[str]]:
    cats = [c for c in cfg["categories"] if shortlists.get(c["id"])]
    errors: list[str] = []
    if not env("GEMINI_API_KEY"):
        errors.append("GEMINI_API_KEY 없음 → 요약 없이 제목만")
        return {c["id"]: fallback(c, shortlists[c["id"]]) for c in cats}, errors

    # 무료 등급은 분당 호출 수 제한이 있어 429(한도 초과)·5xx는 기다렸다가 재시도
    client = genai.Client(api_key=env("GEMINI_API_KEY"), http_options=types.HttpOptions(
        retry_options=types.HttpRetryOptions(attempts=5, initial_delay=5, max_delay=60,
                                             http_status_codes=[429, 500, 502, 503, 504])))

    def run(cat):
        try:
            return cat["id"], summarize_category(client, cfg, cat, shortlists[cat["id"]])
        except Exception as exc:
            errors.append(f"{cat['name']}: {exc}")
            return cat["id"], fallback(cat, shortlists[cat["id"]])

    with ThreadPoolExecutor(max_workers=2) as pool:   # 무료 한도를 고려해 동시 2개만
        results = dict(pool.map(run, cats))
    return results, errors
