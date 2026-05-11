"""
update_valuation.py
Runs daily 4PM IST via GitHub Actions.

For each of 25 indices:
  1. Fetch latest close from yfinance
  2. Fetch latest PE/PB from NSE ind_close_all_DDMMYYYY.csv
  3. Compute EPS = Price / PE
  4. Compute RSI(14) from yfinance history

Appends today's snapshot to data/valuation_history.json
"""
import requests, json, os, sys, time
from datetime import datetime, timedelta
from io import StringIO

import pandas as pd
import numpy as np

try:
    import yfinance as yf
except ImportError:
    print("yfinance not installed"); sys.exit(1)

# Allow running from anywhere
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from index_config import INDICES

OUTPUT = os.path.join(HERE, "data", "valuation_history.json")
NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/csv,application/csv,*/*;q=0.9",
    "Referer": "https://www.nseindia.com/",
}


# ─────────────────────────────────────────────────────────────────────────────
# NSE — daily index close + PE/PB
# ─────────────────────────────────────────────────────────────────────────────

def nse_session():
    s = requests.Session()
    s.headers.update(NSE_HEADERS)
    try:
        s.get("https://www.nseindia.com", timeout=10)
        time.sleep(1.0)
    except Exception:
        pass
    return s


def fetch_nse_indices_for_date(session, dt):
    """
    Fetch NSE ind_close_all_DDMMYYYY.csv for a given date.
    Returns dict: { nse_name: {"close": float, "pe": float, "pb": float, "divyield": float} }
    Returns empty dict if file doesn't exist (weekend/holiday).
    """
    date_str = dt.strftime("%d%m%Y")
    url = f"https://nsearchives.nseindia.com/content/indices/ind_close_all_{date_str}.csv"
    try:
        r = session.get(url, timeout=15)
        if r.status_code != 200 or len(r.content) < 500:
            return {}
        df = pd.read_csv(StringIO(r.text))
        # NSE column names: "Index Name","Index Date","Open Index Value","High Index Value",
        # "Low Index Value","Closing Index Value","Points Change","Change(%)","Volume","Turnover (Rs. Cr.)",
        # "P/E","P/B","Div Yield"
        out = {}
        for _, row in df.iterrows():
            name = str(row.get("Index Name", "")).strip()
            if not name:
                continue
            try:
                close = float(row["Closing Index Value"])
                pe = float(row["P/E"]) if pd.notna(row["P/E"]) else None
                pb = float(row["P/B"]) if pd.notna(row["P/B"]) else None
                dy = float(row["Div Yield"]) if pd.notna(row["Div Yield"]) else None
            except (KeyError, ValueError, TypeError):
                continue
            out[name] = {"close": close, "pe": pe, "pb": pb, "divyield": dy}
        return out
    except Exception as e:
        print(f"    NSE fetch failed for {date_str}: {e}")
        return {}


def latest_nse_indices(session, lookback_days=10):
    """Walk backwards from today until we find a date with data."""
    for back in range(lookback_days):
        dt = datetime.now() - timedelta(days=back)
        if dt.weekday() >= 5:  # skip weekends
            continue
        data = fetch_nse_indices_for_date(session, dt)
        if data:
            print(f"  ✓ NSE data found for {dt.strftime('%d-%b-%Y')} ({len(data)} indices)")
            return dt, data
    return None, {}


# ─────────────────────────────────────────────────────────────────────────────
# yfinance — historical prices for RSI
# ─────────────────────────────────────────────────────────────────────────────

def rsi_14(close_series):
    """Standard 14-day RSI."""
    if len(close_series) < 15:
        return None
    delta = close_series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    val = rsi.iloc[-1]
    return round(float(val), 2) if pd.notna(val) else None


def fetch_yf_history(ticker, period="3mo"):
    """Returns DataFrame with Close column, or None."""
    try:
        end = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        df = yf.download(ticker, period=period, end=end, progress=False, auto_adjust=False)
        if df is None or df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.dropna(subset=["Close"])
        return df if len(df) > 0 else None
    except Exception as e:
        print(f"    yf fetch failed for {ticker}: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# State management
# ─────────────────────────────────────────────────────────────────────────────

def load_db():
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    if os.path.exists(OUTPUT):
        with open(OUTPUT) as f:
            return json.load(f)
    return {
        "schema_version": 1,
        "last_updated": "",
        "indices": {},  # { sheet_name: { "snapshots": [ {date, close, pe, pb, eps, rsi, source}, ...] } }
    }


def save_db(db):
    db["last_updated"] = datetime.now().isoformat()
    with open(OUTPUT, "w") as f:
        json.dump(db, f, indent=2, default=str)


def upsert_snapshot(db, sheet_name, snap):
    """Add or replace a snapshot for a given date."""
    idx = db["indices"].setdefault(sheet_name, {"snapshots": []})
    snaps = idx["snapshots"]
    # Replace if same date already exists
    snaps = [s for s in snaps if s["date"] != snap["date"]]
    snaps.append(snap)
    snaps.sort(key=lambda s: s["date"])
    idx["snapshots"] = snaps


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def run():
    print(f"\n{'='*60}")
    print(f"  Valuation Tracker — Daily Update — {datetime.now():%Y-%m-%d %H:%M}")
    print(f"{'='*60}\n")

    print("[1/3] Fetching NSE indices snapshot...")
    sess = nse_session()
    nse_date, nse_data = latest_nse_indices(sess)
    if not nse_data:
        print("  ✗ NSE fetch returned nothing — aborting (no fallback for PE)")
        # Don't exit 1 — try to update yfinance prices anyway
        nse_date = datetime.now()

    snapshot_date = nse_date.strftime("%Y-%m-%d")
    db = load_db()
    updated = 0
    skipped = 0

    print(f"\n[2/3] Processing {len(INDICES)} indices for {snapshot_date}...")
    for ix in INDICES:
        sheet = ix["sheet_name"]
        print(f"  • {sheet:25s}", end=" ")

        # 1. Price + RSI from yfinance
        hist = fetch_yf_history(ix["yf"], period="3mo")
        if hist is None or hist.empty:
            print("✗ no yf data")
            skipped += 1
            continue
        close = float(hist["Close"].iloc[-1])
        rsi = rsi_14(hist["Close"])

        # 2. PE/PB from NSE (if matched)
        nse_name = ix.get("nse_name")
        pe = pb = None
        if nse_name and nse_name in nse_data:
            pe = nse_data[nse_name]["pe"]
            pb = nse_data[nse_name]["pb"]
            # Prefer NSE's close to keep PE consistent (NSE PE was computed on NSE close)
            close = nse_data[nse_name]["close"]

        # 3. Derive EPS = Price / PE (the whole point of this exercise)
        eps = round(close / pe, 2) if pe and pe > 0 else None

        snap = {
            "date":   snapshot_date,
            "close":  round(close, 2),
            "pe":     round(pe, 2) if pe else None,
            "pb":     round(pb, 2) if pb else None,
            "eps":    eps,
            "rsi":    rsi,
            "source": "nse+yf" if pe else "yf_only",
        }
        upsert_snapshot(db, sheet, snap)
        updated += 1
        print(f"close={close:.2f}  pe={pe}  eps={eps}  rsi={rsi}")

    print(f"\n[3/3] Saving database... ({updated} updated, {skipped} skipped)")
    save_db(db)
    print(f"  ✓ Written to {OUTPUT}")
    print(f"  ✓ {len([k for k in db['indices'] if db['indices'][k]['snapshots']])} indices with data\n")


if __name__ == "__main__":
    run()
