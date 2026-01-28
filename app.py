import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd

st.set_page_config(page_title="Monitor Trendu ETF (EUR)", layout="wide")

# --- KONFIGURACJA BIBLIOTEKI ETF ---
# Wybrane fundusze typu Accumulating, notowane na Xetra/Amsterdam w EUR
etf_library = {
    "USA (S&P 500 / Nasdaq)": {
        "SXR8.DE": "iShares Core S&P 500 Acc",
        "SXRV.DE": "iShares Nasdaq 100 Acc",
        "SXRQ.DE": "iShares $ Treasury 7-10yr (EUR Hedged) Acc"
    },
    "Europa (Stoxx 50 / 600)": {
        "SXRT.DE": "iShares Core EURO STOXX 50 Acc",
        "EXSA.DE": "iShares STOXX Europe 600 Acc",
        "VGEA.DE": "Vanguard EUR Govt Bond Acc"
    },
    "Emerging Markets": {
        "IS3N.DE": "iShares Core MSCI EM IMI Acc",
        "EIMI.AS": "iShares MSCI EM IMI (Acc) - AMS"
    },
    "Obligacje 0-1y (Gotówka/Cash)": {
        "IB01.DE": "iShares $ Treasury 0-1yr (USD) Acc",
        "XEON.DE": "Xtrackers II EUR Overnight Rate Swap Acc",
        "CBU0.DE": "iShares $ Treasury 0-1yr (EUR Hedged) Acc"
    }
}

# Mapowanie kolorów dla najpopularniejszych tickerów
color_map = {
    "SXRV.DE": "#4DAF4A", "SXRT.DE": "#984EA3", "IS3N.DE": "#E41A1C",
    "IB01.DE": "#FFFF33", "XEON.DE": "#A65628", "SXR8.DE": "#377EB8",
    "VGEA.DE": "#FF7F00", "CBU0.DE": "#F781BF"
}

# --- INTERFEJS UŻYTKOWNIKA ---
st.sidebar.header("🔍 Wybór Instrumentów")
selected_tickers = []

for category, items in etf_library.items():
    st.sidebar.subheader(category)
    for ticker, name in items.items():
        if st.sidebar.checkbox(f"{ticker} ({name})", value=(ticker in ["SXRV.DE", "SXRT.DE", "IS3N.DE", "XEON.DE"])):
            selected_tickers.append(ticker)

# --- LOGIKA POBIERANIA DANYCH ---
@st.cache_data(ttl=3600)
def get_data_sync(tickers, start):
    if not tickers: return pd.DataFrame()
    combined = pd.DataFrame()
    for t in tickers:
        df = yf.download(t, start=start, progress=False, multi_level_index=False)
        if not df.empty and 'Close' in df.columns:
            combined[t] = df['Close']
    return combined.dropna()

start_date = datetime.now() - timedelta(days=5*365)
all_data = get_data_sync(selected_tickers, start_date)

if not all_data.empty:
    # Wybór daty i obliczenia (identyczne jak wcześniej)
    month_ends = pd.date_range(start=all_data.index.min(), end=all_data.index.max(), freq='ME')[::-1]
    selected_end = st.selectbox("Miesiąc końcowy:", options=list(month_ends), format_func=lambda x: x.strftime('%m.%Y'))
    
    actual_end = all_data.index[all_data.index <= pd.Timestamp(selected_end)][-1]
    start_view = actual_end - timedelta(days=365)
    window = all_data.loc[start_view:actual_end]
    
    # Ranking i RSI
    perf = []
    for t in selected_tickers:
        if t in window.columns:
            ret = ((window[t].iloc[-1] / window[t].iloc[0]) - 1) * 100
            perf.append({'ticker': t, 'return': ret, 'series': window[t]})
    
    perf = sorted(perf, key=lambda x: x['return'], reverse=True)

    # Wykres główny
    fig = go.Figure()
    for item in perf:
        fig.add_trace(go.Scatter(x=item['series'].index, y=((item['series']/item['series'].iloc[0])-1)*100, 
                                 name=item['ticker'], line=dict(width=3, color=color_map.get(item['ticker'], None))))
    fig.update_layout(template="plotly_dark", height=450, xaxis=dict(tickformat="%m.%Y"), hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

    # Tabela
    st.table(pd.DataFrame([{"Ticker": i['ticker'], "Wynik 12m": f"{i['return']:+.2f}%"} for i in perf]))
