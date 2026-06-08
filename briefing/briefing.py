"""
briefing/briefing.py — Slack 브리핑 생성기

Usage:
    python -m briefing.briefing [morning|kr_close|us_open|weekly]
"""

import json
import sys
import os
import contextlib
import requests
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore

import yfinance as yf
with open(os.devnull, "w") as _devnull, contextlib.redirect_stdout(_devnull):
    from pykrx import stock as krx

from briefing.slack import send

PORTFOLIO_PATH = Path(__file__).parent.parent / "history" / "portfolio.toml"
API_CACHE_PATH = Path(__file__).parent.parent / "history" / "api_cache.json"

TICKER_NAME_MAP = {
    "NVDA": "엔비디아", "GOOGL": "Google(Alphabet)", "VOO": "VOO(S&P500 ETF)",
    "SMR": "NuScale Power", "AAPL": "애플", "MSFT": "마이크로소프트",
    "AMZN": "아마존", "META": "Meta", "TSLA": "테슬라",
}
DAY_KO = ["월", "화", "수", "목", "금", "토", "일"]


# ── 포트폴리오 로드 ────────────────────────────────────────────────────────────

def load_portfolio() -> dict:
    with open(PORTFOLIO_PATH, "rb") as f:
        return tomllib.load(f)


def _tickers(pf: dict, market: str) -> list[str]:
    seen, result = set(), []
    for acct in pf.get("accounts", {}).values():
        for h in acct.get("holdings", []):
            t = h.get("ticker", "")
            if h.get("market") == market and t not in seen:
                seen.add(t)
                result.append(t)
    return result


# ── 가격 수집 ─────────────────────────────────────────────────────────────────

def _hist(ticker_yf: str, days: int = 10):
    try:
        return yf.Ticker(ticker_yf).history(period=f"{days}d")
    except Exception:
        return None


def fetch_rate() -> tuple[float | None, float | None]:
    h = _hist("USDKRW=X", 5)
    if h is None or h.empty:
        return None, None
    price = h["Close"].iloc[-1]
    prev  = h["Close"].iloc[-2] if len(h) >= 2 else price
    return round(price), round((price / prev - 1) * 100, 2)


def fetch_us(ticker: str, days: int = 5) -> tuple[float | None, float | None]:
    h = _hist(ticker, days)
    if h is None or h.empty:
        return None, None
    price = h["Close"].iloc[-1]
    prev  = h["Close"].iloc[-2] if len(h) >= 2 else price
    return round(price, 2), round((price / prev - 1) * 100, 2)


def _kr_ohlcv(ticker: str, days: int = 20):
    try:
        today = datetime.now().strftime("%Y%m%d")
        since = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
        df = krx.get_market_ohlcv_by_date(since, today, ticker)
        return df if not df.empty else None
    except Exception:
        return None


def fetch_kr(ticker: str) -> tuple[int | None, float | None]:
    df = _kr_ohlcv(ticker)
    if df is None or len(df) < 1:
        return None, None
    price = int(df["종가"].iloc[-1])
    chg   = round((df["종가"].iloc[-1] / df["종가"].iloc[-2] - 1) * 100, 2) if len(df) >= 2 else None
    return price, chg


def fetch_kr_idx(code: str) -> tuple[float | None, float | None]:
    try:
        today = datetime.now().strftime("%Y%m%d")
        since = (datetime.now() - timedelta(days=14)).strftime("%Y%m%d")
        df = krx.get_index_ohlcv_by_date(since, today, code)
        if not df.empty:
            price = df["종가"].iloc[-1]
            prev  = df["종가"].iloc[-2] if len(df) >= 2 else price
            return round(price, 2), round((price / prev - 1) * 100, 2)
    except Exception:
        pass
    yf_map = {"1001": "^KS11", "2001": "^KQ11"}
    yf_ticker = yf_map.get(code)
    if yf_ticker:
        h = _hist(yf_ticker, 5)
        if h is not None and not h.empty:
            price = h["Close"].iloc[-1]
            prev  = h["Close"].iloc[-2] if len(h) >= 2 else price
            return round(price, 2), round((price / prev - 1) * 100, 2)
    return None, None


def fetch_us_weekly(ticker: str) -> float | None:
    h = _hist(ticker, 10)
    if h is None or len(h) < 6:
        return None
    return round((h["Close"].iloc[-1] / h["Close"].iloc[-6] - 1) * 100, 2)


# ── 뉴스 / 실적 / 공시 / 감성 ──────────────────────────────────────────────────

def fetch_us_news(tickers: list[str], n: int = 2) -> list[dict]:
    """yfinance 뉴스 헤드라인 (중복 제거, 최신 n건)"""
    all_news, seen = [], set()
    for ticker in tickers:
        try:
            for raw in (yf.Ticker(ticker).news or [])[:3]:
                # yfinance 버전별 구조 차이 처리
                item = raw.get("content", raw)
                title = item.get("title", "")
                pub   = item.get("provider", {})
                publisher = pub.get("displayName", "") if isinstance(pub, dict) else item.get("publisher", "")
                ts = item.get("pubDate", 0) or item.get("providerPublishTime", 0)
                if title and title not in seen:
                    seen.add(title)
                    all_news.append({"title": title, "publisher": publisher, "time": ts})
        except Exception:
            pass
    all_news.sort(key=lambda x: x["time"], reverse=True)
    return all_news[:n]


def fetch_earnings(tickers: list[str], days: int = 7) -> list[dict]:
    """yfinance 실적 발표 일정 (향후 days일 이내 미발표 건)"""
    results = []
    today   = datetime.now().date()
    cutoff  = (datetime.now() + timedelta(days=days)).date()
    for ticker in tickers:
        try:
            df = yf.Ticker(ticker).get_earnings_dates(limit=6)
            if df is None or df.empty:
                continue
            for idx_dt, row in df.iterrows():
                reported = row.get("Reported EPS")
                # NaN 체크 (reported == reported → False if NaN)
                if reported is not None and reported == reported:
                    continue
                d = idx_dt.date() if hasattr(idx_dt, "date") else idx_dt
                if today <= d <= cutoff:
                    eps = row.get("EPS Estimate")
                    results.append({
                        "ticker":  ticker,
                        "date":    d,
                        "eps_est": round(float(eps), 2) if eps and eps == eps else None,
                    })
        except Exception:
            pass
    results.sort(key=lambda x: x["date"])
    return results


def fetch_dart(kr_tickers: list[str], date_from: str, date_to: str) -> list[dict]:
    """Open DART 보유 KR 종목 공시 목록"""
    api_key = os.environ.get("DART_API_KEY", "")
    if not api_key:
        return []
    results, seen = [], set()
    for ticker in kr_tickers:
        if not ticker.isdigit():
            continue
        try:
            r = requests.get(
                "https://opendart.fss.or.kr/api/list.json",
                params={
                    "crtfc_key": api_key,
                    "stock_code": ticker,
                    "bgn_de":    date_from,
                    "end_de":    date_to,
                    "page_count": 5,
                },
                timeout=10,
            )
            data = r.json()
            if data.get("status") != "000":
                continue
            for item in data.get("list", []):
                key = item["rcept_no"]
                if key not in seen:
                    seen.add(key)
                    results.append({
                        "corp_name": item["corp_name"],
                        "report_nm": item["report_nm"],
                        "date":      item["rcept_dt"],
                    })
        except Exception:
            pass
    results.sort(key=lambda x: x["date"], reverse=True)
    return results[:5]


def fetch_av_sentiment(us_tickers: list[str]) -> list[dict]:
    """Alpha Vantage 뉴스 감성 분석 (주간 회고 전용, API 1회 소모)"""
    api_key = os.environ.get("ALPHA_VANTAGE_KEY", "")
    if not api_key:
        return []
    try:
        r = requests.get(
            "https://www.alphavantage.co/query",
            params={
                "function": "NEWS_SENTIMENT",
                "tickers":  ",".join(us_tickers),
                "limit":    5,
                "apikey":   api_key,
            },
            timeout=15,
        )
        data = r.json()
        results = []
        for item in data.get("feed", [])[:5]:
            results.append({
                "title":     item.get("title", ""),
                "source":    item.get("source", ""),
                "sentiment": item.get("overall_sentiment_label", ""),
            })
        return results
    except Exception:
        return []


# ── 포맷 헬퍼 ─────────────────────────────────────────────────────────────────

def _pct(v: float | None) -> str:
    if v is None:
        return "—"
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:.1f}%"


def _cum(price: float | None, avg: float | None) -> str:
    if price is None or avg is None or avg == 0:
        return "—"
    return _pct((price / avg - 1) * 100)


def _kr(v: int | None) -> str:
    return f"{v:,}" if v else "—"


def _us(v: float | None) -> str:
    return f"${v:,.2f}" if v else "—"


def _now_label() -> str:
    now = datetime.now()
    return now.strftime(f"%m/%d {DAY_KO[now.weekday()]}")


def _sentiment_emoji(label: str) -> str:
    label = label.lower()
    if "bullish" in label:
        return "📈"
    if "bearish" in label:
        return "📉"
    return "➡️"


# ── 브리핑 빌더 ───────────────────────────────────────────────────────────────

def morning() -> str:
    pf = load_portfolio()
    accounts   = pf.get("accounts", {})
    us_tickers = _tickers(pf, "US")

    rate, rate_chg = fetch_rate()
    sp,  sp_chg   = fetch_us("^GSPC")
    nq,  nq_chg   = fetch_us("^IXIC")
    dj,  dj_chg   = fetch_us("^DJI")

    lines = [
        f"📊 *[{_now_label()}] 모닝 브리핑*\n",
        f"💱 환율  *{_kr(rate)}원*  {_pct(rate_chg)}\n",
        "*🇺🇸 미국 전일 마감*",
        "```",
        f"S&P500  {sp:>8,.0f}  {_pct(sp_chg):>7}" if sp else "S&P500  —",
        f"NASDAQ  {nq:>8,.0f}  {_pct(nq_chg):>7}" if nq else "NASDAQ  —",
        f"DOW     {dj:>8,.0f}  {_pct(dj_chg):>7}" if dj else "DOW     —",
        "```",
    ]

    us_rows = []
    for acct in accounts.values():
        for h in acct.get("holdings", []):
            if h.get("market") == "US":
                price, chg = fetch_us(h["ticker"])
                us_rows.append((h["ticker"], price, chg, h.get("avg_price")))

    if us_rows:
        lines += ["\n*📈 보유 미국 종목 (전일 등락)*", "```"]
        for ticker, price, chg, avg in us_rows:
            lines.append(f"{ticker:<5}  {_us(price):>9}  {_pct(chg):>7}  (누적 {_cum(price, avg)})")
        lines.append("```")

    earnings = fetch_earnings(us_tickers, days=1)
    if earnings:
        lines.append("\n*📅 오늘의 일정*")
        for e in earnings:
            eps = f"  EPS 예상 {e['eps_est']}" if e["eps_est"] else ""
            lines.append(f"  • {e['ticker']} 실적 발표 (장 후{eps})")

    news = fetch_us_news(us_tickers, n=2)
    if news:
        lines.append("\n*⚠️ 헤드라인*")
        for item in news:
            lines.append(f"  • \"{item['title']}\" — {item['publisher']}")

    return "\n".join(lines)


def kr_close() -> str:
    pf = load_portfolio()
    accounts   = pf.get("accounts", {})
    kr_tickers = _tickers(pf, "KR")

    rate, _ = fetch_rate()
    rate = rate or 1400

    kospi, kospi_chg   = fetch_kr_idx("1001")
    kosdaq, kosdaq_chg = fetch_kr_idx("2001")

    lines = [
        f"🔔 *[{_now_label()}] 한국 장 마감*\n",
        "*📉 지수*",
        "```",
        f"KOSPI   {kospi:>7,.2f}  {_pct(kospi_chg):>7}" if kospi else "KOSPI   —",
        f"KOSDAQ  {kosdaq:>7,.2f}  {_pct(kosdaq_chg):>7}" if kosdaq else "KOSDAQ  —",
        "```",
    ]

    kr_rows = []
    total_kr = 0.0
    for acct in accounts.values():
        for h in acct.get("holdings", []):
            if h.get("market") == "KR":
                price, chg = fetch_kr(h["ticker"])
                kr_rows.append((h.get("name", h["ticker"]), price, chg,
                                 _cum(price, h.get("avg_price")), h.get("qty", 0)))
                if price:
                    total_kr += price * h.get("qty", 0)

    if kr_rows:
        lines += ["\n*💼 보유 종목*", "```"]
        max_name = max(len(r[0]) for r in kr_rows)
        for name, price, chg, cum, _ in kr_rows:
            lines.append(f"{name:<{max_name}}  {_kr(price):>9}원  {_pct(chg):>7}  누적 {cum}")
        lines.append("```")

    today_str = datetime.now().strftime("%Y%m%d")
    disclosures = fetch_dart(kr_tickers, today_str, today_str)
    if disclosures:
        lines.append("\n*📋 오늘의 공시*")
        for d in disclosures:
            lines.append(f"  • {d['corp_name']} — {d['report_nm']}")

    cash_krw = sum(
        v.get("cash", {}).get("KRW", 0) + v.get("cash", {}).get("USD", 0) * rate
        for v in accounts.values()
    )
    lines.append(f"\n💰 *총 포트폴리오 (원화환산): {(total_kr + cash_krw) / 1e8:.2f}억원*")

    return "\n".join(lines)


def us_open() -> str:
    pf = load_portfolio()
    accounts   = pf.get("accounts", {})
    us_tickers = _tickers(pf, "US")

    rate, rate_chg = fetch_rate()
    sp, sp_chg     = fetch_us("^GSPC")
    nq, nq_chg     = fetch_us("^IXIC")

    lines = [
        f"🌙 *[{_now_label()}] 미국 장 개시*\n",
        f"💱 환율  *{_kr(rate)}원*  {_pct(rate_chg)}\n",
        "*📊 미국 주요 지수 (전일 종가)*",
        "```",
        f"S&P500  {sp:>8,.0f}  {_pct(sp_chg):>7}" if sp else "S&P500  —",
        f"NASDAQ  {nq:>8,.0f}  {_pct(nq_chg):>7}" if nq else "NASDAQ  —",
        "```",
    ]

    us_rows = []
    for acct in accounts.values():
        for h in acct.get("holdings", []):
            if h.get("market") == "US":
                price, chg = fetch_us(h["ticker"])
                us_rows.append((h["ticker"], price, chg, h.get("avg_price")))

    if us_rows:
        lines += ["\n*📈 보유 미국 종목*", "```"]
        for ticker, price, chg, avg in us_rows:
            lines.append(f"{ticker:<5}  {_us(price):>9}  {_pct(chg):>7}  (누적 {_cum(price, avg)})")
        lines.append("```")

    earnings = fetch_earnings(us_tickers, days=1)
    if earnings:
        lines.append("\n*📅 오늘 밤 주요 일정*")
        for e in earnings:
            eps = f"  EPS 예상 {e['eps_est']}" if e["eps_est"] else ""
            lines.append(f"  • {e['ticker']} 실적 발표 (장 후{eps})")

    news = fetch_us_news(us_tickers, n=2)
    if news:
        lines.append("\n*📰 보유 종목 헤드라인*")
        for item in news:
            lines.append(f"  • \"{item['title']}\" — {item['publisher']}")

    return "\n".join(lines)


def weekly() -> str:
    pf = load_portfolio()
    accounts   = pf.get("accounts", {})
    us_tickers = _tickers(pf, "US")
    kr_tickers = _tickers(pf, "KR")

    now        = datetime.now()
    week_start = (now - timedelta(days=6)).strftime("%m/%d")
    week_end   = now.strftime("%m/%d")

    # 지수 주간 등락
    kospi_w = kosdaq_w = None
    try:
        today = now.strftime("%Y%m%d")
        since = (now - timedelta(days=20)).strftime("%Y%m%d")
        df_k = krx.get_index_ohlcv_by_date(since, today, "1001")
        df_q = krx.get_index_ohlcv_by_date(since, today, "2001")
        if len(df_k) >= 6:
            kospi_w  = round((df_k["종가"].iloc[-1] / df_k["종가"].iloc[-6] - 1) * 100, 2)
        if len(df_q) >= 6:
            kosdaq_w = round((df_q["종가"].iloc[-1] / df_q["종가"].iloc[-6] - 1) * 100, 2)
    except Exception:
        pass
    if kospi_w is None:
        kospi_w = fetch_us_weekly("^KS11")
    if kosdaq_w is None:
        kosdaq_w = fetch_us_weekly("^KQ11")

    sp_w = fetch_us_weekly("^GSPC")
    nq_w = fetch_us_weekly("^IXIC")

    rate, _ = fetch_rate()
    rate = rate or 1400

    lines = [
        f"📆 *주간 회고 [{week_start} ~ {week_end}]*\n",
        "*📊 지수 주간 등락*",
        "```",
        f"KOSPI   {_pct(kospi_w):>7}",
        f"KOSDAQ  {_pct(kosdaq_w):>7}",
        f"S&P500  {_pct(sp_w):>7}",
        f"NASDAQ  {_pct(nq_w):>7}",
        "```",
    ]

    # 포트폴리오 총합
    total = 0.0
    for acct in accounts.values():
        for h in acct.get("holdings", []):
            if h.get("market") == "KR":
                price, _ = fetch_kr(h["ticker"])
                if price:
                    total += price * h.get("qty", 0)
            else:
                price, _ = fetch_us(h["ticker"])
                if price:
                    total += price * h.get("qty", 0) * rate
        cash = acct.get("cash", {})
        total += cash.get("KRW", 0) + cash.get("USD", 0) * rate

    lines.append(f"\n💰 *포트폴리오 총합: {total / 1e8:.2f}억원*")

    # Open DART 이번 주 공시
    week_ago = (now - timedelta(days=7)).strftime("%Y%m%d")
    disclosures = fetch_dart(kr_tickers, week_ago, now.strftime("%Y%m%d"))
    if disclosures:
        lines.append("\n*📋 이번 주 주요 공시 (보유 종목)*")
        for d in disclosures:
            lines.append(f"  • {d['corp_name']} — {d['report_nm']}")

    # 다음 주 실적 발표
    next_earnings = fetch_earnings(us_tickers, days=14)
    if next_earnings:
        lines.append("\n*📅 다음 주 실적 발표*")
        for e in next_earnings:
            eps = f"  EPS 예상 {e['eps_est']}" if e["eps_est"] else ""
            lines.append(f"  • {e['date'].strftime('%m/%d')} {e['ticker']}{eps}")

    # Alpha Vantage 감성 분석 (주간 1회, 1 req 소모)
    sentiment = fetch_av_sentiment(us_tickers)
    if sentiment:
        lines.append("\n*📰 주요 뉴스 감성 (Alpha Vantage)*")
        for item in sentiment:
            emoji = _sentiment_emoji(item["sentiment"])
            lines.append(f"  {emoji} \"{item['title']}\" — {item['source']}")

    # api_cache.json 저장 (DB 임포트용)
    _save_api_cache(us_tickers, next_earnings, sentiment)

    return "\n".join(lines)


def _save_api_cache(us_tickers: list[str], earnings: list[dict], sentiment: list[dict]):
    """weekly 브리핑 데이터를 history/api_cache.json에 저장."""
    today = datetime.now().strftime("%Y-%m-%d")

    earnings_events = []
    for e in earnings:
        ticker = e["ticker"]
        name_ko = TICKER_NAME_MAP.get(ticker, ticker)
        eps_str = f" EPS 예상 ${e['eps_est']}" if e.get("eps_est") else ""
        earnings_events.append({
            "date":       e["date"].strftime("%Y-%m-%d"),
            "ticker":     ticker,
            "name":       f"{name_ko} 실적 발표{eps_str}",
            "importance": "HIGH" if ticker in ("NVDA", "GOOGL", "AAPL", "MSFT") else "MID",
            "eps_est":    e.get("eps_est"),
        })

    news_sentiment = []
    for item in sentiment:
        news_sentiment.append({
            "title":   item.get("title", ""),
            "source":  item.get("source", ""),
            "label":   item.get("sentiment", ""),
            "tickers": ",".join(us_tickers),
        })

    cache = {
        "generated_at":    today,
        "earnings_events": earnings_events,
        "news_sentiment":  news_sentiment,
    }
    API_CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


# ── 진입점 ────────────────────────────────────────────────────────────────────

BRIEFINGS = {
    "morning":  morning,
    "kr_close": kr_close,
    "us_open":  us_open,
    "weekly":   weekly,
}

if __name__ == "__main__":
    kind = sys.argv[1] if len(sys.argv) > 1 else "morning"
    if kind not in BRIEFINGS:
        print(f"Unknown briefing type: {kind}. Choose from {list(BRIEFINGS)}")
        sys.exit(1)
    text = BRIEFINGS[kind]()
    print(text)
    send(text)
