"""6단계 · 리포트 조립: 웹 리포트(HTML)와 카카오톡 요약(200자)을 만든다.

카카오톡 "나에게 보내기" 텍스트는 200자 제한이 있어 전체 리포트가 들어가지 않는다.
그래서 역할을 나눈다:  카톡 = 알림 + 오늘의 헤드라인,  웹 페이지 = 전체 리포트.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from html import escape

from .config import DOCS
from .models import Story

WEEKDAYS = "월화수목금토일"
KAKAO_LIMIT = 200


def date_label(d: datetime) -> str:
    return f"{d.month}월 {d.day}일 {WEEKDAYS[d.weekday()]}요일"


def source_label(sources: list[str]) -> str:
    if not sources:
        return ""
    return sources[0] if len(sources) == 1 else f"{sources[0]} 외 {len(sources) - 1}곳"


# ── 카카오톡 ─────────────────────────────────────────────────

def kakao_text(cfg: dict, now: datetime, stories: dict[str, list[Story]], terms: list[dict],
               vocab: dict | None = None) -> str:
    head = f"📰 {now.month}/{now.day}({WEEKDAYS[now.weekday()]}) {cfg['report']['title']}"
    lines = []
    for cat in cfg["categories"]:
        items = stories.get(cat["id"]) or []
        if items:
            lines.append(f"{cat['emoji']} {items[0].short}")
    tail = ["📘 " + " · ".join(re.sub(r"\s*\(.*\)$", "", t["term"]) for t in terms)]
    if vocab:
        n_review = sum(len(r["words"]) for r in vocab["reviews"])
        tail.append(f"📝 토익 Day {vocab['day']} {vocab['theme']} · 새 단어 {len(vocab['words'])}"
                    + (f" · 복습 {n_review}" if n_review else ""))

    # 200자 안에 들어갈 때까지 뒤쪽 카테고리부터 줄인다 (용어·토익 줄은 유지)
    while lines and len("\n".join([head, *lines, *tail])) > KAKAO_LIMIT:
        lines.pop()
    text = "\n".join([head, *lines, *tail])
    return text[:KAKAO_LIMIT]


# ── 웹 리포트 ────────────────────────────────────────────────

CSS = """
:root{--bg:#f6f5f2;--card:#fff;--ink:#1d1d1f;--sub:#6b6b70;--line:#e7e5e0;--accent:#2f6fed;
--why-bg:#eef3ff;--why-ink:#1f3f8f;--chip:#f0efeb;--warn:#b35c00}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#141416;--card:#1e1e21;--ink:#ececef;
--sub:#9a9aa2;--line:#2c2c30;--accent:#7aa2ff;--why-bg:#1d2740;--why-ink:#b9ccff;--chip:#2a2a2e;--warn:#ffb366}}
:root[data-theme="dark"]{--bg:#141416;--card:#1e1e21;--ink:#ececef;--sub:#9a9aa2;--line:#2c2c30;--accent:#7aa2ff;
--why-bg:#1d2740;--why-ink:#b9ccff;--chip:#2a2a2e;--warn:#ffb366}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.65 Pretendard,-apple-system,BlinkMacSystemFont,
"Apple SD Gothic Neo","Noto Sans KR",sans-serif;-webkit-text-size-adjust:100%;word-break:keep-all;overflow-wrap:anywhere}
.wrap{max-width:680px;margin:0 auto;padding:0 16px 64px}
header{padding:32px 0 12px}
.date{color:var(--sub);font-size:14px;font-weight:600}
h1{font-size:26px;line-height:1.3;margin:4px 0 6px;letter-spacing:-.02em}
.meta{color:var(--sub);font-size:14px}
.tabs{position:sticky;top:0;z-index:6;background:var(--bg);display:flex;gap:4px;padding:8px 0 0;border-bottom:1px solid var(--line)}
.tabs button{flex:1;font:inherit;font-size:15px;font-weight:700;color:var(--sub);background:none;border:0;
border-bottom:3px solid transparent;padding:8px 0 9px;cursor:pointer}
.tabs button.on{color:var(--ink);border-bottom-color:var(--accent)}
.hint{text-align:center;color:var(--sub);font-size:12px;margin:6px 0 0}
nav{position:sticky;top:48px;z-index:5;background:var(--bg);display:flex;gap:6px;overflow-x:auto;padding:10px 0;
scrollbar-width:none;border-bottom:1px solid var(--line)}
nav::-webkit-scrollbar{display:none}
nav a{flex:none;text-decoration:none;color:var(--ink);background:var(--chip);border-radius:999px;padding:6px 12px;font-size:14px;font-weight:600}
.brief{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:16px 18px;margin:20px 0 8px}
.brief h2{font-size:15px;margin:0 0 8px;color:var(--sub)}
.brief ol{margin:0;padding-left:0;list-style:none}
.brief li{padding:5px 0;border-top:1px dashed var(--line)}
.brief li:first-child{border-top:0}
.brief a{color:var(--ink);text-decoration:none}
section{scroll-margin-top:110px;margin-top:28px}
section>h2{font-size:19px;margin:0 0 12px;letter-spacing:-.01em}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:18px;margin-bottom:12px}
.card h3{font-size:18px;line-height:1.4;margin:0 0 8px;letter-spacing:-.01em}
.what{margin:0 0 8px}
.card ul{margin:0 0 12px;padding-left:20px}
.card li{margin:3px 0}
.why{background:var(--why-bg);color:var(--why-ink);border-radius:10px;padding:10px 12px;font-size:15px;margin-bottom:12px}
.why b{display:block;font-size:13px;margin-bottom:2px}
.foot{display:flex;justify-content:space-between;align-items:center;gap:12px;font-size:14px;color:var(--sub)}
.foot a{color:var(--accent);font-weight:600;text-decoration:none;white-space:nowrap}
.plain{color:var(--warn);font-size:13px;margin-bottom:6px}
.term .field{display:inline-block;font-size:12px;font-weight:700;color:var(--sub);background:var(--chip);border-radius:6px;padding:2px 8px;margin-bottom:6px}
.term h3{margin-bottom:2px}
.term .ko{color:var(--sub);font-size:15px;margin-bottom:8px}
.term p{margin:0 0 6px}
.term .ex{font-size:15px;color:var(--sub)}
details{margin-top:36px;color:var(--sub);font-size:14px}
details table{border-collapse:collapse;width:100%;font-size:13px;margin-top:8px}
details td{padding:3px 6px;border-bottom:1px solid var(--line)}
.links{margin-top:20px;font-size:14px}
.links a{color:var(--accent)}
.archive a{display:block;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 16px;
margin-bottom:8px;color:var(--ink);text-decoration:none}
.archive small{display:block;color:var(--sub)}
.prog{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:14px 18px;margin:20px 0 8px}
.prog b{font-size:17px}
.bar{height:8px;background:var(--chip);border-radius:99px;margin-top:10px;overflow:hidden}
.bar i{display:block;height:100%;background:var(--accent);border-radius:99px}
.tools{display:flex;gap:8px;margin:14px 0 4px}
.tools button{font:inherit;font-size:14px;font-weight:600;color:var(--ink);background:var(--chip);border:0;border-radius:999px;padding:7px 14px;cursor:pointer}
.w{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px 14px;margin-bottom:8px;cursor:pointer}
.w .top{display:flex;align-items:center;gap:8px}
.w .en{font-size:18px;font-weight:700;letter-spacing:-.01em}
.w .pos{font-size:12px;color:var(--sub);background:var(--chip);border-radius:6px;padding:1px 6px}
.w .say{margin-left:auto;background:none;border:0;font-size:18px;cursor:pointer;padding:0 2px}
.w .mean{margin-top:4px}
.w .col{font-size:14px;color:var(--sub);margin-top:2px}
.masked .w:not(.show) .mean{filter:blur(6px);user-select:none}
.masked .w:not(.show) .col .ko{filter:blur(5px)}
.rv h3{font-size:15px;color:var(--sub);margin:22px 0 8px}
"""

HEAD = """<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><meta name="robots" content="noindex">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/pretendard@1.3.9/dist/web/static/pretendard.min.css">
<style>{css}</style></head><body><div class="wrap">"""


def _story_card(s: Story) -> str:
    link = f'<a href="{escape(s.url)}" target="_blank" rel="noopener">원문 ↗</a>'
    foot = f'<div class="foot"><span>{escape(source_label(s.sources))}</span>{link}</div>'
    if not s.summarized:
        return (f'<article class="card"><div class="plain">요약 없이 제목만 표시</div>'
                f'<h3>{escape(s.headline)}</h3>{foot}</article>')
    points = "".join(f"<li>{escape(p)}</li>" for p in s.points)
    return (f'<article class="card"><h3>{escape(s.headline)}</h3>'
            f'<p class="what">{escape(s.what)}</p><ul>{points}</ul>'
            f'<div class="why"><b>왜 중요한가</b>{escape(s.why)}</div>{foot}</article>')


def _term_card(t: dict) -> str:
    return (f'<article class="card term"><span class="field">{escape(t["field"])}</span>'
            f'<h3>{escape(t["term"])}</h3><div class="ko">{escape(t["ko"])}</div>'
            f'<p>{escape(t["definition"])}</p><p class="ex">예) {escape(t["example"])}</p></article>')


def _word(w: dict) -> str:
    en, col = escape(w["w"]), escape(w["col"])
    # "comply with rules (규칙을 준수하다)" → 영어 부분과 뜻 부분을 나눠 뜻만 가릴 수 있게
    col = re.sub(r"\(([^()]*)\)$", r'<span class="ko">(\1)</span>', col)
    return (f'<div class="w"><div class="top"><span class="en">{en}</span><span class="pos">{escape(w["pos"])}</span>'
            f'<button class="say" data-say="{en}" aria-label="발음 듣기">🔊</button></div>'
            f'<div class="mean">{escape(w["ko"])}</div><div class="col">{col}</div></div>')


def _toeic_panel(v: dict) -> str:
    pct = round(100 * (v["day"] - 1) / v["total_days"])
    rnd = f" · {v['round']}회독" if v["round"] > 1 else ""
    out = [f'<div class="prog"><b>Day {v["day"]} / {v["total_days"]} · {escape(v["theme"])}</b>'
           f'<div class="meta">토익 900 과정{rnd} · 지금까지 {v["learned"]}단어</div>'
           f'<div class="bar"><i style="width:{pct}%"></i></div></div>']
    out.append('<section class="nw"><h2>🆕 오늘의 새 단어</h2>'
               '<div class="tools"><button data-mask>뜻 가리고 테스트</button></div>'
               + "".join(_word(w) for w in v["words"]) + '</section>')
    if v["reviews"]:
        groups = "".join(f'<h3>{escape(r["label"])} · Day {r["day"]} {escape(r["theme"])}</h3>'
                         + "".join(_word(w) for w in r["words"]) for r in v["reviews"])
        out.append('<section class="rv masked"><h2>🔁 복습 — 뜻을 떠올린 뒤 눌러서 확인</h2>'
                   '<div class="tools"><button data-mask>뜻 모두 보기</button></div>' + groups + '</section>')
    return "".join(out)


SCRIPT = """<script>
(function(){
  var tabs=[].slice.call(document.querySelectorAll('.tabs button')),ids=tabs.map(function(b){return b.dataset.tab});
  function show(id){
    if(ids.indexOf(id)<0)id=ids[0];
    tabs.forEach(function(b){b.classList.toggle('on',b.dataset.tab===id)});
    ids.forEach(function(x){document.getElementById('p-'+x).hidden=(x!==id)});
    if(location.hash!=='#'+id)history.replaceState(null,'','#'+id);
    window.scrollTo(0,0);
  }
  tabs.forEach(function(b){b.onclick=function(){show(b.dataset.tab)}});
  show(location.hash.slice(1));
  // 좌우로 밀어서 탭 전환 (가로 스크롤 영역에서 시작한 터치는 제외)
  var x0=null,y0=0;
  document.addEventListener('touchstart',function(e){
    x0=e.target.closest('nav')?null:e.touches[0].clientX;y0=e.touches[0].clientY},{passive:true});
  document.addEventListener('touchend',function(e){
    if(x0===null)return;var dx=e.changedTouches[0].clientX-x0,dy=e.changedTouches[0].clientY-y0;x0=null;
    if(Math.abs(dx)<70||Math.abs(dx)<Math.abs(dy)*1.5)return;
    var cur=ids.indexOf((tabs.filter(function(b){return b.classList.contains('on')})[0]||tabs[0]).dataset.tab);
    var nxt=cur+(dx<0?1:-1);if(nxt>=0&&nxt<ids.length)show(ids[nxt]);
  },{passive:true});
  document.addEventListener('click',function(e){
    var say=e.target.closest('[data-say]');
    if(say){e.stopPropagation();if(window.speechSynthesis){var u=new SpeechSynthesisUtterance(say.dataset.say);
      u.lang='en-US';u.rate=.9;speechSynthesis.cancel();speechSynthesis.speak(u)}return}
    var m=e.target.closest('[data-mask]');
    if(m){var sec=m.closest('section'),on=sec.classList.toggle('masked');
      sec.querySelectorAll('.w').forEach(function(w){w.classList.remove('show')});
      m.textContent=on?'뜻 모두 보기':'뜻 가리고 테스트';return}
    var w=e.target.closest('.w');if(w)w.classList.toggle('show');
  });
})();
</script>"""


def report_html(cfg: dict, now: datetime, stories: dict[str, list[Story]], terms: list[dict], stats: dict,
                vocab: dict | None = None) -> str:
    cats = [c for c in cfg["categories"] if stories.get(c["id"])]
    total = sum(len(stories[c["id"]]) for c in cats)
    minutes = max(2, round((total * 45 + len(terms) * 20) / 60))
    title = f"{cfg['report']['title']} · {now:%Y-%m-%d}"

    out = [HEAD.format(title=escape(title), css=CSS)]
    out.append(f'<header><div class="date">{date_label(now)}</div><h1>{escape(cfg["report"]["title"])}</h1>'
               f'<div class="meta">이슈 {total}개 · 용어 {len(terms)}개 · 약 {minutes}분</div></header>')

    if vocab:
        out.append(f'<div class="tabs" role="tablist"><button data-tab="news">📰 뉴스</button>'
                   f'<button data-tab="toeic">📝 토익 Day {vocab["day"]}</button></div>'
                   '<p class="hint">← 좌우로 밀어서 넘기기 →</p>')
    out.append('<div id="p-news">')
    chips = "".join(f'<a href="#{c["id"]}">{c["emoji"]} {escape(c["name"])}</a>' for c in cats)
    out.append(f'<nav>{chips}<a href="#terms">📘 용어</a></nav>')

    brief = "".join(f'<li><a href="#{c["id"]}">{c["emoji"]} {escape(s.headline)}</a></li>'
                    for c in cats for s in stories[c["id"]][:1])
    out.append(f'<div class="brief"><h2>30초 브리핑</h2><ol>{brief}</ol></div>')

    for c in cats:
        cards = "".join(_story_card(s) for s in stories[c["id"]])
        out.append(f'<section id="{c["id"]}"><h2>{c["emoji"]} {escape(c["name"])}</h2>{cards}</section>')

    out.append(f'<section id="terms"><h2>📘 오늘의 용어</h2>{"".join(_term_card(t) for t in terms)}</section>')

    rows = "".join(f"<tr><td>{escape(r['name'])}</td><td>{r['count']}</td><td>{escape(r['error'])}</td></tr>"
                   for r in stats["sources"] if r["error"] or r["count"] == 0)
    errors = "".join(f"<li>{escape(e)}</li>" for e in stats["errors"])
    out.append(
        f'<details><summary>수집 통계</summary>'
        f'<p>기사 {stats["articles"]}건 수집 → 이슈 {stats["clusters"]}개로 묶음 → 후보 {stats["shortlisted"]}개 '
        f'(본문 확보 {stats["enriched"]}개) → 최종 {total}개 선정</p>'
        f'{"<ul>" + errors + "</ul>" if errors else ""}'
        f'{"<p>결과가 없거나 실패한 소스</p><table>" + rows + "</table>" if rows else ""}'
        f'<p>생성 {now:%Y-%m-%d %H:%M} KST</p></details></div>')
    if vocab:
        out.append(f'<div id="p-toeic" hidden>{_toeic_panel(vocab)}</div>')
    out.append('<div class="links"><a href="archive.html">지난 리포트 보기</a></div></div>'
               + (SCRIPT if vocab else "") + '</body></html>')
    return "".join(out)


def write_report(date_str: str, html: str, headline: str) -> None:
    """리포트 저장 + 첫 화면(index.html = 최신 리포트) + 지난 리포트 목록(archive.html) 갱신.

    카카오는 링크가 적용되지 않으면 등록한 도메인 첫 화면으로 보내기 때문에,
    첫 화면 자체가 항상 오늘 리포트여야 버튼이 어떤 경우에도 리포트를 연다.
    """
    DOCS.mkdir(exist_ok=True)
    (DOCS / f"{date_str}.html").write_text(html, encoding="utf-8")

    manifest_path = DOCS / "archive.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else []
    manifest = [m for m in manifest if m["date"] != date_str] + [{"date": date_str, "headline": headline}]
    manifest.sort(key=lambda m: m["date"], reverse=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")

    items = "".join(f'<a href="{m["date"]}.html">{m["date"]}<small>{escape(m["headline"])}</small></a>'
                    for m in manifest)
    archive = (HEAD.format(title="데일리 뉴스 리포트 · 지난 리포트", css=CSS)
               + f'<header><h1>지난 리포트</h1><div class="meta">{len(manifest)}개</div></header>'
               + f'<div class="archive">{items}</div></div></body></html>')
    (DOCS / "archive.html").write_text(archive, encoding="utf-8")
    # 첫 화면 = 최신 리포트 그대로 (리다이렉트 없이 바로 보이게)
    (DOCS / "index.html").write_text(html, encoding="utf-8")
