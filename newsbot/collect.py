"""1단계 · 수집: 카테고리별로 네이버 API / Google News RSS / 언론사 RSS에서 기사를 모은다.

소스 하나가 실패해도 전체는 계속 진행한다(실패는 통계에 기록).
"""
from __future__ import annotations

import calendar
import html
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote, urlparse

import feedparser
import requests

from .config import env
from .models import Article

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"}
TIMEOUT = 15

# 네이버 API는 언론사 이름을 주지 않으므로 도메인으로 추정
DOMAIN_NAMES = {
    "yna.co.kr": "연합뉴스", "chosun.com": "조선일보", "joongang.co.kr": "중앙일보", "donga.com": "동아일보",
    "hani.co.kr": "한겨레", "khan.co.kr": "경향신문", "hankyung.com": "한국경제", "mk.co.kr": "매일경제",
    "sedaily.com": "서울경제", "edaily.co.kr": "이데일리", "mt.co.kr": "머니투데이", "fnnews.com": "파이낸셜뉴스",
    "etnews.com": "전자신문", "zdnet.co.kr": "지디넷코리아", "kbs.co.kr": "KBS", "sbs.co.kr": "SBS",
    "imbc.com": "MBC", "ytn.co.kr": "YTN", "jtbc.co.kr": "JTBC", "newsis.com": "뉴시스", "news1.kr": "뉴스1",
    "hankookilbo.com": "한국일보", "seoul.co.kr": "서울신문", "kmib.co.kr": "국민일보", "heraldcorp.com": "헤럴드경제",
    "asiae.co.kr": "아시아경제", "bizwatch.co.kr": "비즈니스워치", "klnews.co.kr": "물류신문",
    "cargonews.co.kr": "카고뉴스", "dongascience.com": "동아사이언스", "sciencetimes.co.kr": "사이언스타임즈",
}


@dataclass
class SourceStat:
    category: str
    name: str
    count: int = 0
    error: str = ""


def clean(text: str, limit: int = 400) -> str:
    text = html.unescape(re.sub(r"<[^>]+>", " ", text or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def domain_name(url: str) -> str:
    host = urlparse(url).netloc.lower().removeprefix("www.").removeprefix("m.")
    for dom, name in DOMAIN_NAMES.items():
        if host == dom or host.endswith("." + dom):
            return name
    return host


def _entry_time(entry) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            return datetime.fromtimestamp(calendar.timegm(t), tz=timezone.utc)
    return None


def _fetch_feed(url: str):
    resp = requests.get(url, headers=UA, timeout=TIMEOUT)
    resp.raise_for_status()
    feed = feedparser.parse(resp.content)
    if not feed.entries and feed.bozo:
        raise ValueError(f"RSS 파싱 실패: {feed.bozo_exception}")
    return feed.entries


# ── 소스별 수집기 ────────────────────────────────────────────

def from_rss(category: str, name: str, url: str) -> list[Article]:
    out = []
    for e in _fetch_feed(url):
        title, link = clean(e.get("title", ""), 200), e.get("link", "")
        if not title or not link:
            continue
        out.append(Article(title=title, url=link, source=name, published=_entry_time(e),
                           summary=clean(e.get("summary", "")), category=category, via="rss",
                           lang="ko" if re.search(r"[가-힣]", title) else "en"))
    return out


def keyword_pattern(kw: str) -> re.Pattern:
    """영문 키워드는 단어 경계로 ('AI'가 'said'에 걸리지 않게), 한글은 부분 일치로."""
    if re.search(r"[가-힣]", kw):
        return re.compile(re.escape(kw))
    return re.compile(r"\b" + re.escape(kw), 0 if kw.isupper() else re.IGNORECASE)


def google_url(query: str, days: int = 1) -> tuple[str, str]:
    """설정의 검색어 표기를 Google News RSS 주소로 바꾼다."""
    lang = "ko"
    if query.startswith("en:"):
        lang, query = "en", query[3:]
    params = "hl=ko&gl=KR&ceid=KR:ko" if lang == "ko" else "hl=en-US&gl=US&ceid=US:en"
    if query == "top:ko":   # Google 주요 뉴스(여러 언론이 다루는 이슈 모음)
        return f"https://news.google.com/rss?{params}", lang
    return f"https://news.google.com/rss/search?q={quote(f'{query} when:{days}d')}&{params}", lang


def from_google(category: str, query: str, days: int) -> list[Article]:
    url, lang = google_url(query, days)
    out = []
    for e in _fetch_feed(url):
        source = (e.get("source") or {}).get("title", "") or "Google News"
        title = clean(e.get("title", ""), 200)
        suffix = f" - {source}"
        if title.endswith(suffix):
            title = title[: -len(suffix)]
        out.append(Article(title=title, url=e.get("link", ""), source=source, published=_entry_time(e),
                           summary="", category=category, via="google", lang=lang))
    return out


def from_naver(category: str, query: str) -> list[Article]:
    cid, secret = env("NAVER_CLIENT_ID"), env("NAVER_CLIENT_SECRET")
    if not cid or not secret:
        raise RuntimeError("NAVER 키 없음 (건너뜀)")
    resp = requests.get(
        "https://openapi.naver.com/v1/search/news.json",
        params={"query": query, "display": 40, "sort": "date"},
        headers={"X-Naver-Client-Id": cid, "X-Naver-Client-Secret": secret},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    out = []
    for item in resp.json().get("items", []):
        original = item.get("originallink") or item["link"]
        try:
            published = parsedate_to_datetime(item["pubDate"])
        except (KeyError, TypeError, ValueError):
            published = None
        # 네이버 뉴스(n.news.naver.com) 링크는 본문 추출이 안정적이라 우선 사용
        link = item["link"] if "naver.com" in item["link"] else original
        out.append(Article(title=clean(item["title"], 200), url=link, source=domain_name(original),
                           published=published, summary=clean(item.get("description", "")),
                           category=category, via="naver"))
    return out


# ── 전체 수집 ────────────────────────────────────────────────

def lookback_hours(cfg: dict, cat: dict) -> int:
    """인문·과학처럼 뉴스가 느린 분야는 카테고리별로 더 긴 기간을 본다."""
    return cat.get("lookback_hours", cfg["report"]["lookback_hours"])


def _matches(article: Article, patterns: list[re.Pattern]) -> bool:
    text = f"{article.title} {article.summary}"
    return any(p.search(text) for p in patterns)


def collect(cfg: dict, now: datetime) -> tuple[list[Article], list[SourceStat]]:
    jobs = []   # (stat, 함수, 인자, 포함 키워드, 제외 키워드)
    cutoffs = {}
    for cat in cfg["categories"]:
        cid = cat["id"]
        kw = [keyword_pattern(k) for k in cat.get("keywords") or []]
        drop = [keyword_pattern(k) for k in (cfg["report"].get("exclude") or []) + (cat.get("exclude") or [])]
        hours = lookback_hours(cfg, cat)
        cutoffs[cid] = now - timedelta(hours=hours)
        for q in cat.get("naver") or []:
            jobs.append((SourceStat(cid, f"네이버:{q}"), from_naver, (cid, q), None, drop))
        for q in cat.get("google") or []:
            jobs.append((SourceStat(cid, f"구글:{q}"), from_google, (cid, q, max(1, round(hours / 24))), None, drop))
        for f in cat.get("feeds") or []:
            jobs.append((SourceStat(cid, f["name"]), from_rss, (cid, f["name"], f["url"]),
                         kw if f.get("filter") else None, drop))

    def run(job):
        stat, fn, args, keep, drop = job
        try:
            items = fn(*args)
            if keep:
                items = [a for a in items if _matches(a, keep)]
            if drop:   # 인사·부고·보도자료성 기사 제거 (제목 기준)
                items = [a for a in items if not any(p.search(a.title) for p in drop)]
            return stat, items
        except Exception as exc:  # 소스 하나의 실패가 전체를 멈추지 않게
            stat.error = str(exc)[:120]
            return stat, []

    articles, stats, seen_urls = [], [], set()
    with ThreadPoolExecutor(max_workers=12) as pool:
        for stat, items in pool.map(run, jobs):
            cutoff = cutoffs[stat.category]
            fresh = [a for a in items if a.published is None or a.published >= cutoff]
            for a in fresh:
                key = (a.category, a.url)
                if key not in seen_urls:
                    seen_urls.add(key)
                    articles.append(a)
            stat.count = len(fresh)
            stats.append(stat)
    return articles, stats
