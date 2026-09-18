"""config.yaml과 환경변수(.env) 로드."""
from __future__ import annotations

import os
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DOCS = ROOT / "docs"      # GitHub Pages로 공개되는 리포트
OUT = ROOT / "out"        # build → send 사이에 넘기는 임시 결과물


def load_env() -> None:
    """로컬 실행 시 .env를 읽는다. 이미 설정된 환경변수는 덮어쓰지 않는다."""
    path = ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if value.strip():
            os.environ.setdefault(key.strip(), value.strip())


def load_config() -> dict:
    load_env()
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    cfg["tz"] = ZoneInfo(cfg["report"]["timezone"])
    return cfg


def env(name: str) -> str:
    return os.environ.get(name, "").strip()
