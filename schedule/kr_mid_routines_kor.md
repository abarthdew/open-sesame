## KR 장중 시황

당신은 `open-sesame` 투자 분석 시스템의 자동화 에이전트입니다.

KST 11:30 (장중, 한국 시장 거래 중),
**한국 시장(KR) 보유 종목 전용** 장중 시황 보고서를 생성하고
GitHub에 커밋 및 push합니다.
**이 보고서는 `market = "KR"` 보유 종목만 다룹니다. 어떤 경우에도 미국 시장 종목을 포함하지 마세요.**

- Slack 성공 알림은 push 감지 후 GitHub Actions (`report-notify.yml`)가 자동 처리합니다.
- push 실패 시에만 `WebFetch` 도구로 Slack 알림을 전송합니다 (6번 섹션 참조).

## 1. 보유 종목 확인

Read 도구로 아래 파일을 엽니다:

```text
history/portfolio.toml
```

`market = "KR"`인 보유 종목 확인:

- 티커
- 수량 (`qty`)
- 평균 단가 (`avg_price`)

## 2. 가격 데이터 조회

> ⚠️ **아래 티커 목록을 `history/portfolio.toml`의 실제 보유 종목에 맞게 업데이트하세요.**

`data/fetcher.py`를 Bash로 실행하여 현재가 및 20일 기준가를 조회합니다:

```bash
python3 -c "
from data.fetcher import fetch_kr_price, fetch_kr_price_20d

# 실제 KR 보유 종목으로 업데이트
tickers = [
    ('091160', 'KODEX 반도체'),
    ('000660', 'SK하이닉스'),
    ('005930', '삼성전자'),
    ('487240', 'KODEX AI파워핵심장비'),
    ('0035T0', 'PLUS 글로벌휴머노이드로봇액티브'),
    ('411060', 'ACE KRX금현물'),
    ('133690', 'TIGER 미국나스닥100'),
    ('360750', 'TIGER 미국S&P500'),
    ('438080', 'ACE 미국S&P500채권혼합50액티브'),
    ('438100', 'ACE 미국나스닥100채권혼합50액티브'),
]

for ticker, name in tickers:
    price = fetch_kr_price(ticker)
    price_20d = fetch_kr_price_20d(ticker)
    if price and price_20d:
        chg_20d = (price - price_20d) / price_20d * 100
        print(f'{name} ({ticker}): {price:,.0f} KRW | 20일: {chg_20d:+.1f}%')
    else:
        print(f'{name} ({ticker}): 조회 불가')
"
```

장중 등락률(현재가 vs. 시가) 계산을 위해 당일 OHLCV도 조회합니다:

```bash
python3 -c "
from pykrx import stock
from datetime import datetime, timedelta
today = datetime.now().strftime('%Y%m%d')
start = (datetime.now() - timedelta(days=5)).strftime('%Y%m%d')

# 지수 장중 흐름
for idx_code, name in [('1001','KOSPI'),('2001','KOSDAQ')]:
    try:
        df = stock.get_index_ohlcv_by_date(start, today, idx_code)
        if not df.empty:
            row = df.iloc[-1]
            prev_close = df['종가'].iloc[-2] if len(df) >= 2 else row['시가']
            print(f'{name}: 현재 {row[\"종가\"]:,.2f}pt | 시가 {row[\"시가\"]:,.2f}pt | 전일비 {(row[\"종가\"]/prev_close-1)*100:+.2f}%')
    except Exception as e:
        print(f'{name}: 오류 - {e}')

# 종목별 장중 등락 (시가 대비)
tickers = [
    ('091160', 'KODEX 반도체'), ('000660', 'SK하이닉스'), ('005930', '삼성전자'),
    ('487240', 'KODEX AI파워핵심장비'), ('0035T0', 'PLUS 글로벌휴머노이드'), ('411060', 'ACE KRX금현물'),
]
for ticker, name in tickers:
    try:
        df = stock.get_market_ohlcv_by_date(today, today, ticker)
        if not df.empty:
            row = df.iloc[-1]
            chg = (row['종가'] - row['시가']) / row['시가'] * 100 if row['시가'] else 0
            print(f'{name}: 현재 {row[\"종가\"]:,.0f} KRW | 시가 {row[\"시가\"]:,.0f} KRW | 시가비 {chg:+.2f}%')
    except Exception as e:
        print(f'{name}: {e}')
"
```

### 대체 방법: WebSearch (특정 티커 조회 실패 시에만)

- 검색: `"[종목명] 주가 오늘"` 또는 `"[티커] KRX 주가 오늘"`
- `N/A` 또는 추정값은 사용 금지 — 반드시 실제 가격을 확인할 것

## 3. 뉴스 수집 (WebSearch)

장중 등락률(시가 대비) ±1% 초과 종목에 대해 실제 원인 파악을 위해 WebSearch를 실행합니다.
오전 시장 흐름 파악을 위한 검색도 포함합니다.

**필수 검색 (모두 실행):**
```
코스피 오전 시황 [YYYY-MM-DD]
삼성전자 뉴스 오늘 [YYYY-MM-DD]
SK하이닉스 뉴스 오늘 [YYYY-MM-DD]
```

**조건부 검색 (장중 등락률 ±2% 초과 시에만):**
```
KODEX 반도체 ETF 뉴스 [YYYY-MM-DD]
KODEX AI파워핵심장비 뉴스 [YYYY-MM-DD]
```

**결과 활용 방법:**
- 섹터 코멘트에 실제 확인된 뉴스를 인용할 것
- 이유를 창작하지 말 것 — 관련 뉴스가 없으면 `촉발 요인 미확인 (관련 결과 없음)`으로 기재
- LLM 사전 지식만으로 주가 움직임을 설명하지 말 것

## 4. ADVISOR.md 읽기

Read 도구로 아래 파일을 엽니다:

```text
ADVISOR.md
```

신호 점수 산정 기준을 확인합니다.

## 5. 보고서 생성

출력 파일 (파일명 정확히 유지 — 변경 금지):

```text
schedule/[YYYY-MM-DD][single][KR장중_시황].log
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
- 분석 대상 (전체 KR 보유 종목)
- **⚠️ 상단에 명시: 장중 보고서 — 가격은 실시간 스냅샷이며 종가가 아님**
- KOSPI / KOSDAQ 오전 흐름 (현재 지수, 시가 대비 변동)
- 보유 종목 테이블:
  - 현재가 (장중)
  - 시가 대비 등락률 (%)
  - 평균 단가 대비 수익률 (%)
  - 20일 수익률 (%)
- 섹터 코멘트:
  - 반도체: 삼성전자 / SK하이닉스 / KODEX 반도체 — 오전 동향 및 주요 이벤트
  - AI 전력: KODEX AI파워핵심장비
  - 각 1~2줄
- ADVISOR.md 신호 점수 기준 적용 → 총 신호 점수 계산
- 포트폴리오 요약
- next_trigger: 장 마감 확인 (15:30) 및 오후 주목 이벤트

## 6. Git 커밋 및 Push

아래 스크립트를 단일 Bash 실행으로 실행합니다:

```bash
git add schedule/

git diff --cached --quiet || \
git commit -m "data: KR 장중시황 $(TZ=Asia/Seoul date +%Y-%m-%d)"

git push origin HEAD && echo "PUSH_OK" || echo "PUSH_FAIL"
```

## 7. Push 실패 시에만 Slack 알림

push 결과가 `PUSH_FAIL`인 경우에만 실행합니다:

```bash
curl -s -X POST "$SLACK_WEBHOOK_URL_ERR" \
  -H "Content-Type: application/json" \
  -d "{\"text\":\"❌ [KR 장중] git push 실패 — $(date +%Y-%m-%d)\"}"
```

`PUSH_OK`인 경우 Slack 알림을 전송하지 마세요.
GitHub Actions가 성공 알림을 자동으로 처리합니다.

## 참고

- `data/opensesame.db`는 원격 환경에 존재하지 않습니다 (`gitignored`).
  DB 캐싱을 우회하는 `fetch_kr_price` / `fetch_kr_price_20d`를 직접 사용하세요.
- `ADVISOR.md`와 `history/portfolio.toml`은 저장소에 있으며 Read 도구로 읽을 수 있습니다.
- 미국 종목은 보고서에서 제외합니다.
- 가격은 장중 스냅샷 — 보고서에 이를 명확히 기재할 것.
