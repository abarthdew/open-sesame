# Open Sesame

**AI-powered investment advisor & dashboard for Claude Code**  
KR/US stock portfolio tracking + multi-agent analysis via `/open-sesame` CLI command

---

## What It Does

Open Sesame turns Claude Code into a personal investment advisor. You describe a situation — a stock move, a portfolio question, a macro event — and `/open-sesame` calls a structured multi-agent analysis pipeline that reads your actual portfolio data and returns a scored, actionable recommendation.

**5 analysis modes:**

| Mode | Description | Time |
|---|---|---|
| `multi` (default) | Bull agent vs Bear agent → Arbiter verdict | ~60s |
| `single` | Single agent, fast opinion | ~15s |
| `rebalance` | Full portfolio weight/account/sector review | ~30s |
| `scan` | New candidate discovery by theme/sector | ~30s |
| `macro` | 6-axis macro diagnosis → portfolio positioning (7d/30d/90d) | ~30s |

**Other features:**
- Flask dashboard with portfolio overview, signals, event calendar, and snapshot history
- Automated Slack briefings (morning / KR close / US open / weekly) via GitHub Actions
- Remote agent scheduled reports (Claude AI routines)

---

## Quick Start

### 1. Install

```bash
pip3 install flask pykrx yfinance python-dotenv tomli
```

### 2. Configure

Copy `.env.example` to `.env` and fill in your API keys:

```bash
cp .env.example .env
```

Edit `history/portfolio.toml` with your holdings. The sample file has the correct structure.

### 3. Run

```bash
python3 app.py
# → http://localhost:5000
```

---

## Investment Advisor CLI

**Prerequisite:** [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) installed

Run from the project directory:

```bash
# Multi-agent analysis (recommended)
/open-sesame [mode: multi][분석 대상: SK하이닉스 (000660)][질문: 추가 매수 타이밍인지 판단해줘.]

# Quick single-agent opinion
/open-sesame [mode: single][분석 대상: NVDA][질문: 실적 발표 전날, 보유 유지해도 될까?]

# Portfolio rebalance check
/open-sesame [mode: rebalance][질문: 현재 포트폴리오 비중 점검해줘.]

# Sector scan for new candidates
/open-sesame [mode: scan][테마: AI 인프라][질문: 현재 포트폴리오와 겹치지 않는 ETF나 개별주 후보를 찾아줘]

# Macro analysis
/open-sesame [mode: macro][기간: 30일][질문: FOMC 전 포트폴리오 점검]
```

The agent reads your actual portfolio (avg price, P&L, cash ratio) from the local DB and applies the scoring framework in `ADVISOR.md`.

Analysis logs are saved to `report/[YYYY-MM-DD][mode][title].log` (gitignored).

---

## Dashboard

| Tab | Description |
|---|---|
| Overview | Holdings with live prices, P&L, portfolio weights |
| Signals | Technical/fundamental signal scoring per stock |
| Events | Earnings calendar + macro events |
| My Page | Monthly net worth snapshot history |

Edit `history/portfolio.toml` to update your holdings, then hit **Reload** in the dashboard.

---

## Automated Briefings (GitHub Actions)

`.github/workflows/briefing.yml` sends Slack messages on a schedule.

Add these to your repo's **GitHub Secrets**:

```
SLACK_WEBHOOK_URL
ALPHA_VANTAGE_KEY
DART_API_KEY
KRX_ID
KRX_PW
```

Trigger manually:

```bash
python3 -m briefing.briefing morning    # Morning briefing
python3 -m briefing.briefing kr_close  # KR market close
python3 -m briefing.briefing us_open   # US market open
python3 -m briefing.briefing weekly    # Weekly review
```

> **Note:** GitHub Actions' built-in `schedule:` trigger has multi-hour delays. Recommended: use [cron-job.org](https://cron-job.org) → `workflow_dispatch` call.

---

## File Structure

```
open-sesame/
├── app.py                    # Flask server
├── ADVISOR.md                # Advisor prompt & scoring rules
├── history/
│   ├── portfolio.toml        # Your holdings (edit this)
│   ├── events.toml           # Event calendar
│   └── api_cache.json        # Weekly briefing cache (auto)
├── data/
│   ├── db.py                 # SQLite schema & queries
│   └── fetcher.py            # pykrx / yfinance fetcher
├── briefing/                 # Slack briefing generator
├── static/ & templates/      # Dashboard frontend
├── formats/                  # Advisor report templates
└── .github/workflows/        # GitHub Actions automation
```

---

## API Keys

| Key | Purpose | Free tier |
|---|---|---|
| `SLACK_WEBHOOK_URL` | Briefing notifications | Free |
| `ALPHA_VANTAGE_KEY` | News sentiment (weekly only) | 25 req/day |
| `DART_API_KEY` | Korean disclosure (공시) | Free |
| `KRX_ID` / `KRX_PW` | KRX login for pykrx | Free |

---

## Contributing

Issues and PRs welcome. This project is primarily built with and for [Claude Code](https://docs.anthropic.com/en/docs/claude-code).

---

## License

MIT
