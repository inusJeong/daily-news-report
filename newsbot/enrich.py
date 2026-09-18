"""3.5단계 · 본문 보강: 후보 이슈의 원문 본문 앞부분을 가져와 요약 품질을 높인다.

RSS 설명은 1~2문장뿐이라 "핵심 포인트"를 뽑기엔 부족하다. 후보(카테고리당 ~7개)만
가져오므로 요청 수는 하루 30여 건. 실패하면 RSS 설명만으로 요약한다.
"""
from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote

import requests

from .collect import TIMEOUT, UA
from .models import Cluster

BODY_CHARS = 1500

try:
    import trafilatura
except ImportError:          # 없으면 본문 보강만 건너뛴다
    trafilatura = None


def resolve_google(url: str) -> str:
    """Google News 리다이렉트 링크 → 언론사 원문 주소. (비공식 방식이라 실패하면 원래 링크 유지)"""
    aid = url.split("/articles/")[1].split("?")[0]
    page = requests.get(f"https://news.google.com/rss/articles/{aid}", headers=UA, timeout=TIMEOUT).text
    sg = re.search(r'data-n-a-sg="([^"]+)"', page).group(1)
    ts = re.search(r'data-n-a-ts="([^"]+)"', page).group(1)
    req = ["Fbv4je", f'["garturlreq",[["X","X",["X","X"],null,null,1,1,"US:en",null,1,null,null,null,null,null,0,1],'
                     f'"X","X",1,[1,1,1],1,1,null,0,0,null,0],"{aid}",{ts},"{sg}"]']
    resp = requests.post("https://news.google.com/_/DotsSplashUi/data/batchexecute",
                         headers={**UA, "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"},
                         data="f.req=" + quote(json.dumps([[req]])), timeout=TIMEOUT)
    real = json.loads(json.loads(resp.text.split("\n\n")[1])[0][2])[1]
    if not real.startswith("http"):
        raise ValueError("decode failed")
    return real


def _body(url: str) -> str:
    resp = requests.get(url, headers=UA, timeout=TIMEOUT)
    resp.raise_for_status()
    text = trafilatura.extract(resp.text, include_comments=False, include_tables=False) or ""
    return " ".join(text.split())[:BODY_CHARS]


def enrich(shortlists: dict[str, list[Cluster]]) -> int:
    if trafilatura is None:
        return 0
    targets = []
    for clusters in shortlists.values():
        for cl in clusters:
            # 원문 링크가 있는 기사를 우선, 최대 2개까지 시도 (첫 번째가 막히면 두 번째)
            arts = sorted(cl.articles, key=lambda a: not a.direct_link)[:2]
            targets.append(arts)

    def run(arts):
        for a in arts:
            try:
                if not a.direct_link:
                    a.url = resolve_google(a.url)   # 카드의 '원문' 링크도 실제 기사로 바뀐다
                a.body = _body(a.url)
                if len(a.body) > 200:
                    return 1
            except Exception:
                continue
        return 0

    with ThreadPoolExecutor(max_workers=8) as pool:
        return sum(pool.map(run, targets))
