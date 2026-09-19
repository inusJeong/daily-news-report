# 📰 데일리 뉴스 리포트

매일 아침 카카오톡으로 **"오늘 알아야 할 뉴스 12개 + 용어 4개 + 토익 단어"** 를 받는 1인용 브리핑.

리포트 위쪽 탭(또는 좌우로 밀기)으로 **📰 뉴스 ↔ 📝 토익** 패널을 오갑니다.

```
카톡 알림 (200자)                         웹 리포트 (3~5분)
┌──────────────────────────┐             ┌──────────────────────────────┐
│ 📰 9/19(토) 데일리 뉴스 리포트 │   버튼 →   │ 30초 브리핑                    │
│ 🏭 독일 공급망 재편 가속       │             │ 🏭 전공·SCM  💼 취업  🌏 시사 …  │
│ 💼 두산건설 하반기 공채        │             │  ┌ 헤드라인 ─────────────┐     │
│ 🌏 한미 외교장관 회담          │             │  │ 무슨 일 / 핵심 포인트    │     │
│ 🔬 면역항암제 AI 예측          │             │  │ 왜 중요한가 (나와 연결)   │     │
│ 📚 전쟁과 언어, 바스케스        │             │  └ 연합뉴스 외 17곳  원문 ↗ ┘     │
│ 📘 OEE · 채찍효과 · SLA · …   │             │ 📘 오늘의 용어 카드 4장          │
│   [ 전체 리포트 보기 ]         │             │ 지난 리포트 보기                 │
└──────────────────────────┘             └──────────────────────────────┘
```

---

## 1. 설계 논리 — 왜 이렇게 만들었나

목표는 스펙의 한 문장입니다: **"놓치는 뉴스 없이, 빠르게 읽히게."**
이 목표에서 출발해 각 결정이 앞의 결정의 결과로 이어지도록 설계했습니다.

| # | 원인 (문제) | → 결정 | → 새로 생기는 문제 |
|---|---|---|---|
| 1 | 한 소스만 보면 놓친다 | 소스 다변화: 네이버 API + Google News + 언론사·전문지 RSS 30여 개 | 같은 사건이 수십 번 중복된다 |
| 2 | 중복이 많다 | **같은 사건끼리 묶기**(제목 유사도) | 묶고 나니 이슈가 1,000개 넘게 남는다 |
| 3 | 묶인 기사 수는 버리기 아까운 정보 | **"여러 언론이 다룬 이슈 = 중요한 이슈"** 로 점수에 활용 | 중요도만 보면 '나와 무관한 큰 뉴스'만 남는다 |
| 4 | 사람마다 중요한 게 다르다 | 점수 = **관련도(내 관심사)** × w + **중요도(매체 수)** × w, 카테고리마다 비율을 다르게 (시사는 중요도↑, 전공은 관련도↑) | 규칙만으로는 보도자료·홍보 기사를 못 거른다 |
| 5 | 규칙이 맥락을 못 읽는다 | 규칙은 후보를 7개로 **좁히기만** 하고, 최종 선택+요약은 **AI(Gemini)** 가 | RSS 설명 1~2줄로는 요약이 얕다 |
| 6 | 입력이 얕으면 요약도 얕다 | 후보 35개만 **원문 본문을 가져와** AI에 전달 (구글 링크도 원문 주소로 풀어냄) | — |
| 7 | 카톡 텍스트는 **200자 제한** | 역할 분리: **카톡 = 알림 + 헤드라인, 웹 = 전체 리포트** (스펙에서 '보류'였던 웹 아카이브가 필수가 됨) | 웹페이지를 어디에 올리나 |
| 8 | 서버 없이 운영하고 싶다 | GitHub Actions가 매일 실행 → GitHub Pages에 배포 (무료) | 카톡 버튼이 열 페이지가 먼저 떠 있어야 한다 |
| 9 | 순서가 틀리면 링크가 깨진다 | **생성 → 배포 → 발송 → 상태 저장** 순서 고정 | 발송이 실패하면? |
| 10 | 실패한 날 용어를 건너뛰면 안 된다 | 용어 순번·보낸 이슈 기록은 **발송 성공 후에만** 전진 | — |
| 11 | 어제 본 뉴스를 또 보면 지루하다 | 최근 7일 보낸 이슈와 비슷하면 제외, 후속 보도는 감점 | — |

**실패해도 멈추지 않게**: 소스 하나가 죽어도 나머지로 진행 / 카테고리 하나의 요약이 실패하면 그 카테고리만 "제목+링크"로 대체 / 모든 실패는 리포트 하단 `수집 통계`에 기록.

## 2. 파이프라인

```
config.yaml ─┐
             ▼
 ① 수집  collect.py    네이버·구글·RSS 병렬 수집 (카테고리별 기간, 제외어 필터)   ~1,900건
 ② 묶기  cluster.py    같은 사건 → 하나의 이슈 (한글: 글자 2-gram / 영어: 단어)   ~1,600개
 ③ 점수  rank.py       관련도·중요도·신선도·재방송 패널티 → 카테고리별 상위 7    35개
 ③½ 보강 enrich.py     후보의 원문 본문 1,500자 확보                           34/35
 ④ 요약  summarize.py  Gemini가 고르고(2~3개) 구조화 요약 (카테고리별)         12개
 ⑤ 용어  glossary.py   150개 용어 뱅크를 분야별로 번갈아 순환                   4개
 ⑥ 조립  render.py     웹 리포트 HTML + 카톡 200자
 ⑦ 발송  kakao.py      나에게 보내기 (토큰 자동 갱신)
         state.py      용어 순번·보낸 이슈 기록 (발송 성공 시에만)
```

---

## 2½. 토익 단어장 (📝 탭)

- **30일 과정, 하루 LC 10 + RC 15** (`data/toeic_words.json`, 총 LC 300 · RC 450). 날마다 주제가 있습니다(계약·법무 → 인사·채용 → …).
  - 🎧 **LC**: Part 1 사진 묘사 3개(be stacked, lean against…) + 그날 주제의 Part 2~4 대화 표현 7개. 🔊로 **예문 전체**를 듣고 뜻을 떠올리는 방식.
  - 📖 **RC**: Part 5·6에 그대로 나오는 **짝꿍 표현(연어)** 과 함께 외우는 단어. 🔊는 단어 발음.
- **간격 반복 복습**: 1·3·7·14·28 학습일 전 LC·RC를 다시 보여줍니다. 복습은 뜻이 가려져 있고, 떠올린 뒤 눌러서 확인합니다. 새 단어도 "뜻 가리고 테스트"로 셀프 테스트할 수 있습니다.
- 진도는 발송 성공 시에만 하루씩 넘어가고, 30일을 마치면 2회독으로 다시 시작합니다.

## 3. 처음 설정하기 (한 번만, 약 20분)

### ① 로컬에서 미리보기 먼저

터미널에서 아래를 그대로 복사해 실행하세요.

```bash
cd ~/Downloads/daily-news-report && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && cp .env.example .env && open -e .env
```

열린 `.env` 파일에 가진 키를 채우고 저장합니다.
- `GEMINI_API_KEY`: https://aistudio.google.com/apikey → **Create API key** (구글 계정만 있으면 무료, 카드 등록 불필요)
- `NAVER_CLIENT_ID` / `NAVER_CLIENT_SECRET`: 네이버 개발자센터 → 내 애플리케이션 (이미 있음)
- `KAKAO_REST_API_KEY`: 카카오 디벨로퍼스 → 내 애플리케이션 → 앱 키 → REST API 키

그다음 미리보기(발송 없음):

```bash
cd ~/Downloads/daily-news-report && .venv/bin/python -m newsbot preview
```

브라우저에 오늘 리포트가 열리고 터미널에 카톡 미리보기가 나옵니다.

### ② 카카오톡 발송 준비

카카오 디벨로퍼스(https://developers.kakao.com) → 내 애플리케이션 → 내 앱에서:
1. **카카오 로그인** → 활성화 ON, **Redirect URI**에 `http://localhost:5555` 추가
2. **동의항목** → "카카오톡 메시지 전송(talk_message)" → 선택 동의로 설정
3. **플랫폼 → Web → 사이트 도메인**에 `https://<GitHub아이디>.github.io` 추가 (⚠️ 이게 없으면 카톡 버튼이 안 열립니다)
4. (보안 → Client Secret을 켜 두었다면 그 값을 `.env`의 `KAKAO_CLIENT_SECRET`에)

refresh token 발급 (브라우저가 열리면 로그인 → 동의):

```bash
cd ~/Downloads/daily-news-report && .venv/bin/python -m newsbot kakao-auth
```

출력된 토큰을 `.env`의 `KAKAO_REFRESH_TOKEN`에 붙여넣습니다.

### ③ GitHub에 올리기

1. github.com에서 **Public** 저장소 `daily-news-report` 생성 (README 추가 체크 해제)
   - Private 저장소는 GitHub Pages가 유료라서 Public을 권장합니다. 키는 Secrets에만 들어가므로 코드에 노출되지 않습니다.
2. 아래 명령에서 `<GitHub아이디>`만 바꿔 실행:

```bash
cd ~/Downloads/daily-news-report && git init && git add . && git commit -m "데일리 뉴스 리포트" && git branch -M main && git remote add origin https://github.com/<GitHub아이디>/daily-news-report.git && git push -u origin main
```

3. 저장소 → **Settings → Pages → Source: GitHub Actions** 선택
4. 저장소 → **Settings → Secrets and variables → Actions → New repository secret** 으로 `.env`의 값을 같은 이름으로 등록:
   `GEMINI_API_KEY`, `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET`, `KAKAO_REST_API_KEY`, `KAKAO_REFRESH_TOKEN`, (쓰면) `KAKAO_CLIENT_SECRET`
5. (권장) `GH_PAT`: 카카오 refresh token은 2개월마다 바뀝니다. GitHub → Settings → Developer settings → Fine-grained tokens에서 이 저장소에 **Secrets: Read and write** 권한을 준 토큰을 만들어 `GH_PAT`로 등록하면 자동 교체됩니다. (없으면 만료 전에 경고만 뜹니다)
6. **Actions 탭 → daily-report → Run workflow** 로 첫 실행 → 카톡이 오면 완료 🎉

이후 매일 아침 6:30(KST)에 자동 실행됩니다. (GitHub 스케줄 특성상 10~30분 늦게 도착할 수 있어요)

---

## 4. 튜닝하기 — `config.yaml` 하나만

| 이런 느낌이면 | 이렇게 |
|---|---|
| 전공 뉴스가 너무 광범위하다 | `profile.interests`에서 가중치 조정, 카테고리 `keywords` 좁히기 |
| 특정 유형 기사가 거슬린다 | 해당 카테고리 `exclude`에 단어 추가 |
| 시사가 너무 나와 무관하다 | 시사 `weights.relevance`를 올리기 |
| 기사 개수를 바꾸고 싶다 | 카테고리 `pick` |
| 새 소스 추가 | `feeds`에 RSS 추가 또는 `google`에 `"site:도메인"` 추가 |
| 요약이 '한도 초과'로 자주 실패한다 | `llm.model: gemini-3.5-flash-lite` (더 가볍고 한도가 넉넉함) |

소스 상태 점검 (어떤 소스가 0건/에러인지):

```bash
cd ~/Downloads/daily-news-report && .venv/bin/python -m newsbot check
```

## 5. 비용 (대략)

- Gemini API **무료 등급**: 하루 5번 호출(카테고리별). `gemini-3.5-flash` 무료 한도는 하루 약 20회라, **로컬 `preview`를 여러 번 돌리면 그날 자동 실행분이 부족할 수 있습니다.** 한도가 차면 `gemini-3.5-flash-lite`로 자동 전환합니다.
  - ⚠️ 무료 등급은 보낸 내용(뉴스 후보 목록)이 Google 서비스 개선에 쓰일 수 있습니다. 공개 뉴스라 문제는 없지만 개인정보는 넣지 마세요.
- GitHub Actions / Pages, 네이버 API, 카카오 메시지: 무료 범위.

## 6. 파일 구조

```
config.yaml            ← 튜닝은 여기만
data/terms.json        용어 150개 (산업공학 40 · SCM 40 · 리스크 40 · 비즈니스 영어 30)
data/toeic_words.json  토익 30일 과정 (LC 300 · RC 450, 주제별)
data/state.json        용어 순번, 최근 보낸 이슈 (Actions가 자동 커밋)
docs/                  웹 리포트 아카이브 (GitHub Pages로 공개)
newsbot/               파이프라인 코드 (위 2번의 단계별 파일)
.github/workflows/daily.yml
```

## 7. 문제 해결

- **카톡 버튼을 눌러도 안 열림** → 카카오 앱 설정의 Web 사이트 도메인에 `https://<아이디>.github.io` 등록 여부 확인
- **"카카오 토큰 갱신 실패"** → refresh token 만료. `kakao-auth`로 재발급 후 Secret 교체
- **특정 카테고리가 "요약 없이 제목만"** → Actions 로그의 `4 요약` 줄에서 경고 확인 (API 키 오타, 무료 한도 초과 → 모델을 flash-lite로)
- **오늘 다시 받고 싶음** → Actions → Run workflow → `force` 체크
