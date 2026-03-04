import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import time

st.set_page_config(page_title="Quant Research Lab v2.1", layout="wide")

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

st.title("🧠 Quant Research Lab v2.1 – Ultra Fast Cloud Engine")

# =========================
# FAST LIVE PRICE (3s)
# =========================
@st.cache_data(ttl=3)
def get_live_price():
    url = "https://data-api.binance.vision/api/v3/ticker/24hr?symbol=BTCUSDT"
    try:
        r = requests.get(url, timeout=5)
        if r.status_code != 200:
            return None, None
        data = r.json()
        if "lastPrice" not in data:
            return None, None
        return float(data["lastPrice"]), float(data["priceChangePercent"])
    except:
        return None, None

# =========================
# 5M DATA (60s cache)
# =========================
@st.cache_data(ttl=60)
def get_5m_data():
    url = "https://data-api.binance.vision/api/v3/klines"
    params = {"symbol":"BTCUSDT","interval":"5m","limit":500}
    r = requests.get(url, params=params, timeout=10)
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

    # Indicator Engine
    df['Momentum'] = df['Close'].pct_change(10)
    df['Volatility'] = df['Close'].rolling(20).std()

    return df

# =========================
# LOAD DATA
# =========================
price, change_pct = get_live_price()
df = get_5m_data()

# =========================
# PRICE DISPLAY
# =========================
if price is not None:
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
else:
    st.warning("Live price unavailable")

# =========================
# CHART
# =========================
if not df.empty:

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
        x=df.index, y=df['EMA20'],
        line=dict(color='orange', width=1.5),
        name="EMA20"
    ))

    fig.add_trace(go.Scatter(
        x=df.index, y=df['EMA50'],
        line=dict(color='yellow', width=1.5),
        name="EMA50"
    ))

    # VWAP
    fig.add_trace(go.Scatter(
        x=df.index, y=df['VWAP'],
        line=dict(color='cyan', width=2),
        name="VWAP"
    ))

    # Volume
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
        height=820,
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

else:
    st.warning("Historical data unavailable")

# =========================
# AUTO REFRESH (3s)
# =========================
time.sleep(3)
st.rerun()
