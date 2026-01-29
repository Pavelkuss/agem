import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Ustawienia strony
st.set_page_config(page_title="Monitor Trendu ETF (EUR)", layout="wide")
st.title("📈 Analiza Trendu (Okno 12m) - Baza: EUR")

# --- BIBLIOTEKA ETF (Zaktualizowana) ---
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
        "IB01.AS": "iShares $ Treasury 0-1yr (USD)",
        "VGEA.DE": "Vanguard EUR Govt Bond (7-10y EUR)",
        "SXRQ.DE": "iShares $ Treasury 7-10yr (EUR Hedged)"
    }
}

# Stałe przypisanie kolorów do tickerów
color_map = {
    "SXRV.DE": "#4DAF4A",  # Zielony
    "SXRT.DE": "#984EA3",  # Fioletowy
    "IS3N.DE": "#E41A1C",  # Czerwony
    "SXR8.DE": "#377EB8",  # Niebieski
    "EXSA.DE": "#4DBEEE",  # Jasnoniebieski
    "EIMI.AS": "#FFD700",  # Złoty
    "XEON.DE": "#A65628",  # Brązowy
    "CBU0.DE": "#F781BF",  # Różowy
    "IB01.AS": "#D95F02",  # Ciemnopomarańczowy
    "VGEA.DE": "#FF7F00",  # Pomarańczowy
    "SXRQ.DE": "#FFFF33"   # Żółty
}

# --- FUNKCJE POMOCNICZE ---
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

@st.cache_data(ttl=3600)
def get_synchronized_data(tickers, start):
    if not tickers: return pd.DataFrame()
    combined = pd.DataFrame()
    failed = []
    for t in tickers:
        try:
            df = yf.download(t, start=start, progress=False, multi_level_index=False)
            if not df.empty and 'Close' in df.columns:
                combined[t] = df['Close']
            else:
                failed.append(t)
        except:
            failed.append(t)
    
    if failed:
        st.sidebar.warning(f"Brak danych dla: {', '.join(failed)}")
    
    return combined.dropna()

# --- INTERFEJS BOCZNY ---
st.sidebar.header("🔍 Wybór Instrumentów")
selected_tickers = []

for category, items in etf_library.items():
    st.sidebar.subheader(category)
    for ticker, name in items.items():
        # Domyślnie zaznaczone walory
        is_default = ticker in ["SXRV.DE", "SXRT.DE", "IS3N.DE", "XEON.DE"]
        if st.sidebar.checkbox(f"{ticker} ({name})", value=is_default):
            selected_tickers.append(ticker)

# --- ANALIZA DANYCH ---
start_date = datetime.now() - timedelta(days=5*365)
all_data = get_synchronized_data(selected_tickers, start_date)

if not all_data.empty:
    # Wybór daty
    month_ends = pd.date_range(start=all_data.index.min(), end=all_data.index.max(), freq='ME')[::-1]
    selected_month = st.selectbox("Wybierz miesiąc końcowy okna 12m:", options=list(month_ends), format_func=lambda x: x.strftime('%m.%Y'))
    
    # Synchronizacja okna czasowego
    actual_end = all_data.index[all_data.index <= pd.Timestamp(selected_month)][-1]
    start_view = actual_end - timedelta(days=365)
    window_data = all_data.loc[start_view:actual_end]
    
    # Obliczanie wskaźników
    perf_data = []
    for t in selected_tickers:
        if t in window_data.columns:
            series = window_data[t]
            ret = ((series.iloc[-1] / series.iloc[0]) - 1) * 100
            
            # RSI obliczane na pełnych danych do wybranej daty
            full_series = all_data[t].loc[:actual_end]
            rsi_val = calculate_rsi(full_series).iloc[-1]
            
            perf_data.append({'ticker': t, 'return': ret, 'rsi': rsi_val, 'series': series})
    
    # Sortowanie (najlepszy wynik pierwszy)
    perf_data = sorted(perf_data, key=lambda x: x['return'], reverse=True)

    # 1. WYKRES LINIOWY (Skumulowany zwrot)
    fig_line = go.Figure()
    for item in perf_data:
        t = item['ticker']
        fig_line.add_trace(go.Scatter(
            x=item['series'].index, 
            y=((item['series']/item['series'].iloc[0])-1)*100, 
            name=t, 
            line=dict(width=3, color=color_map.get(t))
        ))
    
    fig_line.update_layout(
        template="plotly_dark", height=500,
        xaxis=dict(tickformat="%m.%Y", dtick="M1", gridcolor='rgba(255,255,255,0.1)'),
        yaxis=dict(ticksuffix="%", gridcolor='rgba(255,255,255,0.1)'),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5, traceorder="normal")
    )
    fig_line.add_hline(y=0, line_dash="dash", line_color="gray")
    st.plotly_chart(fig_line, use_container_width=True)

    # 2. TABELA RANKINGOWA
    st.markdown(f"<h4 style='text-align: center;'>🏆 Ranking końcowy: {actual_end.strftime('%d.%m.%Y')}</h4>", unsafe_allow_html=True)
    
    rank_list = []
    for i in perf_data:
        rsi_stat = "🔥 Wykupiony" if i['rsi'] > 70 else "❄️ Wyprzedany" if i['rsi'] < 30 else "✅ Stabilny"
        rank_list.append({
            "Ticker": i['ticker'],
            "Wynik 12m": f"{i['return']:+.2f}%",
            "RSI (14)": f"{i['rsi']:.1f}",
            "Status": rsi_stat
        })
    
    st.table(pd.DataFrame(rank_list))

    # 3. WYKRES MOMENTUM (Miesięczne słupki)
    st.markdown("---")
    st.markdown("<h4 style='text-align: center;'>📊 Miesięczne stopy zwrotu (Momentum)</h4>", unsafe_allow_html=True)
    
    monthly_rets = window_data.resample('ME').last().pct_change().dropna() * 100
    
    fig_bar = go.Figure()
    for item in perf_data:
        t = item['ticker']
        fig_bar.add_trace(go.Bar(
            x=monthly_rets.index.strftime('%m.%Y'),
            y=monthly_rets[t],
            name=t,
            marker_color=color_map.get(t)
        ))
    
    fig_bar.update_layout(
        template="plotly_dark", height=400, barmode='group',
        xaxis=dict(title="Miesiąc"), yaxis=dict(ticksuffix="%"),
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5),
        hovermode="x unified"
    )
    st.plotly_chart(fig_bar, use_container_width=True)

else:
    st.info("Wybierz instrumenty z menu po lewej stronie, aby wyświetlić analizę.")
