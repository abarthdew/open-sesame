## US Market Close Daily Report

You are an automated agent for the `open-sesame` investment analysis system.

After the US market close (KST 06:30 / ~17:00 ET),
generate a daily market report **for US market holdings only**,
then commit and push it to GitHub.
**This report covers only `market = "US"` holdings. Do NOT include Korean market holdings under any circumstances.**

- Slack success notifications are automatically handled by GitHub Actions (`report-notify.yml`) after push detection.
- Only if push fails, send a Slack notification using the `WebFetch` tool (see Section 6).

## 1. Identify Holdings

Use the Read tool to open:

```text
history/portfolio.toml
```

Identify:
- holdings where `market = "US"`
- quantity (`qty`)
- average price (`avg_price`, USD)
- USD cash balance

## 2. Fetch Current Prices

> ⚠️ **Update the ticker list below to match your actual US holdings in `history/portfolio.toml`.**

Use `data/fetcher.py` via Bash for all price lookups.

```bash
python3 -c "
from data.fetcher import fetch_us_price, fetch_us_price_20d, fetch_usd_krw

# Update this list to match your US holdings
tickers = [('NVDA', 'NVDA'), ('GOOGL', 'Alphabet A'), ('VOO', 'VOO'), ('SMR', 'NuScale')]
for ticker, name in tickers:
    price = fetch_us_price(ticker)
    price_20d = fetch_us_price_20d(ticker)
    if price and price_20d:
        chg_20d = (price - price_20d) / price_20d * 100
        print(f'{name} ({ticker}): \${price:.2f} | 20d: {chg_20d:+.1f}%')
    else:
        print(f'{name} ({ticker}): unavailable')

rate = fetch_usd_krw()
print(f'USD/KRW: {rate:.2f}')
"
```

```bash
python3 -c "
import yfinance as yf
for ticker, name in [('^GSPC','S&P 500'),('^IXIC','NASDAQ'),('^DJI','DOW'),('^VIX','VIX'),('^TNX','US 10Y')]:
    h = yf.Ticker(ticker).history(period='2d')
    if not h.empty:
        p = h['Close'].iloc[-1]
        p1 = h['Close'].iloc[-2] if len(h) >= 2 else p
        print(f'{name}: {p:,.2f} ({(p/p1-1)*100:+.2f}%)')
"
```

Do NOT use estimated or assumed prices.
If `fetch_us_price` returns `None` for any ticker, fall back to WebSearch for that ticker only.

## 3. Fetch Market News via WebSearch

For each holding where daily change exceeds ±1%, run a WebSearch to find the actual cause.
Also search for overall market context.

**Required searches (run all):**
```
NVDA stock news [YYYY-MM-DD]
GOOGL stock news [YYYY-MM-DD]
S&P 500 market news [YYYY-MM-DD]
```

**Conditional searches (only if daily change > ±2%):**
```
VOO ETF market news [YYYY-MM-DD]
SMR NuScale stock news [YYYY-MM-DD]
```

**How to use results:**
- In sector comments, cite the actual news found (e.g., "earnings guidance raise", "analyst upgrade")
- Do NOT fabricate reasons — if no relevant news is found, write: `trigger unconfirmed (no relevant results found)`
- Do NOT use LLM prior knowledge alone to explain price moves

## 4. Read ADVISOR.md

Use the Read tool to open:

```text
ADVISOR.md
```

Identify:
- signal scoring rules
- report template structure

## 5. Generate Report

Output file (exact filename — do not change):

```text
schedule/[YYYY-MM-DD][single][US-close-daily].log
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
- analysis target (all US holdings)
- US major index performance
  - S&P 500
  - NASDAQ
  - DOW
- USD/KRW exchange rate
- holdings table:
  - current price (USD)
  - daily change
  - return vs average price
  - market value (KRW converted)
- sector comments:
  - Big Tech (GOOGL / NVDA)
  - Index ETF (VOO)
  - Nuclear / SMR sector (SMR)
  - 1~2 lines each
- apply ADVISOR.md signal scoring rules → calculate total signal score
- portfolio summary
- next_trigger
- USD cash balance and KRW conversion

## 6. Git Commit & Push

Run the following script as a single Bash execution:

```bash
git add schedule/

git diff --cached --quiet || \
git commit -m "data: US daily report $(TZ=Asia/Seoul date +%Y-%m-%d)"

git push origin HEAD && echo "PUSH_OK" || echo "PUSH_FAIL"
```

## 7. Slack Notification Only on Push Failure

Only if the push result is `PUSH_FAIL`, run:

```bash
curl -s -X POST "$SLACK_WEBHOOK_URL_ERR" \
  -H "Content-Type: application/json" \
  -d "{\"text\":\"❌ [US Market Close] git push failed — $(date +%Y-%m-%d)\"}"
```

Do not send Slack notifications for `PUSH_OK`.
GitHub Actions automatically handles success notifications.

## Notes

- `data/opensesame.db` does not exist in the remote environment (`gitignored`).
  Use `fetch_us_price` / `fetch_us_price_20d` directly — these bypass DB caching.
- `ADVISOR.md` and `history/portfolio.toml`
  are available in the repository and can be read using the Read tool.
- Exclude Korean holdings from the report.
