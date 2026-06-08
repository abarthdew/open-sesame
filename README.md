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
/open-sesame [mode: multi][analysis target: SK hynix (000660)][question: Should I add to my position now?]

# Quick single-agent opinion
/open-sesame [mode: single][analysis target: NVDA][question: Should I hold through the earnings release tomorrow?]

# Portfolio rebalance check
/open-sesame [mode: rebalance][question: Review my current portfolio allocation.]

# Sector scan for new candidates
/open-sesame [mode: scan][theme: AI infrastructure][question: Find ETFs or stocks that do not overlap with my current portfolio]

# Macro analysis
/open-sesame [mode: macro][period: 30d][question: Portfolio check before FOMC]
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

## Scheduled Routines (Claude Code Routines)

`schedule/` contains prompt files for **Claude Code Remote Agents** — cloud-based agents that run automatically on a schedule, without your local machine.

Each `*_routines.md` file is a self-contained agent prompt: fetch prices, search news, generate a report, commit and push to GitHub.

| Routine | Trigger | Output |
|---|---|---|
| `kr_close_routines.md` | Weekdays 16:10 KST | `schedule/[date][single][KR-close-daily].log` |
| `kr_mid_routines.md` | Weekdays 11:40 KST | `schedule/[date][single][KR-midday].log` |
| `us_close_routines.md` | Weekdays 06:40 KST | `schedule/[date][single][US-close-daily].log` |
| `event_cal_routines.md` | Sundays 18:00 KST | `history/events.toml` (overwritten) |

**To register a routine:**
1. Open **https://claude.ai/code/routines**
2. Click **New Routine**, paste the `.md` file contents as the prompt
3. Set the cron schedule and connect your GitHub repo

Update the ticker list inside each routine file to match your actual holdings before registering.

See `schedule/ROUTINES.md` for full setup instructions and cron expressions.

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
| `DART_API_KEY` | Korean public disclosure (DART) | Free |
| `KRX_ID` / `KRX_PW` | KRX login for pykrx | Free |

---

## Contributing

Issues and PRs welcome. This project is primarily built with and for [Claude Code](https://docs.anthropic.com/en/docs/claude-code).

---

## License

MIT
