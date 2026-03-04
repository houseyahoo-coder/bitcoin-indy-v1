import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import websocket
import json
import threading

st.set_page_config(page_title="Quant Research Lab v2.0", layout="wide")

# =========================
# DARK AMOLED STYLE
# =========================
st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background-color: #000000; }
.big-price { font-size: 64px; font-weight: 900; }
.green { color: #00ff88; }
.red { color: #ff3b3b; }
.percent { font-size: 28px; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

st.title("🧠 Quant Research Lab v2.0 – Institutional Terminal")

# =========================
# SESSION STATE PRICE
# =========================
if "live_price" not in st.session_state:
    st.session_state.live_price = 0.0
if "change_pct" not in st.session_state:
    st.session_state.change_pct = 0.0

# =========================
# WEBSOCKET LIVE STREAM
# =========================
def on_message(ws, message):
    data = json.loads(message)
    st.session_state.live_price = float(data['c'])
    st.session_state.change_pct = float(data['P'])

def start_ws():
    ws = websocket.WebSocketApp(
        "wss://stream.binance.com:9443/ws/btcusdt@ticker",
        on_message=on_message
    )
    ws.run_forever()

if "ws_started" not in st.session_state:
    threading.Thread(target=start_ws, daemon=True).start()
    st.session_state.ws_started = True

# =========================
# 5M DATA
# =========================
@st.cache_data(ttl=60)
def get_5m_data():
    url = "https://data-api.binance.vision/api/v3/klines"
    params = {"symbol":"BTCUSDT","interval":"5m","limit":500}
    r = requests.get(url, params=params, timeout=20)
    data = r.json()

    df = pd.DataFrame(data, columns=[
        'ts','Open','High','Low','Close','Vol',
        'ct','q','n','tb','tq','i'
    ])
    df['ts'] = pd.to_datetime(df['ts'], unit='ms')
    df.set_index('ts', inplace=True)
    df = df[['Open','High','Low','Close','Vol']].astype(float)

    # EMA
    df['EMA20'] = df['Close'].ewm(span=20).mean()
    df['EMA50'] = df['Close'].ewm(span=50).mean()

    # VWAP
    df['VWAP'] = (df['Close']*df['Vol']).cumsum() / df['Vol'].cumsum()

    # Indicator Engine (Momentum + Volatility)
    df['Momentum'] = df['Close'].pct_change(10)
    df['Volatility'] = df['Close'].rolling(20).std()

    return df

df = get_5m_data()

# =========================
# PRICE DISPLAY
# =========================
price = st.session_state.live_price
change_pct = st.session_state.change_pct

color = "green" if change_pct >= 0 else "red"
arrow = "▲" if change_pct >= 0 else "▼"

col1, col2 = st.columns([3,1])

with col1:
    st.markdown(
        f'<div class="big-price {color}">${price:,.2f}</div>',
        unsafe_allow_html=True
    )
with col2:
    st.markdown(
        f'<div class="percent {color}">{arrow} {change_pct:.2f}% (24H)</div>',
        unsafe_allow_html=True
    )

# =========================
# CHART
# =========================
fig = go.Figure()

# Candles
fig.add_trace(go.Candlestick(
    x=df.index,
    open=df['Open'],
    high=df['High'],
    low=df['Low'],
    close=df['Close'],
    increasing_line_color='#00ff88',
    decreasing_line_color='#ff3b3b',
    name="Price"
))

# EMA
fig.add_trace(go.Scatter(
    x=df.index,
    y=df['EMA20'],
    line=dict(color='orange', width=1.5),
    name="EMA20"
))

fig.add_trace(go.Scatter(
    x=df.index,
    y=df['EMA50'],
    line=dict(color='yellow', width=1.5),
    name="EMA50"
))

# VWAP
fig.add_trace(go.Scatter(
    x=df.index,
    y=df['VWAP'],
    line=dict(color='cyan', width=2),
    name="VWAP"
))

# Volume Panel
fig.add_trace(go.Bar(
    x=df.index,
    y=df['Vol'],
    name="Volume",
    marker_color='rgba(255,255,255,0.2)',
    yaxis="y2"
))

fig.update_layout(
    template="plotly_dark",
    paper_bgcolor="#000000",
    plot_bgcolor="#000000",
    height=800,
    xaxis=dict(
        tickfont=dict(size=18),
        gridcolor='rgba(255,255,255,0.05)'
    ),
    yaxis=dict(
        tickfont=dict(size=20),
        gridcolor='rgba(255,255,255,0.05)'
    ),
    yaxis2=dict(
        overlaying='y',
        side='right',
        showgrid=False
    ),
    legend=dict(font=dict(size=14))
)

st.plotly_chart(fig, use_container_width=True)
