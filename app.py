import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd

# --- KONFIGURACJA ---
st.set_page_config(page_title="Advanced GEM", layout="wide")

# --- CSS: WYMUSZENIE JEDNEJ LINII NA MOBILE ---
st.markdown("""
    <style>
    /* Ukrycie menu Streamlit */
    #MainMenu, footer, header {visibility: hidden;}
    .block-container { padding-top: 0.5rem; padding-bottom: 0rem; }
    
    /* KLUCZ: Wymuszenie układu poziomego na każdym ekranie */
    [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: center !important;
        gap: 4px !important;
    }

    /* Dopasowanie szerokości kolumn wewnątrz flexa */
    [data-testid="column"]:nth-of-type(1) { flex: 0 0 15% !important; min-width: 45px !important; }
    [data-testid="column"]:nth-of-type(2) { flex: 0 0 10% !important; min-width: 35px !important; }
    [data-testid="column"]:nth-of-type(3) { flex: 1 1 auto !important; }
    [data-testid="column"]:nth-of-type(4) { flex: 0 0 10% !important; min-width: 35px !important; }

    /* Estetyka przycisków i selectboxa */
    .stButton button { width: 100% !important; padding: 0px !important; height: 38px !important; }
    div[data-baseweb="select"] input { pointer-events: none !important; }
    .stExpander { border: none !important; background: transparent !important; }
    .stExpander > div:first-child { padding: 0 !important; }
    
    /* Tabela historyczna */
    .custom-table { width: 100%; border-collapse: collapse; font-size: 10px; color: white; table-layout: fixed; }
    .custom-table th { border-bottom: 2px solid #444; padding: 4px 1px; text-align: center; }
    .custom-table td { border-bottom: 1px solid #333; padding: 4px 0px; text-align: center; line-height: 1.2; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNKCJE DANYCH ---
@st.cache_data(ttl=86400)
def get_dates():
    try:
        # Pobieramy daty z S&P 500 jako wzorca
        df = yf.download("SXR8.DE", period="5y", progress=False)
        return list(pd.date_range(start=df.index.min(), end=df.index.max(), freq='ME')[::-1])
    except:
        return [datetime.now().replace(day=1) - timedelta(days=i*30) for i in range(60)]

# --- LOGIKA STANU ---
dates_list = get_dates()
if 'date_idx' not in st.session_state:
    st.session_state.date_idx = 0

# --- PORTFEL ---
etf_data = {
    "SXR8.DE": "S&P 500", "SXRV.DE": "Nasdaq 100", "XRS2.DE": "Russell 2000",
    "EXSA.DE": "Europe 600", "SXRT.DE": "Euro Stoxx 50", "IS3N.DE": "MSCI EM",
    "XEON.DE": "Cash", "DBXP.DE": "Gov Bond"
}
color_map = {
    "SXR8.DE": "#377EB8", "SXRV.DE": "#4DAF4A", "XRS2.DE": "#FFFF33",
    "EXSA.DE": "#4DBEEE", "SXRT.DE": "#984EA3", "IS3N.DE": "#E41A1C",
    "XEON.DE": "#FF7F00", "DBXP.DE": "#F781BF"
}

params = st.query_params.to_dict()
active_tickers = params.get("t", "SXR8.DE,EXSA.DE,IS3N.DE,XEON.DE").split(",")

# --- PASEK STEROWANIA (⚙️ - DATA +) ---
c1, c2, c3, c4 = st.columns([1, 1, 4, 1])

with c1:
    with st.expander("⚙️"):
        st.caption("Fundusze:")
        new_sel = []
        for t in etf_data:
            if st.checkbox(t, value=(t in active_tickers), key=f"c_{t}"):
                new_sel.append(t)
        if st.button("Zapisz"):
            st.query_params["t"] = ",".join(new_sel)
            st.rerun()

with c2:
    if st.button("－"):
        if st.session_state.date_idx < len(dates_list) - 1:
            st.session_state.date_idx += 1
            st.rerun()

with c3:
    selected_month = st.selectbox("D", options=dates_list, index=st.session_state.date_idx,
                                  format_func=lambda x: x.strftime('%m.%Y'),
                                  label_visibility="collapsed")
    st.session_state.date_idx = dates_list.index(selected_month)

with c4:
    if st.button("＋"):
        if st.session_state.date_idx > 0:
            st.session_state.date_idx -= 1
            st.rerun()

# --- ANALIZA ---
@st.cache_data(ttl=3600)
def fetch_prices(tickers):
    d = yf.download(tickers, start=datetime.now()-timedelta(days=5*365), progress=False, multi_level_index=False)['Close']
    return d.dropna()

prices = fetch_prices(active_tickers)

if not prices.empty:
    target_date = pd.Timestamp(selected_month)
    actual_end = prices.index[prices.index <= target_date][-1]
    window = prices.loc[actual_end - timedelta(days=365):actual_end]
    
    perf = sorted([
        {'t': t, 'r': ((window[t].iloc[-1]/window[t].iloc[0])-1)*100, 's': window[t]}
        for t in active_tickers if t in window.columns
    ], key=lambda x: x['r'], reverse=True)

    # Sygnał
    best = perf[0]
    xeon_r = next((x['r'] for x in perf if x['t'] == "XEON.DE"), -99)
    if best['t'] == "XEON.DE" or best['r'] < xeon_r:
        st.error(f"🚨 SYGNAŁ: GOTÓWKA (XEON)")
    else:
        st.success(f"🚀 SYGNAŁ: {best['t']} ({best['r']:+.2f}%)")

    # Wykres
    fig = go.Figure()
    for item in perf:
        n = ((item['s']/item['s'].iloc[0])-1)*100
        fig.add_trace(go.Scatter(x=n.index, y=n, name=item['t'], line=dict(color=color_map.get(item['t'], "#FFF"))))
    fig.update_layout(template="plotly_dark", height=250, margin=dict(l=0, r=0, t=10, b=0),
                      legend=dict(orientation="h", y=1.1, font=dict(size=9)), xaxis=dict(showgrid=False), hovermode=False)
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
