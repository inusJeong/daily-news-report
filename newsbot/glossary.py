"""5단계 · 오늘의 용어: 고정 용어 뱅크를 순서대로 순환한다 (그날 기사와 무관 → 빠짐없이 커버).

분야를 번갈아 섞은 순서(산업공학→SCM→리스크→영어→산업공학…)로 돌기 때문에
하루 4개를 뽑으면 자연스럽게 분야별 1개씩이 된다.
커서는 발송에 성공했을 때만 전진한다 → 실패한 날의 용어를 건너뛰지 않는다.
"""
from __future__ import annotations

import json
from itertools import zip_longest

from .config import DATA


def rotation() -> list[dict]:
    bank = json.loads((DATA / "terms.json").read_text(encoding="utf-8"))
    columns = [[{**t, "field": c["name"]} for t in c["terms"]] for c in bank["categories"]]
    return [t for row in zip_longest(*columns) for t in row if t]


def todays_terms(cursor: int, per_day: int) -> tuple[list[dict], int]:
    """(오늘의 용어, 다음 커서). 끝까지 가면 처음부터 반복."""
    order = rotation()
    picked = [order[(cursor + i) % len(order)] for i in range(per_day)]
    return picked, (cursor + per_day) % len(order)
