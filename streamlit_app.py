import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from streamlit_autorefresh import st_autorefresh

# ======================================
# CONFIG
# ======================================
st.set_page_config(
    page_title="Bitcoin Indy v1.5 Pro",
    layout="wide"
)

# Refresh ทุก 7 วิ (เร็วแต่ Cloud safe)
st_autorefresh(interval=7000, key="btc_refresh")

# ======================================
# DARK PRO STYLE
# ======================================
st.markdown("""
<style>
.stApp {
    background-color: #0a0e13;
    color: #e6edf3;
}
h1 {
    font-weight: 800;
}
[data-testid="stMetricValue"] {
    font-size: 64px !important;
    font-weight: 900 !important;
}
[data-testid="stMetricDelta"] {
    font-size: 20px !important;
}
.block-container {
    padding-top: 1rem;
}
</style>
""", unsafe_allow_html=True)

# ======================================
# DATA FETCH
# ======================================
@st.cache_data(ttl=15)
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

@st.cache_data(ttl=15)
def get_24h():
    try:
        url = "https://data-api.binance.vision/api/v3/ticker/24hr"
        res = requests.get(url, params={"symbol":"BTCUSDT"}, timeout=10)
        return res.json()
    except:
        return {}

# ======================================
# MCC ENGINE
# ======================================
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

# ======================================
# MAIN
# ======================================
st.title("🚀 Bitcoin Indy v1.5 Pro Engine")

df = get_data()
if df.empty:
    st.error("Data unavailable")
    st.stop()

stats = get_24h()
mcc = calculate_mcc(df)

last_price = mcc['Close'].iloc[-1]
pct_24h = float(stats.get("priceChangePercent", 0))
volume_24h = float(stats.get("volume", 0))

# ======================================
# HEADER METRICS
# ======================================
col1, col2, col3 = st.columns(3)

col1.metric("BTC / USDT", f"{last_price:,.2f}", f"{pct_24h:+.2f}%")
col2.metric("24H Volume", f"{volume_24h:,.0f}")
col3.metric("ATR", f"{mcc['atr'].iloc[-1]:.2f}")

st.divider()

# ======================================
# CHART
# ======================================
view = mcc.tail(150)

fig = go.Figure()

fig.add_trace(go.Candlestick(
    x=view.index,
    open=view['Open'],
    high=view['High'],
    low=view['Low'],
    close=view['Close'],
    name="Price"
))

fig.add_trace(go.Scatter(
    x=view.index,
    y=view['trend'],
    name="EMA 50",
    line=dict(color="#f1c40f", width=1)
))

fig.add_trace(go.Scatter(
    x=view.index,
    y=view['upper'],
    name="Upper Band",
    line=dict(color="#ff4d4f", width=2)
))

fig.add_trace(go.Scatter(
    x=view.index,
    y=view['lower'],
    name="Lower Band",
    line=dict(color="#00e676", width=2)
))

for t in view.index[view['rev_long']]:
    fig.add_annotation(
        x=t,
        y=view.loc[t,'Low'],
        text="LONG",
        bgcolor="#00e676",
        font=dict(color="black"),
        ay=40
    )

for t in view.index[view['rev_short']]:
    fig.add_annotation(
        x=t,
        y=view.loc[t,'High'],
        text="SHORT",
        bgcolor="#ff4d4f",
        font=dict(color="white"),
        ay=-40
    )

fig.update_layout(
    template="plotly_dark",
    paper_bgcolor="#0a0e13",
    plot_bgcolor="#0a0e13",
    height=750,
    xaxis_rangeslider_visible=False
)

st.plotly_chart(fig, use_container_width=True)
