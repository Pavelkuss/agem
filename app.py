import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Advanced GEM Strategy", layout="wide")

# --- FUNKCJA POBIERANIA DAT (Zdefiniowana wcześniej dla selectboxa) ---
@st.cache_data(ttl=86400)
def get_dates():
    try:
        # Pobieramy dane dla S&P 500 jako referencję do listy miesięcy
        df = yf.download("SXR8.DE", period="5y", progress=False, multi_level_index=False)
        return list(pd.date_range(start=df.index.min(), end=df.index.max(), freq='ME')[::-1])
    except:
        # Awaryjna lista dat, gdyby Yahoo nie odpowiedziało
        return [datetime.now().replace(day=1) - timedelta(days=i*30) for i in range(60)]

# --- CSS: WYMUSZENIE UKŁADU POZIOMEGO NA MOBILE ---
st.markdown("""
    <style>
    /* Blokada pionowego układu na telefonach */
    [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: flex-start !important;
        gap: 0.5rem !important;
    }
    
    [data-testid="column"] {
        width: 50% !important;
        flex: 1 1 50% !important;
        min-width: 50% !important;
    }

    /* Styl tabeli */
    .custom-table { width: 100%; border-collapse: collapse; font-size: 10px; color: white; table-layout: fixed; }
    .custom-table th { border-bottom: 2px solid #444; padding: 4px 1px; text-align: center; background-color: #1E1E1E; }
    .custom-table td { border-bottom: 1px solid #333; padding: 4px 0px; text-align: center; line-height: 1.2; }
    .col-rank { width: 22px; color: #888; font-weight: bold; }
    
    .block-container { padding-top: 1rem; padding-bottom: 1rem; }
    .stPlotlyChart { pointer-events: none; }
    #MainMenu, footer, header {visibility: hidden;}
    
    /* Poprawka wysokości selectboxa, by pasował do expandera */
    div[data-baseweb="select"] { margin-top: -2px; }
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

# --- LOGO ---
col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
with col_l2:
    try: st.image("agemlogo.png", use_container_width=True)
    except: st.markdown("<h3 style='text-align:center;'>Advanced GEM</h3>", unsafe_allow_html=True)

# --- LOGIKA PAMIĘCI (URL) ---
params = st.query_params.to_dict()
url_tickers = params.get("t", "").split(",") if params.get("t") else []
default_selection = [t for t in url_tickers if t in etf_data]
if not default_selection:
    default_selection = ["SXR8.DE", "EXSA.DE", "IS3N.DE", "XEON.DE"]

# --- NAGŁÓWEK: PRZYCISKI OBOK SIEBIE ---
col_cfg, col_date = st.columns(2)

with col_cfg:
    exp_cfg = st.expander("⚙️ Portfel")

with col_date:
    dates_list = get_dates()
    selected_month = st.selectbox("Data:", options=dates_list, 
                                  format_func=lambda x: x.strftime('%m.%Y'), 
                                  label_visibility="collapsed")

# --- ZAWARTOŚĆ EXPANDERA ---
with exp_cfg:
    current_selection = []
    for ticker, full_name in etf_data.items():
        is_checked = ticker in default_selection
        if st.checkbox(f"{ticker} - {full_name}", value=is_checked, key=f"cb_{ticker}"):
            current_selection.append(ticker)
    
    if st.button("Zapisz 💾", use_container_width=True):
        st.query_params["t"] = ",".join(current_selection)
        st.rerun()

# Wybrane tickery do obliczeń
active_tickers = current_selection if current_selection else default_selection

# --- POBIERANIE DANYCH ---
@st.cache_data(ttl=3600)
def fetch_all(tickers, start):
    if not tickers: return pd.DataFrame()
    data = pd.DataFrame()
    for t in tickers:
        try:
            df = yf.download(t, start=start, progress=False, multi_level_index=False)
            if not df.empty: data[t] = df['Close']
        except: continue
    return data.dropna()

all_prices = fetch_all(active_tickers, datetime.now() - timedelta(days=5*365))

# --- ANALIZA ---
if not all_prices.empty:
    # Wyznaczenie punktu końcowego
    target_dt = pd.Timestamp(selected_month)
    actual_end = all_prices.index[all_prices.index <= target_dt][-1]
    
    # Okno 12 miesięcy (Momentum)
    start_window = actual_end - timedelta(days=365)
    window_data = all_prices.loc[start_window:actual_end]
    
    perf_list = []
    for t in active_tickers:
        if t in window_data.columns:
            ret = ((window_data[t].iloc[-1] / window_data[t].iloc[0]) - 1) * 100
            perf_list.append({'ticker': t, 'return': ret, 'series': window_data[t]})
    
    perf_list = sorted(perf_list, key=lambda x: x['return'], reverse=True)

    # SYGNAŁ
    best_etf = perf_list[0]
    xeon_val = next((item['return'] for item in perf_list if item['ticker'] == "XEON.DE"), -999.0)
    
    if best_etf['ticker'] == "XEON.DE" or best_etf['return'] < xeon_ret_val if (xeon_ret_val := xeon_val) else 0:
        st.error(f"🚨 SYGNAŁ: GOTÓWKA (XEON)")
    else:
        st.success(f"🚀 SYGNAŁ: {best_etf['ticker']} ({best_etf['return']:+.2f}%)")

    # --- WYKRES ---
    fig = go.Figure()
    for item in perf_list:
        norm_series = ((item['series'] / item['series'].iloc[0]) - 1) * 100
        fig.add_trace(go.Scatter(x=norm_series.index, y=norm_series, 
                                 name=item['ticker'], 
                                 line=dict(width=2, color=color_map.get(item['ticker'], "#FFFFFF"))))
    
    fig.update_layout(
        template="plotly_dark", height=250, margin=dict(l=5, r=5, t=10, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(size=8)),
        xaxis=dict(showgrid=False), yaxis=dict(ticksuffix="%"), hovermode=False
    )
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    # --- TABELA RANKINGOWA ---
    st.markdown("---")
    curr_idx = dates_list.index(selected_month)
    history_dates = dates_list[curr_idx:curr_idx+5][::-1] 
    
    hist_table_data = []
    for d in history_dates:
        d_end = all_prices.index[all_prices.index <= d][-1]
        d_win = all_prices.loc[d_end - timedelta(days=365):d_end]
        r = sorted([(t, ((d_win[t].iloc[-1]/d_win[t].iloc[0])-1)*100) for t in active_tickers if t in d_win.columns], 
                   key=lambda x: x[1], reverse=True)
        hist_table_data.append({'date': d.strftime('%m/%y'), 'ranks': {x[0]: i+1 for i, x in enumerate(r)}, 'data': r})

    html = "<table class='custom-table'><tr><th class='col-rank'>#</th>"
    for h in hist_table_data: html += f"<th>{h['date']}</th>"
    html += "</tr>"

    for i in range(len(active_tickers)):
        html += f"<tr><td class='col-rank'>#{i+1}</td>"
        for j in range(len(hist_table_data)):
            if i < len(hist_table_data[j]['data']):
                t_name, t_ret = hist_table_data[j]['data'][i]
                clr = color_map.get(t_name, "white")
                trend = "white"; icon = ""
                if j > 0:
                    prev_pos = hist_table_data[j-1]['ranks'].get(t_name, 99)
                    if i+1 < prev_pos: trend = "#00ff00"; icon = "↑"
                    elif i+1 > prev_pos: trend = "#ff4b4b"; icon = "↓"
                html += f"<td><b style='color:{clr};'>{t_name}</b><br><span style='color:{trend};'>{t_ret:+.1f}%{icon}</span></td>"
            else: html += "<td>-</td>"
        html += "</tr>"
    st.write(html + "</table>", unsafe_allow_html=True)
else:
    st.info("Skonfiguruj portfel, aby zobaczyć analizę.")
