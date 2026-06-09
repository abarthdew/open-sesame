# Automated Routines

The `schedule/` directory contains prompt files for **Claude Code remote agents** — automated agents that run on a schedule in the cloud, with no local machine required.

Each `*_routines.md` file defines one routine: what data to fetch, how to analyze it, and how to commit the output back to the repository.

---

## What Each Routine Does

| File | Trigger | Output |
|---|---|---|
| `kr_close_routines.md` | Weekdays after KR market close (16:00 KST) | `schedule/[date][single][KR-close-daily].log` |
| `kr_mid_routines.md` | Weekdays at midday (11:30 KST) | `schedule/[date][single][KR-midday].log` |
| `us_close_routines.md` | Weekdays after US market close (06:30 KST / ~17:00 ET) | `schedule/[date][single][US-close-daily].log` |
| `event_cal_routines.md` | Weekly (Sunday) | `history/events.toml` (overwrite) |

Generated `.log` files are gitignored — they exist only on the machine that pulls the repo.

---

## How to Register a Routine in Claude Code

### Step 1 — Open Routines

Go to: **https://claude.ai/code/routines**

> Requires a Claude Code subscription (Pro or above).

### Step 2 — Create a New Routine

Click **New Routine** and fill in:

| Field | Value |
|---|---|
| **Name** | e.g. `KR Market Close Report` |
| **Prompt** | Paste the full contents of the routine file (e.g. `kr_close_routines.md`) |
| **Schedule** | Set via cron or preset (see below) |
| **Repository** | Connect your GitHub repo |

### Step 3 — Set the Schedule

Recommended cron expressions (KST = UTC+9):

| Routine | KST time | Cron (UTC) |
|---|---|---|
| KR close | 16:10 weekdays | `10 7 * * 1-5` |
| KR midday | 11:40 weekdays | `40 2 * * 1-5` |
| US close | 06:40 weekdays | `40 21 * * 1-5` |
| Event calendar | 18:00 Sunday | `0 9 * * 0` |

> **Note:** GitHub Actions' built-in `schedule:` trigger has multi-hour delays. Using
> [cron-job.org](https://cron-job.org) → `workflow_dispatch` is more reliable for
> time-sensitive reports. Claude Code Routines run directly without this limitation.

### Step 4 — Configure Cloud Environment

Go to **each routine window** and update the cloud environment before registering routines.

**Network access:** Custom

**Allowed domains:**
```
data.krx.co.kr
marketdata.krx.co.kr
fchart.stock.naver.com
query1.finance.yahoo.com
query2.finance.yahoo.com
hooks.slack.com
```

**Environment variables:**
```
KRX_ID=               # fill yours
KRX_PW=               # fill yours
SLACK_WEBHOOK_URL_ERR= # fill yours
```

**Setup script** (pre-installs dependencies to save tokens per run):
```bash
pip install yfinance python-dotenv requests
pip install pykrx || true
git config --global user.name "claude"
git config --global user.email "claude@open-sesame.local"
```

Save changes → then select this environment in the **Edit Routine** window.

### Step 5 — Update Ticker Lists

Each routine file contains a hardcoded ticker list matching the sample portfolio.
**Update these lists to match your actual holdings** in `history/portfolio.toml`
before registering the routine.

---

## How It Works

```
Claude Code Routines (cloud)
        │
        ├── Read portfolio.toml + ADVISOR.md
        ├── Fetch live prices (pykrx / yfinance)
        ├── WebSearch for news
        ├── Generate report using formats/ templates
        └── git commit + push → your GitHub repo
                │
                └── GitHub Actions (report-notify.yml)
                        └── Slack notification on success
```

The routine agent runs entirely in the cloud. It clones your repo, generates the report,
commits it, and pushes. You then `git pull` to see the result, or view it directly on GitHub.

---

## Output Format

Reports follow the same templates as manual `/open-sesame` analysis:

- Header: `formats/ADVISOR_form_common.log`
- Body: `formats/ADVISOR_form_single.log`
- Example: `formats/ADVISOR_ex_single.log`

The report language follows the routine file's language (English routines → English reports,
Korean routines → Korean reports).
