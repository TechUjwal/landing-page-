"""
scraper.py — Daily FII/DII data fetcher using NSE API (no browser required).
Runs via GitHub Actions cron. Fetches last 7 days and merges into CSV.
"""

import requests
import pandas as pd
from datetime import date, timedelta
from pathlib import Path
import time
import sys

CSV_PATH = Path("data/fii_dii_checkpoint.csv")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": "https://www.nseindia.com/",
}

session = requests.Session()
session.headers.update(HEADERS)

def init_session():
    """Hit NSE pages to get valid session cookies before API call."""
    print("Initialising NSE session...")
    try:
        session.get("https://www.nseindia.com", timeout=20)
        time.sleep(3)
        session.get("https://www.nseindia.com/reports/fii-dii", timeout=20)
        time.sleep(2)
        print("Session ready.")
    except Exception as e:
        print(f"Warning: session init issue — {e}. Continuing anyway.")

def fetch_fii_dii(from_date: date, to_date: date) -> list:
    url = "https://www.nseindia.com/api/fiidiiTradeReact"
    params = {
        "startDate": from_date.strftime("%d-%m-%Y"),
        "endDate":   to_date.strftime("%d-%m-%Y"),
    }
    print(f"Fetching {from_date} → {to_date} ...")
    try:
        resp = session.get(url, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        print(f"  → {len(data) if isinstance(data, list) else 'unexpected format'} records")
        return data if isinstance(data, list) else []
    except Exception as e:
        print(f"  ✗ Fetch failed: {e}")
        return []

def parse_to_df(raw: list) -> pd.DataFrame:
    """
    NSE fiidiiTradeReact returns rows like:
    {"date":"12-05-2026","category":"FII/FPI","buyValue":"...","sellValue":"...","netVal":"..."}
    One row per category per date — we pivot to one row per date.
    """
    if not raw:
        return pd.DataFrame()

    rows = []
    for item in raw:
        try:
            date_val = (item.get("date") or item.get("Date") or "").strip()
            category = (item.get("category") or item.get("Category") or "").strip().upper()
            net_raw  = str(item.get("netValue") or item.get("netVal") or item.get("net") or "0")
            net      = float(net_raw.replace(",", ""))
            rows.append({"DATE": date_val, "category": category, "net": net})
        except Exception:
            continue

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    fii = df[df['category'].str.contains("FII|FPI", na=False)][['DATE','net']].rename(columns={'net':'FII_Net_Purchase_Sales'})
    dii = df[df['category'] == "DII"][['DATE','net']].rename(columns={'net':'DII_Net_Purchase_Sales'})
    merged = pd.merge(fii, dii, on='DATE', how='outer')
    merged['Total_Net'] = merged['FII_Net_Purchase_Sales'].fillna(0) + merged['DII_Net_Purchase_Sales'].fillna(0)
    return merged

def merge_and_save(df_new: pd.DataFrame):
    if df_new.empty:
        print("No new rows to save.")
        return

    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)

    if CSV_PATH.exists():
        df_old = pd.read_csv(CSV_PATH, encoding='utf-8-sig')
        df_combined = pd.concat([df_old, df_new], ignore_index=True)
    else:
        df_combined = df_new.copy()

    df_combined['_D'] = pd.to_datetime(df_combined['DATE'], format='mixed', dayfirst=True, errors='coerce')
    df_combined = df_combined.dropna(subset=['_D'])
    df_combined = (
        df_combined
        .sort_values('_D', ascending=False)
        .drop_duplicates(subset=['_D'], keep='first')
        .drop(columns=['_D'])
    )
    df_combined.to_csv(CSV_PATH, index=False, encoding='utf-8-sig')
    print(f"✓ Saved {len(df_combined)} total rows → {CSV_PATH}")

def main():
    init_session()

    # Fetch last 10 calendar days (covers weekends + any lag)
    to_date   = date.today()
    from_date = to_date - timedelta(days=10)

    raw    = fetch_fii_dii(from_date, to_date)
    df_new = parse_to_df(raw)

    if df_new.empty:
        print("⚠ No data parsed from NSE response. Exiting without changes.")
        sys.exit(0)

    print(f"Parsed {len(df_new)} new trading days:")
    print(df_new.to_string(index=False))

    merge_and_save(df_new)

if __name__ == "__main__":
    main()
