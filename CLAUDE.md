# Open Sesame — AI Investment Advisor for Claude Code

## Project Overview
Personal investment dashboard with AI-powered analysis.  
Korean/U.S. stock portfolio tracking + Claude Code investment advisor.  
Usage: `README.md`

## File Structure
```text
open-sesame/
├── app.py                        # Flask server (API + HTML serving)
├── ADVISOR.md                    # Investment advisor prompt (includes CLI usage)
├── history/
│   ├── portfolio.toml            # Portfolio data (editable)
│   ├── events.toml               # Event calendar data (editable)
│   ├── api_cache.json            # Weekly briefing API cache (auto-generated)
│   └── YYYY-MM-DD.json           # My-page snapshot output (auto-generated, gitignored)
├── data/
│   ├── db.py                     # SQLite schema & query functions
│   ├── fetcher.py                # pykrx / yfinance price fetcher
│   └── opensesame.db             # gitignored
├── briefing/
│   ├── briefing.py               # Slack briefing content generator
│   └── slack.py                  # Slack Webhook sender
├── static/                       # Frontend assets
├── templates/                    # Jinja2 HTML templates (4 tabs)
├── report/                       # Investment advisor analysis logs (gitignored)
├── schedule/                     # Remote agent auto-generated reports (gitignored)
├── .github/workflows/
│   └── briefing.yml              # Briefing automation (GitHub Actions)
└── formats/                      # Advisor report format templates
```

## Run
```bash
python3 app.py   # → http://localhost:5000
```

## Git Workflow
- **Commit unit**: Commit immediately for each meaningful change
- **Commit message**: English only, concise, essential only  
  (prefix: `feat:`, `fix:`, `refactor:`, `docs:`, `data:` etc.)
- **Push**: Auto-push to main branch (`git push origin HEAD:main`)  
  *(Modify this if you want to protect the main branch)*
- **No force push**: Never use `--force`
