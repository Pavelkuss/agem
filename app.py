import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd

st.set_page_config(page_title="Monitor Trendu ETF (EUR)", layout="wide")

# --- OCZYSZCZONA BIBLIOTEKA ETF ---
etf_library = {
    "USA (S&P 500 / Nasdaq)": {
        "SXR8.DE": "iShares Core S&P 500 Acc",
        "SXRV.DE": "iShares Nasdaq 100 Acc"
    },
    "Europa (Stoxx 50 / 600)": {
        "SXRT.DE": "iShares Core EURO STOXX 50 Acc",
        "EXSA.DE": "iShares STOXX Europe 600 Acc"
    },
    "Emerging Markets": {
        "IS3N.DE": "iShares Core MSCI EM IMI Acc",
        "EIMI.AS": "iShares MSCI EM IMI (Acc) - AMS"
    },
    "Obligacje i Gotówka": {
        "XEON.DE": "Xtrackers II EUR Overnight Rate (0-1y EUR)",
        "CBU0.DE": "iShares $ Treasury 0-1yr (EUR Hedged)",
        "IB01.DE": "iShares $ Treasury 0-1yr (USD)",
        "VGEA.DE": "Vanguard EUR Govt Bond (7-10y EUR)",
        "SXRQ.DE": "iShares $ Treasury 7-10yr (EUR Hedged)"
    }
}

# Mapowanie kolorów dla spójności wizualnej
color_map = {
    "SXRV.DE": "#4DAF4A", "SXRT.DE": "#984EA3", "IS3N.DE": "#E41A1C",
    "XEON.DE": "#A65628", "SXR8.DE": "#377EB8", "VGEA.DE": "#FF7F00",
    "CBU0.DE": "#F781BF", "SXRQ.DE": "#FFFF33"
}

# --- SIDEBAR: WYBÓR INSTRUMENTÓW ---
st.sidebar.header("🔍 Wybór Instrumentów")
selected_tickers = []

for category, items in etf_library.items():
    st.sidebar.subheader(category)
    for ticker, name in items.items():
        # Domyślnie zaznaczamy główne indeksy i gotówkę dla porównania
        default_val = ticker in ["SXRV.DE", "SXRT.DE", "IS3N.DE", "XEON.DE"]
        if st.sidebar.checkbox(f"{ticker} ({name})", value=default_val):
            selected_tickers.append(ticker)

# --- FUNKCJA POBIERANIA I SYNCHRONIZACJI ---
@st.cache_data(ttl=3600)
def get_synchronized_data(tickers, start):
    if not tickers: return pd.DataFrame()
    combined = pd.DataFrame()
    for t in tickers:
        try:
            df = yf.download(t, start=start, progress=False, multi_level_index=False)
            if not df.empty and 'Close' in df.columns:
                combined[t] = df['Close']
        except:
            continue
    return combined.dropna() # Synchronizacja końcówek (rozwiązuje problem NaN z obrazka)

# --- GŁÓWNA LOGIKA ANALIZY ---
start_date = datetime.now() - timedelta(days=5*365)
all_data = get_synchronized_data(selected_tickers, start_date)

if not all_data.empty:
    month_ends = pd.date_range(start=all_data.index.min(), end=all_data.index.max(), freq='ME')[::-1]
    selected_end = st.selectbox("Wybierz miesiąc końcowy okna 12m:", options=list(month_ends), format_func=lambda x: x.strftime('%m.%Y'))
    
    # Wyznaczenie precyzyjnej daty końcowej po synchronizacji
    actual_end = all_data.index[all_data.index <= pd.Timestamp(selected_end)][-1]
    start_view = actual_end - timedelta(days=365)
    window = all_data.loc[start_view:actual_end]
    
    # Obliczenia zwrotów
    perf = []
    for t in selected_tickers:
        if t in window.columns:
            ret = ((window[t].iloc[-1] / window[t].iloc[0]) - 1) * 100
            perf.append({'ticker': t, 'return': ret, 'series': window[t]})
    
    # Sortowanie dla legendy i rankingu (najlepszy po lewej/na górze)
    perf = sorted(perf, key=lambda x: x['return'], reverse=True)

    # 1. Wykres skumulowany
    fig = go.Figure()
    for item in perf:
        t = item['ticker']
        fig.add_trace(go.Scatter(
            x=item['series'].index, 
            y=((item['series']/item['series'].iloc[0])-1)*100, 
            name=t, 
            line=dict(width=3, color=color_map.get(t))
        ))
    
    fig.update_layout(
        template="plotly_dark", height=450,
        xaxis=dict(tickformat="%m.%Y", dtick="M1"),
        yaxis=dict(ticksuffix="%"),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5, traceorder="normal")
    )
    st.plotly_chart(fig, use_container_width=True)

    # 2. Tabela rankingowa
    st.markdown(f"<h4 style='text-align: center;'>🏆 Ranking końcowy: {actual_end.strftime('%d.%m.%Y')}</h4>", unsafe_allow_html=True)
    df_rank = pd.DataFrame([{"Ticker": i['ticker'], "Wynik 12m": f"{i['return']:+.2f}%"} for i in perf])
    st.table(df_rank)

    # 3. Wykres momentum (miesięczne słupki)
    st.markdown("---")
    monthly_returns = window.resample('ME').last().pct_change().dropna() * 100
    
    fig_bar = go.Figure()
    for item in perf:
        t = item['ticker']
        fig_bar.add_trace(go.Bar(
            x=monthly_returns.index.strftime('%m.%Y'),
            y=monthly_returns[t],
            name=t,
            marker_color=color_map.get(t)
        ))
    
    fig_bar.update_layout(
        template="plotly_dark", height=350, barmode='group',
        xaxis=dict(title="Miesiąc"), yaxis=dict(ticksuffix="%"),
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5)
    )
    st.plotly_chart(fig_bar, use_container_width=True)
else:
    st.info("Zaznacz instrumenty w menu bocznym, aby rozpocząć analizę.")
