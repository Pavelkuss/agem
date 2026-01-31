import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd

st.set_page_config(page_title="GEM Monitor (EUR)", layout="wide")
st.title("🛡️ GEM Momentum: USA - EU - EM")

# --- BIBLIOTEKA INSTRUMENTÓW ---
etf_library = {
    "USA": {
        "SXR8.DE": "iShares S&P 500",
        "SXRV.DE": "iShares Nasdaq 100",
        "XRS2.DE": "Xtrackers Russell 2000"
    },
    "Europa": {
        "EXSA.DE": "iShares STOXX 600",
        "SXRT.DE": "iShares EURO STOXX 50"
    },
    "Emerging Markets": {
        "IS3N.DE": "iShares MSCI EM IMI"
    },
    "Bezpieczna Baza": {
        "XEON.DE": "Overnight Rate (EUR)",
        "DBXP.DE": "Govt Bond 1-3y"
    }
}

color_map = {
    "SXR8.DE": "#377EB8", "SXRV.DE": "#4DAF4A", "XRS2.DE": "#FFFF33",
    "EXSA.DE": "#4DBEEE", "SXRT.DE": "#984EA3",
    "IS3N.DE": "#E41A1C", "XEON.DE": "#FF7F00", "DBXP.DE": "#F781BF"
}

@st.cache_data(ttl=3600)
def get_data(tickers, start):
    combined = pd.DataFrame()
    for t in tickers:
        df = yf.download(t, start=start, progress=False, multi_level_index=False)
        if not df.empty and 'Close' in df.columns:
            combined[t] = df['Close']
    return combined.dropna()

# --- SIDEBAR ---
selected_tickers = []
st.sidebar.header("🔍 Wybór ETF")
for cat, items in etf_library.items():
    st.sidebar.subheader(cat)
    for ticker, name in items.items():
        if st.sidebar.checkbox(f"{ticker}", value=ticker in ["SXR8.DE", "XRS2.DE", "EXSA.DE", "XEON.DE"]):
            selected_tickers.append(ticker)

# --- ANALIZA ---
start_date = datetime.now() - timedelta(days=5*365)
all_data = get_data(selected_tickers, start_date)

if not all_data.empty:
    month_ends = pd.date_range(start=all_data.index.min(), end=all_data.index.max(), freq='ME')
    selected_month = st.selectbox("Miesiąc końcowy:", options=list(month_ends[::-1]), format_func=lambda x: x.strftime('%m.%Y'))
    
    actual_end = all_data.index[all_data.index <= pd.Timestamp(selected_month)][-1]
    start_view = actual_end - timedelta(days=365)
    window = all_data.loc[start_view:actual_end]
    
    perf = sorted([{'ticker': t, 'return': ((window[t].iloc[-1]/window[t].iloc[0])-1)*100, 'series': window[t]} 
                   for t in selected_tickers if t in window.columns], key=lambda x: x['return'], reverse=True)

    # SYGNAŁ
    best = perf[0]
    xeon_ret = next((x['return'] for x in perf if x['ticker'] == "XEON.DE"), -999)
    if best['ticker'] == "XEON.DE" or best['return'] < xeon_ret:
        st.error(f"SYGNAŁ: GOTÓWKA (XEON)")
    else:
        st.success(f"SYGNAŁ: INVEST ({best['ticker']}) {best['return']:+.2f}%")

    # --- WYKRES (Z odblokowanym przewijaniem dla mobile) ---
    fig = go.Figure()
    for item in perf:
        fig.add_trace(go.Scatter(x=item['series'].index, y=((item['series']/item['series'].iloc[0])-1)*100, 
                                 name=f"{item['ticker']} ({item['return']:+.1f}%)", 
                                 line=dict(width=3, color=color_map.get(item['ticker']))))
    
    fig.update_layout(template="plotly_dark", height=450, 
                      xaxis=dict(fixedrange=False), yaxis=dict(fixedrange=False), # Ważne dla mobile!
                      legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center"),
                      margin=dict(l=0, r=0, t=30, b=0))
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False, 'scrollZoom': False})

    # --- TABELA HTML (Kolory i Mobile-friendly) ---
    st.markdown("---")
    st.subheader("🗓️ Historia Rankingu")
    
    current_idx = list(month_ends).index(pd.Timestamp(selected_month))
    past_months = month_ends[max(0, current_idx-5):current_idx+1]
    
    # Obliczanie rankingów
    rank_history = []
    for m in past_months:
        m_e = all_data.index[all_data.index <= m][-1]
        m_w = all_data.loc[m_e - timedelta(days=365):m_e]
        r = sorted([(t, ((m_w[t].iloc[-1]/m_w[t].iloc[0])-1)*100) for t in selected_tickers], key=lambda x: x[1], reverse=True)
        rank_history.append({'date': m.strftime('%m/%y'), 'ranks': {x[0]: i+1 for i, x in enumerate(r)}, 'data': r})

    # Budowanie tabeli HTML
    html = "<table style='width:100%; border-collapse: collapse; font-size: 12px; color: white;'>"
    html += "<tr><th style='border-bottom: 1px solid #444;'>Poz.</th>"
    for rh in rank_history:
        html += f"<th style='border-bottom: 1px solid #444; text-align: center;'>{rh['date']}</th>"
    html += "</tr>"

    for i in range(4): # Top 4
        html += f"<tr><td style='font-weight: bold; border-bottom: 1px solid #222;'>#{i+1}</td>"
        for j in range(len(rank_history)):
            curr_t, curr_v = rank_history[j]['data'][i]
            # Logika strzałki i koloru
            icon = ""
            color = "white"
            if j > 0:
                prev_ranks = rank_history[j-1]['ranks']
                old_pos = prev_ranks.get(curr_t, 99)
                if i+1 < old_pos: 
                    icon = " ↑"
                    color = "#00ff00" # Zielony
                elif i+1 > old_pos: 
                    icon = " ↓"
                    color = "#ff4b4b" # Czerwony
            
            html += f"<td style='text-align: center; border-bottom: 1px solid #222; padding: 5px 2px; color: {color};'>"
            html += f"{curr_t}<br><span style='font-size: 10px;'>{curr_v:+.1f}%{icon}</span></td>"
        html += "</tr>"
    html += "</table>"
    
    st.write(html, unsafe_allow_html=True)

    # --- STOPKA ---
    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2 = st.columns([1, 4])
    c1.image("https://s.yimg.com/rz/p/yahoo_finance_en-US_h_p_finance_2.png", width=120)
    c2.markdown("""
    <p style='font-size: 12px; color: #888;'>
    Aplikacja korzysta z darmowych danych <b>Yahoo Finance</b>. Dane mogą być opóźnione.<br>
    Pamiętaj o weryfikacji sygnałów przed podjęciem decyzji inwestycyjnych.
    </p>
    """, unsafe_allow_html=True)
else:
    st.info("Zaznacz instrumenty w menu bocznym.")
