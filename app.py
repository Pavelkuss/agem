import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd

# --- KONFIGURACJA ---
st.set_page_config(page_title="Advanced GEM", layout="wide", initial_sidebar_state="collapsed")

# --- CSS: MODERN APP INTERFACE ---
st.markdown("""
    <style>
    /* Ukrycie elementów systemowych */
    #MainMenu, footer, header {visibility: hidden;}
    .block-container { padding-top: 0.5rem; padding-bottom: 1rem; }

    /* TOOLBAR: Wymuszenie układu jak w aplikacji Android */
    .app-toolbar {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: center !important;
        background-color: #1e1e1e;
        padding: 5px;
        border-radius: 10px;
        margin-bottom: 15px;
    }

    /* Wymuszenie linii dla kolumn Streamlit */
    [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: center !important;
        gap: 2px !important;
    }

    /* Szerokości elementów */
    [data-testid="column"]:nth-of-type(1) { flex: 0 0 45px !important; } /* Hamburger */
    [data-testid="column"]:nth-of-type(2) { flex: 0 0 35px !important; } /* Minus */
    [data-testid="column"]:nth-of-type(3) { flex: 1 1 auto !important; } /* Data */
    [data-testid="column"]:nth-of-type(4) { flex: 0 0 35px !important; } /* Plus */

    /* Stylizacja przycisków */
    .stButton button {
        background-color: #333 !important;
        border: 1px solid #444 !important;
        color: white !important;
        height: 40px !important;
        width: 100% !important;
        padding: 0px !important;
        font-weight: bold !important;
    }

    /* Blokada klawiatury w selectboxie */
    div[data-baseweb="select"] input { pointer-events: none !important; }
    
    /* Wykres i Tabela */
    .stPlotlyChart { margin-top: -10px; }
    .custom-table { width: 100%; border-collapse: collapse; font-size: 10px; color: white; table-layout: fixed; }
    .custom-table th { border-bottom: 2px solid #444; padding: 4px 1px; text-align: center; }
    .custom-table td { border-bottom: 1px solid #333; padding: 4px 0px; text-align: center; line-height: 1.2; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNKCJE DANYCH ---
@st.cache_data(ttl=86400)
def get_dates():
    try:
        df = yf.download("SXR8.DE", period="5y", progress=False)
        return list(pd.date_range(start=df.index.min(), end=df.index.max(), freq='ME')[::-1])
    except:
        return [datetime.now().replace(day=1) - timedelta(days=i*30) for i in range(60)]

# --- LOGIKA STANU ---
dates_list = get_dates()
if 'date_idx' not in st.session_state:
    st.session_state.date_idx = 0

# --- PORTFEL (W PANELU BOCZNYM JAK W APKACH) ---
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

with st.sidebar:
    st.title("⚙️ Ustawienia")
    params = st.query_params.to_dict()
    active_tickers = params.get("t", "SXR8.DE,EXSA.DE,IS3N.DE,XEON.DE").split(",")
    
    new_selection = []
    st.subheader("Twój Portfel:")
    for t, name in etf_data.items():
        if st.checkbox(f"{t} ({name})", value=(t in active_tickers)):
            new_selection.append(t)
    
    if st.button("Zapisz i Przeładuj"):
        st.query_params["t"] = ",".join(new_selection)
        st.rerun()

# --- TOOLBAR (MENU + NAWIGACJA) ---
# To jest "serce" interfejsu Androidowego
col_menu, col_prev, col_date, col_next = st.columns([1, 1, 4, 1])

with col_menu:
    if st.button("☰"): # Hamburger otwiera sidebar
        st.markdown('<script>window.parent.document.querySelector(".st-emotion-cache-1wb5hy5").click();</script>', unsafe_allow_html=True)
        # W Streamlit 1.27+ sidebar otwiera się też automatycznie po kliknięciu strzałki

with col_prev:
    if st.button("－"):
        if st.session_state.date_idx < len(dates_list) - 1:
            st.session_state.date_idx += 1
            st.rerun()

with col_date:
    selected_month = st.selectbox("Date", options=dates_list, index=st.session_state.date_idx,
                                  format_func=lambda x: x.strftime('%m.%Y'),
                                  label_visibility="collapsed")
    st.session_state.date_idx = dates_list.index(selected_month)

with col_next:
    if st.button("＋"):
        if st.session_state.date_idx > 0:
            st.session_state.date_idx -= 1
            st.rerun()

# --- OBLICZENIA ---
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

    # SYGNAŁ
    best = perf[0]
    xeon_r = next((x['r'] for x in perf if x['t'] == "XEON.DE"), -99)
    if best['t'] == "XEON.DE" or best['r'] < xeon_r:
        st.error(f"🚨 SYGNAŁ: GOTÓWKA (XEON)")
    else:
        st.success(f"🚀 SYGNAŁ: {best['t']} ({best['r']:+.2f}%)")

    # WYKRES (Kompaktowy)
    fig = go.Figure()
    for item in perf:
        n = ((item['s']/item['s'].iloc[0])-1)*100
        fig.add_trace(go.Scatter(x=n.index, y=n, name=item['t'], line=dict(color=color_map.get(item['t'], "#FFF"))))
    fig.update_layout(template="plotly_dark", height=220, margin=dict(l=0, r=0, t=10, b=0),
                      legend=dict(orientation="h", y=1.1, font=dict(size=9)), xaxis=dict(showgrid=False), hovermode=False)
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    # TABELA (Historyczna)
    st.markdown("---")
    view_dates = dates_list[st.session_state.date_idx : st.session_state.date_idx + 4][::-1]
    
    h_html = "<table class='custom-table'><tr><th>#</th>"
    for d in view_dates: h_html += f"<th>{d.strftime('%m/%y')}</th>"
    h_html += "</tr>"
    
    for i in range(min(len(active_tickers), 4)): # Pokaż top 4 dla czytelności
        h_html += f"<tr><td>{i+1}</td>"
        for d in view_dates:
            try:
                d_e = prices.index[prices.index <= d][-1]
                d_w = prices.loc[d_e-timedelta(days=365):d_e]
                r_l = sorted([(t, ((d_w[t].iloc[-1]/d_w[t].iloc[0])-1)*100) for t in active_tickers], key=lambda x: x[1], reverse=True)
                t_n, t_r = r_l[i]
                h_html += f"<td><span style='color:{color_map.get(t_n, '#FFF')}'>{t_n}</span><br>{t_r:+.1f}%</td>"
            except: h_html += "<td>-</td>"
        h_html += "</tr>"
    st.write(h_html + "</table>", unsafe_allow_html=True)
