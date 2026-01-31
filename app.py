import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd

# Ustawienia strony
st.set_page_config(page_title="GEM Monitor (EUR)", layout="wide")

# --- CSS: STYLIZACJA ---
st.markdown("""
    <style>
    .stPlotlyChart { pointer-events: none; }
    .main-title { font-size: 2.2rem; font-weight: bold; margin-bottom: 0; text-align: center; }
    .custom-table { width: 100%; border-collapse: collapse; font-size: 11px; color: white; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

# Nagłówek
st.markdown("""
    <div style="text-align: center; margin-bottom: 20px;">
        <h1 class="main-title">📈 GEM Momentum: USA - EU - EM</h1>
    </div>
    """, unsafe_allow_html=True)

# --- KONFIGURACJA I BIBLIOTEKA ---
etf_library = {
    "USA": {"SXR8.DE": "iShares S&P 500", "SXRV.DE": "iShares Nasdaq 100", "XRS2.DE": "Xtrackers Russell 2000"},
    "Europa": {"EXSA.DE": "iShares STOXX 600", "SXRT.DE": "iShares EURO STOXX 50"},
    "Emerging Markets": {"IS3N.DE": "iShares MSCI EM IMI"},
    "Bezpieczna Baza": {"XEON.DE": "Overnight Rate (EUR)", "DBXP.DE": "Govt Bond 1-3y"}
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

# --- SIDEBAR: WYBÓR I ZAPAMIĘTYWANIE ---
st.sidebar.header("🔍 Wybór ETF")
selected_tickers = []

for cat, items in etf_library.items():
    st.sidebar.subheader(cat)
    for ticker, name in items.items():
        # Domyślne ładowanie: S&P500, STOXX600, EM, XEON
        default_val = ticker in ["SXR8.DE", "EXSA.DE", "IS3N.DE", "XEON.DE"]
        if st.sidebar.checkbox(f"{ticker}", value=default_val, key=f"cb_{ticker}"):
            selected_tickers.append(ticker)

# --- ANALIZA ---
start_date = datetime.now() - timedelta(days=5*365)
all_data = get_data(selected_tickers, start_date)

if not all_data.empty:
    month_ends = pd.date_range(start=all_data.index.min(), end=all_data.index.max(), freq='ME')
    dates_list = list(month_ends[::-1]) # Najnowsze na górze
    
    # --- NOWA LOGIKA WYBORU MIESIĄCA ---
    # Inicjalizacja stanu, jeśli nie istnieje
    if 'sel_month_idx' not in st.session_state:
        st.session_state.sel_month_idx = 0

    selected_month = st.selectbox(
        "Wybierz miesiąc końcowy (okno 12m):", 
        options=dates_list, 
        index=st.session_state.sel_month_idx,
        format_func=lambda x: x.strftime('%m.%Y'), 
        key="sel_month_widget"
    )
    # Aktualizacja indeksu w sesji po wyborze
    st.session_state.sel_month_idx = dates_list.index(selected_month)
    
    actual_end = all_data.index[all_data.index <= pd.Timestamp(selected_month)][-1]
    start_view = actual_end - timedelta(days=365)
    window = all_data.loc[start_view:actual_end]
    
    perf = sorted([{'ticker': t, 'return': ((window[t].iloc[-1]/window[t].iloc[0])-1)*100, 'series': window[t]} 
                   for t in selected_tickers if t in window.columns], key=lambda x: x['return'], reverse=True)

    # SYGNAŁ
    best = perf[0]
    xeon_ret = next((x['return'] for x in perf if x['ticker'] == "XEON.DE"), -999)
    if best['ticker'] == "XEON.DE" or best['return'] < xeon_ret:
        st.error(f"🚨 SYGNAŁ: GOTÓWKA (XEON)")
    else:
        st.success(f"🚀 SYGNAŁ: INVEST ({best['ticker']}) {best['return']:+.2f}%")

    # --- WYKRES (Statyczny) ---
    fig = go.Figure()
    for item in perf:
        fig.add_trace(go.Scatter(x=item['series'].index, y=((item['series']/item['series'].iloc[0])-1)*100, 
                                 name=f"{item['ticker']} ({item['return']:+.1f}%)", 
                                 line=dict(width=3, color=color_map.get(item['ticker']))))
    
    fig.update_layout(
        template="plotly_dark", height=400, 
        xaxis=dict(fixedrange=True, showgrid=False), 
        yaxis=dict(fixedrange=True, ticksuffix="%"), 
        hovermode=False,
        legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center"),
        margin=dict(l=10, r=10, t=30, b=0)
    )
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False, 'staticPlot': True})

    # --- TABELA HISTORYCZNA (HTML + Kolory Wykresu + Kolory Trendu) ---
    st.markdown("---")
    st.subheader("🗓️ Historia Rankingu Momentum")
    
    current_idx = dates_list.index(selected_month)
    # Wybieramy 6 miesięcy wokół wybranej daty (lub ostatnie 6, jeśli jesteśmy na końcu)
    # dates_list jest malejąca (najnowsze na początku)
    start_idx_table = max(0, current_idx - 2)
    end_idx_table = min(len(dates_list), start_idx_table + 6)
    past_months = dates_list[start_idx_table:end_idx_table][::-1] # Odwracamy do tabeli (chronologicznie)
    
    rank_history = []
    for m in past_months:
        m_e = all_data.index[all_data.index <= m][-1]
        m_w = all_data.loc[m_e - timedelta(days=365):m_e]
        r = sorted([(t, ((m_w[t].iloc[-1]/m_w[t].iloc[0])-1)*100) for t in selected_tickers], key=lambda x: x[1], reverse=True)
        rank_history.append({'date': m.strftime('%m/%y'), 'ranks': {x[0]: i+1 for i, x in enumerate(r)}, 'data': r})

    html = "<table class='custom-table'><tr><th style='border-bottom: 1px solid #444;'>#</th>"
    for rh in rank_history:
        # Wyróżnienie aktualnie wybranego miesiąca w nagłówku tabeli
        border = "3px solid #555" if rh['date'] == selected_month.strftime('%m/%y') else "1px solid #444"
        html += f"<th style='border-bottom: {border}; text-align: center;'>{rh['date']}</th>"
    html += "</tr>"

    for i in range(4):
        html += f"<tr><td style='font-weight: bold; border-bottom: 1px solid #333;'>{i+1}</td>"
        for j in range(len(rank_history)):
            curr_t, curr_v = rank_history[j]['data'][i]
            ticker_color = color_map.get(curr_t, "white")
            
            indicator = ""; trend_color = "white"
            if j > 0:
                old_pos = rank_history[j-1]['ranks'].get(curr_t, 99)
                if i+1 < old_pos: indicator = " ↑"; trend_color = "#00ff00"
                elif i+1 > old_pos: indicator = " ↓"; trend_color = "#ff4b4b"
            
            html += f"<td style='text-align: center; border-bottom: 1px solid #333; padding: 6px 2px;'>"
            html += f"<b style='color: {ticker_color};'>{curr_t}</b><br>"
            html += f"<span style='font-size: 9px; color: {trend_color};'>{curr_v:+.1f}%{indicator}</span></td>"
        html += "</tr>"
    html += "</table>"
    st.write(html, unsafe_allow_html=True)

    # --- STOPKA Z LOGO ---
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("---")
    c1, c2 = st.columns([1, 4])
    c1.image("https://s.yimg.com/rz/p/yahoo_finance_en-US_h_p_finance_2.png", width=120)
    c2.markdown("""
    <p style='font-size: 11px; color: #777;'>
    Aplikacja korzysta z darmowych danych <b>Yahoo Finance</b>. Dane mogą być opóźnione.<br>
    Pamiętaj o weryfikacji sygnałów przed podjęciem decyzji inwestycyjnych.
    </p>
    """, unsafe_allow_html=True)
else:
    st.info("Zaznacz instrumenty w menu bocznym.")

