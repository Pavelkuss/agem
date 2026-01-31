import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="GEM Monitor (EUR)", layout="wide")

# --- CSS: STYLIZACJA ---
st.markdown("""
    <style>
    .stPlotlyChart { pointer-events: none; }
    .main-title { font-size: 2.2rem; font-weight: bold; margin-bottom: 0; text-align: center; }
    .custom-table { width: 100%; border-collapse: collapse; font-size: 12px; color: white; margin-top: 20px; }
    .custom-table th { border-bottom: 2px solid #444; padding: 10px; text-align: center; background-color: #1E1E1E; }
    .custom-table td { border-bottom: 1px solid #333; padding: 8px; text-align: center; }
    .stMultiSelect span { font-size: 14px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNKCJA POBIERANIA DANYCH (NAPRAWIONA) ---
@st.cache_data(ttl=3600)
def get_data(tickers, start):
    if not tickers:
        return pd.DataFrame()
    combined = pd.DataFrame()
    for t in tickers:
        try:
            df = yf.download(t, start=start, progress=False, multi_level_index=False)
            if not df.empty and 'Close' in df.columns:
                combined[t] = df['Close']
        except:
            continue
    return combined.dropna()

# --- LOGO I TYTUŁ ---
st.markdown("""
    <div style="text-align: center; margin-bottom: 20px;">
        <h1 class="main-title">📈 GEM Momentum: USA - EU - EM</h1>
        <p style="color: #888; margin: 0;">Smart Momentum. Safe Haven.</p>
    </div>
    """, unsafe_allow_html=True)

# --- BIBLIOTEKA ---
etf_data = {
    "SXR8.DE": "iShares S&P 500", "SXRV.DE": "iShares Nasdaq 100", "XRS2.DE": "Xtrackers Russell 2000",
    "EXSA.DE": "iShares STOXX 600", "SXRT.DE": "iShares EURO STOXX 50",
    "IS3N.DE": "iShares MSCI EM IMI", "XEON.DE": "Overnight Rate (EUR)", "DBXP.DE": "Govt Bond 1-3y"
}

color_map = {
    "SXR8.DE": "#377EB8", "SXRV.DE": "#4DAF4A", "XRS2.DE": "#FFFF33",
    "EXSA.DE": "#4DBEEE", "SXRT.DE": "#984EA3",
    "IS3N.DE": "#E41A1C", "XEON.DE": "#FF7F00", "DBXP.DE": "#F781BF"
}

# --- SIDEBAR: KONFIGURACJA ---
st.sidebar.header("⚙️ Konfiguracja")

# Odczyt domyślnych z adresu URL lub standardowe
url_tickers = st.query_params.get_all("t")
default_selection = url_tickers if url_tickers else ["SXR8.DE", "EXSA.DE", "IS3N.DE", "XEON.DE"]

selected_tickers = st.sidebar.multiselect(
    "Wybierz instrumenty:",
    options=list(etf_data.keys()),
    default=default_selection,
    format_func=lambda x: f"{x} ({etf_data[x]})"
)

if st.sidebar.button("Zapisz w adresie URL 🔗"):
    st.query_params.clear()
    for t in selected_tickers:
        st.query_params.append("t", t)
    st.sidebar.success("Zapisano! Możesz teraz dodać tę stronę do zakładek.")

# --- ANALIZA ---
start_date = datetime.now() - timedelta(days=5*365)
all_data = get_data(selected_tickers, start_date)

if not all_data.empty:
    month_ends = pd.date_range(start=all_data.index.min(), end=all_data.index.max(), freq='ME')
    dates_list = list(month_ends[::-1])
    
    selected_month = st.selectbox("Miesiąc końcowy:", options=dates_list, 
                                  format_func=lambda x: x.strftime('%m.%Y'), key="sel_m")
    
    actual_end = all_data.index[all_data.index <= pd.Timestamp(selected_month)][-1]
    start_view = actual_end - timedelta(days=365)
    window = all_data.loc[start_view:actual_end]
    
    perf = sorted([{'ticker': t, 'return': ((window[t].iloc[-1]/window[t].iloc[0])-1)*100, 'series': window[t]} 
                   for t in selected_tickers if t in window.columns], key=lambda x: x['return'], reverse=True)

    # SYGNAŁ
    best = perf[0]
    xeon_ret = next((x['return'] for x in perf if x['ticker'] == "XEON.DE"), -999.0)
    if best['ticker'] == "XEON.DE" or best['return'] < xeon_ret:
        st.error(f"🚨 SYGNAŁ: GOTÓWKA (XEON)")
    else:
        st.success(f"🚀 SYGNAŁ: INVEST ({best['ticker']}) {best['return']:+.2f}%")

    # --- WYKRES ---
    fig = go.Figure()
    for item in perf:
        fig.add_trace(go.Scatter(x=item['series'].index, y=((item['series']/item['series'].iloc[0])-1)*100, 
                                 name=f"{item['ticker']}", 
                                 line=dict(width=3, color=color_map.get(item['ticker']))))
    fig.update_layout(template="plotly_dark", height=400, xaxis=dict(fixedrange=True), yaxis=dict(fixedrange=True, ticksuffix="%"), 
                      hovermode=False, margin=dict(l=10, r=10, t=30, b=0), staticPlot=True)
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False, 'staticPlot': True})

    # --- TABELA WEDŁUG SZKICU ---
    st.markdown("---")
    st.subheader("🗓️ Historia Rankingu")
    
    curr_idx = dates_list.index(selected_month)
    past_months = dates_list[max(0, curr_idx-2):min(len(dates_list), curr_idx+4)][::-1]
    
    rank_history = []
    for m in past_months:
        m_e = all_data.index[all_data.index <= m][-1]
        m_w = all_data.loc[m_e - timedelta(days=365):m_e]
        r = sorted([(t, ((m_w[t].iloc[-1]/m_w[t].iloc[0])-1)*100) for t in selected_tickers], key=lambda x: x[1], reverse=True)
        rank_history.append({'date': m.strftime('%m/%Y'), 'ranks': {x[0]: i+1 for i, x in enumerate(r)}, 'data': r})

    html = "<table class='custom-table'><tr><th></th>"
    for rh in rank_history:
        html += f"<th>{rh['date']}</th>"
    html += "</tr>"

    for i in range(4): # Pozycje #1, #2, #3, #4
        html += f"<tr><td style='font-weight: bold; color: #888;'>#{i+1}</td>"
        for j in range(len(rank_history)):
            curr_t, curr_v = rank_history[j]['data'][i]
            ticker_color = color_map.get(curr_t, "white")
            
            trend_color = "white"
            icon = ""
            if j > 0:
                old_pos = rank_history[j-1]['ranks'].get(curr_t, 99)
                if i+1 < old_pos: trend_color = "#00ff00"; icon = " ↑"
                elif i+1 > old_pos: trend_color = "#ff4b4b"; icon = " ↓"
            
            html += f"<td><b style='color: {ticker_color};'>{curr_t}</b><br>"
            html += f"<span style='color: {trend_color}; font-size: 10px;'>({curr_v:+.2f}%){icon}</span></td>"
        html += "</tr>"
    html += "</table>"
    st.write(html, unsafe_allow_html=True)

    # --- STOPKA ---
    st.markdown("<br><hr>", unsafe_allow_html=True)
    c1, c2 = st.columns([1, 4])
    c1.image("https://s.yimg.com/rz/p/yahoo_finance_en-US_h_p_finance_2.png", width=120)
    c2.markdown("<p style='font-size: 11px; color: #777;'>Dane Yahoo Finance. Dane mogą być opóźnione. Pamiętaj o weryfikacji sygnałów przed decyzją.</p>", unsafe_allow_html=True)
else:
    st.info("Wybierz instrumenty w menu bocznym.")
