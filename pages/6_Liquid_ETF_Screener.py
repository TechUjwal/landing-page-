"""
Scanner 06 — Liquid ETF Screener
Finviz-style treemap for the 160 most-liquid ETFs across 21 curated categories.
Box size = 30D volume, color = performance over selected window.
Mirrors Scanner 02 (Global ETF Screener) structure with the curated liquid universe.
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime
import os, sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from theme import (
    apply_theme, render_header,
    RH_MAROON, RH_MAROON_DK, RH_GOLD, RH_GOLD_LIGHT, RH_GOLD_DIM,
    RH_RED, RH_GREEN, RH_BG, RH_SURFACE, RH_SURFACE2, RH_TEXT, RH_MUTED, RH_BORDER
)

st.set_page_config(layout="wide", page_title="RH | Liquid ETF Screener",
                   initial_sidebar_state="expanded")
apply_theme()
render_header("Scanner 06 · Liquid ETF Screener")


# ─────────────────────────────────────────────────────
#  SUPER-CATEGORY MAPPING (for treemap top level)
# ─────────────────────────────────────────────────────
def super_category(cat: str) -> str:
    if cat.startswith("US Equity"):       return "🇺🇸 US Equity"
    if cat.startswith("Factor"):           return "📊 Factor / Smart Beta"
    if cat.startswith("Fixed Income"):     return "🏦 Fixed Income"
    if cat.startswith("Commodities"):      return "🪙 Commodities"
    if cat.startswith("Alternatives"):     return "🔀 Alternatives"
    if cat.startswith("Thematic"):         return "🚀 Thematic"
    if cat.startswith("Geography"):        return "🌍 Geography"
    return "Other"


# ─────────────────────────────────────────────────────
#  DATA
# ─────────────────────────────────────────────────────
@st.cache_data
def load_baseline():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates = [
        os.path.join(root, "data", "liquid_etf_baseline.csv"),
        os.path.join(root, "liquid_etf_baseline.csv"),
        "liquid_etf_baseline.csv",
    ]
    csv_path = next((p for p in candidates if os.path.exists(p)), None)
    if not csv_path:
        return pd.DataFrame()

    df = pd.read_csv(csv_path)
    df["Ticker"]   = df["Ticker"].astype(str).str.strip()
    df["Category"] = df["Category"].fillna("Other")
    df["Segment"]  = df["Segment"].fillna(df["Ticker"])
    df["Name"]     = df["Name"].fillna(df["Ticker"])
    df["Super"]    = df["Category"].apply(super_category)

    for col in ["1W (%)", "1M (%)", "3M (%)", "6M (%)", "1Y (%)"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


@st.cache_data(ttl=600, show_spinner=False)
def fetch_one(ticker: str):
    try:
        import yfinance as yf
        tk = yf.Ticker(ticker)
        data = tk.history(period="1mo", interval="1d", auto_adjust=True, timeout=10)
        if data is None or data.empty or "Close" not in data.columns:
            return np.nan, np.nan, np.nan
        closes = data["Close"].dropna()
        vol = data["Volume"].dropna() if "Volume" in data.columns else pd.Series(dtype=float)
        if len(closes) >= 2:
            latest = float(closes.iloc[-1])
            prev   = float(closes.iloc[-2])
            ret_1d = round(((latest - prev) / prev) * 100, 2)
        else:
            latest, ret_1d = np.nan, np.nan
        avg_vol = float(vol.mean()) if len(vol) > 0 else np.nan
        return latest, ret_1d, avg_vol
    except Exception:
        return np.nan, np.nan, np.nan


def get_live_data(tickers: list) -> pd.DataFrame:
    records = []
    progress = st.progress(0, text="Fetching live ETF prices…")
    n = len(tickers)
    success = 0
    for i, t in enumerate(tickers):
        latest, ret_1d, avg_vol = fetch_one(t)
        if not np.isnan(latest):
            success += 1
        records.append({
            "Ticker": t,
            "Live_CMP": latest,
            "Dynamic_1D_Return": ret_1d,
            "30D_Volume": avg_vol,
        })
        progress.progress((i + 1) / n, text=f"Fetching {t}… ({i+1}/{n}) • ✓ {success}")
    progress.empty()
    return pd.DataFrame(records)


# ─────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────
df_baseline = load_baseline()

if df_baseline.empty:
    st.error("`liquid_etf_baseline.csv` not found. Place it at the project root or in `/data`.")
    st.markdown(
        f"<div style='color:{RH_MUTED}; font-size:11px; margin-top:8px;'>"
        f"Run <code>update_liquid_etf.py</code> to generate it.</div>",
        unsafe_allow_html=True
    )
    if st.button("← BACK TO HUB", key="back_top"):
        st.switch_page("Home.py")
    st.stop()

tickers_list = df_baseline["Ticker"].dropna().unique().tolist()

# ── Refresh control ──
col_refresh, col_ts = st.columns([1, 5])
with col_refresh:
    refresh_clicked = st.button("⟳ REFRESH LIVE", use_container_width=True, type="primary")
with col_ts:
    if "lqetf_last_refresh" in st.session_state:
        st.markdown(
            f"<div style='color:{RH_MUTED}; font-size:10px; letter-spacing:0.12em; "
            f"text-transform:uppercase; padding-top:8px;'>"
            f"Last updated: <span style='color:{RH_GOLD_LIGHT};'>{st.session_state.lqetf_last_refresh}</span> · "
            f"<span style='color:{RH_GOLD_LIGHT};'>{len(tickers_list)}</span> ETFs tracked"
            f"</div>",
            unsafe_allow_html=True
        )

if refresh_clicked or "lqetf_df_merged" not in st.session_state:
    df_live = get_live_data(tickers_list)

    good = int(df_live["Live_CMP"].notna().sum())
    bad  = int(df_live["Live_CMP"].isna().sum())
    if bad > 0:
        st.warning(
            f"Yahoo Finance returned data for {good}/{good+bad} tickers. "
            f"{bad} failed (rate limits or invalid symbols)."
        )

    df_merged = pd.merge(df_baseline, df_live, on="Ticker", how="left")
    df_merged["Intraday 1D (%)"] = df_merged.get("Dynamic_1D_Return", np.nan)

    if "52W High" in df_merged.columns and "52W Low" in df_merged.columns:
        df_merged["% From 52W High"] = ((df_merged["Live_CMP"] - df_merged["52W High"]) / df_merged["52W High"] * 100).round(2)
        df_merged["% From 52W Low"]  = ((df_merged["Live_CMP"] - df_merged["52W Low"])  / df_merged["52W Low"]  * 100).round(2)

    for col in ["Live_CMP", "Intraday 1D (%)"]:
        if col in df_merged.columns:
            df_merged[col] = pd.to_numeric(df_merged[col], errors="coerce").round(2)

    st.session_state.lqetf_df_merged = df_merged
    st.session_state.lqetf_last_refresh = datetime.now().strftime("%d %b %Y %H:%M:%S")
    st.rerun()

df = st.session_state.lqetf_df_merged

# ── KPI ROW ──
total = len(df)
gainers = int((df["Intraday 1D (%)"] > 0).sum())
losers  = int((df["Intraday 1D (%)"] < 0).sum())
avg_ret = df["Intraday 1D (%)"].mean()
avg_str = f"{avg_ret:+.2f}%" if not np.isnan(avg_ret) else "—"

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total ETFs", total)
c2.metric("Gainers", gainers, f"+{gainers} today" if gainers else "—")
c3.metric("Losers", losers, f"-{losers} today" if losers else "—", delta_color="inverse")
c4.metric("Avg 1D Return", avg_str)

st.divider()

# ── FILTERS ──
with st.expander("FILTERS", expanded=True):
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        sel_supers = st.multiselect("Super-Category",
                                     options=sorted(df["Super"].dropna().unique()))
    with fc2:
        avail_cats = sorted(df["Category"].dropna().unique())
        if sel_supers:
            avail_cats = sorted(df[df["Super"].isin(sel_supers)]["Category"].dropna().unique())
        sel_cats = st.multiselect("Category", options=avail_cats)
    with fc3:
        sel_amcs = st.multiselect("AMC / Issuer",
                                   options=sorted(df.get("AMC", pd.Series(dtype=str)).dropna().unique())
                                   if "AMC" in df.columns else [])

filtered = df.copy()
if sel_supers: filtered = filtered[filtered["Super"].isin(sel_supers)]
if sel_cats:   filtered = filtered[filtered["Category"].isin(sel_cats)]
if sel_amcs and "AMC" in filtered.columns:
    filtered = filtered[filtered["AMC"].isin(sel_amcs)]

# ── TREEMAP ──
st.subheader("Capital Rotation Treemap")

timeframe_options = {
    "1 Day": "Intraday 1D (%)",
    "1 Week": "1W (%)",
    "1 Month": "1M (%)",
    "3 Months": "3M (%)",
    "6 Months": "6M (%)",
    "1 Year": "1Y (%)",
}

tc1, tc2 = st.columns([3, 2])
with tc1:
    sel_tf = st.radio("Performance window",
                       options=list(timeframe_options.keys()),
                       horizontal=True, label_visibility="collapsed")
with tc2:
    st.markdown(
        f"<div style='color:{RH_MUTED}; font-size:10px; letter-spacing:0.1em; "
        f"text-transform:uppercase; padding-top:6px; text-align:right;'>"
        f"BOX SIZE = 30D VOLUME · COLOR = RETURN</div>",
        unsafe_allow_html=True
    )

metric_col = timeframe_options[sel_tf]
plot_df = filtered.dropna(subset=["Ticker"]).copy()

if metric_col in plot_df.columns:
    plot_df[metric_col] = pd.to_numeric(plot_df[metric_col], errors="coerce")
else:
    plot_df[metric_col] = np.nan

plot_df["30D_Volume"] = pd.to_numeric(
    plot_df.get("30D_Volume", 1000), errors="coerce"
).fillna(1000).clip(lower=1)

plot_df = plot_df.dropna(subset=[metric_col])

if plot_df.empty:
    st.warning("No ETFs match the selected filters or have data for this timeframe.")
else:
    c_range_map = {
        "1 Day": [-3, 3], "1 Week": [-5, 5], "1 Month": [-10, 10],
        "3 Months": [-20, 20], "6 Months": [-25, 25], "1 Year": [-35, 35]
    }
    c_range = c_range_map.get(sel_tf, [-10, 10])

    plot_df["_pct"] = plot_df[metric_col].apply(
        lambda v: f"{v:+.2f}%" if pd.notna(v) else ""
    )

    fig = px.treemap(
        plot_df,
        path=[px.Constant("Liquid ETFs"), "Super", "Category", "Ticker"],
        values="30D_Volume",
        color=metric_col,
        color_continuous_scale=[
            [0.0,  "#8B0000"],
            [0.2,  "#CC3333"],
            [0.35, "#E8795A"],
            [0.45, "#F5C4A8"],
            [0.5,  "#F0EDE8"],
            [0.55, "#B8D4B0"],
            [0.65, "#6DBF67"],
            [0.8,  "#2E8B57"],
            [1.0,  "#1A5E2A"],
        ],
        range_color=c_range,
        custom_data=["Name", "_pct"]
    )

    fig.update_layout(
        height=560,
        margin=dict(t=10, l=5, r=5, b=5),
        paper_bgcolor="#F5ECD7",
        plot_bgcolor="#F5ECD7",
        font=dict(family="IBM Plex Mono", color="#2C1810"),
        coloraxis_colorbar=dict(
            title=dict(text="Return (%)", font=dict(size=10, color=RH_MAROON, family="IBM Plex Mono")),
            thicknessmode="pixels", thickness=14,
            lenmode="pixels", len=280,
            yanchor="top", y=1,
            ticks="outside",
            tickfont=dict(size=10, color=RH_MUTED, family="IBM Plex Mono"),
            outlinecolor="rgba(139,26,26,0.2)",
        )
    )

    fig.update_traces(
        texttemplate="<b>%{label}</b><br>%{customdata[1]}",
        textfont=dict(size=12, family="IBM Plex Mono", color="#1A1A1A"),
        marker_line_color="#FFFFFF",
        marker_line_width=2,
        hovertemplate=(
            "<b>%{label}</b><br>"
            "<i>%{customdata[0]}</i><br>"
            "────────────<br>"
            "Return : <b>%{customdata[1]}</b><br>"
            "Avg vol: <b>%{value:,.0f}</b>"
            "<extra></extra>"
        )
    )

    st.plotly_chart(fig, use_container_width=True, theme=None)

# ── DATA TABLE ──
st.subheader("Underlying Performance Data")

display_cols = [
    "Ticker", "Name", "Category", "Segment", "AMC",
    "Live_CMP", "Intraday 1D (%)",
    "1W (%)", "1M (%)", "3M (%)", "6M (%)", "1Y (%)",
    "% From 52W High", "% From 52W Low", "30D_Volume"
]
valid_cols = [c for c in display_cols if c in plot_df.columns]
sort_col = "Intraday 1D (%)" if "Intraday 1D (%)" in valid_cols else valid_cols[0]

styled = plot_df[valid_cols].sort_values(by=sort_col, ascending=False).reset_index(drop=True)
pct_cols = [c for c in valid_cols if "(%)" in c]


def color_pct(val):
    try:
        v = float(val)
        if v > 0: return f"color: {RH_GREEN}; font-weight:500"
        elif v < 0: return f"color: {RH_RED}; font-weight:500"
    except (TypeError, ValueError):
        pass
    return ""


st.dataframe(
    styled.style.map(color_pct, subset=pct_cols)
    .format({c: "{:.2f}" for c in pct_cols if c in styled.columns}, na_rep="—")
    .format({"Live_CMP": "{:.2f}", "30D_Volume": "{:,.0f}"}, na_rep="—"),
    use_container_width=True, hide_index=True, height=420
)

st.markdown("<br>", unsafe_allow_html=True)
if st.button("← BACK TO HUB", use_container_width=True, key="back_bottom"):
    st.switch_page("Home.py")
