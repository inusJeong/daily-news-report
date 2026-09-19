"""토익 단어장: 30일 과정(하루 LC 10 + RC 15, 주제별) + 간격 반복 복습.

LC = Part 1 사진 묘사 3 + Part 2~4 대화 표현 7 (예문을 🔊로 듣고 뜻 떠올리기)
RC = Part 5·6에 나오는 짝꿍 표현(연어) 중심 단어 15

망각 곡선에 맞춰 1·3·7·14·28 학습일 전에 배운 단어를 다시 보여준다.
날짜가 아니라 "학습일(Day)" 기준이라, 발송이 빠진 날이 있어도 복습 순서가 꼬이지 않는다.
진도(word_day)는 용어 코너처럼 발송 성공 시에만 전진한다.
"""
from __future__ import annotations

import json

from .config import DATA

REVIEW_GAPS = [(1, "어제"), (3, "3일 전"), (7, "1주 전"), (14, "2주 전"), (28, "4주 전")]


def _bank() -> list[dict]:
    return json.loads((DATA / "toeic_words.json").read_text(encoding="utf-8"))["days"]


def todays_vocab(word_day: int) -> tuple[dict, int]:
    """word_day(0부터)의 새 단어와 복습 묶음. (오늘 단어장, 다음 word_day)"""
    bank = _bank()
    total = len(bank)
    today = bank[word_day % total]
    reviews = []
    for gap, label in REVIEW_GAPS:
        past = word_day - gap
        if past >= 0:
            d = bank[past % total]
            reviews.append({"label": label, "day": past % total + 1, "theme": d["theme"],
                            "lc": d["lc"], "rc": d["rc"]})
    vocab = {
        "day": word_day % total + 1,
        "total_days": total,
        "round": word_day // total + 1,          # 30일을 다 돌면 2회독, 3회독…
        "theme": today["theme"],
        "lc": today["lc"],
        "rc": today["rc"],
        "reviews": reviews,
        "learned": min(word_day, total) * (len(today["lc"]) + len(today["rc"])),
    }
    return vocab, word_day + 1
