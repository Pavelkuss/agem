import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd

# --- KONFIGURACJA ---
st.set_page_config(page_title="Advanced GEM", layout="wide")

# --- CSS: CAŁKOWITA KONTROLA NAD UKŁADEM ---
st.markdown("""
    <style>
    /* Ukrycie elementów Streamlit */
    #MainMenu, footer, header {visibility: hidden;}
    .block-container { padding-top: 0.5rem; padding-bottom: 0rem; }
    
    /* Blokada klawiatury w selectboxie */
    div[data-baseweb="select"] input { pointer-events: none !important; }

    /* Customowy pasek nawigacji bez kolumn Streamlit */
    .custom-nav {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 2px;
        margin-bottom: 10px;
    }
    
    /* Tabela */
    .custom-table { width: 100%; border-collapse: collapse; font-size: 10px; color: white; table-layout: fixed; }
    .custom-table th { border-bottom: 2px solid #444; padding: 4px 1px; text-align: center; background-color: #1E1E1E; }
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

# --- PORTFEL I PARAMETRY ---
etf_data = {
    "SXR8.DE": "S&P 500", "SXRV.DE": "Nasdaq 100", "XRS2.DE": "Russell 2000",
    "EXSA.DE": "Europe 600", "SXRT.DE": "Euro Stoxx 50", "IS3N.DE": "MSCI EM",
    "XEON.DE": "Cash (Overnight)", "DBXP.DE": "Gov Bond 1-3"
}
color_map = {
    "SXR8.DE": "#377EB8", "SXRV.DE": "#4DAF4A", "XRS2.DE": "#FFFF33",
    "EXSA.DE": "#4DBEEE", "SXRT.DE": "#984EA3", "IS3N.DE": "#E41A1C",
    "XEON.DE": "#FF7F00", "DBXP.DE": "#F781BF"
}

params = st.query_params.to_dict()
active_tickers = params.get("t", "SXR8.DE,EXSA.DE,IS3N.DE,XEON.DE").split(",")

# --- PASEK STEROWANIA (FIXED LAYOUT) ---
# Używamy st.columns, ale z bardzo sztywnym CSS wbudowanym
c1, c2, c3, c4 = st.columns([0.4, 0.4, 1.8, 0.4])

with c1:
    with st.expander("⚙️"):
        st.write("Wybierz fundusze:")
        new_selection = []
        for t in etf_data:
            if st.checkbox(t, value=(t in active_tickers), key=f"ch_{t}"):
                new_selection.append(t)
        if st.button("Zastosuj"):
            st.query_params["t"] = ",".join(new_selection)
            st.rerun()

with c2:
    if st.button("－", use_container_width=True):
        if st.session_state.date_idx < len(dates_list) - 1:
            st.session_state.date_idx += 1
            st.rerun()

with c3:
    # Kluczowy element: selectbox
    selected_month = st.selectbox("Data", options=dates_list, index=st.session_state.date_idx,
                                  format_func=lambda x: x.strftime('%m.%Y'),
                                  label_visibility="collapsed", key="main_date")
    st.session_state.date_idx = dates_list.index(selected_month)

with c4:
    if st.button("＋", use_container_width=True):
        if st.session_state.date_idx > 0:
            st.session_state.date_idx -= 1
            st.rerun()

# --- ANALIZA I WYKRES ---
@st.cache_data(ttl=3600)
def fetch_prices(tickers):
    data = yf.download(tickers, start=datetime.now()-timedelta(days=5*365), progress=False, multi_level_index=False)['Close']
    return data.dropna()

prices = fetch_prices(active_tickers)

if not prices.empty:
    target_date = pd.Timestamp(selected_month)
    actual_end = prices.index[prices.index <= target_date][-1]
    window = prices.loc[actual_end - timedelta(days=365):actual_end]
    
    perf = []
    for t in active_tickers:
        if t in window.columns:
            r = ((window[t].iloc[-1] / window[t].iloc[0]) - 1) * 100
            perf.append({'t': t, 'r': r, 's': window[t]})
    
    perf = sorted(perf, key=lambda x: x['r'], reverse=True)
    best = perf[0]
    
    # Sygnał
    xeon_r = next((x['r'] for x in perf if x['t'] == "XEON.DE"), -99)
    if best['t'] == "XEON.DE" or best['r'] < xeon_r:
        st.error(f"🚨 SYGNAŁ: GOTÓWKA (XEON)")
    else:
        st.success(f"🚀 SYGNAŁ: {best['t']} ({best['r']:+.2f}%)")

    # Wykres
    fig = go.Figure()
    for item in perf:
        norm = ((item['s'] / item['s'].iloc[0]) - 1) * 100
        fig.add_trace(go.Scatter(x=norm.index, y=norm, name=item['t'], line=dict(color=color_map.get(item['t'], "#FFF"))))
    fig.update_layout(template="plotly_dark", height=250, margin=dict(l=0, r=0, t=10, b=0),
                      legend=dict(orientation="h", y=1.1), xaxis=dict(showgrid=False), hovermode=False)
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    # Tabela historyczna
    st.markdown("<br>", unsafe_allow_html=True)
    hist_html = "<table class='custom-table'><tr><th>#</th>"
    view_dates = dates_list[st.session_state.date_idx : st.session_state.date_idx + 5][::-1]
    for d in view_dates: hist_html += f"<th>{d.strftime('%m/%y')}</th>"
    hist_html += "</tr>"
    
    for i in range(len(active_tickers)):
        hist_html += f"<tr><td>{i+1}</td>"
        for d in view_dates:
            try:
                d_end = prices.index[prices.index <= d][-1]
                d_win = prices.loc[d_end-timedelta(days=365):d_end]
                r_list = sorted([(t, ((d_win[t].iloc[-1]/d_win[t].iloc[0])-1)*100) for t in active_tickers], key=lambda x: x[1], reverse=True)
                t_name, t_ret = r_list[i]
                hist_html += f"<td><span style='color:{color_map.get(t_name, '#FFF')}'>{t_name}</span><br>{t_ret:+.1f}%</td>"
            except: hist_html += "<td>-</td>"
        hist_html += "</tr>"
    st.write(hist_html + "</table>", unsafe_allow_html=True)
