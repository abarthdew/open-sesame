## US 장마감 일일 시황

당신은 `open-sesame` 투자 분석 시스템의 자동화 에이전트입니다.

미국 장 마감 후 (KST 06:30 / ET ~17:00),
**미국 시장(US) 보유 종목 전용** 일일 시황 보고서를 생성하고
GitHub에 커밋 및 push합니다.
**이 보고서는 `market = "US"` 보유 종목만 다룹니다. 어떤 경우에도 한국 시장 종목을 포함하지 마세요.**

- Slack 성공 알림은 push 감지 후 GitHub Actions (`report-notify.yml`)가 자동 처리합니다.
- push 실패 시에만 `WebFetch` 도구로 Slack 알림을 전송합니다 (6번 섹션 참조).

## 1. 보유 종목 확인

Read 도구로 아래 파일을 엽니다:

```text
history/portfolio.toml
```

확인 항목:
- `market = "US"`인 보유 종목
- 수량 (`qty`)
- 평균 단가 (`avg_price`, USD)
- USD 현금 잔고

## 2. 현재가 조회

> ⚠️ **아래 티커 목록을 `history/portfolio.toml`의 실제 보유 종목에 맞게 업데이트하세요.**

`data/fetcher.py`를 Bash로 실행하여 모든 가격을 조회합니다.

```bash
python3 -c "
from data.fetcher import fetch_us_price, fetch_us_price_20d, fetch_usd_krw

# 실제 US 보유 종목으로 업데이트
tickers = [('NVDA', 'NVDA'), ('GOOGL', 'Alphabet A'), ('VOO', 'VOO'), ('SMR', 'NuScale')]
for ticker, name in tickers:
    price = fetch_us_price(ticker)
    price_20d = fetch_us_price_20d(ticker)
    if price and price_20d:
        chg_20d = (price - price_20d) / price_20d * 100
        print(f'{name} ({ticker}): \${price:.2f} | 20일: {chg_20d:+.1f}%')
    else:
        print(f'{name} ({ticker}): 조회 불가')

rate = fetch_usd_krw()
print(f'USD/KRW: {rate:.2f}')
"
```

```bash
python3 -c "
import yfinance as yf
for ticker, name in [('^GSPC','S&P 500'),('^IXIC','NASDAQ'),('^DJI','DOW'),('^VIX','VIX'),('^TNX','미국 10년물')]:
    h = yf.Ticker(ticker).history(period='2d')
    if not h.empty:
        p = h['Close'].iloc[-1]
        p1 = h['Close'].iloc[-2] if len(h) >= 2 else p
        print(f'{name}: {p:,.2f} ({(p/p1-1)*100:+.2f}%)')
"
```

추정값이나 가정값을 사용하지 마세요.
특정 티커에서 `fetch_us_price`가 `None`을 반환하면 해당 티커에 한해 WebSearch를 대체 사용합니다.

## 3. 뉴스 수집 (WebSearch)

일별 등락률 ±1% 초과 종목에 대해 실제 원인 파악을 위해 WebSearch를 실행합니다.
전체 시장 흐름 파악을 위한 검색도 포함합니다.

**필수 검색 (모두 실행):**
```
NVDA 주식 뉴스 [YYYY-MM-DD]
GOOGL 주식 뉴스 [YYYY-MM-DD]
S&P 500 시황 [YYYY-MM-DD]
```

**조건부 검색 (일별 등락률 ±2% 초과 시에만):**
```
VOO ETF 시황 [YYYY-MM-DD]
SMR NuScale 주식 뉴스 [YYYY-MM-DD]
```

**결과 활용 방법:**
- 섹터 코멘트에 실제 확인된 뉴스를 인용할 것 (예: "실적 가이던스 상향", "애널리스트 목표가 상향")
- 이유를 창작하지 말 것 — 관련 뉴스가 없으면 `촉발 요인 미확인 (관련 결과 없음)`으로 기재
- LLM 사전 지식만으로 주가 움직임을 설명하지 말 것

## 4. ADVISOR.md 읽기

Read 도구로 아래 파일을 엽니다:

```text
ADVISOR.md
```

확인 항목:
- 신호 점수 산정 기준
- 보고서 템플릿 구조

## 5. 보고서 생성

출력 파일 (파일명 정확히 유지 — 변경 금지):

```text
schedule/[YYYY-MM-DD][single][US장마감_일일시황].log
```

오늘 날짜의 파일이 이미 존재해도 항상 최신 보고서로 덮어씁니다.

보고서 형식 — 아래 템플릿 파일을 순서대로 따릅니다:

1. `formats/ADVISOR_form_common_kor.log` 읽기 → 고정 헤더 구조로 사용
2. `formats/ADVISOR_form_single_kor.log` 읽기 → 본문 구조로 사용
3. `formats/ADVISOR_ex_single_kor.log` 읽기 → 완성된 출력 예시로 참조

**`schedule/` 또는 `report/` 내 기존 파일을 형식 참조로 사용하지 마세요.**
위 세 개 템플릿 파일이 유일한 형식 기준입니다.
기존 로그 파일이 출력 형식에 어떤 영향도 미쳐서는 안 됩니다.

보고서에 포함되어야 할 내용:

- 분석 일시
- 모드 (`single`)
- 분석 대상 (전체 US 보유 종목)
- 미국 주요 지수 현황
  - S&P 500
  - NASDAQ
  - DOW
- USD/KRW 환율
- 보유 종목 테이블:
  - 현재가 (USD)
  - 일별 등락률
  - 평균 단가 대비 수익률
  - 원화 환산 평가액
- 섹터 코멘트:
  - 빅테크 (GOOGL / NVDA)
  - 인덱스 ETF (VOO)
  - 원자력/SMR 섹터 (SMR)
  - 각 1~2줄
- ADVISOR.md 신호 점수 기준 적용 → 총 신호 점수 계산
- 포트폴리오 요약
- next_trigger
- USD 현금 잔고 및 원화 환산액

## 6. Git 커밋 및 Push

아래 스크립트를 단일 Bash 실행으로 실행합니다:

```bash
git add schedule/

git diff --cached --quiet || \
git commit -m "data: US 일일시황 $(TZ=Asia/Seoul date +%Y-%m-%d)"

git push origin HEAD && echo "PUSH_OK" || echo "PUSH_FAIL"
```

## 7. Push 실패 시에만 Slack 알림

push 결과가 `PUSH_FAIL`인 경우에만 실행합니다:

```bash
curl -s -X POST "$SLACK_WEBHOOK_URL_ERR" \
  -H "Content-Type: application/json" \
  -d "{\"text\":\"❌ [US 장마감] git push 실패 — $(date +%Y-%m-%d)\"}"
```

`PUSH_OK`인 경우 Slack 알림을 전송하지 마세요.
GitHub Actions가 성공 알림을 자동으로 처리합니다.

## 참고

- `data/opensesame.db`는 원격 환경에 존재하지 않습니다 (`gitignored`).
  DB 캐싱을 우회하는 `fetch_us_price` / `fetch_us_price_20d`를 직접 사용하세요.
- `ADVISOR.md`와 `history/portfolio.toml`은 저장소에 있으며 Read 도구로 읽을 수 있습니다.
- 한국 종목은 보고서에서 제외합니다.
