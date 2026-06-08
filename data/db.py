import json
import re
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib

DB_PATH = Path(__file__).parent.parent / "data" / "opensesame.db"
PORTFOLIO_TOML = Path(__file__).parent.parent / "history" / "portfolio.toml"
EVENTS_TOML    = Path(__file__).parent.parent / "history" / "events.toml"
API_CACHE      = Path(__file__).parent.parent / "history" / "api_cache.json"
BACKUP_PATH    = Path.home() / ".claude" / "backups" / "opensesame.db"


def backup_db():
    BACKUP_PATH.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(DB_PATH, BACKUP_PATH)

SCHEMA = """
CREATE TABLE IF NOT EXISTS holdings (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    account   TEXT    NOT NULL,
    ticker    TEXT    NOT NULL,
    name      TEXT    NOT NULL,
    market    TEXT    NOT NULL,
    qty       REAL    NOT NULL,
    avg_price REAL    NOT NULL
);

CREATE TABLE IF NOT EXISTS cash (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    account  TEXT    NOT NULL,
    currency TEXT    NOT NULL,
    amount   REAL    NOT NULL DEFAULT 0,
    memo     TEXT    DEFAULT ''
);

CREATE TABLE IF NOT EXISTS signals (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    type    TEXT    NOT NULL,
    text    TEXT    NOT NULL,
    hint    TEXT    DEFAULT '',
    checked INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS events (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    date       TEXT NOT NULL,
    importance TEXT NOT NULL,
    name       TEXT NOT NULL,
    scenarios  TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS news_sentiment (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    fetched_week TEXT NOT NULL,
    title        TEXT NOT NULL,
    source       TEXT NOT NULL,
    label        TEXT NOT NULL,
    tickers      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS price_cache (
    ticker     TEXT PRIMARY KEY,
    market     TEXT NOT NULL,
    price      REAL NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS price_history (
    ticker     TEXT NOT NULL,
    period     TEXT NOT NULL,
    price      REAL NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (ticker, period)
);

CREATE TABLE IF NOT EXISTS snapshot_dates (
    date         TEXT PRIMARY KEY,
    salary_krw   REAL NOT NULL DEFAULT 0,
    spending_krw REAL NOT NULL DEFAULT 0,
    tax_krw      REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS snapshot_accounts (
    date      TEXT NOT NULL,
    account   TEXT NOT NULL,
    value_krw REAL NOT NULL DEFAULT 0,
    PRIMARY KEY (date, account)
);

CREATE TABLE IF NOT EXISTS sold_transactions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    account    TEXT NOT NULL,
    ticker     TEXT NOT NULL,
    name       TEXT NOT NULL,
    market     TEXT NOT NULL,
    qty        REAL NOT NULL,
    avg_price  REAL NOT NULL,
    sell_price REAL NOT NULL,
    sell_date  TEXT NOT NULL,
    tax        REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS triggers (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file TEXT NOT NULL,
    idx         INTEGER NOT NULL,
    text        TEXT NOT NULL,
    condition   TEXT,
    action      TEXT,
    event_date  TEXT,
    checked     INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL
);
"""

SEED_SIGNALS = [
    ("sell", "D램 현물가 2개월 연속 하락",             "→ dramexchange.com 매월 초 확인"),
    ("sell", "증권사 목표주가 하향 3곳 이상 동시",      "→ 단순 상향은 후행 지표, 하향만 의미있음"),
    ("sell", "분기 영업이익 전분기 대비 감소 확인",     "→ 하이닉스 2분기 실적 8월 발표"),
    ("sell", "외국인 순매도 3거래일 이상 연속 대규모",  "→ 단기 차익실현인지 구조적 이탈인지 구분 필요"),
    ("sell", "CXMT 범용 D램 시장점유율 급등 뉴스",      "→ HBM과 무관하지만 투자심리 영향"),
    ("buy",  "코스피 현재 대비 15% 이상 하락 → 현금 30% 투입", "→ 약 4,950만원 · 하이닉스+삼성전자 분할 매수"),
    ("buy",  "코스피 현재 대비 30% 이상 하락 → 추가 30%",      "→ 잔여 40%는 항상 보유 유지"),
    ("buy",  "이란 협상 결렬 + 시장 급락 시",                   "→ 가장 강력한 매수 기회 · 3회 분할 진입"),
]



def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        _migrate(conn)
        _seed_if_empty(conn)
    seed_snapshots()
    sync_api_cache()


def _migrate(conn):
    """idempotent 스키마 마이그레이션."""
    snap_cols = {r[1] for r in conn.execute("PRAGMA table_info(snapshot_dates)").fetchall()}
    if "tax_krw" not in snap_cols:
        conn.execute("ALTER TABLE snapshot_dates ADD COLUMN tax_krw REAL NOT NULL DEFAULT 0")

    hold_cols = {r[1] for r in conn.execute("PRAGMA table_info(holdings)").fetchall()}
    if "status" in hold_cols:
        conn.execute("ALTER TABLE holdings DROP COLUMN status")
    if "memo" in hold_cols:
        conn.execute("ALTER TABLE holdings DROP COLUMN memo")

    ev_cols = {r[1] for r in conn.execute("PRAGMA table_info(events)").fetchall()}
    if "source" not in ev_cols:
        conn.execute("ALTER TABLE events ADD COLUMN source TEXT NOT NULL DEFAULT 'manual'")

    trade_cols = {r[1] for r in conn.execute("PRAGMA table_info(sold_transactions)").fetchall()}
    if "tax" not in trade_cols:
        conn.execute("ALTER TABLE sold_transactions ADD COLUMN tax REAL NOT NULL DEFAULT 0")

    # triggers.event_date 의미 변경 (텍스트 추출 → 파일명 날짜) — 기존 데이터 초기화
    row = conn.execute("SELECT COUNT(*) FROM triggers WHERE event_date NOT LIKE '____-__-__%' OR event_date IS NULL").fetchone()
    if row and row[0] > 0:
        conn.execute("DELETE FROM triggers")


def _seed_if_empty(conn):
    if conn.execute("SELECT COUNT(*) FROM holdings").fetchone()[0] > 0:
        return

    toml_data = tomllib.loads(PORTFOLIO_TOML.read_text(encoding="utf-8"))
    accounts = toml_data.get("accounts", {})

    for acct_name, acct in accounts.items():
        for h in acct.get("holdings", []):
            conn.execute(
                "INSERT INTO holdings (account, ticker, name, market, qty, avg_price) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (acct_name, h["ticker"], h["name"], h["market"],
                 h["qty"], h["avg_price"]),
            )

        cash = acct.get("cash", {})
        for currency in ("KRW", "USD"):
            amount = cash.get(currency, 0)
            if amount:
                conn.execute(
                    "INSERT INTO cash (account, currency, amount, memo) VALUES (?, ?, ?, ?)",
                    (acct_name, currency, amount, cash.get("memo", "")),
                )

    if conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0] == 0:
        conn.executemany(
            "INSERT INTO signals (type, text, hint) VALUES (?, ?, ?)", SEED_SIGNALS
        )

    if conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0:
        _insert_events_from_toml(conn)


# ── Events helpers ────────────────────────────────────────────────────────────

def _insert_events_from_toml(conn):
    toml_data = tomllib.loads(EVENTS_TOML.read_text(encoding="utf-8"))
    rows = [
        (e["date"], e["importance"], e["name"], e.get("scenarios", ""))
        for e in toml_data.get("events", [])
    ]
    conn.executemany(
        "INSERT INTO events (date, importance, name, scenarios) VALUES (?, ?, ?, ?)", rows
    )


def reseed_events():
    with get_conn() as conn:
        conn.execute("DELETE FROM events")
        _insert_events_from_toml(conn)
    backup_db()


# ── API cache sync ────────────────────────────────────────────────────────────

TICKER_NAME_MAP = {
    "NVDA": "엔비디아", "GOOGL": "Google(Alphabet)", "VOO": "VOO(S&P500 ETF)",
    "SMR": "NuScale Power", "AAPL": "애플", "MSFT": "마이크로소프트",
    "AMZN": "아마존", "META": "Meta", "TSLA": "테슬라",
}


def sync_api_cache() -> dict:
    """history/api_cache.json → events + news_sentiment 테이블 동기화."""
    if not API_CACHE.exists():
        return {"status": "no_file"}

    data = json.loads(API_CACHE.read_text(encoding="utf-8"))
    fetched_week = data.get("generated_at", "")
    ev_inserted = ns_inserted = 0

    with get_conn() as conn:
        # earnings_events → events 테이블 (date+name 중복 스킵)
        for e in data.get("earnings_events", []):
            existing = conn.execute(
                "SELECT id FROM events WHERE date = ? AND name = ?",
                (e["date"], e["name"]),
            ).fetchone()
            if not existing:
                conn.execute(
                    "INSERT INTO events (date, importance, name, scenarios, source) "
                    "VALUES (?, ?, ?, ?, 'api')",
                    (e["date"], e.get("importance", "MID"), e["name"],
                     f"EPS 예상: ${e['eps_est']}" if e.get("eps_est") else ""),
                )
                ev_inserted += 1

        # news_sentiment → fetched_week 단위 교체
        existing_week = conn.execute(
            "SELECT fetched_week FROM news_sentiment LIMIT 1"
        ).fetchone()
        if existing_week and existing_week[0] == fetched_week:
            pass  # 같은 주 → 스킵
        else:
            conn.execute("DELETE FROM news_sentiment")
            for item in data.get("news_sentiment", []):
                conn.execute(
                    "INSERT INTO news_sentiment (fetched_week, title, source, label, tickers) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (fetched_week, item["title"], item["source"],
                     item["label"], item.get("tickers", "")),
                )
                ns_inserted += 1

    backup_db()
    return {"status": "ok", "ev_inserted": ev_inserted, "ns_inserted": ns_inserted}


def get_news_sentiment() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM news_sentiment ORDER BY id"
        ).fetchall()
    return [dict(r) for r in rows]


# ── Holdings ──────────────────────────────────────────────────────────────────

def get_holdings(market=None):
    with get_conn() as conn:
        if market:
            rows = conn.execute(
                "SELECT * FROM holdings WHERE market = ? ORDER BY account, id", (market,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM holdings ORDER BY account, id"
            ).fetchall()
    return [dict(r) for r in rows]


# ── Cash ──────────────────────────────────────────────────────────────────────

def get_cash():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM cash ORDER BY account, currency").fetchall()
    return [dict(r) for r in rows]


def get_cash_totals():
    """계좌를 합산한 통화별 총액 반환."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT currency, SUM(amount) as total FROM cash GROUP BY currency"
        ).fetchall()
    return {r["currency"]: r["total"] for r in rows}


# ── Signals ───────────────────────────────────────────────────────────────────

def get_signals():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM signals ORDER BY type DESC, id").fetchall()
    return [dict(r) for r in rows]


def toggle_signal(signal_id):
    with get_conn() as conn:
        conn.execute(
            "UPDATE signals SET checked = CASE WHEN checked = 1 THEN 0 ELSE 1 END WHERE id = ?",
            (signal_id,),
        )
        row = conn.execute("SELECT * FROM signals WHERE id = ?", (signal_id,)).fetchone()
    return dict(row) if row else None


# ── Events ────────────────────────────────────────────────────────────────────

def get_events(date_from: str = None, date_to: str = None):
    with get_conn() as conn:
        if date_from and date_to:
            rows = conn.execute(
                "SELECT * FROM events WHERE date >= ? AND date <= ? ORDER BY date",
                (date_from, date_to),
            ).fetchall()
        elif date_from:
            rows = conn.execute(
                "SELECT * FROM events WHERE date >= ? ORDER BY date", (date_from,)
            ).fetchall()
        elif date_to:
            rows = conn.execute(
                "SELECT * FROM events WHERE date <= ? ORDER BY date", (date_to,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM events ORDER BY date").fetchall()
    return [dict(r) for r in rows]


# ── Price cache ───────────────────────────────────────────────────────────────

def get_cached_price(ticker):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM price_cache WHERE ticker = ?", (ticker,)
        ).fetchone()
    return dict(row) if row else None


def upsert_price(ticker, market, price):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO price_cache (ticker, market, price, updated_at) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(ticker) DO UPDATE SET price = excluded.price, updated_at = excluded.updated_at",
            (ticker, market, price, now),
        )


def get_history_price(ticker, period='20d'):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM price_history WHERE ticker = ? AND period = ?", (ticker, period)
        ).fetchone()
    return dict(row) if row else None


def upsert_history_price(ticker, period, price):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO price_history (ticker, period, price, updated_at) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(ticker, period) DO UPDATE SET price = excluded.price, updated_at = excluded.updated_at",
            (ticker, period, price, now),
        )


# ── Snapshots ─────────────────────────────────────────────────────────────────

def seed_snapshots():
    """portfolio.toml의 현재 상태로 스냅샷 계산 → snapshot_dates + snapshot_accounts INSERT.

    같은 날짜가 이미 존재하면 삽입하지 않음 (freeze). 날짜를 바꿀 때마다 새 스냅샷 누적.
    계좌별 평가금액 = Σ(qty × price_cache[ticker]) + cash.KRW + cash.USD × rate
    price_cache 미조회 시 avg_price 폴백, 환율 미조회 시 1400 폴백.
    성공 시 JSON 출력용 dict 반환, date 없으면 None 반환.
    """
    toml_data = tomllib.loads(PORTFOLIO_TOML.read_text(encoding="utf-8"))
    meta = toml_data.get("meta", {})
    date = str(meta.get("updated", "")).strip()
    if not date:
        return {"status": "error", "reason": "date_missing"}

    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', date):
        return {"status": "error", "reason": "invalid_date", "date": date}
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return {"status": "error", "reason": "invalid_date", "date": date}

    salary   = meta.get("salary_krw", 0)
    spending = meta.get("spending_krw", 0)
    tax      = meta.get("tax_krw", 0)
    accounts = toml_data.get("accounts", {})
    acct_values = {}

    with get_conn() as conn:
        row = conn.execute(
            "SELECT price FROM price_cache WHERE ticker = '_USDKRW'"
        ).fetchone()
        rate = row["price"] if row else 1400.0

        price_map = {
            r["ticker"]: r["price"]
            for r in conn.execute("SELECT ticker, price FROM price_cache").fetchall()
        }

        conn.execute(
            "INSERT INTO snapshot_dates (date, salary_krw, spending_krw, tax_krw) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(date) DO NOTHING",
            (date, salary, spending, tax),
        )

        acct_detail = {}
        for acct_name, acct in accounts.items():
            detail = {}
            value = 0.0
            for h in acct.get("holdings", []):
                price  = price_map.get(h["ticker"], h.get("avg_price", 0))
                qty    = h.get("qty", 0)
                amount = qty * price
                if h.get("market") == "US":
                    amount *= rate
                value += amount
                detail[h["name"]] = round(amount)

            cash = acct.get("cash", {})
            cash_krw = cash.get("KRW", 0) + cash.get("USD", 0) * rate
            value += cash_krw
            if cash_krw:
                detail["현금"] = round(cash_krw)

            acct_values[acct_name] = round(value)
            acct_detail[acct_name] = {"총합": round(value), **detail}
            conn.execute(
                "INSERT INTO snapshot_accounts (date, account, value_krw) VALUES (?, ?, ?) "
                "ON CONFLICT(date, account) DO NOTHING",
                (date, acct_name, round(value)),
            )

    backup_db()
    return {
        "date":         date,
        "salary_krw":   salary,
        "spending_krw": spending,
        "tax_krw":      tax,
        "accounts":     acct_detail,
        "total":        sum(acct_values.values()),
    }


def reseed_holdings():
    """holdings + cash만 재시드. snapshot 테이블은 건드리지 않음."""
    toml_data = tomllib.loads(PORTFOLIO_TOML.read_text(encoding="utf-8"))
    accounts = toml_data.get("accounts", {})
    with get_conn() as conn:
        conn.execute("DELETE FROM holdings")
        conn.execute("DELETE FROM cash")
        for acct_name, acct in accounts.items():
            for h in acct.get("holdings", []):
                conn.execute(
                    "INSERT INTO holdings (account, ticker, name, market, qty, avg_price) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (acct_name, h["ticker"], h["name"], h["market"],
                     h["qty"], h["avg_price"]),
                )
            cash = acct.get("cash", {})
            for currency in ("KRW", "USD"):
                amount = cash.get(currency, 0)
                if amount:
                    conn.execute(
                        "INSERT INTO cash (account, currency, amount, memo) VALUES (?, ?, ?, ?)",
                        (acct_name, currency, amount, cash.get("memo", "")),
                    )
    backup_db()


def get_snapshot_table(date_from: str = None, date_to: str = None) -> dict:
    """날짜 범위 내 스냅샷을 pivot 구조로 반환. 미지정 시 전체."""
    with get_conn() as conn:
        if date_from and date_to:
            date_rows = conn.execute(
                "SELECT date, salary_krw, spending_krw, tax_krw FROM snapshot_dates "
                "WHERE date >= ? AND date <= ? ORDER BY date",
                (date_from, date_to),
            ).fetchall()
        elif date_from:
            date_rows = conn.execute(
                "SELECT date, salary_krw, spending_krw, tax_krw FROM snapshot_dates "
                "WHERE date >= ? ORDER BY date",
                (date_from,),
            ).fetchall()
        elif date_to:
            date_rows = conn.execute(
                "SELECT date, salary_krw, spending_krw, tax_krw FROM snapshot_dates "
                "WHERE date <= ? ORDER BY date",
                (date_to,),
            ).fetchall()
        else:
            date_rows = conn.execute(
                "SELECT date, salary_krw, spending_krw, tax_krw FROM snapshot_dates ORDER BY date",
            ).fetchall()
        if not date_rows:
            return {"dates": [], "accounts": [], "totals": [], "salary": [],
                    "spending": [], "tax": [], "net_savings": [], "delta": None}

        dates    = [r["date"] for r in date_rows]
        salary   = [r["salary_krw"] for r in date_rows]
        spending = [r["spending_krw"] for r in date_rows]
        tax      = [r["tax_krw"] for r in date_rows]

        acct_rows = conn.execute(
            f"SELECT account FROM snapshot_accounts WHERE date IN ({','.join('?' * len(dates))}) "
            "GROUP BY account ORDER BY account",
            dates,
        ).fetchall()
        account_names = [r["account"] for r in acct_rows]

        val_rows = conn.execute(
            f"SELECT date, account, value_krw FROM snapshot_accounts "
            f"WHERE date IN ({','.join('?' * len(dates))})",
            dates,
        ).fetchall()

    val_map = {}
    for r in val_rows:
        val_map[(r["date"], r["account"])] = r["value_krw"]

    accounts = []
    for acct in account_names:
        values = [val_map.get((d, acct), 0) for d in dates]
        accounts.append({"name": acct, "values": values})

    totals = [sum(val_map.get((d, a), 0) for a in account_names) for d in dates]
    net_savings = [salary[i] - spending[i] - tax[i] for i in range(len(dates))]

    delta = None
    if len(dates) >= 2:
        first, last = totals[0], totals[-1]
        diff = last - first
        pct = round(diff / first * 100, 2) if first else 0
        delta = {"from": dates[0], "to": dates[-1], "amount": round(diff), "pct": pct}

    return {
        "dates":       dates,
        "accounts":    accounts,
        "totals":      [round(t) for t in totals],
        "salary":      [round(s) for s in salary],
        "spending":    [round(s) for s in spending],
        "tax":         [round(t) for t in tax],
        "net_savings": [round(s) for s in net_savings],
        "delta":       delta,
    }


# ── Sold Transactions ─────────────────────────────────────────────────────────

def upsert_trades(trades: list) -> None:
    """portfolio.toml [[trades]] 섹션을 sold_transactions 테이블에 전량 교체."""
    with get_conn() as conn:
        conn.execute("DELETE FROM sold_transactions")
        conn.executemany(
            "INSERT INTO sold_transactions "
            "(account, ticker, name, market, qty, avg_price, sell_price, sell_date, tax) "
            "VALUES (:account, :ticker, :name, :market, :qty, :avg_price, :sell_price, :sell_date, :tax)",
            [{**t, "tax": t.get("tax", 0)} for t in trades],
        )


def get_trades(from_date: str = None, to_date: str = None) -> dict:
    """매도 내역 조회. net_pnl = (sell_price - avg_price) * qty - tax."""
    clauses, params = [], []
    if from_date:
        clauses.append("sell_date >= ?"); params.append(from_date)
    if to_date:
        clauses.append("sell_date <= ?"); params.append(to_date)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT * FROM sold_transactions {where} ORDER BY sell_date DESC",
            params,
        ).fetchall()
    result = []
    for r in rows:
        gross = (r["sell_price"] - r["avg_price"]) * r["qty"]
        tax   = r["tax"]
        pct   = round((r["sell_price"] - r["avg_price"]) / r["avg_price"] * 100, 2) if r["avg_price"] else 0
        result.append({**dict(r), "realized_pnl": round(gross), "tax": round(tax), "net_pnl": round(gross - tax), "pct": pct})
    total_pnl = sum(t["net_pnl"] for t in result)
    return {"trades": result, "total_pnl": round(total_pnl)}


# ── Triggers ──────────────────────────────────────────────────────────────────

_CIRCLED = '①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳'


def parse_trigger_block(text: str) -> list[dict]:
    """보고서 텍스트에서 next_trigger 블록을 파싱."""
    import re
    m = re.search(r'next_trigger:\s*\n(.*?)(?:\n[ \t]*[-━─═=]{3,}|\Z)', text, re.DOTALL)
    if not m:
        return []
    block = m.group(1)
    parts = re.split(r'(?=[ \t]*[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳])', block)
    results = []
    for part in parts:
        part = part.strip()
        if not part or part[0] not in _CIRCLED:
            continue
        idx = _CIRCLED.index(part[0]) + 1
        body = ' '.join(part[1:].split())        # 마커 제거 + 줄바꿈 정리
        arrow = re.search(r'\s*→\s*', body)
        if arrow:
            condition = body[:arrow.start()].strip()
            action    = body[arrow.end():].strip()
        else:
            condition, action = body, None
        results.append({'idx': idx, 'text': body, 'condition': condition, 'action': action})
    return results


def upsert_triggers(source_file: str, file_text: str) -> int:
    """파일 단위 트리거 업서트. checked=1 항목은 보존, checked=0만 교체."""
    from datetime import datetime, timezone
    triggers = parse_trigger_block(file_text)
    base   = source_file.split('/')[-1]
    date_m = re.match(r'\[(\d{4}-\d{2}-\d{2})\]', base)
    file_date = date_m.group(1) if date_m else None
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    with get_conn() as conn:
        dismissed = {r[0] for r in conn.execute(
            "SELECT idx FROM triggers WHERE source_file = ? AND checked = 1", (source_file,)
        ).fetchall()}
        conn.execute("DELETE FROM triggers WHERE source_file = ? AND checked = 0", (source_file,))
        conn.executemany(
            "INSERT INTO triggers (source_file, idx, text, condition, action, event_date, checked, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, 0, ?)",
            [(source_file, t['idx'], t['text'], t['condition'], t['action'], file_date, now)
             for t in triggers if t['idx'] not in dismissed],
        )
    return len(triggers)


def get_triggers() -> list[dict]:
    """미처리(checked=0) 트리거만 반환. 보고서 날짜 내림차순."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM triggers WHERE checked = 0 "
            "ORDER BY event_date DESC, source_file DESC, idx ASC"
        ).fetchall()
    return [dict(r) for r in rows]


def toggle_trigger(trigger_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT checked FROM triggers WHERE id = ?", (trigger_id,)).fetchone()
        if row is None:
            return None
        new_val = 0 if row["checked"] else 1
        conn.execute("UPDATE triggers SET checked = ? WHERE id = ?", (new_val, trigger_id))
        return dict(conn.execute("SELECT * FROM triggers WHERE id = ?", (trigger_id,)).fetchone())


if __name__ == "__main__":
    init_db()
    print("DB initialized:", DB_PATH)
    print("Holdings:", len(get_holdings()))
    print("Cash rows:", len(get_cash()))
    print("Signals:", len(get_signals()))
    print("Events:", len(get_events()))
