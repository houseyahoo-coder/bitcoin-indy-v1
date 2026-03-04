import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
import time
from datetime import datetime

# --- CONFIG ---
st.set_page_config(page_title="Bitcoin Indy v1.3.2", layout="wide", initial_sidebar_state="collapsed")

# --- STYLE ---
st.markdown("""
    <style>
    .main { background-color: #0b0e11; }
    .stApp { background-color: #0b0e11; }
    div[data-testid="stMetricValue"] > div { font-size: 75px !important; font-weight: 900 !important; font-family: 'Courier New', monospace; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNCTIONS ---
@st.cache_data(ttl=60)
def get_historical_data():
    url = "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1m&limit=500"
    data = requests.get(url).json()
    df = pd.DataFrame(data, columns=['ts', 'Open', 'High', 'Low', 'Close', 'Vol', 'ct','q','n','tb','tq','i'])
    df['ts'] = pd.to_datetime(df['ts'], unit='ms')
    df.set_index('ts', inplace=True)
    return df[['Open', 'High', 'Low', 'Close', 'Vol']].astype(float)

def get_24h_stats():
    url = "https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT"
    return requests.get(url).json()

def calculate_mcc(df, ema_len=50, atr_len=50, vol_len=200, m=2.0, min_stretch=1.05):
    temp = df.copy()
    temp['trend'] = temp['Close'].ewm(span=ema_len, adjust=False).mean()
    hl, hc, lc = temp['High']-temp['Low'], abs(temp['High']-temp['Close'].shift()), abs(temp['Low']-temp['Close'].shift())
    temp['atr'] = pd.concat([hl, hc, lc], axis=1).max(axis=1).rolling(atr_len).mean()
    temp['q'] = (temp['Close'] - temp['trend']) / temp['atr']
    temp['vol'] = temp['q'].rolling(vol_len).std()
    temp['csl'] = m * temp['vol']
    temp['upper'] = temp['trend'] + (temp['csl'] * temp['atr'])
    temp['lower'] = temp['trend'] - (temp['csl'] * temp['atr'])
    temp['q_slope'] = temp['q'].diff()
    temp['rev_short'] = (temp['q'] > (temp['csl'] * min_stretch)) & (temp['q_slope'] < 0)
    temp['rev_long'] = (temp['q'] < -(temp['csl'] * min_stretch)) & (temp['q_slope'] > 0)
    return temp

# --- APP EXECUTION ---
# ส่วนแสดงผล Header
col_title, col_price = st.columns([1, 2])

with col_title:
    st.title("BITCOIN INDY v1.3.2")
    st.caption("MCC ADAPTIVE • STREAMLIT CLOUD LIVE")

# ดึงข้อมูล
df = get_historical_data()
stats = get_24h_stats()
mcc_df = calculate_mcc(df)

last_price = mcc_df['Close'].iloc[-1]
prev_price = mcc_df['Close'].iloc[-2]
pct_24h = float(stats['priceChangePercent'])

with col_price:
    st.metric(label="BTC / USDT", 
              value=f"{last_price:,.2f}", 
              delta=f"{pct_24h:+.2f}% (24h Change)")

# กราฟ
view_df = mcc_df.tail(120)
fig = go.Figure()
fig.add_trace(go.Candlestick(x=view_df.index, open=view_df['Open'], high=view_df['High'], low=view_df['Low'], close=view_df['Close'], name='Price'))
fig.add_trace(go.Scatter(x=view_df.index, y=view_df['trend'], line=dict(color='yellow', width=1), name='Trend'))
fig.add_trace(go.Scatter(x=view_df.index, y=view_df['upper'], line=dict(color='#cf304a', width=2), name='Upper'))
fig.add_trace(go.Scatter(x=view_df.index, y=view_df['lower'], line=dict(color='#02c076', width=2), name='Lower'))

# สัญญาณ
for t in view_df.index[view_df['rev_long']]:
    fig.add_annotation(x=t, y=view_df.loc[t, 'Low'], text="LONG MCC", bgcolor="#02c076", font=dict(color="white"), ay=40)
for t in view_df.index[view_df['rev_short']]:
    fig.add_annotation(x=t, y=view_df.loc[t, 'High'], text="SHORT MCC", bgcolor="#cf304a", font=dict(color="white"), ay=-40)

fig.update_layout(template='plotly_dark', xaxis_rangeslider_visible=False, height=600, margin=dict(l=0,r=50,t=0,b=0))
st.plotly_chart(fig, use_container_width=True)

# Auto-refresh ทุก 10 วินาที (Streamlit Cloud แนะนำให้ไม่ถี่เกินไป)
time.sleep(10)

st.rerun()
