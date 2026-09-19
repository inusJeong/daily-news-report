"""실행 사이에 기억해야 하는 것: 용어 커서, 토익 진도, 최근 보낸 이슈(재방송 방지), 마지막 발송일(중복 발송 방지)."""
from __future__ import annotations

import json
from datetime import date, timedelta

from .config import DATA

PATH = DATA / "state.json"


def load() -> dict:
    if PATH.exists():
        return json.loads(PATH.read_text(encoding="utf-8"))
    return {"term_cursor": 0, "last_sent": None, "history": []}


def save(state: dict) -> None:
    PATH.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")


def recent_titles(state: dict, today: date, days: int) -> list[str]:
    since = (today - timedelta(days=days)).isoformat()
    return [t for h in state["history"] if h["date"] >= since and h["date"] < today.isoformat()
            for t in h["titles"]]


def record_sent(state: dict, today: date, titles: list[str], next_cursor: int, keep_days: int,
                next_word_day: int | None = None) -> dict:
    since = (today - timedelta(days=keep_days)).isoformat()
    history = [h for h in state["history"] if h["date"] >= since and h["date"] != today.isoformat()]
    history.append({"date": today.isoformat(), "titles": titles})
    word_day = state.get("word_day", 0) if next_word_day is None else next_word_day
    return {"term_cursor": next_cursor, "word_day": word_day, "last_sent": today.isoformat(), "history": history}
