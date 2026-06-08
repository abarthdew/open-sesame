# Open Sesame

**Claude Code용 AI 투자 자문 & 대시보드**  
KR/US 주식 포트폴리오 추적 + `/open-sesame` CLI 명령어를 통한 멀티 에이전트 분석

---

## 무엇을 하는가

Open Sesame은 Claude Code를 개인 투자 자문가로 전환합니다. 상황을 설명하면 — 종목 급등락, 포트폴리오 질문, 거시 이벤트 — `/open-sesame`이 구조화된 멀티 에이전트 분석 파이프라인을 호출하여 실제 포트폴리오 데이터를 읽고 점수화된 실행 가능한 권고를 반환합니다.

**5가지 분석 모드:**

| 모드 | 설명 | 소요 |
|---|---|---|
| `multi` (기본값) | 강세 에이전트 vs 약세 에이전트 → Arbiter 판결 | ~60초 |
| `single` | 단일 에이전트, 빠른 의견 | ~15초 |
| `rebalance` | 전체 포트폴리오 비중/계좌/섹터 검토 | ~30초 |
| `scan` | 테마/섹터 기반 신규 후보 발굴 | ~30초 |
| `macro` | 6축 거시 진단 → 포트폴리오 포지셔닝 (7일/30일/90일) | ~30초 |

**기타 기능:**
- 포트폴리오 개요, 시그널, 이벤트 캘린더, 스냅샷 히스토리가 있는 Flask 대시보드
- GitHub Actions를 통한 자동 Slack 브리핑 (모닝 / KR 장마감 / US 장개시 / 주간)
- 원격 에이전트 예약 보고서 (Claude AI 루틴)

---

## 빠른 시작

### 1. 설치

```bash
pip3 install flask pykrx yfinance python-dotenv tomli
```

### 2. 설정

`.env.example`을 `.env`로 복사하고 API 키를 입력합니다:

```bash
cp .env.example .env
```

`history/portfolio.toml`을 보유 종목으로 편집합니다. 샘플 파일에 올바른 구조가 있습니다.

### 3. 실행

```bash
python3 app.py
# → http://localhost:5000
```

---

## 투자 자문 CLI

**전제 조건:** [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) 설치

프로젝트 디렉토리에서 실행합니다:

```bash
# 멀티 에이전트 분석 (권장)
/open-sesame [mode: multi][분석 대상: SK하이닉스 (000660)][질문: 추가 매수 타이밍인지 판단해줘.]

# 빠른 단일 에이전트 의견
/open-sesame [mode: single][분석 대상: NVDA][질문: 실적 발표 전날, 보유 유지해도 될까?]

# 포트폴리오 리밸런싱 점검
/open-sesame [mode: rebalance][질문: 현재 포트폴리오 비중 점검해줘.]

# 신규 후보 섹터 탐색
/open-sesame [mode: scan][테마: AI 인프라][질문: 현재 포트폴리오와 겹치지 않는 ETF나 개별주 후보를 찾아줘]

# 거시 분석
/open-sesame [mode: macro][기간: 30일][질문: FOMC 전 포트폴리오 점검]
```

에이전트는 로컬 DB에서 실제 포트폴리오(평단가, 손익, 현금 비중)를 읽고 `ADVISOR.md`의 채점 프레임워크를 적용합니다.

분석 로그는 `report/[YYYY-MM-DD][mode][제목].log`에 저장됩니다 (gitignored).

---

## 대시보드

| 탭 | 설명 |
|---|---|
| 개요 | 실시간 시세, 손익, 포트폴리오 비중이 있는 보유 종목 |
| 시그널 | 종목별 기술적/펀더멘털 시그널 점수 |
| 이벤트 | 실적 캘린더 + 거시 이벤트 |
| 마이페이지 | 월간 순자산 스냅샷 히스토리 |

`history/portfolio.toml`을 편집하여 보유 종목을 업데이트한 후 대시보드에서 **재로드** 버튼을 클릭합니다.

---

## 자동화 브리핑 (GitHub Actions)

`.github/workflows/briefing.yml`이 스케줄에 따라 Slack 메시지를 전송합니다.

저장소의 **GitHub Secrets**에 다음을 추가합니다:

```
SLACK_WEBHOOK_URL
ALPHA_VANTAGE_KEY
DART_API_KEY
KRX_ID
KRX_PW
```

수동 실행:

```bash
python3 -m briefing.briefing morning    # 모닝 브리핑
python3 -m briefing.briefing kr_close  # KR 장마감
python3 -m briefing.briefing us_open   # US 장개시
python3 -m briefing.briefing weekly    # 주간 회고
```

> **참고:** GitHub Actions 내장 `schedule:` 트리거는 수 시간 지연이 발생합니다. 권장 방법: [cron-job.org](https://cron-job.org) → `workflow_dispatch` 호출.

---

## 파일 구조

```
open-sesame/
├── app.py                    # Flask 서버
├── ADVISOR.md                # 자문 프롬프트 & 채점 규칙
├── history/
│   ├── portfolio.toml        # 보유 종목 (직접 편집)
│   ├── events.toml           # 이벤트 캘린더
│   └── api_cache.json        # 주간 브리핑 캐시 (자동)
├── data/
│   ├── db.py                 # SQLite 스키마 & 쿼리
│   └── fetcher.py            # pykrx / yfinance 시세 조회
├── briefing/                 # Slack 브리핑 생성기
├── static/ & templates/      # 대시보드 프론트엔드
├── formats/                  # 자문 리포트 템플릿
└── .github/workflows/        # GitHub Actions 자동화
```

---

## API 키

| 키 | 목적 | 무료 티어 |
|---|---|---|
| `SLACK_WEBHOOK_URL` | 브리핑 알림 | 무료 |
| `ALPHA_VANTAGE_KEY` | 뉴스 감성 (주간 전용) | 25 req/일 |
| `DART_API_KEY` | 한국 공시 조회 | 무료 |
| `KRX_ID` / `KRX_PW` | pykrx용 KRX 로그인 | 무료 |

---

## 기여

이슈와 PR을 환영합니다. 이 프로젝트는 주로 [Claude Code](https://docs.anthropic.com/en/docs/claude-code)와 함께, 그리고 Claude Code를 위해 만들어졌습니다.

---

## 라이선스

MIT
