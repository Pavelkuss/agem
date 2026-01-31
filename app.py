import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="GEM Monitor", layout="wide")

# --- CSS: RESPONSYWNOŚĆ I STYLIZACJA ---
st.markdown("""
    <style>
    .stPlotlyChart { pointer-events: none; }
    .main-title { font-size: 1.8rem; font-weight: bold; margin-bottom: 0; text-align: center; }
    
    /* Kontener tabeli z przewijaniem bocznym na mobile */
    .table-container {
        width: 100%;
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
    }
    
    .custom-table { 
        width: 100%; 
        border-collapse: collapse; 
        font-size: 11px; 
        color: white; 
        margin-top: 10px;
        min-width: 500px; /* Gwarantuje czytelność przy przewijaniu */
    }
    
    .custom-table th { border-bottom: 2px solid #444; padding: 8px 4px; text-align: center; background-color: #1E1E1E; }
    .custom-table td { border-bottom: 1px solid #333; padding: 6px 2px; text-align: center; }
    
    /* Szerokość pierwszej kolumny */
    .col-rank { width: 30px; color: #888; font-weight: bold; }
    
    /* Poprawka dla multiselect na mobile */
    .stMultiSelect span { font-size: 12px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNKCJA POBIERANIA DANYCH ---
@st.cache_data(ttl=3600)
def get_data(tickers, start):
    if not tickers: return pd.DataFrame()
    combined = pd.DataFrame()
    for t in tickers:
        try:
            df = yf.download(t, start=start, progress=False, multi_level_index=False)
            if not df.empty: combined[t] = df['Close']
        except: continue
    return combined.dropna()

# --- NAGŁÓWEK ---
st.markdown("""
    <div style="text-align: center; margin-bottom: 15px;">
        <h1 class="main-title">📈 GEM Momentum</h1>
        <p style="color: #888; margin: 0; font-size: 0.9rem;">Smart Momentum. Safe Haven.</p>
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

# --- SIDEBAR & URL PARAMS ---
st.sidebar.header("⚙️ Konfiguracja")
params = st.query_params.to_dict()
url_tickers = params.get("t", "").split(",") if params.get("t") else []
default_selection = [t for t in url_tickers if t in etf_data] if url_tickers else ["SXR8.DE", "EXSA.DE", "IS3N.DE", "XEON.DE"]

selected_tickers = st.sidebar.multiselect(
    "Instrumenty:", options=list(etf_data.keys()), default=default_selection,
    format_func=lambda x: f"{x} ({etf_data[x]})"
)

if st.sidebar.button("Zapisz URL 🔗"):
    st.query_params["t"] = ",".join(selected_tickers)
    st.sidebar.success("Zapisano!")

# --- ANALIZA ---
all_data = get_data(selected_tickers, datetime.now() - timedelta(days=5*365))

if not all_data.empty:
    month_ends = pd.date_range(start=all_data.index.min(), end=all_data.index.max(), freq='ME')
    dates_list = list(month_ends[::-1])
    
    selected_month = st.selectbox("Miesiąc końcowy:", options=dates_list, format_func=lambda x: x.strftime('%m.%Y'))
    
    actual_end = all_data.index[all_data.index <= pd.Timestamp(selected_month)][-1]
    window = all_data.loc[actual_end - timedelta(days=365):actual_end]
    
    perf = sorted([{'ticker': t, 'return': ((window[t].iloc[-1]/window[t].iloc[0])-1)*100, 'series': window[t]} 
                   for t in selected_tickers if t in window.columns], key=lambda x: x['return'], reverse=True)

    # SYGNAŁ
    best = perf[0]
    xeon_ret = next((x['return'] for x in perf if x['ticker'] == "XEON.DE"), -999.0)
    if best['ticker'] == "XEON.DE" or best['return'] < xeon_ret:
        st.error(f"🚨 SYGNAŁ: GOTÓWKA (XEON)")
    else:
        st.success(f"🚀 SYGNAŁ: {best['ticker']} ({best['return']:+.2f}%)")

    # --- WYKRES (PRZYWRÓCONA LEGENDA) ---
    fig = go.Figure()
    for item in perf:
        fig.add_trace(go.Scatter(x=item['series'].index, y=((item['series']/item['series'].iloc[0])-1)*100, 
                                 name=item['ticker'], line=dict(width=2, color=color_map.get(item['ticker']))))
    
    fig.update_layout(
        template="plotly_dark", height=300, 
        margin=dict(l=5, r=5, t=10, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(size=10)),
        xaxis=dict(fixedrange=True, showgrid=False), 
        yaxis=dict(fixedrange=True, ticksuffix="%"),
        hovermode=False
    )
    st.plotly_chart(fig, use_container_width=True, config={'staticPlot': True})

    # --- TABELA (ZOPTYMALIZOWANA) ---
    st.markdown("---")
    curr_idx = dates_list.index(selected_month)
    display_months = dates_list[curr_idx:curr_idx+5][::-1] 
    
    rank_history = []
    for m in display_months:
        m_e = all_data.index[all_data.index <= m][-1]
        m_w = all_data.loc[m_e - timedelta(days=365):m_e]
        r = sorted([(t, ((m_w[t].iloc[-1]/m_w[t].iloc[0])-1)*100) for t in selected_tickers], key=lambda x: x[1], reverse=True)
        rank_history.append({'date': m.strftime('%m/%y'), 'ranks': {x[0]: i+1 for i, x in enumerate(r)}, 'data': r})

    html = "<div class='table-container'><table class='custom-table'><tr><th class='col-rank'>#</th>"
    for rh in rank_history:
        html += f"<th>{rh['date']}</th>"
    html += "</tr>"

    for i in range(len(selected_tickers)):
        html += f"<tr><td class='col-rank'>#{i+1}</td>"
        for j in range(len(rank_history)):
            if i < len(rank_history[j]['data']):
                curr_t, curr_v = rank_history[j]['data'][i]
                t_color = color_map.get(curr_t, "white")
                trend_color = "white"; icon = ""
                if j > 0:
                    old_pos = rank_history[j-1]['ranks'].get(curr_t, 99)
                    if i+1 < old_pos: trend_color = "#00ff00"; icon = "↑"
                    elif i+1 > old_pos: trend_color = "#ff4b4b"; icon = "↓"
                
                html += f"<td><b style='color: {t_color};'>{curr_t}</b><br>"
                html += f"<span style='color: {trend_color}; font-size: 9px;'>{curr_v:+.1f}% {icon}</span></td>"
            else:
                html += "<td>-</td>"
        html += "</tr>"
    html += "</table></div>"
    st.write(html, unsafe_allow_html=True)

    # --- STOPKA ---
    st.markdown("<br>", unsafe_allow_html=True)
    st.image("https://s.yimg.com/rz/p/yahoo_finance_en-US_h_p_finance_2.png", width=100)
else:
    st.info("Wybierz instrumenty w menu bocznym.")
