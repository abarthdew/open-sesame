import time
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
load_dotenv()

CACHE_TTL_SECONDS = 300    # 5분
HISTORY_TTL_SECONDS = 86400  # 24시간

def _is_stale(updated_at: str, ttl: int = CACHE_TTL_SECONDS) -> bool:
    try:
        ts = datetime.fromisoformat(updated_at)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - ts).total_seconds() > ttl
    except Exception:
        return True


def fetch_kr_price(ticker: str) -> float | None:
    """pykrx로 한국 주식 당일 종가 조회."""
    try:
        from pykrx import stock
        today = datetime.now().strftime("%Y%m%d")
        df = stock.get_market_ohlcv_by_date(today, today, ticker)
        if df.empty:
            # 장 마감 전이거나 휴장일이면 최근 거래일 데이터 사용
            one_week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")
            df = stock.get_market_ohlcv_by_date(one_week_ago, today, ticker)
        if not df.empty:
            return float(df["종가"].iloc[-1])
    except Exception:
        pass
    return None


def fetch_us_price(ticker: str) -> float | None:
    """yfinance로 미국 주식 현재가 조회."""
    try:
        import yfinance as yf
        info = yf.Ticker(ticker).fast_info
        price = info.get("lastPrice") or info.get("regularMarketPrice")
        if price:
            return float(price)
    except Exception:
        pass
    return None


def fetch_usd_krw() -> float | None:
    """yfinance로 USD/KRW 환율 조회."""
    try:
        import yfinance as yf
        info = yf.Ticker("KRW=X").fast_info
        rate = info.get("lastPrice") or info.get("regularMarketPrice")
        if rate:
            return float(rate)
    except Exception:
        pass
    return None


def get_price(ticker: str, market: str, force: bool = False) -> float | None:
    """캐시 확인 후 신선하면 캐시값 반환, 만료/없으면 수집 후 저장."""
    from data.db import get_cached_price, upsert_price

    if not force:
        cached = get_cached_price(ticker)
        if cached and not _is_stale(cached["updated_at"]):
            return cached["price"]

    if market == "KR":
        price = fetch_kr_price(ticker)
    else:
        price = fetch_us_price(ticker)

    if price is not None:
        upsert_price(ticker, market, price)

    return price


def get_exchange_rate(force: bool = False) -> float:
    """USD/KRW 환율. 캐시 TTL 적용, 실패 시 1400 폴백."""
    from data.db import get_cached_price, upsert_price

    RATE_TICKER = "_USDKRW"

    if not force:
        cached = get_cached_price(RATE_TICKER)
        if cached and not _is_stale(cached["updated_at"]):
            return cached["price"]

    rate = fetch_usd_krw()
    if rate is not None:
        upsert_price(RATE_TICKER, "FX", rate)
        return rate

    # 캐시가 낡았어도 있으면 사용
    cached = get_cached_price(RATE_TICKER)
    if cached:
        return cached["price"]

    return 1400.0  # 최후 폴백


def fetch_kr_price_20d(ticker: str) -> float | None:
    """pykrx로 20거래일 전 종가 조회."""
    try:
        from pykrx import stock
        end = datetime.now()
        start = end - timedelta(days=35)
        df = stock.get_market_ohlcv_by_date(
            start.strftime("%Y%m%d"), end.strftime("%Y%m%d"), ticker
        )
        if not df.empty:
            idx = -20 if len(df) >= 20 else 0
            return float(df["종가"].iloc[idx])
    except Exception:
        pass
    return None


def fetch_us_price_20d(ticker: str) -> float | None:
    """yfinance로 20거래일 전 종가 조회."""
    try:
        import yfinance as yf
        hist = yf.Ticker(ticker).history(period='2mo')
        if not hist.empty:
            idx = -20 if len(hist) >= 20 else 0
            return float(hist['Close'].iloc[idx])
    except Exception:
        pass
    return None


def get_price_20d(ticker: str, market: str, force: bool = False) -> float | None:
    """20거래일 전 가격. 24시간 TTL 캐시."""
    from data.db import get_history_price, upsert_history_price

    if not force:
        cached = get_history_price(ticker, '20d')
        if cached and not _is_stale(cached['updated_at'], ttl=HISTORY_TTL_SECONDS):
            return cached['price']

    price = fetch_kr_price_20d(ticker) if market == 'KR' else fetch_us_price_20d(ticker)
    if price is not None:
        upsert_history_price(ticker, '20d', price)
    return price


if __name__ == "__main__":
    from data.db import init_db, get_holdings
    init_db()

    print("환율 USD/KRW:", get_exchange_rate(force=True))

    holdings = get_holdings()
    for h in holdings[:5]:
        price = get_price(h["ticker"], h["market"], force=True)
        print(f"  {h['name']} ({h['ticker']}): {price}")
