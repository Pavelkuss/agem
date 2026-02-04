import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Advanced GEM Strategy", layout="wide")

# --- FUNKCJA POBIERANIA DAT ---
@st.cache_data(ttl=86400)
def get_dates():
    try:
        df = yf.download("SXR8.DE", period="5y", progress=False, multi_level_index=False)
        return list(pd.date_range(start=df.index.min(), end=df.index.max(), freq='ME')[::-1])
    except:
        return [datetime.now().replace(day=1) - timedelta(days=i*30) for i in range(60)]

# --- CSS: KOMPAKTOWY INTERFEJS I BLOKADA KLAWIATURY ---
st.markdown("""
    <style>
    /* Wymuszenie równego układu w jednej linii */
    [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: center !important;
        gap: 5px !important;
    }
    
    /* Układ kolumn: Portfel (20%), Przycisk- (15%), Data (30%), Przycisk+ (15%) */
    [data-testid="column"] { width: auto !important; flex: 1 !important; }

    /* Blokada wpisywania z klawiatury w selectboxie */
    div[data-baseweb="select"] input { pointer-events: none !important; }

    /* Styl tabeli */
    .custom-table { width: 100%; border-collapse: collapse; font-size: 10px; color: white; table-layout: fixed; }
    .custom-table th { border-bottom: 2px solid #444; padding: 4px 1px; text-align: center; background-color: #1E1E1E; }
    .custom-table td { border-bottom: 1px solid #333; padding: 4px 0px; text-align: center; line-height: 1.2; }
    .col-rank { width: 22px; color: #888; font-weight: bold; }
    
    .block-container { padding-top: 1rem; padding-bottom: 1rem; }
    #MainMenu, footer, header {visibility: hidden;}
    
    /* Ukrycie obramowania expandera dla czystszego wyglądu przycisku */
    .stExpander { border: none !important; background: transparent !important; }
    .stExpander > div:first-child { padding: 0 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- BIBLIOTEKA INSTRUMENTÓW ---
etf_data = {
    "SXR8.DE": "iShares Core S&P 500 UCITS ETF USD (Acc)",
    "SXRV.DE": "iShares Nasdaq 100 UCITS ETF (Acc)",
    "XRS2.DE": "Xtrackers Russell 2000 UCITS ETF (Acc)",
    "EXSA.DE": "iShares STOXX Europe 600 UCITS ETF (DE)",
    "SXRT.DE": "iShares Core EURO STOXX 50 UCITS ETF (Acc)",
    "IS3N.DE": "iShares Core MSCI EM IMI UCITS ETF USD (Acc)",
    "XEON.DE": "Xtrackers II EUR Overnight Rate Swap UCITS ETF",
    "DBXP.DE": "Xtrackers II Germany Government Bond 1-3 UCITS ETF"
}
color_map = {
    "SXR8.DE": "#377EB8", "SXRV.DE": "#4DAF4A", "XRS2.DE": "#FFFF33",
    "EXSA.DE": "#4DBEEE", "SXRT.DE": "#984EA3",
    "IS3N.DE": "#E41A1C", "XEON.DE": "#FF7F00", "DBXP.DE": "#F781BF"
}

# --- LOGIKA PAMIĘCI I DAT ---
params = st.query_params.to_dict()
url_tickers = params.get("t", "").split(",") if params.get("t") else []
default_selection = [t for t in url_tickers if t in etf_data]
if not default_selection:
    default_selection = ["SXR8.DE", "EXSA.DE", "IS3N.DE", "XEON.DE"]

dates_list = get_dates()

# Obsługa stanu wybranego indeksu daty
if 'date_idx' not in st.session_state:
    st.session_state.date_idx = 0

# --- PASEK NAWIGACJI (⚙️ - + DATA +) ---
col_cfg, col_prev, col_main_date, col_next = st.columns([1, 1, 3, 1])

with col_cfg:
    # Expander jako ikona koła zębatego
    cfg_menu = st.expander("⚙️")

with col_prev:
    if st.button("－"):
        if st.session_state.date_idx < len(dates_list) - 1:
            st.session_state.date_idx += 1
            st.rerun()

with col_main_date:
    selected_month = st.selectbox(
        "Data", 
        options=dates_list, 
        index=st.session_state.date_idx,
        format_func=lambda x: x.strftime('%m.%Y'),
        label_visibility="collapsed",
        key="date_selector"
    )
    # Synchronizacja indeksu, jeśli użytkownik kliknie bezpośrednio w selectbox
    st.session_state.date_idx = dates_list.index(selected_month)

with col_next:
    if st.button("＋"):
        if st.session_state.date_idx > 0:
            st.session_state.date_idx -= 1
            st.rerun()

# --- ZAWARTOŚĆ USTAWIEŃ ---
with cfg_menu:
    st.write("Skonfiguruj portfel:")
    current_selection = []
    for ticker, full_name in etf_data.items():
        if st.checkbox(f"{ticker}", value=(ticker in default_selection), key=f"cb_{ticker}", help=full_name):
            current_selection.append(ticker)
    
    if st.button("Zapisz 💾", use_container_width=True):
        st.query_params["t"] = ",".join(current_selection)
        st.rerun()

active_tickers = current_selection if current_selection else default_selection

# --- OBLICZENIA I WYKRES ---
@st.cache_data(ttl=3600)
def fetch_data(tickers, start):
    if not tickers: return pd.DataFrame()
    data = pd.DataFrame()
    for t in tickers:
        try:
            df = yf.download(t, start=start, progress=False, multi_level_index=False)
            if not df.empty: data[t] = df['Close']
        except: continue
    return data.dropna()

all_prices = fetch_data(active_tickers, datetime.now() - timedelta(days=5*365))

if not all_prices.empty:
    target_dt = pd.Timestamp(selected_month)
    actual_end = all_prices.index[all_prices.index <= target_dt][-1]
    window_data = all_prices.loc[actual_end - timedelta(days=365):actual_end]
    
    perf_list = sorted([
        {'ticker': t, 'return': ((window_data[t].iloc[-1]/window_data[t].iloc[0])-1)*100, 'series': window_data[t]}
        for t in active_tickers if t in window_data.columns
    ], key=lambda x: x['return'], reverse=True)

    # SYGNAŁ
    best = perf_list[0]
    xeon_ret = next((x['return'] for x in perf_list if x['ticker'] == "XEON.DE"), -99.0)
    if best['ticker'] == "XEON.DE" or best['return'] < xeon_ret:
        st.error(f"🚨 GOTÓWKA (XEON)")
    else:
        st.success(f"🚀 {best['ticker']} ({best['return']:+.2f}%)")

    # WYKRES
    fig = go.Figure()
    for item in perf_list:
        norm = ((item['series']/item['series'].iloc[0])-1)*100
        fig.add_trace(go.Scatter(x=norm.index, y=norm, name=item['ticker'], 
                                 line=dict(width=2, color=color_map.get(item['ticker'], "#FFF"))))
    fig.update_layout(template="plotly_dark", height=230, margin=dict(l=5, r=5, t=10, b=0),
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(size=8)),
                      xaxis=dict(showgrid=False), yaxis=dict(ticksuffix="%"), hovermode=False)
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    # TABELA
    st.markdown("---")
    curr_idx = dates_list.index(selected_month)
    history_dates = dates_list[curr_idx:curr_idx+5][::-1] 
    hist_data = []
    for d in history_dates:
        d_end = all_prices.index[all_prices.index <= d][-1]
        d_win = all_prices.loc[d_end - timedelta(days=365):d_end]
        r = sorted([(t, ((d_win[t].iloc[-1]/d_win[t].iloc[0])-1)*100) for t in active_tickers if t in d_win.columns], key=lambda x: x[1], reverse=True)
        hist_data.append({'date': d.strftime('%m/%y'), 'ranks': {x[0]: i+1 for i, x in enumerate(r)}, 'data': r})

    html = "<table class='custom-table'><tr><th class='col-rank'>#</th>"
    for h in hist_data: html += f"<th>{h['date']}</th>"
    html += "</tr>"
    for i in range(len(active_tickers)):
        html += f"<tr><td class='col-rank'>#{i+1}</td>"
        for j in range(len(hist_data)):
            if i < len(hist_data[j]['data']):
                tn, tr = hist_data[j]['data'][i]
                clr = color_map.get(tn, "white")
                trend = "white"; icon = ""
                if j > 0:
                    prev_p = hist_data[j-1]['ranks'].get(tn, 99)
                    if i+1 < prev_p: trend = "#00ff00"; icon = "↑"
                    elif i+1 > prev_p: trend = "#ff4b4b"; icon = "↓"
                html += f"<td><b style='color:{clr};'>{tn}</b><br><span style='color:{trend};'>{tr:+.1f}%{icon}</span></td>"
            else: html += "<td>-</td>"
        html += "</tr>"
    st.write(html + "</table>", unsafe_allow_html=True)
