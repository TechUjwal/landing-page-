"""
reconstruct_valuation_history.py
ONE-TIME backfill script. Run locally once, commit the resulting JSON.

For each of 25 indices, fetches:
  - Year-end snapshots: 2019-12-31, 2020-12-31, ..., 2025-12-31, plus latest
  - Quarter-end snapshots: 2023-03-31 → 2025-12-31, plus latest

Logic:
  1. For each target date, walk back to the nearest trading day
  2. Fetch NSE ind_close_all_DDMMYYYY.csv for that date (has close + PE + PB)
  3. Cross-reference with yfinance (for Nasdaq 100 + RSI)
  4. Derive EPS = Close / PE
"""
import requests, json, os, sys, time
from datetime import datetime, timedelta
from io import StringIO

import pandas as pd
import numpy as np
import yfinance as yf

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from index_config import INDICES

OUTPUT = os.path.join(HERE, "data", "valuation_history.json")

NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/csv,*/*;q=0.9",
    "Referer": "https://www.nseindia.com/",
}


def nse_session():
    s = requests.Session()
    s.headers.update(NSE_HEADERS)
    try:
        s.get("https://www.nseindia.com", timeout=10)
        time.sleep(1.0)
    except Exception:
        pass
    return s


def fetch_nse_for_date(session, dt):
    date_str = dt.strftime("%d%m%Y")
    url = f"https://nsearchives.nseindia.com/content/indices/ind_close_all_{date_str}.csv"
    try:
        r = session.get(url, timeout=20)
        if r.status_code != 200 or len(r.content) < 500:
            return None
        df = pd.read_csv(StringIO(r.text))
        out = {}
        for _, row in df.iterrows():
            name = str(row.get("Index Name", "")).strip()
            if not name:
                continue
            try:
                close = float(row["Closing Index Value"])
                pe = float(row["P/E"]) if pd.notna(row["P/E"]) else None
                pb = float(row["P/B"]) if pd.notna(row["P/B"]) else None
            except (KeyError, ValueError, TypeError):
                continue
            out[name] = {"close": close, "pe": pe, "pb": pb}
        return out
    except Exception:
        return None


def walk_back_to_trading_day(session, target_dt, max_back=10):
    """Return the most recent NSE trading day <= target_dt with data available."""
    for back in range(max_back):
        dt = target_dt - timedelta(days=back)
        if dt.weekday() >= 5:
            continue
        data = fetch_nse_for_date(session, dt)
        if data:
            return dt, data
        time.sleep(0.5)
    return None, None


def rsi_14_at(hist, target_date):
    """Compute RSI(14) using all data up to and including target_date."""
    if hist is None or hist.empty:
        return None
    df = hist[hist.index <= pd.Timestamp(target_date)]
    if len(df) < 15:
        return None
    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    val = rsi.iloc[-1]
    return round(float(val), 2) if pd.notna(val) else None


def target_dates_for(start_year):
    """
    Build list of target dates for a single index:
      - Year-ends: Dec 31 of start_year, start_year+1, ..., current_year-1
      - Quarter-ends: Mar/Jun/Sep/Dec end from start_year onwards
      - Plus today's date (date-truncated for clean dedup)
    """
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    cur_year = today.year
    targets = set()
    # Year-ends
    for y in range(start_year, cur_year):
        targets.add(datetime(y, 12, 31))
    # Quarter-ends
    for y in range(start_year, cur_year + 1):
        for m, d in [(3, 31), (6, 30), (9, 30), (12, 31)]:
            dt = datetime(y, m, d)
            if dt <= today:
                targets.add(dt)
    # Latest
    targets.add(today)
    return sorted(targets)


def all_target_dates(indices):
    """Union of target dates across all indices — these are the NSE CSVs we need to fetch."""
    s = set()
    for ix in indices:
        for d in target_dates_for(ix["start_year"]):
            s.add(d)
    return sorted(s)


def main():
    print(f"\n{'='*60}")
    print(f"  Valuation History Reconstruction")
    print(f"{'='*60}\n")

    # Union of all dates we need across all indices (some go back to 2012, others to 2023)
    targets = all_target_dates(INDICES)
    print(f"Targets: {len(targets)} dates from {targets[0].date()} to {targets[-1].date()}")
    print(f"Indices: {len(INDICES)} (range of start years: "
          f"{min(ix['start_year'] for ix in INDICES)}-{max(ix['start_year'] for ix in INDICES)})\n")

    sess = nse_session()

    # Step 1: fetch NSE data for each target date (one CSV → all NSE indices on that date)
    print(f"[1/3] Fetching {len(targets)} NSE snapshots...")
    nse_by_date = {}
    for i, t in enumerate(targets):
        actual_dt, data = walk_back_to_trading_day(sess, t)
        if data is None:
            print(f"  [{i+1}/{len(targets)}] {t.date()} → ✗ no data found")
            continue
        key = actual_dt.strftime("%Y-%m-%d")
        nse_by_date[key] = data
        print(f"  [{i+1}/{len(targets)}] {t.date()} → got {actual_dt.date()} ({len(data)} indices)")
        time.sleep(0.5)

    # Step 2: fetch yfinance history for each index (full period — for Nasdaq 100 + RSI)
    print(f"\n[2/3] Fetching yfinance history for {len(INDICES)} indices...")
    yf_hist = {}
    end = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    for ix in INDICES:
        try:
            df = yf.download(ix["yf"], start="2011-01-01", end=end, progress=False, auto_adjust=False)
            if df is not None and not df.empty:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                df = df.dropna(subset=["Close"])
                yf_hist[ix["sheet_name"]] = df
                print(f"  ✓ {ix['sheet_name']:25s} {len(df)} bars")
            else:
                print(f"  ✗ {ix['sheet_name']:25s} no data")
        except Exception as e:
            print(f"  ✗ {ix['sheet_name']:25s} {e}")

    # Step 3: build per-index snapshot list
    print(f"\n[3/3] Building snapshots...")
    db = {
        "schema_version": 1,
        "last_updated": datetime.now().isoformat(),
        "indices": {},
    }

    for ix in INDICES:
        sheet = ix["sheet_name"]
        nse_name = ix.get("nse_name")
        hist = yf_hist.get(sheet)
        start_year = ix.get("start_year", 2012)
        snaps = []
        for date_key, nse_data in sorted(nse_by_date.items()):
            # Skip dates before this index's start year
            if int(date_key[:4]) < start_year:
                continue
            close = pe = pb = None
            # Prefer NSE
            if nse_name and nse_name in nse_data:
                close = nse_data[nse_name]["close"]
                pe = nse_data[nse_name]["pe"]
                pb = nse_data[nse_name]["pb"]
            else:
                # Nasdaq / fallback — use yfinance close on that date
                if hist is not None:
                    dt = pd.Timestamp(date_key)
                    sub = hist[hist.index <= dt]
                    if not sub.empty:
                        close = float(sub["Close"].iloc[-1])
            if close is None:
                continue
            eps = round(close / pe, 2) if pe and pe > 0 else None
            rsi = rsi_14_at(hist, date_key) if hist is not None else None
            snaps.append({
                "date":   date_key,
                "close":  round(close, 2),
                "pe":     round(pe, 2) if pe else None,
                "pb":     round(pb, 2) if pb else None,
                "eps":    eps,
                "rsi":    rsi,
                "source": "reconstruct",
            })
        db["indices"][sheet] = {"snapshots": snaps}
        print(f"  ✓ {sheet:25s} → {len(snaps)} snapshots (from {start_year})")

    # Save
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w") as f:
        json.dump(db, f, indent=2, default=str)
    print(f"\n✓ Written to {OUTPUT}")
    print(f"  Total: {sum(len(v['snapshots']) for v in db['indices'].values())} snapshots across {len(db['indices'])} indices")


if __name__ == "__main__":
    main()
