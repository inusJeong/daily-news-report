"""2단계 · 중복 제거: 같은 사건을 다룬 기사를 하나의 이슈(Cluster)로 묶는다.

제목의 글자 2-gram 유사도(Dice)로 묶는다. 한국어 제목은 조사·어순이 달라도
핵심 명사가 겹치기 때문에 형태소 분석 없이도 잘 동작한다.
묶인 기사 수는 버리지 않고 "중요도" 신호로 다음 단계에 넘긴다.
"""
from __future__ import annotations

import re
from collections import defaultdict

from .models import Article, Cluster

THRESHOLD = 0.42      # 이 이상 비슷하면 같은 사건
STOPWORDS = {"속보", "단독", "종합", "영상", "포토", "사진", "르포", "인터뷰", "기자", "뉴스",
             "the", "and", "for", "with", "from", "into", "over", "after", "amid", "says", "said", "will",
             "that", "this", "what", "how", "why", "new", "its", "are", "was", "has", "have", "about", "more"}


def normalize(title: str) -> str:
    t = re.sub(r"\[[^\]]*\]|\([^)]*\)|【[^】]*】|<[^>]*>", " ", title)   # [속보] (종합) 같은 말머리 제거
    t = re.sub(r"[^\w가-힣 ]", " ", t.lower())
    return re.sub(r"\s+", " ", t).strip()


def words(title: str) -> set[str]:
    return {w for w in normalize(title).split() if len(w) >= 2 and w not in STOPWORDS}


def is_korean(title: str) -> bool:
    return len(re.findall(r"[가-힣]", title)) >= 4


def signature(title: str) -> set[str]:
    """비교용 특징 집합. 한국어는 글자 2-gram, 영어는 내용어(단어) 집합.

    영어에 글자 2-gram을 쓰면 'supply chain'만 겹쳐도 같은 사건으로 묶여버린다.
    """
    if is_korean(title):
        s = normalize(title).replace(" ", "")
        return {s[i:i + 2] for i in range(len(s) - 1)}
    return {"w:" + w.rstrip("s") for w in words(title) if len(w) >= 3}


def dice(x: set[str], y: set[str]) -> float:
    return 2 * len(x & y) / (len(x) + len(y)) if x and y else 0.0


def similarity(a: str, b: str) -> float:
    return dice(signature(a), signature(b))


def cluster_articles(articles: list[Article], category_order: list[str]) -> list[Cluster]:
    """전체 기사를 한 번에 묶는다 → 카테고리를 넘나드는 중복도 제거된다."""
    rank = {c: i for i, c in enumerate(category_order)}
    # 설명이 긴(정보가 많은) 기사를 먼저 → 대표 제목이 좋아진다
    ordered = sorted(articles, key=lambda a: (rank.get(a.category, 99), -len(a.summary)))

    clusters: list[Cluster] = []
    seeds: list[set[str]] = []                # 클러스터 첫 기사의 특징 (멤버끼리 연쇄로 번지는 것 방지)
    index: dict[str, set[int]] = defaultdict(set)   # 특징 → 클러스터 번호 (비교 대상 좁히기)

    for art in ordered:
        sig = signature(art.title)
        if len(sig) < 3:
            continue
        candidates = set().union(*(index[f] for f in sig))
        best, best_sim = None, 0.0
        for ci in candidates:
            sim = dice(sig, seeds[ci])
            if sim > best_sim:
                best, best_sim = ci, sim
        if best is not None and best_sim >= THRESHOLD:
            clusters[best].articles.append(art)
        else:
            ci = len(clusters)
            # 카테고리는 가장 먼저 들어온 기사(=우선순위가 가장 높은 카테고리)를 따른다
            clusters.append(Cluster(id=f"c{ci}", category=art.category, articles=[art]))
            seeds.append(sig)
            for f in sig:
                index[f].add(ci)
    return merge_split(clusters)


def merge_split(clusters: list[Cluster], threshold: float = 0.5) -> list[Cluster]:
    """같은 사건이 표현 차이로 두 묶음으로 갈라진 경우를 다시 합친다.

    1차 묶기는 첫 기사하고만 비교해서(연쇄 번짐 방지) 가끔 둘로 갈라진다.
    2차에서는 묶음의 멤버끼리 비교하되, 더 엄격한 기준을 쓴다.
    """
    big = [c for c in clusters if len(c.articles) >= 2]
    sigs = {c.id: [signature(a.title) for a in c.articles[:5]] for c in big}
    merged: set[str] = set()
    for i, a in enumerate(big):
        if a.id in merged:
            continue
        for b in big[i + 1:]:
            if b.id in merged:
                continue
            if any(dice(x, y) >= threshold for x in sigs[a.id] for y in sigs[b.id]):
                a.articles.extend(b.articles)
                merged.add(b.id)
    return [c for c in clusters if c.id not in merged]
