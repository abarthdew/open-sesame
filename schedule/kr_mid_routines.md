## KR Market Midday Briefing

You are an automated agent for the `open-sesame` investment analysis system.

At KST 11:30 (midday, while the Korean market is still open),
generate a KR market midday briefing **for Korean market (KR) holdings only**,
then commit and push it to GitHub.
**This report covers only `market = "KR"` holdings. Do NOT include US market holdings under any circumstances.**

- Slack success notifications are automatically handled by GitHub Actions (`report-notify.yml`) after push detection.
- Only if push fails, send a Slack notification using the `WebFetch` tool (see Section 6).

## 1. Identify Holdings

Use the Read tool to open:

```text
history/portfolio.toml
```

Identify holdings where `market = "KR"`:

- ticker
- quantity (`qty`)
- average price (`avg_price`)

## 2. Fetch Price Data

> ⚠️ **Update the ticker list below to match your actual KR holdings in `history/portfolio.toml`.**

Use `data/fetcher.py` via Bash for current price and 20-day baseline:

```bash
python3 -c "
from data.fetcher import fetch_kr_price, fetch_kr_price_20d

# Update this list to match your KR holdings
tickers = [
    ('091160', 'KODEX Semiconductor'),
    ('000660', 'SK hynix'),
    ('005930', 'Samsung Electronics'),
    ('487240', 'KODEX AI Power Core Equipment'),
    ('0035T0', 'PLUS Global Humanoid Robot Active'),
    ('411060', 'ACE KRX Gold Spot'),
    ('133690', 'TIGER US NASDAQ 100'),
    ('360750', 'TIGER US S&P500'),
    ('438080', 'ACE US S&P500 Bond Mixed 50 Active'),
    ('438100', 'ACE US NASDAQ100 Bond Mixed 50 Active'),
]

for ticker, name in tickers:
    price = fetch_kr_price(ticker)
    price_20d = fetch_kr_price_20d(ticker)
    if price and price_20d:
        chg_20d = (price - price_20d) / price_20d * 100
        print(f'{name} ({ticker}): {price:,.0f} KRW | 20d: {chg_20d:+.1f}%')
    else:
        print(f'{name} ({ticker}): unavailable')
"
```

Also fetch today's OHLCV to compute intraday change (current vs open):

```bash
python3 -c "
from pykrx import stock
from datetime import datetime, timedelta
today = datetime.now().strftime('%Y%m%d')
start = (datetime.now() - timedelta(days=5)).strftime('%Y%m%d')

# Morning index movement
for idx_code, name in [('1001','KOSPI'),('2001','KOSDAQ')]:
    try:
        df = stock.get_index_ohlcv_by_date(start, today, idx_code)
        if not df.empty:
            row = df.iloc[-1]
            prev_close = df['종가'].iloc[-2] if len(df) >= 2 else row['시가']
            print(f'{name}: current {row[\"종가\"]:,.2f}pt | open {row[\"시가\"]:,.2f}pt | vs prev close {(row[\"종가\"]/prev_close-1)*100:+.2f}%')
    except Exception as e:
        print(f'{name}: error - {e}')

# Per-stock intraday move vs open
tickers = [
    ('091160', 'KODEX Semiconductor'), ('000660', 'SK hynix'), ('005930', 'Samsung Electronics'),
    ('487240', 'KODEX AI Power Core Equipment'), ('0035T0', 'PLUS Global Humanoid'), ('411060', 'ACE KRX Gold Spot'),
]
for ticker, name in tickers:
    try:
        df = stock.get_market_ohlcv_by_date(today, today, ticker)
        if not df.empty:
            row = df.iloc[-1]
            chg = (row['종가'] - row['시가']) / row['시가'] * 100 if row['시가'] else 0
            print(f'{name}: current {row[\"종가\"]:,.0f} KRW | open {row[\"시가\"]:,.0f} KRW | vs open {chg:+.2f}%')
    except Exception as e:
        print(f'{name}: {e}')
"
```

### Fallback: WebSearch (only if a specific ticker returns unavailable)

- Search: `"[stock name] stock price today"` or `"[ticker] KRX stock price today"`
- Do NOT write `N/A` or estimated values — always obtain a real price

## 3. Fetch Market News via WebSearch

For each holding where intraday change (vs. open) exceeds ±1%, run a WebSearch to find the actual cause.
Also search for morning market context.

**Required searches (run all):**
```
KOSPI morning market news [YYYY-MM-DD]
Samsung Electronics news today [YYYY-MM-DD]
SK hynix news today [YYYY-MM-DD]
```

**Conditional searches (only if intraday change > ±2%):**
```
KODEX Semiconductor ETF news [YYYY-MM-DD]
KODEX AI Power Core Equipment news [YYYY-MM-DD]
```

**How to use results:**
- In sector comments, cite the actual news found
- Do NOT fabricate reasons — if no relevant news is found, write: `trigger unconfirmed (no relevant results found)`
- Do NOT use LLM prior knowledge alone to explain price moves

## 4. Read ADVISOR.md

Use the Read tool to open:

```text
ADVISOR.md
```

Identify the signal scoring rules.

## 5. Generate Report

Output file (exact filename — do not change):

```text
schedule/[YYYY-MM-DD][single][KR-midday].log
```

Always overwrite the file with the latest report,
even if today's file already exists.

Report format — you MUST follow these template files in order:

1. Read `formats/ADVISOR_form_common.log` → use as the fixed header structure
2. Read `formats/ADVISOR_form_single.log` → use as the body structure
3. Read `formats/ADVISOR_ex_single.log` → refer to as a completed output example

**Do NOT use any existing files in `schedule/` or `report/` as format reference.**
The three template files above are the sole format authority.
Existing log files must not influence the output format in any way.

The report must include:

- analysis datetime
- mode (`single`)
- analysis target (all KR holdings)
- **⚠️ Note clearly at the top: this is an intraday report — prices are live snapshots, not closing prices**
- KOSPI / KOSDAQ morning movement (current level, change vs open)
- holdings table:
  - current price (intraday)
  - change vs open (%)
  - return vs average price (%)
  - 20-day return (%)
- sector comments:
  - Semiconductors: Samsung Electronics / SK hynix / KODEX Semiconductor — morning movement & notable events
  - AI Power: KODEX AI Power Core Equipment
  - 1~2 lines each
- apply ADVISOR.md signal scoring rules → calculate total signal score
- portfolio summary
- next_trigger: market close confirmation (15:30) and afternoon events to watch

## 6. Git Commit & Push

Run the following script as a single Bash execution:

```bash
git add schedule/

git diff --cached --quiet || \
git commit -m "data: KR midday report $(TZ=Asia/Seoul date +%Y-%m-%d)"

git push origin HEAD && echo "PUSH_OK" || echo "PUSH_FAIL"
```

## 7. Slack Notification Only on Push Failure

Only if the push result is `PUSH_FAIL`, run:

```bash
curl -s -X POST "$SLACK_WEBHOOK_URL_ERR" \
  -H "Content-Type: application/json" \
  -d "{\"text\":\"❌ [KR Midday] git push failed — $(date +%Y-%m-%d)\"}"
```

Do not send Slack notifications for `PUSH_OK`.
GitHub Actions automatically handles success notifications.

## Notes

- `data/opensesame.db` does not exist in the remote environment (`gitignored`).
  Use `fetch_kr_price` / `fetch_kr_price_20d` directly — these bypass DB caching.
- `ADVISOR.md` and `history/portfolio.toml` are available in the repository and can be read using the Read tool.
- Exclude US holdings from the report.
- Prices are intraday snapshots — note this clearly in the report.
