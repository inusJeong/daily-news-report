"""파이프라인 전 단계가 공유하는 데이터 구조."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Article:
    title: str
    url: str
    source: str               # 언론사/매체 이름
    published: datetime | None
    summary: str = ""         # RSS/API가 준 짧은 설명
    category: str = ""        # 이 기사를 가져온 카테고리 id
    via: str = ""             # naver / google / rss
    lang: str = "ko"
    body: str = ""            # 원문 본문 발췌 (상위 후보만 채움)

    @property
    def direct_link(self) -> bool:
        """Google News 리다이렉트가 아닌 언론사 원문 링크인가."""
        return "news.google.com" not in self.url


@dataclass
class Cluster:
    """같은 사건을 다룬 기사 묶음. 묶인 기사 수 = 그 이슈의 무게."""
    id: str
    category: str
    articles: list[Article] = field(default_factory=list)
    score: float = 0.0
    relevance: float = 0.0
    importance: float = 0.0

    @property
    def lead(self) -> Article:
        """대표 기사: 원문 링크가 있고, 설명이 가장 긴 기사."""
        return max(self.articles, key=lambda a: (a.direct_link, bool(a.body), len(a.summary)))

    @property
    def sources(self) -> list[str]:
        seen: list[str] = []
        for a in self.articles:
            if a.source and a.source not in seen:
                seen.append(a.source)
        return seen

    @property
    def latest(self) -> datetime | None:
        times = [a.published for a in self.articles if a.published]
        return max(times) if times else None


@dataclass
class Story:
    """리포트에 실리는 최종 이슈 (AI 요약 결과)."""
    category: str
    headline: str
    short: str                # 카톡용 20자 헤드라인
    what: str
    points: list[str]
    why: str
    url: str
    sources: list[str]
    lead_title: str = ""      # 원문 대표 제목 (다음 날 중복 판정용)
    summarized: bool = True   # False면 요약 실패 → 제목+링크만 노출
