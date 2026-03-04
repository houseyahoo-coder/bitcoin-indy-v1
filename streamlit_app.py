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

st_autorefresh(interval=15000, key="btc_refresh")  # refresh ทุก 15 วิ (Cloud safe)

# =========================
# STYLE
# =========================
st.markdown("""
<style>
.stApp { background-color: #0b0e11; color: white; }
div[data-testid="stMetricValue"] > div {
    font-size: 60px !important;
    font-weight: 900 !important;
    font-family: 'Courier New', monospace;
}
</style>
""", unsafe_allow_html=True)

# =========================
# DATA FETCH (Cloud Safe)
# =========================
@st.cache_data(ttl=60)
def get_historical_data():
    url = "https://data-api.binance.vision/api/v3/klines"
    params = {
        "symbol": "BTCUSDT",
        "interval": "1m",
        "limit": 500
    }

    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        res = requests.get(url, params=params, headers=headers, timeout=20)

        if res.status_code != 200:
            st.error(f"HTTP Error {res.status_code}")
            return pd.DataFrame()

        data = res.json()

        if not isinstance(data, list):
            st.error("Unexpected API response")
            return pd.DataFrame()

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
# MCC CALCULATION
# =========================
def calculate_mcc(df, ema_len=50, atr_len=50, vol_len=200, m=2.0, stretch=1.05):

    temp = df.copy()

    temp['trend'] = temp['Close'].ewm(span=ema_len, adjust=False).mean()

    hl = temp['High'] - temp['Low']
    hc = abs(temp['High'] - temp['Close'].shift())
    lc = abs(temp['Low'] - temp['Close'].shift())

    temp['atr'] = pd.concat([hl, hc, lc], axis=1).max(axis=1).rolling(atr_len).mean()
    temp['atr'] = temp['atr'].replace(0, np.nan)

    temp['q'] = (temp['Close'] - temp['trend']) / temp['atr']
    temp['vol'] = temp['q'].rolling(vol_len).std()
    temp['csl'] = m * temp['vol']

    temp['upper'] = temp['trend'] + temp['csl'] * temp['atr']
    temp['lower'] = temp['trend'] - temp['csl'] * temp['atr']

    temp['q_slope'] = temp['q'].diff()

    temp['rev_long'] = (temp['q'] < -temp['csl'] * stretch) & (temp['q_slope'] > 0)
    temp['rev_short'] = (temp['q'] > temp['csl'] * stretch) & (temp['q_slope'] < 0)

    return temp

# =========================
# MAIN
# =========================
st.title("🚀 Bitcoin Indy v1.4 Institutional Stable Engine")

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
    name="EMA Trend",
    line=dict(color="yellow", width=1)
))

fig.add_trace(go.Scatter(
    x=view.index,
    y=view['upper'],
    name="Upper Band",
    line=dict(color="#cf304a", width=2)
))

fig.add_trace(go.Scatter(
    x=view.index,
    y=view['lower'],
    name="Lower Band",
    line=dict(color="#02c076", width=2)
))

for t in view.index[view['rev_long']]:
    fig.add_annotation(
        x=t,
        y=view.loc[t, 'Low'],
        text="LONG",
        bgcolor="#02c076",
        font=dict(color="white"),
        ay=40
    )

for t in view.index[view['rev_short']]:
    fig.add_annotation(
        x=t,
        y=view.loc[t, 'High'],
        text="SHORT",
        bgcolor="#cf304a",
        font=dict(color="white"),
        ay=-40
    )

fig.update_layout(
    template="plotly_dark",
    xaxis_rangeslider_visible=False,
    height=650
)

st.plotly_chart(fig, use_container_width=True)
