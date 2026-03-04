import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from streamlit_autorefresh import st_autorefresh

# =========================
# CONFIG
# =========================
st.set_page_config(
    page_title="Bitcoin Indy v1.4",
    layout="wide"
)

# 🔥 เร็วขึ้น (ทุก 8 วิ)
st_autorefresh(interval=8000, key="btc_refresh")

# =========================
# DARK THEME STYLE
# =========================
st.markdown("""
<style>
.stApp {
    background-color: #0b0f14;
    color: #e6edf3;
}
[data-testid="stMetricValue"] {
    font-size: 70px !important;
    font-weight: 900 !important;
    color: #ffffff;
}
[data-testid="stMetricDelta"] {
    font-size: 20px !important;
}
</style>
""", unsafe_allow_html=True)

# =========================
# DATA FETCH
# =========================
@st.cache_data(ttl=20)  # ลด cache ให้สดขึ้น
def get_historical_data():
    url = "https://data-api.binance.vision/api/v3/klines"

    params = {
        "symbol": "BTCUSDT",
        "interval": "1m",
        "limit": 500
    }

    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        res = requests.get(url, params=params, headers=headers, timeout=15)

        if res.status_code != 200:
            st.error(f"HTTP Error {res.status_code}")
            return pd.DataFrame()

        data = res.json()

        df = pd.DataFrame(data, columns=[
            'ts','Open','High','Low','Close','Vol',
            'ct','q','n','tb','tq','i'
        ])

        df['ts'] = pd.to_datetime(df['ts'], unit='ms')
        df.set_index('ts', inplace=True)

        return df[['Open','High','Low','Close','Vol']].astype(float)

    except Exception as e:
        st.error(f"Data Fetch Error: {e}")
        return pd.DataFrame()

# =========================
# MCC
# =========================
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

# =========================
# MAIN
# =========================
st.title("🟢 Bitcoin Indy v1.4 – Dark Institutional")

df = get_historical_data()
if df.empty:
    st.stop()

mcc = calculate_mcc(df)

last_price = mcc['Close'].iloc[-1]

st.metric("BTC / USDT", f"{last_price:,.2f}")

# =========================
# CHART
# =========================
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
    name="Upper",
    line=dict(color="#ff4d4f", width=2)
))

fig.add_trace(go.Scatter(
    x=view.index,
    y=view['lower'],
    name="Lower",
    line=dict(color="#00c853", width=2)
))

fig.update_layout(
    template="plotly_dark",
    xaxis_rangeslider_visible=False,
    height=700,
    paper_bgcolor="#0b0f14",
    plot_bgcolor="#0b0f14"
)

st.plotly_chart(fig, use_container_width=True)
