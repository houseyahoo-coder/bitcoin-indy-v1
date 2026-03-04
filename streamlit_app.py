import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- CONFIG ---
st.set_page_config(
    page_title="Bitcoin Indy v1.4 Stable Engine",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- STYLE ---
st.markdown("""
<style>
.main { background-color: #0b0e11; color: white; }
.stApp { background-color: #0b0e11; }
div[data-testid="stMetricValue"] > div {
    font-size: 75px !important;
    font-weight: 900 !important;
    font-family: 'Courier New', monospace;
}
</style>
""", unsafe_allow_html=True)

# --- AUTORELOAD EVERY 10s ---
st_autorefresh(interval=10000, key="btc_live")

# --- API FUNCTIONS ---
@st.cache_data(ttl=10)
def get_historical_data():
    url = "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1m&limit=500"
    try:
        res = requests.get(url, timeout=3)
        res.raise_for_status()
        data = res.json()
        df = pd.DataFrame(data, columns=['ts','Open','High','Low','Close','Vol','ct','q','n','tb','tq','i'])
        df['ts'] = pd.to_datetime(df['ts'], unit='ms')
        df.set_index('ts', inplace=True)
        return df[['Open','High','Low','Close','Vol']].astype(float)
    except Exception as e:
        st.error("Unable to fetch historical price")
        return pd.DataFrame()

@st.cache_data(ttl=10)
def get_24h_stats():
    url = "https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT"
    try:
        res = requests.get(url, timeout=2)
        res.raise_for_status()
        return res.json()
    except:
        return {}

# --- MCC CALCULATION ---
def calculate_mcc(df, ema_len=50, atr_len=50, vol_len=200, m=2.0, min_stretch=1.05):
    temp = df.copy()
    temp['trend'] = temp['Close'].ewm(span=ema_len, adjust=False).mean()
    hl = temp['High'] - temp['Low']
    hc = abs(temp['High'] - temp['Close'].shift())
    lc = abs(temp['Low'] - temp['Close'].shift())
    temp['atr'] = pd.concat([hl,hc,lc], axis=1).max(axis=1).rolling(atr_len).mean()
    temp['atr'] = temp['atr'].replace(0, np.nan)

    temp['q'] = (temp['Close'] - temp['trend']) / temp['atr']
    temp['vol'] = temp['q'].rolling(vol_len).std()
    temp['csl'] = m * temp['vol']

    temp['upper'] = temp['trend'] + (temp['csl'] * temp['atr'])
    temp['lower'] = temp['trend'] - (temp['csl'] * temp['atr'])

    temp['q_slope'] = temp['q'].diff()
    temp['rev_short'] = (temp['q'] > (temp['csl']*min_stretch)) & (temp['q_slope'] < 0)
    temp['rev_long']  = (temp['q'] < -(temp['csl']*min_stretch)) & (temp['q_slope'] > 0)

    return temp

# --- MAIN UI ---
df = get_historical_data()
if df.empty:
    st.stop()

stats = get_24h_stats()
mcc_df = calculate_mcc(df)

last_price = mcc_df['Close'].iloc[-1]
pct_24h = float(stats.get('priceChangePercent', 0))

# HEADER
c1, c2 = st.columns([1,2])
with c1:
    st.title("Bitcoin Indy v1.4 Stable Engine")
    st.caption("Institutional MCC Adaptive Dashboard")

with c2:
    st.metric("BTC / USDT", f"{last_price:,.2f}", f"{pct_24h:+.2f}% (24h)")

# LIVE SIGNAL PANEL
with st.expander("📊 Live Signal Summary", expanded=True):
    cols = st.columns(4)
    cols[0].metric("EMA50 Trend", f"{mcc_df['trend'].iloc[-1]:.2f}", "")
    cols[1].metric("ATR", f"{mcc_df['atr'].iloc[-1]:.2f}", "")
    cols[2].metric("Volatility", f"{mcc_df['vol'].iloc[-1]:.4f}", "")
    cols[3].metric("Stretch Level", f"{mcc_df['csl'].iloc[-1]:.4f}", "")

# PRICE + MCC CHART
view = mcc_df.tail(120)
fig = go.Figure()

fig.add_trace(go.Candlestick(
    x=view.index, open=view['Open'], high=view['High'],
    low=view['Low'], close=view['Close'], name="Price"
))
fig.add_trace(go.Scatter(x=view.index, y=view['trend'], name="Trend(EMA50)", line=dict(color="yellow", width=1)))
fig.add_trace(go.Scatter(x=view.index, y=view['upper'], name="Upper Band", line=dict(color="#cf304a", width=2)))
fig.add_trace(go.Scatter(x=view.index, y=view['lower'], name="Lower Band", line=dict(color="#02c076", width=2)))

# SIGNAL ANNOTATIONS
for t in view.index[view['rev_long']]:
    fig.add_annotation(x=t, y=view.loc[t,'Low'], text="LONG", bgcolor="#02c076", font=dict(color="white"), ay=40)
for t in view.index[view['rev_short']]:
    fig.add_annotation(x=t, y=view.loc[t,'High'], text="SHORT", bgcolor="#cf304a", font=dict(color="white"), ay=-40)

fig.update_layout(
    template="plotly_dark",
    xaxis_rangeslider_visible=False,
    height=600,
    margin=dict(l=0,r=50,t=0,b=0),
)

st.plotly_chart(fig, use_container_width=True)
