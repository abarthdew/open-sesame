import json
import logging
import re
import time
from logging.handlers import BaseRotatingHandler
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, jsonify, request, render_template, g
from data.db import (
    init_db, get_holdings, get_cash, get_signals, toggle_signal,
    get_events, reseed_events, seed_snapshots, get_snapshot_table, reseed_holdings,
    sync_api_cache, get_news_sentiment, upsert_trades, get_trades,
    upsert_triggers, get_triggers, toggle_trigger,
)
from data.fetcher import get_price, get_exchange_rate, get_price_20d

HISTORY_DIR   = Path(__file__).parent / "history"
SCHEDULE_DIR  = Path(__file__).parent / "schedule"
REPORT_DIR    = Path(__file__).parent / "report"
DEBUG_DIR     = Path(__file__).parent / "debug"


# ── Logging ───────────────────────────────────────────────────────────────────

class _DailyDebugHandler(BaseRotatingHandler):
    """Auto-rotates to debug/YYYY-MM-DD.debug when the date changes."""
    def __init__(self, dir_path: Path):
        dir_path.mkdir(exist_ok=True)
        self._dir = dir_path
        self._date = datetime.now().strftime('%Y-%m-%d')
        super().__init__(str(dir_path / f"{self._date}.debug"), mode='a', encoding='utf-8')

    def shouldRollover(self, record):
        return datetime.now().strftime('%Y-%m-%d') != self._date

    def doRollover(self):
        if self.stream:
            self.stream.close()
            self.stream = None
        self._date = datetime.now().strftime('%Y-%m-%d')
        self.baseFilename = str(self._dir / f"{self._date}.debug")
        self.stream = self._open()


_handler = _DailyDebugHandler(DEBUG_DIR)
_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)-5s %(message)s', datefmt='%H:%M:%S'))
logger = logging.getLogger('open-sesame')
logger.setLevel(logging.DEBUG)
logger.addHandler(_handler)


app = Flask(__name__, static_folder="static")


@app.before_request
def _before():
    global _initialized
    if not _initialized:
        init_db()
        _initialized = True
    g.t0 = time.time()

@app.after_request
def _after(response):
    ms = round((time.time() - g.t0) * 1000)
    logger.info('%s %s %s %dms', request.method, request.path, response.status_code, ms)
    return response

@app.errorhandler(Exception)
def _error(e):
    logger.error('unhandled exception: %s', e, exc_info=True)
    raise e

_initialized = False


# ── Static ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("dashboard.html")


# ── Portfolio ──────────────────────────────────────────────────────────────────

@app.route("/api/portfolio")
def portfolio():
    rate = get_exchange_rate()
    holdings = get_holdings()

    kr_total = 0.0
    us_total_usd = 0.0
    items = []

    for h in holdings:
        price = get_price(h["ticker"], h["market"])
        if price is None:
            price = h["avg_price"]  # fall back to avg price if no live price

        cost = h["avg_price"]
        pct = round((price / cost - 1) * 100, 2) if cost else 0
        value = price * h["qty"]

        price_20d = get_price_20d(h["ticker"], h["market"])
        chg_20d = round((price / price_20d - 1) * 100, 2) if price_20d else None
        if chg_20d is None:
            rec = None
        elif chg_20d >= 20:
            rec = "sell"
        elif chg_20d <= -15:
            rec = "buy"
        else:
            rec = "hold"

        if h["market"] == "KR":
            kr_total += value
        else:
            us_total_usd += value

        items.append({
            "id":        h["id"],
            "account":   h["account"],
            "ticker":    h["ticker"],
            "name":      h["name"],
            "market":    h["market"],
            "qty":       h["qty"],
            "avg_price": cost,
            "price":     price,
            "value":     round(value),
            "pct":       pct,


            "alert":     pct >= 5,
            "chg_20d":   chg_20d,
            "rec":       rec,
        })

    us_total_krw = us_total_usd * rate
    cash_rows = get_cash()
    cash_krw = sum(r["amount"] for r in cash_rows if r["currency"] == "KRW")
    cash_usd = sum(r["amount"] for r in cash_rows if r["currency"] == "USD")
    cash_krw_total = cash_krw + cash_usd * rate

    total = kr_total + us_total_krw + cash_krw_total
    total = max(total, 1)  # prevent zero-division

    # per-account total (stocks + cash)
    acct_stock_krw = {}
    for item in items:
        val_krw = item["value"] if item["market"] == "KR" else round(item["value"] * rate)
        acct_stock_krw[item["account"]] = acct_stock_krw.get(item["account"], 0) + val_krw
    acct_cash_krw = {}
    for r in cash_rows:
        krw = r["amount"] if r["currency"] == "KRW" else round(r["amount"] * rate)
        acct_cash_krw[r["account"]] = acct_cash_krw.get(r["account"], 0) + krw
    account_totals = {
        acct: acct_stock_krw.get(acct, 0) + acct_cash_krw.get(acct, 0)
        for acct in set(list(acct_stock_krw) + list(acct_cash_krw))
    }

    return jsonify({
        "rate":           round(rate, 2),
        "holdings":       items,
        "account_totals": {k: round(v) for k, v in account_totals.items()},
        "summary": {
            "kr_stock":     round(kr_total),
            "us_stock_usd": round(us_total_usd, 2),
            "us_stock_krw": round(us_total_krw),
            "cash_krw":     round(cash_krw),
            "cash_usd":     round(cash_usd, 2),
            "total_krw":    round(total),
            "weight": {
                "kr_stock": round(kr_total / total * 100, 1),
                "us_stock": round(us_total_krw / total * 100, 1),
                "cash":     round(cash_krw_total / total * 100, 1),
            },
        },
    })


# ── Cash ──────────────────────────────────────────────────────────────────────

@app.route("/api/cash")
def cash():
    rate = get_exchange_rate()
    rows = get_cash()
    result = []
    for r in rows:
        krw_equiv = r["amount"] if r["currency"] == "KRW" else round(r["amount"] * rate)
        result.append({**r, "krw_equiv": krw_equiv})
    return jsonify(result)


# ── Signals ───────────────────────────────────────────────────────────────────

@app.route("/api/signals")
def signals():
    return jsonify(get_signals())


@app.route("/api/signals/<int:signal_id>/toggle", methods=["POST"])
def signal_toggle(signal_id):
    updated = toggle_signal(signal_id)
    if updated is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(updated)


# ── Events ────────────────────────────────────────────────────────────────────

@app.route("/api/events")
def events():
    date_from = request.args.get("from")
    date_to   = request.args.get("to")
    return jsonify(get_events(date_from, date_to))


@app.route("/api/events/reload", methods=["POST"])
def events_reload():
    reseed_events()
    return jsonify({"ok": True, "count": len(get_events())})


@app.route("/api/news-sentiment")
def news_sentiment():
    return jsonify(get_news_sentiment())


@app.route("/api/cache/sync", methods=["POST"])
def cache_sync():
    result = sync_api_cache()
    return jsonify({"ok": True, **result})


# ── Mypage ────────────────────────────────────────────────────────────────────

@app.route("/api/mypage")
def mypage():
    date_from = request.args.get("from")
    date_to   = request.args.get("to")
    return jsonify(get_snapshot_table(date_from, date_to))


@app.route("/api/mypage/reload", methods=["POST"])
def mypage_reload():
    import sys
    if sys.version_info >= (3, 11):
        import tomllib
    else:
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib
    toml_data = tomllib.loads((HISTORY_DIR / "portfolio.toml").read_text(encoding="utf-8"))
    upsert_trades(toml_data.get("trades", []))

    result = seed_snapshots()
    if result.get("status") == "error":
        return jsonify({"ok": False, "error": result.get("reason", "unknown")}), 400
    out = HISTORY_DIR / f"{result['date']}.json"
    json_written = not out.exists()
    if json_written:
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return jsonify({"ok": True, "snapshot": result, "json_written": json_written})


# ── Portfolio reload ──────────────────────────────────────────────────────────

@app.route("/api/portfolio/reload", methods=["POST"])
def portfolio_reload():
    reseed_holdings()
    return jsonify({"ok": True})


@app.route("/api/trades")
def trades():
    from_date = request.args.get("from")
    to_date   = request.args.get("to")
    return jsonify(get_trades(from_date, to_date))


# ── Triggers ─────────────────────────────────────────────────────────────────

@app.route("/api/triggers")
def triggers():
    return jsonify(get_triggers())


@app.route("/api/triggers/<int:trigger_id>/toggle", methods=["POST"])
def trigger_toggle(trigger_id):
    updated = toggle_trigger(trigger_id)
    if updated is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(updated)


@app.route("/api/triggers/reload", methods=["POST"])
def triggers_reload():
    cutoff = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    synced = 0
    total  = 0
    for log_dir, prefix in [(SCHEDULE_DIR, "schedule"), (REPORT_DIR, "report")]:
        for log_file in sorted(log_dir.glob("*.log")):
            date_m = re.match(r'\[(\d{4}-\d{2}-\d{2})\]', log_file.name)
            if date_m and date_m.group(1) < cutoff:
                continue
            text = log_file.read_text(encoding="utf-8", errors="ignore")
            source = f"{prefix}/{log_file.name}"
            n = upsert_triggers(source, text)
            if n > 0:
                synced += 1
                total  += n
    logger.info('triggers reload: %d files, %d triggers', synced, total)
    return jsonify({"ok": True, "synced": synced, "triggers": total})


# ── Refresh ───────────────────────────────────────────────────────────────────

@app.route("/api/refresh-prices")
def refresh_prices():
    holdings = get_holdings()
    updated = []
    for h in holdings:
        price = get_price(h["ticker"], h["market"], force=True)
        if price is not None:
            updated.append({"ticker": h["ticker"], "price": price})
    get_exchange_rate(force=True)
    return jsonify({"updated": len(updated), "tickers": updated})


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
