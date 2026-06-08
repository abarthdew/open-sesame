## Event Calendar Auto-Update

You are maintaining the events calendar for a personal investment dashboard (`open-sesame`).

Your task:
research upcoming market events, update `history/events.toml`, then commit and push.

- Use the `WebSearch` tool for all web research.
- Slack success notifications are automatically handled by GitHub Actions (`report-notify.yml`) after push detection.
- Only if push fails, send a Slack notification using the `WebFetch` tool (see Step 6).

## Portfolio Context

> ⚠️ **Update this section to match your actual holdings in `history/portfolio.toml`.**

Korean stocks:
- KODEX Semiconductor ETF (091160)
- SK hynix (000660)
- Samsung Electronics (005930)

US stocks:
- NVDA (Nvidia)
- GOOGL (Alphabet)
- VOO (S&P 500 ETF)
- SMR (NuScale Power)

## Step 1 — Read Current Events

Use the Read tool to open:

```text
history/events.toml
```

## Step 2 — Determine Today's Date

Run:

```bash
date +%Y-%m-%d
```

## Step 3 — Research Upcoming Events

Use the `WebSearch` tool for all searches.

Research:

- NVDA next earnings date
- GOOGL (Alphabet) next earnings date
- Samsung Electronics next quarterly earnings date
- SK hynix next quarterly earnings date
- Remaining FOMC meeting and decision dates (current year)
- Remaining Bank of Korea base-rate decision dates (current year)
- US CPI release dates (next 3 months)
- US PCE release dates (next 3 months)
- US Nonfarm Payrolls (NFP) release dates (next 3 months)
- Jackson Hole Fed symposium date (if upcoming)
- Major geopolitical events affecting semiconductors
  (US-China trade, export controls, etc.)

## Step 4 — Write Updated events.toml

Rules:

- Remove all events dated before today.
- Keep future events already present in the file.
- Do not duplicate existing future events.
- Add newly discovered upcoming events.
- If a date is uncertain, append `(Estimated)` to the event name.
- `importance` rules:
  - `HIGH`
    - earnings for held stocks
    - FOMC with SEP projections
    - major geopolitical events
  - `MID`
    - regular FOMC
    - CPI / PCE / NFP
    - Bank of Korea decisions
  - `LOW`
    - minor events
- `scenarios` must be limited to 2 lines maximum.
  Write in the user's language (Korean if the user communicates in Korean, English otherwise).

File format:

```toml
[[events]]
date       = "YYYY-MM-DD"
importance = "HIGH"
name       = "Event name"
scenarios  = "A: bullish scenario → portfolio impact\nB: bearish scenario → portfolio impact"
```

Write the complete updated file to:

```text
history/events.toml
```

Always overwrite the existing file with the latest data, even if today's file already exists.

## Step 5 — Git Commit & Push

Run the following script as a single Bash execution:

```bash
git add history/events.toml

git diff --cached --quiet || \
git commit -m "data: auto-update events calendar $(TZ=Asia/Seoul date +%Y-%m-%d)"

git push origin HEAD && echo "PUSH_OK" || echo "PUSH_FAIL"
```

## Step 6 — Slack Notification Only on Push Failure

Only if the push result is `PUSH_FAIL`, run:

```bash
curl -s -X POST "$SLACK_WEBHOOK_URL_ERR" \
  -H "Content-Type: application/json" \
  -d "{\"text\":\"❌ [Events Calendar] git push failed — $(date +%Y-%m-%d)\"}"
```

Do not send Slack notifications for `PUSH_OK`.
GitHub Actions handles success notifications automatically.

## Note

The Flask server runs on the user's local machine and is not accessible from this environment.

After pulling changes, the user will manually reload events from the dashboard.
