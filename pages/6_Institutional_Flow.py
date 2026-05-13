import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import os, sys
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from theme import (
    apply_theme, render_header,
    RH_MAROON, RH_MAROON_DK, RH_GOLD, RH_GOLD_LIGHT, RH_GOLD_DIM,
    RH_RED, RH_GREEN, RH_BG, RH_SURFACE, RH_SURFACE2, RH_TEXT, RH_MUTED, RH_BORDER
)

st.set_page_config(layout="wide", page_title="RH | Institutional Flow",
                   initial_sidebar_state="expanded")
apply_theme()
render_header("Scanner 6 · Institutional Flow Analytics")

# --- EXTRA CSS ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:wght@700;900&family=IBM+Plex+Mono:wght@300;400;500&display=swap');
.kpi-row {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 10px;
    margin-bottom: 22px;
}
.kpi {
    background: #FFFFFF;
    border: 1px solid rgba(139,26,26,0.15);
    border-top: 3px solid #8B1A1A;
    padding: 14px 16px;
    text-align: center;
}
.kpi-val {
    font-family: 'Fraunces', serif;
    font-size: 1.75rem;
    font-weight: 900;
    line-height: 1;
}
.kpi-lbl {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.6rem;
    color: #8B6A4A;
    text-transform: uppercase;
    letter-spacing: 0.16em;
    margin-top: 8px;
}
.note {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.62rem;
    color: #8B6A4A;
    margin-top: 8px;
    letter-spacing: 0.05em;
}
</style>
""", unsafe_allow_html=True)

# --- DATA LOADER ---
@st.cache_data(ttl=1800, show_spinner=False)
def load_data():
    # Look for CSV next to this file, or in parent (repo root)
    search_paths = [
        Path(__file__).parent / "fii_dii_checkpoint.csv",
        Path(__file__).parent.parent / "fii_dii_checkpoint.csv",
        Path("fii_dii_checkpoint.csv"),
    ]
    csv_path = None
    for p in search_paths:
        if p.exists():
            csv_path = p
            break

    if csv_path is None:
        return None, 0, 0

    df = pd.read_csv(csv_path, encoding='utf-8-sig')
    df.columns = df.columns.str.strip().str.upper()
    raw_rows = len(df)

    df['DATE'] = pd.to_datetime(df['DATE'], format='mixed', dayfirst=True, errors='coerce')
    df = df.dropna(subset=['DATE'])
    parsed_rows = len(df)

    for col in ['FII_NET_PURCHASE_SALES', 'DII_NET_PURCHASE_SALES', 'TOTAL_NET']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce')

    df = df.sort_values('DATE').reset_index(drop=True)
    return df, raw_rows, parsed_rows

data, raw_count, parsed_count = load_data()

if data is None:
    st.error("fii_dii_checkpoint.csv not found. Make sure it is in the repo root.")
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.markdown(
        "<div style='font-family:IBM Plex Mono,monospace;font-size:0.65rem;"
        "color:#D4A830;letter-spacing:0.14em;text-transform:uppercase;"
        "margin-bottom:14px;'>⚙ View Settings</div>",
        unsafe_allow_html=True
    )
    view_mode = st.radio(
        "Aggregation",
        ["Daily", "Monthly", "Yearly"],
        index=1
    )
    st.markdown("---")
    st.markdown(
        f"<div class='note'>Rows in CSV: {raw_count}<br>Rows plotted: {parsed_count}</div>",
        unsafe_allow_html=True
    )
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("⟳ REFRESH", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# --- AGGREGATE ---
if view_mode == "Yearly":
    plot_df = data.set_index('DATE').resample('YE').sum(numeric_only=True).reset_index()
    plot_df['DISPLAY_DATE'] = plot_df['DATE'].dt.strftime('%Y')
    sma_window = 2
elif view_mode == "Monthly":
    plot_df = data.set_index('DATE').resample('ME').sum(numeric_only=True).reset_index()
    plot_df['DISPLAY_DATE'] = plot_df['DATE'].dt.strftime("%b '%y")
    sma_window = 3
else:
    plot_df = data.copy()
    plot_df['DISPLAY_DATE'] = plot_df['DATE'].dt.strftime('%d %b %y')
    sma_window = 20

plot_df['FII_SMA'] = plot_df['FII_NET_PURCHASE_SALES'].rolling(window=sma_window, min_periods=1).mean()
plot_df['DII_SMA'] = plot_df['DII_NET_PURCHASE_SALES'].rolling(window=sma_window, min_periods=1).mean()
plot_df['TOTAL_SMA'] = plot_df['TOTAL_NET'].rolling(window=sma_window, min_periods=1).mean()

roll_win = 60 if view_mode == "Daily" else 12
fii_mean = plot_df['FII_NET_PURCHASE_SALES'].rolling(window=roll_win, min_periods=5).mean()
fii_std  = plot_df['FII_NET_PURCHASE_SALES'].rolling(window=roll_win, min_periods=5).std()
plot_df['FII_Z_SCORE'] = (plot_df['FII_NET_PURCHASE_SALES'] - fii_mean) / fii_std.replace(0, np.nan)
plot_df['ABSORPTION_RATIO'] = np.where(
    plot_df['FII_NET_PURCHASE_SALES'] < 0,
    abs(plot_df['DII_NET_PURCHASE_SALES'] / plot_df['FII_NET_PURCHASE_SALES'].replace(0, np.nan)),
    np.nan
)

# --- KPI ROW ---
latest = plot_df.iloc[-1]
fii_val   = latest['FII_NET_PURCHASE_SALES']
dii_val   = latest['DII_NET_PURCHASE_SALES']
tot_val   = latest['TOTAL_NET']
fii_z     = latest['FII_Z_SCORE']
fii_30    = plot_df.tail(30)['FII_NET_PURCHASE_SALES'].sum() if view_mode == "Daily" else plot_df.tail(3)['FII_NET_PURCHASE_SALES'].sum()

def fmt_cr(v):
    if pd.isna(v): return "—"
    sign = "+" if v > 0 else ""
    col  = RH_GREEN if v > 0 else RH_RED
    return f'<span style="color:{col}">{sign}₹{v:,.0f} Cr</span>'

def fmt_z(v):
    if pd.isna(v): return "—"
    col = RH_GREEN if v > 0 else RH_RED
    return f'<span style="color:{col}">{v:+.2f}σ</span>'

period_lbl = "30D FII" if view_mode == "Daily" else "3M FII"

st.markdown(f"""
<div class="kpi-row">
    <div class="kpi">
        <div class="kpi-val">{fmt_cr(fii_val)}</div>
        <div class="kpi-lbl">FII Net · Latest</div>
    </div>
    <div class="kpi">
        <div class="kpi-val">{fmt_cr(dii_val)}</div>
        <div class="kpi-lbl">DII Net · Latest</div>
    </div>
    <div class="kpi">
        <div class="kpi-val">{fmt_cr(tot_val)}</div>
        <div class="kpi-lbl">Combined Net · Latest</div>
    </div>
    <div class="kpi">
        <div class="kpi-val">{fmt_z(fii_z)}</div>
        <div class="kpi-lbl">FII Z-Score</div>
    </div>
    <div class="kpi">
        <div class="kpi-val">{fmt_cr(fii_30)}</div>
        <div class="kpi-lbl">{period_lbl} Cumulative</div>
    </div>
</div>
""", unsafe_allow_html=True)

# --- TIMEFRAME SELECTOR ---
if view_mode == "Yearly":
    tf_options = ["Max"]
    default_idx = 0
else:
    tf_options = ["1 Month", "3 Months", "6 Months", "1 Year", "3 Years", "5 Years", "Max"]
    default_idx = 6

timeframes = {
    "1 Month":  pd.DateOffset(months=1),
    "3 Months": pd.DateOffset(months=3),
    "6 Months": pd.DateOffset(months=6),
    "1 Year":   pd.DateOffset(years=1),
    "3 Years":  pd.DateOffset(years=3),
    "5 Years":  pd.DateOffset(years=5),
    "Max":      None
}

selected_tf = st.radio("Timeframe:", options=tf_options, horizontal=True, index=default_idx)
if timeframes[selected_tf] is not None:
    cutoff = plot_df['DATE'].max() - timeframes[selected_tf]
    fdf = plot_df[plot_df['DATE'] >= cutoff].copy()
else:
    fdf = plot_df.copy()

# --- CHART HELPER ---
def bar_with_avg(df, y_col, sma_col, title, pos_color, neg_color, avg_color):
    colors = [pos_color if v >= 0 else neg_color for v in df[y_col].fillna(0)]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df['DISPLAY_DATE'], y=df[y_col],
        name="Net Flow",
        marker_color=colors,
        opacity=0.75,
        hovertemplate="%{x}<br>₹%{y:,.0f} Cr<extra></extra>"
    ))
    if not df[sma_col].isnull().all():
        fig.add_trace(go.Scatter(
            x=df['DISPLAY_DATE'], y=df[sma_col],
            mode='lines', name=f"{sma_window}P Avg",
            line=dict(color=avg_color, width=2.5, dash='solid'),
            hovertemplate="%{x}<br>Avg: ₹%{y:,.0f} Cr<extra></extra>"
        ))
    fig.update_layout(
        title=dict(text=title, font=dict(family="IBM Plex Mono", color=RH_TEXT, size=13)),
        plot_bgcolor=RH_BG,
        paper_bgcolor=RH_SURFACE2,
        font=dict(family="IBM Plex Mono", color=RH_MUTED, size=10),
        hovermode="x unified",
        height=320,
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    font=dict(size=9)),
        xaxis=dict(
            type='category',
            categoryorder='array',
            categoryarray=df['DISPLAY_DATE'].tolist(),
            nticks=20,
            gridcolor='rgba(139,26,26,0.08)',
            tickfont=dict(size=9)
        ),
        yaxis=dict(gridcolor='rgba(139,26,26,0.08)', zeroline=True,
                   zerolinecolor=RH_MAROON, zerolinewidth=1)
    )
    return fig

# --- TABS ---
tab1, tab2 = st.tabs(["📉 Trend & Averages", "⚡ Statistical Extremes"])

with tab1:
    st.markdown(
        f"<div style='font-family:IBM Plex Mono,monospace;font-size:0.7rem;"
        f"color:{RH_GOLD_DIM};margin:8px 0 16px;letter-spacing:0.14em;text-transform:uppercase;'>"
        f"<span style='color:{RH_GOLD_LIGHT};font-weight:500;'>▶</span>"
        f"&nbsp;&nbsp;FII / DII / Combined — {view_mode} view</div>",
        unsafe_allow_html=True
    )
    st.plotly_chart(
        bar_with_avg(fdf, 'FII_NET_PURCHASE_SALES', 'FII_SMA',
                     'FII Net Flow', '#2E7D32', '#C0392B', RH_MAROON),
        use_container_width=True
    )
    st.plotly_chart(
        bar_with_avg(fdf, 'DII_NET_PURCHASE_SALES', 'DII_SMA',
                     'DII Net Flow', RH_GOLD, '#C0392B', RH_MAROON_DK),
        use_container_width=True
    )
    st.plotly_chart(
        bar_with_avg(fdf, 'TOTAL_NET', 'TOTAL_SMA',
                     'Combined Net Flow', '#2E7D32', '#C0392B', RH_GOLD_DIM),
        use_container_width=True
    )

with tab2:
    if len(fdf) > 1:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(
                f"<div style='font-family:IBM Plex Mono,monospace;font-size:0.7rem;"
                f"color:{RH_GOLD_DIM};margin:8px 0 14px;letter-spacing:0.14em;'>"
                f"<span style='color:{RH_GOLD_LIGHT};'>▶</span>&nbsp;FII Z-Score (Deviation from {roll_win}-period mean)</div>",
                unsafe_allow_html=True
            )
            z_colors = [RH_GREEN if v >= 0 else RH_RED for v in fdf['FII_Z_SCORE'].fillna(0)]
            fig_z = go.Figure()
            fig_z.add_trace(go.Bar(
                x=fdf['DISPLAY_DATE'], y=fdf['FII_Z_SCORE'],
                marker_color=z_colors, opacity=0.8,
                hovertemplate="%{x}<br>Z: %{y:.2f}σ<extra></extra>"
            ))
            fig_z.add_hline(y=2, line_dash="dot", line_color=RH_RED, annotation_text="2σ", annotation_font_color=RH_RED)
            fig_z.add_hline(y=-2, line_dash="dot", line_color=RH_GREEN, annotation_text="-2σ", annotation_font_color=RH_GREEN)
            fig_z.update_layout(
                plot_bgcolor=RH_BG, paper_bgcolor=RH_SURFACE2,
                font=dict(family="IBM Plex Mono", color=RH_MUTED, size=10),
                hovermode="x unified", height=340,
                margin=dict(l=10, r=10, t=20, b=10),
                xaxis=dict(type='category', nticks=12, gridcolor='rgba(139,26,26,0.08)'),
                yaxis=dict(gridcolor='rgba(139,26,26,0.08)', zeroline=True,
                           zerolinecolor=RH_MAROON, zerolinewidth=1)
            )
            st.plotly_chart(fig_z, use_container_width=True)

        with c2:
            st.markdown(
                f"<div style='font-family:IBM Plex Mono,monospace;font-size:0.7rem;"
                f"color:{RH_GOLD_DIM};margin:8px 0 14px;letter-spacing:0.14em;'>"
                f"<span style='color:{RH_GOLD_LIGHT};'>▶</span>&nbsp;DII Absorption Ratio (on FII sell days)</div>",
                unsafe_allow_html=True
            )
            sell_days = fdf[fdf['FII_NET_PURCHASE_SALES'] < 0].copy()
            if not sell_days.empty:
                dot_colors = [RH_GREEN if v >= 1 else RH_MUTED for v in sell_days['ABSORPTION_RATIO'].fillna(0)]
                fig_abs = go.Figure()
                fig_abs.add_trace(go.Scatter(
                    x=sell_days['DISPLAY_DATE'], y=sell_days['ABSORPTION_RATIO'],
                    mode='markers',
                    marker=dict(size=10, color=dot_colors, line=dict(width=1, color=RH_MAROON)),
                    hovertemplate="%{x}<br>Ratio: %{y:.2f}x<extra></extra>"
                ))
                fig_abs.add_hline(y=1, line_dash="dot", line_color=RH_MAROON,
                                  annotation_text="Full absorption", annotation_font_color=RH_MUTED)
                fig_abs.update_layout(
                    plot_bgcolor=RH_BG, paper_bgcolor=RH_SURFACE2,
                    font=dict(family="IBM Plex Mono", color=RH_MUTED, size=10),
                    hovermode="x unified", height=340,
                    margin=dict(l=10, r=10, t=20, b=10),
                    yaxis=dict(range=[0, 3.2], gridcolor='rgba(139,26,26,0.08)'),
                    xaxis=dict(type='category', nticks=12, gridcolor='rgba(139,26,26,0.08)')
                )
                st.plotly_chart(fig_abs, use_container_width=True)
            else:
                st.info("No net FII sell days in current selection.")
    else:
        st.info("Not enough data points for statistical extremes in current selection.")

# --- DATA TABLE (expander) ---
with st.expander("📋 Raw Data Table", expanded=False):
    show_cols = ['DISPLAY_DATE', 'FII_NET_PURCHASE_SALES', 'DII_NET_PURCHASE_SALES', 'TOTAL_NET']
    st.dataframe(
        fdf[show_cols].rename(columns={
            'DISPLAY_DATE': 'Date',
            'FII_NET_PURCHASE_SALES': 'FII Net (Cr)',
            'DII_NET_PURCHASE_SALES': 'DII Net (Cr)',
            'TOTAL_NET': 'Total Net (Cr)'
        }).sort_values('Date', ascending=False),
        use_container_width=True, height=320
    )

st.markdown(
    f"<div class='note'>Data: fii_dii_checkpoint.csv · Auto-updated daily via GitHub Actions · "
    f"Rows: {parsed_count}</div>",
    unsafe_allow_html=True
)

st.markdown("<br>", unsafe_allow_html=True)
if st.button("← BACK TO HUB", use_container_width=True):
    st.switch_page("Home.py")
