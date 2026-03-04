import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from streamlit_autorefresh import st_autorefresh

# =========================================
# CONFIG
# =========================================
st.set_page_config(page_title="Bitcoin Indy v1.6 Quant Lab", layout="wide")

# Refresh 6 วินาที (เร็ว + ปลอดภัย)
st_autorefresh(interval=6000, key="quant_refresh")

# =========================================
# QUANT DARK THEME
# =========================================
st.markdown("""
<style>
.stApp {
    background-color: #05080f;
    color: #e0e6ed;
}
h1 {
    font-weight: 800;
    letter-spacing: 1px;
}
[data-testid="stMetricValue"] {
    font-size: 72px !important;
    font-weight: 900 !important;
}
[data-testid="stMetricDelta"] {
    font-size: 22px !important;
}
.block-container {
    padding-top: 1rem;
}
</style>
""", unsafe_allow_html=True)

# =========================================
# DATA FETCH
# =========================================
@st.cache_data(ttl=10)
def get_data():
    url = "https://data-api.binance.vision/api/v3/klines"
    params = {"symbol": "BTCUSDT", "interval": "1m", "limit": 500}
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        res = requests.get(url, params=params, headers=headers, timeout=15)
        res.raise_for_status()
        data = res.json()

        df = pd.DataFrame(data, columns=[
            'ts','Open','High','Low','Close','Vol',
            'ct','q','n','tb','tq','i'
        ])

        df['ts'] = pd.to_datetime(df['ts'], unit='ms')
        df.set_index('ts', inplace=True)
        df = df[['Open','High','Low','Close','Vol']].astype(float)

        return df
    except:
        return pd.DataFrame()

@st.cache_data(ttl=10)
def get_24h():
    try:
        url = "https://data-api.binance.vision/api/v3/ticker/24hr"
        res = requests.get(url, params={"symbol":"BTCUSDT"}, timeout=10)
        return res.json()
    except:
        return {}

# =========================================
# MCC ENGINE
# =========================================
def calculate_mcc(df):

    temp = df.copy()

    temp['trend'] = temp['Close'].ewm(span=50, adjust=False).mean()

    hl = temp['High'] - temp['Low']
    hc = abs(temp['High'] - temp['Close'].shift())
    lc = abs(temp['Low'] - temp['Close'].shift())

    temp['atr'] = pd.concat([hl, hc, lc], axis=1).max(axis=1).rolling(50).mean()
    temp['atr'] = temp['atr'].replace(0, np.nan)

    temp['q'] = (temp['Close'] - temp['trend']) / temp['atr']
    temp['vol'] = temp['q'].rolling(200).std()
    temp['csl'] = 2.0 * temp['vol']

    temp['upper'] = temp['trend'] + temp['csl'] * temp['atr']
    temp['lower'] = temp['trend'] - temp['csl'] * temp['atr']

    temp['q_slope'] = temp['q'].diff()

    temp['rev_long'] = (temp['q'] < -temp['csl'] * 1.05) & (temp['q_slope'] > 0)
    temp['rev_short'] = (temp['q'] > temp['csl'] * 1.05) & (temp['q_slope'] < 0)

    return temp

# =========================================
# MAIN
# =========================================
st.title("🧪 Bitcoin Indy – Quant Research Lab v1.6")

df = get_data()
if df.empty:
    st.error("Market data unavailable")
    st.stop()

stats = get_24h()
mcc = calculate_mcc(df)

last_price = mcc['Close'].iloc[-1]
prev_price = mcc['Close'].iloc[-2]
pct_24h = float(stats.get("priceChangePercent", 0))
volume_24h = float(stats.get("volume", 0))

# Dynamic color
price_color = "#00ff88" if last_price > prev_price else "#ff4d4f"

# =========================================
# HEADER PANEL
# =========================================
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(f"<h2 style='color:{price_color}; font-size:60px;'>${last_price:,.2f}</h2>", unsafe_allow_html=True)
    st.markdown("BTC / USDT")

with col2:
    st.metric("24H Change", f"{pct_24h:+.2f}%")

with col3:
    st.metric("24H Volume", f"{volume_24h:,.0f}")

st.divider()

# =========================================
# CHART
# =========================================
view = mcc.tail(200)

fig = go.Figure()

fig.add_trace(go.Candlestick(
    x=view.index,
    open=view['Open'],
    high=view['High'],
    low=view['Low'],
    close=view['Close'],
    increasing_line_color="#00ff88",
    decreasing_line_color="#ff4d4f",
    name="Price"
))

fig.add_trace(go.Scatter(
    x=view.index,
    y=view['trend'],
    name="EMA 50",
    line=dict(color="#ffd166", width=2)
))

fig.add_trace(go.Scatter(
    x=view.index,
    y=view['upper'],
    name="Upper Band",
    line=dict(color="#ff4d4f", width=3)
))

fig.add_trace(go.Scatter(
    x=view.index,
    y=view['lower'],
    name="Lower Band",
    line=dict(color="#00ff88", width=3)
))

fig.update_layout(
    template="plotly_dark",
    paper_bgcolor="#05080f",
    plot_bgcolor="#05080f",
    height=800,
    xaxis_rangeslider_visible=False,
    font=dict(size=14)
)

st.plotly_chart(fig, use_container_width=True)
