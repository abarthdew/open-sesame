# 자동화 루틴

`schedule/` 디렉토리는 **Claude Code 원격 에이전트**의 프롬프트 파일을 담고 있습니다 — 로컬 머신 없이 클라우드에서 스케줄에 따라 자동 실행되는 에이전트입니다.

각 `*_routines.md` 파일은 하나의 루틴을 정의합니다: 어떤 데이터를 수집하고, 어떻게 분석하며, 결과를 어떻게 저장소에 커밋할지.

---

## 각 루틴의 역할

| 파일 | 실행 시점 | 출력 |
|---|---|---|
| `kr_close_routines.md` | 평일 KR 장 마감 후 (KST 16:00) | `schedule/[날짜][single][KR장마감_일일시황].log` |
| `kr_mid_routines.md` | 평일 장중 (KST 11:30) | `schedule/[날짜][single][KR장중_시황].log` |
| `us_close_routines.md` | 평일 US 장 마감 후 (KST 06:30 / ET ~17:00) | `schedule/[날짜][single][US_Market_Close_Daily_Report].log` |
| `event_cal_routines.md` | 매주 (일요일) | `history/events.toml` (덮어쓰기) |

생성된 `.log` 파일은 gitignored — repo를 pull한 머신에서만 존재합니다.

---

## Claude Code에 루틴 등록하는 방법

### Step 1 — 루틴 페이지 열기

주소: **https://claude.ai/code/routines**

> Claude Code 구독 필요 (Pro 이상).

### Step 2 — 새 루틴 생성

**New Routine**을 클릭하고 입력:

| 항목 | 값 |
|---|---|
| **이름** | 예: `KR 장마감 시황` |
| **프롬프트** | 루틴 파일 전체 내용 붙여넣기 (예: `kr_close_routines.md`) |
| **스케줄** | cron 또는 프리셋으로 설정 (아래 참조) |
| **저장소** | GitHub repo 연결 |

### Step 3 — 스케줄 설정

권장 cron 표현식 (KST = UTC+9):

| 루틴 | KST 시각 | Cron (UTC) |
|---|---|---|
| KR 장마감 | 평일 16:10 | `10 7 * * 1-5` |
| KR 장중 | 평일 11:40 | `40 2 * * 1-5` |
| US 장마감 | 평일 06:40 | `40 21 * * 1-5` |
| 이벤트 캘린더 | 일요일 18:00 | `0 9 * * 0` |

> **참고:** GitHub Actions 내장 `schedule:` 트리거는 수 시간 지연이 발생합니다. 시간에 민감한 보고서에는 [cron-job.org](https://cron-job.org) → `workflow_dispatch` 방식이 더 안정적입니다. Claude Code Routines는 이 제한 없이 직접 실행됩니다.

### Step 4 — 환경 변수 설정

루틴은 Slack 오류 알림에 다음 환경 변수를 사용합니다:

```
SLACK_WEBHOOK_URL_ERR=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

루틴의 환경 설정 또는 GitHub Secrets에 등록하세요.

### Step 5 — 티커 목록 업데이트

각 루틴 파일에는 샘플 포트폴리오에 맞게 하드코딩된 티커 목록이 있습니다.
루틴을 등록하기 전에 `history/portfolio.toml`의 **실제 보유 종목에 맞게 수정**하세요.

---

## 동작 흐름

```
Claude Code Routines (클라우드)
        │
        ├── portfolio.toml + ADVISOR.md 읽기
        ├── 실시간 시세 조회 (pykrx / yfinance)
        ├── 뉴스 WebSearch
        ├── formats/ 템플릿으로 보고서 생성
        └── git commit + push → GitHub repo
                │
                └── GitHub Actions (report-notify.yml)
                        └── 성공 시 Slack 알림
```

루틴 에이전트는 클라우드에서 완전히 실행됩니다. repo를 clone하고, 보고서를 생성하고, 커밋 후 push합니다. `git pull` 하거나 GitHub에서 직접 확인할 수 있습니다.

---

## 출력 포맷

보고서는 수동 `/open-sesame` 분석과 동일한 템플릿을 따릅니다:

- 헤더: `formats/ADVISOR_form_common_kor.log`
- 본문: `formats/ADVISOR_form_single_kor.log`
- 예시: `formats/ADVISOR_ex_single_kor.log`

보고서 언어는 루틴 파일의 언어를 따릅니다 (한국어 루틴 → 한국어 보고서, 영어 루틴 → 영어 보고서).
