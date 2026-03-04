import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import time

st.set_page_config(
    page_title="Quant Research Lab v1.7",
    layout="wide"
)

# =========================
# DARK QUANT THEME
# =========================
st.markdown("""
<style>
body {
    background-color: #0e1117;
    color: white;
}
.metric-container {
    font-size: 28px;
    font-weight: 700;
}
.big-price {
    font-size: 52px;
    font-weight: 900;
}
.green { color: #00ff88; }
.red { color: #ff3b3b; }
</style>
""", unsafe_allow_html=True)

st.title("🧠 Quant Research Lab v1.7 – Institutional 5M Engine")

# =========================
# LIVE PRICE (FAST)
# =========================
def get_live_price():
    url = "https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT"
    r = requests.get(url, timeout=10)
    data = r.json()
    return float(data["lastPrice"]), float(data["priceChangePercent"])

# =========================
# 5 MIN HISTORICAL DATA
# =========================
@st.cache_data(ttl=30)
def get_5m_data():
    url = "https://data-api.binance.vision/api/v3/klines"
    params = {
        "symbol": "BTCUSDT",
        "interval": "5m",
        "limit": 500
    }
    r = requests.get(url, params=params, timeout=20)
    data = r.json()

    df = pd.DataFrame(data, columns=[
        'ts','Open','High','Low','Close','Vol',
        'ct','q','n','tb','tq','i'
    ])

    df['ts'] = pd.to_datetime(df['ts'], unit='ms')
    df.set_index('ts', inplace=True)

    return df[['Open','High','Low','Close','Vol']].astype(float)

# =========================
# LOAD DATA
# =========================
price, change_pct = get_live_price()
df = get_5m_data()

# =========================
# PRICE HEADER
# =========================
color_class = "green" if change_pct >= 0 else "red"
arrow = "▲" if change_pct >= 0 else "▼"

col1, col2 = st.columns([2,1])

with col1:
    st.markdown(
        f'<div class="big-price {color_class}">${price:,.2f}</div>',
        unsafe_allow_html=True
    )

with col2:
    st.markdown(
        f'<div class="{color_class}">{arrow} {change_pct:.2f}% (24H)</div>',
        unsafe_allow_html=True
    )

# =========================
# CANDLE CHART (PRO STYLE)
# =========================
fig = go.Figure()

fig.add_trace(go.Candlestick(
    x=df.index,
    open=df['Open'],
    high=df['High'],
    low=df['Low'],
    close=df['Close'],
    increasing_line_color='#00ff88',
    decreasing_line_color='#ff3b3b'
))

fig.update_layout(
    template="plotly_dark",
    height=650,
    xaxis=dict(
        showgrid=True,
        gridcolor='rgba(255,255,255,0.05)',
        tickfont=dict(size=14, color="white"),
    ),
    yaxis=dict(
        showgrid=True,
        gridcolor='rgba(255,255,255,0.05)',
        tickfont=dict(size=16, color="white"),
    ),
    font=dict(
        family="Arial",
        size=16,
        color="white"
    ),
    margin=dict(l=40, r=40, t=40, b=40)
)

st.plotly_chart(fig, use_container_width=True)

# =========================
# AUTO REFRESH
# =========================
time.sleep(10)
st.rerun()
