## 이벤트 캘린더 자동 업데이트

당신은 개인 투자 대시보드(`open-sesame`)의 이벤트 캘린더를 관리하는 에이전트입니다.

할 일:
예정된 시장 이벤트를 조사하고, `history/events.toml`을 업데이트한 후 커밋 및 push합니다.

- 모든 웹 조사에는 `WebSearch` 도구를 사용하세요.
- Slack 성공 알림은 push 감지 후 GitHub Actions (`report-notify.yml`)가 자동 처리합니다.
- push 실패 시에만 `WebFetch` 도구로 Slack 알림을 전송합니다 (6번 단계 참조).

## 포트폴리오 컨텍스트

> ⚠️ **이 섹션을 `history/portfolio.toml`의 실제 보유 종목에 맞게 업데이트하세요.**

한국 주식:
- KODEX 반도체 ETF (091160)
- SK하이닉스 (000660)
- 삼성전자 (005930)

미국 주식:
- NVDA (엔비디아)
- GOOGL (알파벳)
- VOO (S&P 500 ETF)
- SMR (NuScale Power)

## 1단계 — 현재 이벤트 읽기

Read 도구로 아래 파일을 엽니다:

```text
history/events.toml
```

## 2단계 — 오늘 날짜 확인

실행:

```bash
date +%Y-%m-%d
```

## 3단계 — 예정 이벤트 조사

모든 검색에 `WebSearch` 도구를 사용합니다.

조사 항목:

- NVDA 다음 실적 발표일
- GOOGL(알파벳) 다음 실적 발표일
- 삼성전자 다음 분기 실적 발표일
- SK하이닉스 다음 분기 실적 발표일
- 남은 FOMC 회의 및 결정 날짜 (올해)
- 남은 한국은행 기준금리 결정 날짜 (올해)
- 미국 CPI 발표일 (향후 3개월)
- 미국 PCE 발표일 (향후 3개월)
- 미국 비농업 고용지수(NFP) 발표일 (향후 3개월)
- 잭슨홀 연준 심포지엄 날짜 (예정된 경우)
- 반도체에 영향을 주는 주요 지정학 이벤트
  (미중 무역, 수출 규제 등)

## 4단계 — events.toml 업데이트

규칙:

- 오늘 이전 날짜의 이벤트는 모두 삭제합니다.
- 파일에 이미 있는 미래 이벤트는 유지합니다.
- 기존 미래 이벤트를 중복 추가하지 않습니다.
- 새로 확인된 예정 이벤트를 추가합니다.
- 날짜가 불확실한 경우 이벤트명에 `(예정)`을 붙입니다.
- `importance` 기준:
  - `HIGH`
    - 보유 종목 실적 발표
    - SEP 전망 포함 FOMC
    - 주요 지정학 이벤트
  - `MID`
    - 일반 FOMC
    - CPI / PCE / NFP
    - 한국은행 결정
  - `LOW`
    - 소규모 이벤트
- `scenarios`는 최대 2줄로 제한합니다.
  사용자의 언어로 작성합니다 (한국어로 소통하는 사용자면 한국어, 그렇지 않으면 영어).

파일 형식:

```toml
[[events]]
date       = "YYYY-MM-DD"
importance = "HIGH"
name       = "이벤트명"
scenarios  = "A: 강세 시나리오 → 포트폴리오 영향\nB: 약세 시나리오 → 포트폴리오 영향"
```

아래 파일에 완성된 파일을 씁니다:

```text
history/events.toml
```

오늘 날짜의 파일이 이미 존재해도 항상 최신 데이터로 덮어씁니다.

## 5단계 — Git 커밋 및 Push

아래 스크립트를 단일 Bash 실행으로 실행합니다:

```bash
git add history/events.toml

git diff --cached --quiet || \
git commit -m "data: 이벤트 캘린더 자동 업데이트 $(TZ=Asia/Seoul date +%Y-%m-%d)"

git push origin HEAD && echo "PUSH_OK" || echo "PUSH_FAIL"
```

## 6단계 — Push 실패 시에만 Slack 알림

push 결과가 `PUSH_FAIL`인 경우에만 실행합니다:

```bash
curl -s -X POST "$SLACK_WEBHOOK_URL_ERR" \
  -H "Content-Type: application/json" \
  -d "{\"text\":\"❌ [이벤트 캘린더] git push 실패 — $(date +%Y-%m-%d)\"}"
```

`PUSH_OK`인 경우 Slack 알림을 전송하지 마세요.
GitHub Actions가 성공 알림을 자동으로 처리합니다.

## 참고

Flask 서버는 사용자의 로컬 머신에서 실행되므로 이 환경에서는 접근할 수 없습니다.

변경 사항을 pull한 후 사용자가 대시보드에서 이벤트를 수동으로 새로고침합니다.
