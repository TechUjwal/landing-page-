"""
Scanner 04 — India Custom Research
Full port of streamlit_app.py from india-research repo.
Original brand (maroon/gold/cream) restyled to gold/dark RH terminal aesthetic.

Reads from data/companies.json (produced by fetcher.py via GitHub Actions).
"""
import streamlit as st
import pandas as pd
import json
import os, sys
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from theme import (
    apply_theme, render_header,
    RH_GOLD, RH_GOLD_LIGHT, RH_GOLD_DIM, RH_RED, RH_GREEN,
    RH_BG, RH_SURFACE, RH_SURFACE2, RH_TEXT, RH_MUTED, RH_BORDER
)
from auth import require_login, render_logout_button

st.set_page_config(layout="wide", page_title="RH | India Research",
                   initial_sidebar_state="expanded")
apply_theme()
require_login()
render_logout_button()
render_header("Scanner 04 · India Custom Research")

# ─────────────────────────────────────────────────────
#  PAGE-SPECIFIC OVERRIDES
#  India Research has its own sidebar with filters — we
#  match the gold/dark aesthetic of theme.py while
#  reproducing the original layout.
# ─────────────────────────────────────────────────────
st.markdown(f"""
<style>
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stNumberInput label,
[data-testid="stSidebar"] .stTextInput label,
[data-testid="stSidebar"] .stRadio label {{
    color: {RH_GOLD_DIM} !important;
    font-size: 10px !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase;
    font-weight: 500 !important;
}}
[data-testid="stSidebar"] hr {{ border-color: {RH_BORDER} !important; }}
[data-testid="stSidebar"] h3 {{
    color: {RH_GOLD_LIGHT} !important;
    font-size: 11px !important;
    letter-spacing: 0.16em !important;
    text-transform: uppercase;
    font-weight: 400 !important;
}}
[data-testid="stSidebar"] .stMarkdown strong {{
    color: {RH_GOLD_DIM} !important;
    font-size: 10px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
}}

/* Active filter pill */
.f-pill {{
    display: inline-block;
    background: rgba(184,136,26,0.05);
    border: 1px solid {RH_GOLD_DIM};
    color: {RH_GOLD_LIGHT};
    font-size: 10px;
    padding: 3px 9px;
    margin: 2px 0;
    letter-spacing: 0.05em;
}}

/* Number/select inputs */
[data-testid="stSidebar"] .stSelectbox > div > div,
[data-testid="stSidebar"] .stNumberInput > div > div > input,
[data-testid="stSidebar"] .stTextInput > div > div > input {{
    background-color: {RH_BG} !important;
    border: 1px solid {RH_BORDER} !important;
    color: {RH_TEXT} !important;
    border-radius: 0 !important;
}}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {{
    background: transparent;
    border-bottom: 1px solid {RH_BORDER};
    gap: 4px;
}}
.stTabs [data-baseweb="tab"] {{
    background: transparent !important;
    color: {RH_MUTED} !important;
    border: none !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 11px !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase;
    padding: 8px 16px !important;
}}
.stTabs [aria-selected="true"] {{
    color: {RH_GOLD_LIGHT} !important;
    border-bottom: 2px solid {RH_GOLD} !important;
}}

/* Download button */
.stDownloadButton > button {{
    background: transparent !important;
    color: {RH_GOLD_LIGHT} !important;
    border: 1px solid {RH_GOLD_DIM} !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 10px !important;
    letter-spacing: 0.12em;
    border-radius: 0 !important;
}}
.stDownloadButton > button:hover {{
    background: {RH_GOLD} !important;
    color: {RH_BG} !important;
}}

/* Captions inside this page */
.stCaption, small {{ color: {RH_MUTED} !important; font-size: 10px !important; }}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────
#  DATA FILES — check both data/ and project root
# ─────────────────────────────────────────────────────
def _find(*candidates):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for path in candidates:
        full = os.path.join(root, path)
        if os.path.exists(full):
            return full
    return None


DATA_FILE  = _find("data/companies.json", "companies.json")
META_FILE  = _find("data/meta.json", "meta.json")
SAVED_FILE = _find("data/saved_screeners.json", "saved_screeners.json") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "saved_screeners.json"
)


@st.cache_data(ttl=3600)
def load_companies():
    if not DATA_FILE or not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE) as f:
        return json.load(f)


@st.cache_data(ttl=3600)
def load_meta():
    if not META_FILE or not os.path.exists(META_FILE):
        return {}
    with open(META_FILE) as f:
        return json.load(f)


def load_saved():
    if not os.path.exists(SAVED_FILE):
        return {}
    try:
        with open(SAVED_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def save_screener(name, filters, sector):
    s = load_saved()
    s[name] = {"filters": filters, "sector": sector,
               "saved_at": datetime.utcnow().isoformat()}
    os.makedirs(os.path.dirname(SAVED_FILE), exist_ok=True)
    with open(SAVED_FILE, "w") as f:
        json.dump(s, f, indent=2)


def delete_screener(name):
    s = load_saved()
    s.pop(name, None)
    with open(SAVED_FILE, "w") as f:
        json.dump(s, f, indent=2)


# ─────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────
def fmt_cr(v):
    if v is None:
        return "—"
    try:
        v = float(v)
        if v >= 100000:
            return f"₹{v/100000:.2f}L Cr"
        if v >= 1000:
            return f"₹{v/1000:.1f}K Cr"
        return f"₹{v:,.0f} Cr"
    except Exception:
        return "—"


def fmt(v, pre="", suf="", dec=2):
    if v is None:
        return "—"
    try:
        return f"{pre}{float(v):.{dec}f}{suf}"
    except Exception:
        return "—"


def rec_icon(r):
    if not r:
        return ""
    r = r.lower()
    if "buy" in r:
        return "▲"
    if "hold" in r or "neutral" in r:
        return "◆"
    if "sell" in r or "under" in r:
        return "▼"
    return ""


# ─────────────────────────────────────────────────────
#  FILTER DEFINITIONS — full set from original
# ─────────────────────────────────────────────────────
FILTERS = {
    "Valuation": {
        "P/E Ratio":   ("pe_ratio", 0, 200, .5),
        "P/B Ratio":   ("pb_ratio", 0, 50, .1),
        "P/S Ratio":   ("ps_ratio", 0, 50, .1),
        "EV/EBITDA":   ("ev_ebitda", 0, 80, .5),
        "PEG Ratio":   ("peg_ratio", 0, 10, .1),
    },
    "Profitability": {
        "ROE (%)":          ("roe_pct", -50, 100, 1),
        "ROA (%)":          ("roa_pct", -50, 50, .5),
        "Gross Margin (%)": ("gross_margin_pct", 0, 100, 1),
        "Op Margin (%)":    ("op_margin_pct", -50, 100, 1),
        "Net Margin (%)":   ("net_margin_pct", -50, 100, 1),
    },
    "Growth": {
        "Revenue Growth (%)": ("revenue_growth_pct", -50, 300, 1),
        "EPS Growth (%)":     ("eps_growth_pct", -100, 500, 5),
    },
    "Size": {
        "Market Cap (Cr)": ("market_cap_cr", 500, 2000000, 500),
        "Revenue (Cr)":    ("revenue_cr", 0, 500000, 500),
        "Cash (Cr)":       ("cash_cr", 0, 200000, 500),
    },
    "Financial Health": {
        "Debt/Equity":   ("debt_to_equity", 0, 20, .1),
        "Current Ratio": ("current_ratio", 0, 10, .1),
        "Quick Ratio":   ("quick_ratio", 0, 10, .1),
    },
    "Dividends": {
        "Div Yield (%)":     ("dividend_yield_pct", 0, 20, .25),
        "Payout Ratio (%)":  ("payout_ratio_pct", 0, 100, 1),
    },
    "Market": {
        "Beta":         ("beta", -2, 5, .1),
        "52W High (₹)": ("week_52_high", 0, 50000, 50),
        "52W Low (₹)":  ("week_52_low", 0, 50000, 50),
    },
}


# ─────────────────────────────────────────────────────
#  SCREENER ENGINE
# ─────────────────────────────────────────────────────
def run_screener(companies, filters, sector, sort_col, sort_asc):
    rows = []
    for c in companies:
        if sector != "All sectors" and c.get("sector") != sector:
            continue
        mc = c.get("market_cap_cr")
        if mc is not None and mc < 500:
            continue
        ok = True
        for f in filters:
            v = c.get(f["column"])
            if v is None:
                ok = False
                break
            try:
                fv = float(v)
                if f["op"] == "≤" and fv > f["val"]:
                    ok = False
                    break
                if f["op"] == "≥" and fv < f["val"]:
                    ok = False
                    break
            except Exception:
                ok = False
                break
        if not ok:
            continue
        rows.append({
            "Ticker": c.get("ticker_short", ""),
            "Company": c.get("name", ""),
            "Sector": c.get("sector", "—"),
            "Mkt Cap": fmt_cr(c.get("market_cap_cr")),
            "Price (₹)": c.get("current_price"),
            "P/E": c.get("pe_ratio"),
            "P/B": c.get("pb_ratio"),
            "EV/EBITDA": c.get("ev_ebitda"),
            "ROE %": c.get("roe_pct"),
            "Net Margin %": c.get("net_margin_pct"),
            "Rev Growth %": c.get("revenue_growth_pct"),
            "D/E": c.get("debt_to_equity"),
            "Div Yield %": c.get("dividend_yield_pct"),
            "Rating": (rec_icon(c.get("recommendation")) + " " +
                       (c.get("recommendation") or "—")).strip(),
            "Fetched": (c.get("fetched_at") or "")[:10],
            "_t": c.get("ticker", ""),
            "_mc": c.get("market_cap_cr") or 0,
        })
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    sk = {
        "Market Cap": "_mc", "P/E Ratio": "P/E", "P/B Ratio": "P/B",
        "ROE %": "ROE %", "Net Margin %": "Net Margin %",
        "Revenue Growth %": "Rev Growth %", "Dividend Yield %": "Div Yield %",
    }.get(sort_col, "_mc")
    if sk in df.columns:
        df = df.sort_values(sk, ascending=sort_asc, na_position="last")
    return df


# ─────────────────────────────────────────────────────
#  COMPANY DETAIL — full panel with 4 tabs
# ─────────────────────────────────────────────────────
def company_detail(tf, companies):
    c = next((x for x in companies if x.get("ticker") == tf), None)
    if not c:
        st.warning("Not found.")
        return

    st.markdown(f"""
    <div style="background:{RH_SURFACE}; border:1px solid {RH_BORDER};
                padding:18px 22px; margin-bottom:10px;">
      <div style="display:flex; justify-content:space-between;
                  align-items:flex-start; flex-wrap:wrap; gap:12px;">
        <div>
          <div style="font-family:'Fraunces',serif; font-size:22px;
                      font-weight:700; color:{RH_TEXT};">{c.get("name", tf)}</div>
          <div style="font-size:11px; color:{RH_GOLD_DIM}; margin-top:6px;
                      letter-spacing:0.08em; text-transform:uppercase;">
            <span style="background:{RH_BG}; border:1px solid {RH_BORDER};
                         padding:2px 8px; margin-right:6px; color:{RH_GOLD_LIGHT};">
              {c.get("ticker_short", "")}
            </span>
            {c.get("sector", "—")} <span style="color:{RH_MUTED};">· {c.get("industry", "—")}</span>
          </div>
        </div>
        <div style="text-align:right;">
          <div style="font-family:'Fraunces',serif; font-size:28px;
                      font-weight:900; color:{RH_TEXT}; line-height:1;">
            {"₹{:,.2f}".format(c["current_price"]) if c.get("current_price") else "—"}
          </div>
          <div style="font-size:11px; color:{RH_GOLD_LIGHT}; margin-top:4px;
                      letter-spacing:0.08em;">
            {fmt_cr(c.get("market_cap_cr"))}
          </div>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

    st.caption(
        f"Source: [{c.get('source_name', 'Yahoo Finance')}]({c.get('source_url', '#')}) "
        f"· Fetched: {(c.get('fetched_at', ''))[:10]}"
    )

    rec = c.get("recommendation", "")
    if rec:
        tp = c.get("target_price")
        ac = c.get("analyst_count")
        tstr = f" · Target ₹{tp:,.2f} ({ac} analysts)" if tp else ""
        bg_map = {"buy": RH_GREEN, "strong_buy": RH_GREEN,
                  "hold": RH_GOLD, "sell": RH_RED, "underperform": RH_RED}
        bg = bg_map.get(rec.lower(), RH_GOLD_DIM)
        st.markdown(
            f'<div style="background:rgba(184,136,26,0.05); border:1px solid {bg}; '
            f'padding:8px 14px; font-size:11px; color:{RH_TEXT}; margin-bottom:8px; '
            f'letter-spacing:0.06em;">'
            f'<span style="color:{bg};">{rec_icon(rec)}</span> '
            f'Analyst: <strong style="color:{RH_GOLD_LIGHT};">{rec.upper()}</strong>{tstr}</div>',
            unsafe_allow_html=True
        )

    t1, t2, t3, t4 = st.tabs(["RATIOS", "FINANCIALS", "EARNINGS", "NEWS"])

    def mc(label, value):
        return (
            f'<div style="background:{RH_BG}; border:1px solid {RH_BORDER}; '
            f'padding:12px; text-align:center;">'
            f'<div style="font-size:9px; color:{RH_GOLD_DIM}; '
            f'letter-spacing:0.14em; text-transform:uppercase; margin-bottom:6px;">'
            f'{label}</div>'
            f'<div style="font-family:Fraunces,serif; font-size:18px; '
            f'font-weight:700; color:{RH_TEXT};">{value}</div></div>'
        )

    with t1:
        for section, items in [
            ("Valuation",
             [("P/E", fmt(c.get("pe_ratio"))),
              ("P/B", fmt(c.get("pb_ratio"))),
              ("EV/EBITDA", fmt(c.get("ev_ebitda"))),
              ("PEG", fmt(c.get("peg_ratio"))),
              ("P/S", fmt(c.get("ps_ratio")))]),
            ("Profitability",
             [("ROE", fmt(c.get("roe_pct"), suf="%")),
              ("ROA", fmt(c.get("roa_pct"), suf="%")),
              ("Gross Margin", fmt(c.get("gross_margin_pct"), suf="%")),
              ("Op Margin", fmt(c.get("op_margin_pct"), suf="%")),
              ("Net Margin", fmt(c.get("net_margin_pct"), suf="%"))]),
            ("Financial Health",
             [("D/E", fmt(c.get("debt_to_equity"))),
              ("Current", fmt(c.get("current_ratio"))),
              ("Quick", fmt(c.get("quick_ratio"))),
              ("Beta", fmt(c.get("beta"))),
              ("Div Yield", fmt(c.get("dividend_yield_pct"), suf="%"))]),
        ]:
            st.markdown(f"**{section}**")
            cols = st.columns(5)
            for col, (lbl, val) in zip(cols, items):
                col.markdown(mc(lbl, val), unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

        hi, lo, cp = c.get("week_52_high"), c.get("week_52_low"), c.get("current_price")
        if hi and lo and cp and hi != lo:
            pct = max(0.0, min(1.0, (cp - lo) / (hi - lo)))
            st.markdown("**52-week range**")
            st.progress(
                pct,
                text=f"Low ₹{lo:,.0f}  ·  Current ₹{cp:,.0f}  ·  High ₹{hi:,.0f}  ({pct*100:.0f}%)"
            )

    with t2:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Income statement**")
            st.table(pd.DataFrame([
                ("Revenue",        fmt_cr(c.get("revenue_cr"))),
                ("Revenue growth", fmt(c.get("revenue_growth_pct"), suf="%")),
                ("Gross profit",   fmt_cr(c.get("gross_profit_cr"))),
                ("EBITDA",         fmt_cr(c.get("ebitda_cr"))),
                ("Net income",     fmt_cr(c.get("net_income_cr"))),
                ("EPS",            fmt(c.get("eps"), pre="₹")),
                ("EPS growth",     fmt(c.get("eps_growth_pct"), suf="%")),
            ], columns=["Metric", "Value"]).set_index("Metric"))
        with c2:
            st.markdown("**Balance sheet**")
            st.table(pd.DataFrame([
                ("Total assets",     fmt_cr(c.get("total_assets_cr"))),
                ("Total debt",       fmt_cr(c.get("total_debt_cr"))),
                ("Cash",             fmt_cr(c.get("cash_cr"))),
                ("Book value/share", fmt(c.get("book_value"), pre="₹")),
                ("Enterprise value", fmt_cr(c.get("enterprise_value_cr"))),
                ("Dividend rate",    fmt(c.get("dividend_rate"), pre="₹")),
                ("Payout ratio",     fmt(c.get("payout_ratio_pct"), suf="%")),
            ], columns=["Metric", "Value"]).set_index("Metric"))
        st.caption(f"Source: {c.get('source_name', 'Yahoo Finance')} · {c.get('source_url', '')}")

    with t3:
        rows = [
            ("Trailing EPS", fmt(c.get("eps"), pre="₹")),
            ("EPS growth",   fmt(c.get("eps_growth_pct"), suf="%")),
            ("Rev growth",   fmt(c.get("revenue_growth_pct"), suf="%")),
        ]
        st.table(pd.DataFrame(rows, columns=["Metric", "Value"]).set_index("Metric"))
        st.caption(f"Source: Yahoo Finance · {(c.get('fetched_at', ''))[:10]}")

    with t4:
        news = c.get("news", [])
        if news:
            for n in news:
                st.markdown(
                    f'<div style="padding:12px 0; border-bottom:1px solid {RH_BORDER};">'
                    f'<a href="{n.get("link", "#")}" target="_blank" '
                    f'style="color:{RH_GOLD_LIGHT}; font-weight:500; font-size:13px; '
                    f'text-decoration:none;">'
                    f'{n.get("title", "")}</a>'
                    f'<div style="font-size:10px; color:{RH_MUTED}; margin-top:4px; '
                    f'letter-spacing:0.06em;">'
                    f'{n.get("publisher", "")} · {n.get("published", "")}</div></div>',
                    unsafe_allow_html=True
                )
        else:
            st.info("No news yet. Refreshes every 3 days via GitHub Actions.")


# ══════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════
companies = load_companies()
meta      = load_meta()

if "ir_filters" not in st.session_state:
    st.session_state.ir_filters = []
if "ir_results" not in st.session_state:
    st.session_state.ir_results = None

# Top status strip
last_upd = (meta.get("last_financial_update") or "")[:10]
st.markdown(f"""
<div style='display:flex; gap:24px; padding:8px 0 16px;
            border-bottom:1px solid {RH_BORDER}; margin-bottom:18px;
            font-family:IBM Plex Mono; font-size:10px;
            letter-spacing:0.1em; text-transform:uppercase;
            color:{RH_MUTED};'>
    <span><strong style='color:{RH_GOLD_LIGHT}; font-weight:500;'>{len(companies):,}</strong>
        Companies tracked</span>
    <span><strong style='color:{RH_GOLD_LIGHT}; font-weight:500;'>
        {last_upd or "Pending"}</strong> Last refresh</span>
    <span><strong style='color:{RH_GOLD_LIGHT}; font-weight:500;'>
        ₹500 Cr+</strong> Mkt cap floor</span>
    <span style='margin-left:auto;'>NSE · Yahoo Finance</span>
</div>
""", unsafe_allow_html=True)


# ─── SIDEBAR ───────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Screener filters")
    sectors = sorted(set(c.get("sector", "") for c in companies if c.get("sector")))
    sector_filter = st.selectbox("Sector", ["All sectors"] + sectors)
    st.divider()

    st.markdown("**Add a filter**")
    cat = st.selectbox("Category", list(FILTERS.keys()), key="cat")
    metric = st.selectbox("Metric", list(FILTERS[cat].keys()), key="metric")
    col_key, mn, mx, step = FILTERS[cat][metric]
    op = st.radio("Operator", ["≤", "≥"], horizontal=True)
    val = st.number_input(
        "Value",
        min_value=float(mn),
        max_value=float(mx),
        value=float(round(mn + (mx - mn) * 0.25, 2)),
        step=float(step)
    )

    if st.button("ADD FILTER", use_container_width=True):
        st.session_state.ir_filters.append({
            "label": f"{metric} {op} {val}",
            "column": col_key, "op": op, "val": float(val)
        })
        st.rerun()

    if st.session_state.ir_filters:
        st.divider()
        st.markdown("**Active filters**")
        rm = []
        for i, f in enumerate(st.session_state.ir_filters):
            ca, cb = st.columns([5, 1])
            ca.markdown(f'<div class="f-pill">{f["label"]}</div>',
                        unsafe_allow_html=True)
            if cb.button("✕", key=f"rm{i}"):
                rm.append(i)
        for i in reversed(rm):
            st.session_state.ir_filters.pop(i)
        if rm:
            st.rerun()
        if st.button("CLEAR ALL", use_container_width=True):
            st.session_state.ir_filters = []
            st.session_state.ir_results = None
            st.rerun()

    st.divider()
    st.markdown("**Sort by**")
    sort_col = st.selectbox(
        "",
        ["Market Cap", "P/E Ratio", "P/B Ratio", "ROE %",
         "Net Margin %", "Revenue Growth %", "Dividend Yield %"],
        label_visibility="collapsed"
    )
    sort_asc = st.checkbox("Ascending", value=False)
    st.divider()

    if st.button("▶ RUN SCREENER", use_container_width=True, type="primary"):
        if not companies:
            st.error("No data. Run GitHub Actions first.")
        else:
            with st.spinner(f"Screening {len(companies):,} companies..."):
                st.session_state.ir_results = run_screener(
                    companies, st.session_state.ir_filters,
                    sector_filter, sort_col, sort_asc
                )
            st.rerun()

    st.divider()
    st.markdown("**Save screener**")
    sname = st.text_input("Name", placeholder="e.g. Quality large caps")
    if st.button("SAVE", use_container_width=True):
        if not sname.strip():
            st.warning("Enter a name")
        elif not st.session_state.ir_filters:
            st.warning("Add a filter first")
        else:
            save_screener(sname.strip(), st.session_state.ir_filters, sector_filter)
            st.success("Saved!")
            st.rerun()

    saved = load_saved()
    if saved:
        st.markdown("**Saved screeners**")
        for name in list(saved.keys()):
            ca, cb = st.columns([4, 1])
            if ca.button(f"▸ {name}", key=f"ld_{name}", use_container_width=True):
                st.session_state.ir_filters = saved[name]["filters"]
                st.rerun()
            if cb.button("✕", key=f"dl_{name}"):
                delete_screener(name)
                st.rerun()

    st.divider()
    if meta:
        st.markdown(
            f'<div style="font-size:10px; color:{RH_MUTED}; '
            f'line-height:1.9; letter-spacing:0.06em;">'
            f'Companies: <span style="color:{RH_GOLD_LIGHT};">'
            f'{meta.get("total_companies", 0):,}</span><br>'
            f'Financials: <span style="color:{RH_GOLD_LIGHT};">'
            f'{(meta.get("last_financial_update", ""))[:10] or "pending"}</span><br>'
            f'News: <span style="color:{RH_GOLD_LIGHT};">'
            f'{(meta.get("last_news_update", ""))[:10] or "pending"}</span><br>'
            f'Source: <span style="color:{RH_GOLD_LIGHT};">Yahoo Finance</span></div>',
            unsafe_allow_html=True
        )


# ─── EMPTY STATE ─────────────────────────────────────────────
if not companies:
    st.markdown(f"""
    <div style="text-align:center; padding:60px 20px;">
        <div style="font-family:Fraunces,serif; font-size:60px;
                    font-weight:900; color:{RH_GOLD_DIM}; line-height:1;
                    margin-bottom:16px;">04</div>
        <div style="font-family:IBM Plex Mono; font-size:13px;
                    color:{RH_TEXT}; margin-bottom:8px; letter-spacing:0.1em;
                    text-transform:uppercase;">No data loaded yet</div>
        <div style="font-family:IBM Plex Mono; font-size:11px;
                    color:{RH_MUTED}; max-width:480px; margin:0 auto;
                    letter-spacing:0.04em; line-height:1.7;">
            GitHub repo → <span style="color:{RH_GOLD_LIGHT};">Actions</span> →
            <span style="color:{RH_GOLD_LIGHT};">Data refresh</span> →
            <span style="color:{RH_GOLD_LIGHT};">Run workflow → both</span>.
            Takes ~25 minutes.
        </div>
    </div>""", unsafe_allow_html=True)
    if st.button("← BACK TO HUB", key="back_empty"):
        st.switch_page("Home.py")
    st.stop()


# ─── LANDING — example screener cards ─────────────────────────
if st.session_state.ir_results is None:
    st.markdown(f"""
    <div style='background:{RH_SURFACE}; border:1px solid {RH_GOLD_DIM};
                padding:14px 22px; margin-bottom:20px;
                font-family:IBM Plex Mono,monospace; font-size:0.78rem;
                color:{RH_GOLD_LIGHT}; letter-spacing:0.06em;'>
        ◀ Open the sidebar from the top-left to add filters and run the screener.
        <span style='color:{RH_MUTED};'>If the sidebar arrow isn't visible, try
        keyboard shortcut</span>
        <kbd style='background:{RH_BG}; padding:2px 6px; border:1px solid {RH_BORDER};
                    color:{RH_GOLD_LIGHT}; font-family:IBM Plex Mono;'>Ctrl/Cmd + Shift + .</kbd>
    </div>
    """, unsafe_allow_html=True)
    st.subheader("Build your screener")
    st.markdown(
        f'<p style="color:{RH_MUTED}; font-size:11px; '
        f'letter-spacing:0.06em; margin-bottom:16px;">'
        f'Add filters in the sidebar → click '
        f'<strong style="color:{RH_GOLD_LIGHT};">RUN SCREENER</strong></p>',
        unsafe_allow_html=True
    )

    c1, c2, c3 = st.columns(3)

    def ecard(title, items, accent):
        li = "".join(
            f'<div style="font-size:10px; color:{RH_MUTED}; padding:3px 0; '
            f'letter-spacing:0.04em;">▸ {i}</div>'
            for i in items
        )
        return (
            f'<div style="background:{RH_SURFACE}; border:1px solid {RH_BORDER}; '
            f'border-left:3px solid {accent}; padding:16px;">'
            f'<div style="font-family:IBM Plex Mono; font-size:11px; '
            f'font-weight:500; color:{accent}; margin-bottom:10px; '
            f'letter-spacing:0.14em; text-transform:uppercase;">{title}</div>'
            f'{li}</div>'
        )

    c1.markdown(ecard(
        "Quality Screen",
        ["ROE ≥ 15%", "Net Margin ≥ 10%", "D/E ≤ 0.5", "Mkt Cap ≥ ₹5000 Cr"],
        RH_GREEN
    ), unsafe_allow_html=True)
    c2.markdown(ecard(
        "Value Screen",
        ["P/E ≤ 15", "P/B ≤ 2", "Div Yield ≥ 2%", "Mkt Cap ≥ ₹2000 Cr"],
        RH_GOLD_LIGHT
    ), unsafe_allow_html=True)
    c3.markdown(ecard(
        "Growth Screen",
        ["Rev Growth ≥ 20%", "EPS Growth ≥ 15%", "ROE ≥ 12%", "Mkt Cap ≥ ₹1000 Cr"],
        "#8E6FD8"
    ), unsafe_allow_html=True)

elif len(st.session_state.ir_results) == 0:
    st.warning("No companies match. Try relaxing your filters.")

else:
    # ─── RESULTS VIEW ───────────────────────────────────
    df = st.session_state.ir_results
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Results", len(df))
    c2.metric("Median P/E",
              f"{df['P/E'].dropna().median():.1f}x"
              if df['P/E'].notna().any() else "—")
    c3.metric("Median ROE",
              f"{df['ROE %'].dropna().median():.1f}%"
              if df['ROE %'].notna().any() else "—")
    c4.metric("Sectors", df["Sector"].nunique())
    st.divider()

    show = ["Ticker", "Company", "Sector", "Mkt Cap", "Price (₹)",
            "P/E", "P/B", "ROE %", "Net Margin %", "Rev Growth %",
            "D/E", "Rating", "Fetched"]
    show = [c for c in show if c in df.columns]
    st.dataframe(
        df[show], use_container_width=True, hide_index=True,
        column_config={
            "Price (₹)":    st.column_config.NumberColumn(format="₹%.2f"),
            "P/E":          st.column_config.NumberColumn(format="%.1f"),
            "P/B":          st.column_config.NumberColumn(format="%.2f"),
            "ROE %":        st.column_config.NumberColumn(format="%.1f"),
            "Net Margin %": st.column_config.NumberColumn(format="%.1f"),
            "Rev Growth %": st.column_config.NumberColumn(format="%.1f"),
            "D/E":          st.column_config.NumberColumn(format="%.2f"),
        }
    )
    st.caption("All data from Yahoo Finance via yfinance · "
               "[Verify on Yahoo Finance ↗](https://finance.yahoo.com)")
    st.download_button(
        "DOWNLOAD CSV",
        df[show].to_csv(index=False).encode(),
        f"RH_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        "text/csv"
    )
    st.divider()

    # Company detail
    st.subheader("Company detail")
    tl = df["Ticker"].tolist()
    sel = st.selectbox("Select company", ["— select —"] + tl)
    if sel and sel != "— select —":
        company_detail(df[df["Ticker"] == sel]["_t"].values[0], companies)
    st.divider()

    # Compare two
    st.subheader("Compare two companies")
    ca_col, cb_col = st.columns(2)
    with ca_col:
        cmp_a = st.selectbox("Company A", ["— select —"] + tl, key="ca")
    with cb_col:
        cmp_b = st.selectbox("Company B", ["— select —"] + tl, key="cb")
    if (cmp_a != "— select —" and cmp_b != "— select —" and cmp_a != cmp_b):
        ta = df[df["Ticker"] == cmp_a]["_t"].values[0]
        tb = df[df["Ticker"] == cmp_b]["_t"].values[0]
        ca = next((x for x in companies if x["ticker"] == ta), {})
        cb = next((x for x in companies if x["ticker"] == tb), {})
        if ca.get("sector") != cb.get("sector"):
            st.warning(
                f"Different sectors: **{ca.get('sector', '?')}** vs "
                f"**{cb.get('sector', '?')}** — comparisons may be misleading."
            )
        rows = [
            ("Sector",       ca.get("sector", "—"),                   cb.get("sector", "—")),
            ("Market Cap",   fmt_cr(ca.get("market_cap_cr")),         fmt_cr(cb.get("market_cap_cr"))),
            ("Price (₹)",    fmt(ca.get("current_price"), "₹"),       fmt(cb.get("current_price"), "₹")),
            ("P/E",          fmt(ca.get("pe_ratio")),                  fmt(cb.get("pe_ratio"))),
            ("P/B",          fmt(ca.get("pb_ratio")),                  fmt(cb.get("pb_ratio"))),
            ("EV/EBITDA",    fmt(ca.get("ev_ebitda")),                 fmt(cb.get("ev_ebitda"))),
            ("ROE %",        fmt(ca.get("roe_pct"), suf="%"),          fmt(cb.get("roe_pct"), suf="%")),
            ("Net Margin %", fmt(ca.get("net_margin_pct"), suf="%"),   fmt(cb.get("net_margin_pct"), suf="%")),
            ("Revenue",      fmt_cr(ca.get("revenue_cr")),             fmt_cr(cb.get("revenue_cr"))),
            ("Net Income",   fmt_cr(ca.get("net_income_cr")),          fmt_cr(cb.get("net_income_cr"))),
            ("D/E",          fmt(ca.get("debt_to_equity")),            fmt(cb.get("debt_to_equity"))),
            ("Div Yield %",  fmt(ca.get("dividend_yield_pct"), suf="%"), fmt(cb.get("dividend_yield_pct"), suf="%")),
            ("Rating",       (ca.get("recommendation", "—")).upper(),  (cb.get("recommendation", "—")).upper()),
            ("Target Price", fmt(ca.get("target_price"), "₹"),         fmt(cb.get("target_price"), "₹")),
            ("Last fetched", (ca.get("fetched_at", ""))[:10],          (cb.get("fetched_at", ""))[:10]),
        ]
        st.dataframe(
            pd.DataFrame(rows, columns=["Metric", cmp_a, cmp_b]).set_index("Metric"),
            use_container_width=True
        )
        st.caption("Source: Yahoo Finance via yfinance")

st.markdown("<br>", unsafe_allow_html=True)
if st.button("← BACK TO HUB", key="back_bottom", use_container_width=True):
    st.switch_page("Home.py")
