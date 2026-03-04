import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(
    page_title="Quant Research Lab v1.8",
    layout="wide"
)

# =========================
# DARK QUANT STYLE
# =========================
st.markdown("""
<style>
body {
    background-color: #0e1117;
    color: white;
}
.big-price {
    font-size: 54px;
    font-weight: 900;
}
.green { color: #00ff88; }
.red { color: #ff3b3b; }
.small-text {
    font-size: 20px;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

st.title("🧠 Quant Research Lab v1.8 – Institutional 5M Engine")

# =========================
# SAFE LIVE PRICE
# =========================
@st.cache_data(ttl=5)
def get_live_price():
    url = "https://data-api.binance.vision/api/v3/ticker/24hr?symbol=BTCUSDT"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return None, None

        data = r.json()

        if "lastPrice" not in data:
            return None, None

        return float(data["lastPrice"]), float(data["priceChangePercent"])

    except:
        return None, None

# =========================
# SAFE 5M DATA
# =========================
@st.cache_data(ttl=30)
def get_5m_data():
    url = "https://data-api.binance.vision/api/v3/klines"
    params = {
        "symbol": "BTCUSDT",
        "interval": "5m",
        "limit": 500
    }

    try:
        r = requests.get(url, params=params, timeout=20)
        if r.status_code != 200:
            return pd.DataFrame()

        data = r.json()

        if not isinstance(data, list):
            return pd.DataFrame()

        df = pd.DataFrame(data, columns=[
            'ts','Open','High','Low','Close','Vol',
            'ct','q','n','tb','tq','i'
        ])

        df['ts'] = pd.to_datetime(df['ts'], unit='ms')
        df.set_index('ts', inplace=True)

        return df[['Open','High','Low','Close','Vol']].astype(float)

    except:
        return pd.DataFrame()

# =========================
# LOAD DATA
# =========================
price, change_pct = get_live_price()
df = get_5m_data()

# =========================
# HEADER PRICE DISPLAY
# =========================
if price is not None:

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
            f'<div class="small-text {color_class}">{arrow} {change_pct:.2f}% (24H)</div>',
            unsafe_allow_html=True
        )

else:
    st.warning("Live price unavailable")

# =========================
# CHART
# =========================
if not df.empty:

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
            tickfont=dict(size=14, color="white")
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='rgba(255,255,255,0.05)',
            tickfont=dict(size=16, color="white")
        ),
        font=dict(
            family="Arial",
            size=16,
            color="white"
        ),
        margin=dict(l=40, r=40, t=40, b=40)
    )

    st.plotly_chart(fig, use_container_width=True)

else:
    st.warning("Historical data unavailable")
