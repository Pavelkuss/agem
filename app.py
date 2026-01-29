import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd

# Ustawienia strony
st.set_page_config(page_title="GEM Monitor (EUR)", layout="wide")
st.title("🛡️ GEM Momentum: USA - EU - EM")
st.markdown("Strategia dualnego momentum z bezpieczną bazą w gotówce (EUR).")

# --- BIBLIOTEKA INSTRUMENTÓW (Zgodnie z ustaleniami) ---
etf_library = {
    "USA": {
        "SXR8.DE": "iShares Core S&P 500 Acc",
        "SXRV.DE": "iShares Nasdaq 100 Acc"
    },
    "Europa": {
        "EXSA.DE": "iShares STOXX Europe 600 Acc",
        "SXRT.DE": "iShares Core EURO STOXX 50 Acc"
    },
    "Emerging Markets": {
        "IS3N.DE": "iShares Core MSCI EM IMI Acc"
    },
    "Bezpieczna Baza (Backup)": {
        "XEON.DE": "Xtrackers Overnight Rate (Gotówka EUR)",
        "DBXP.DE": "Xtrackers Eurozone Govt Bond 1-3y"
    }
}

# Stałe kolory dla czytelności
color_map = {
    "SXR8.DE": "#377EB8", "SXRV.DE": "#4DAF4A", 
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

# --- SIDEBAR: KONFIGURACJA ---
st.sidebar.header("🔍 Wybór ETF")
selected_tickers = []
for cat, items in etf_library.items():
    st.sidebar.subheader(cat)
    for ticker, name in items.items():
        # Domyślnie zaznaczamy główne indeksy i XEON
        default = ticker in ["SXR8.DE", "EXSA.DE", "IS3N.DE", "XEON.DE"]
        if st.sidebar.checkbox(f"{ticker} ({name})", value=default):
            selected_tickers.append(ticker)

# --- ANALIZA DANYCH ---
start_date = datetime.now() - timedelta(days=5*365)
all_data = get_data(selected_tickers, start_date)

if not all_data.empty:
    # Wybór daty końcowej
    month_ends = pd.date_range(start=all_data.index.min(), end=all_data.index.max(), freq='ME')[::-1]
    selected_month = st.selectbox("Wybierz miesiąc końcowy okna 12m:", options=list(month_ends), format_func=lambda x: x.strftime('%m.%Y'))
    
    # Synchronizacja okna 12 miesięcy
    actual_end = all_data.index[all_data.index <= pd.Timestamp(selected_month)][-1]
    start_view = actual_end - timedelta(days=365)
    window = all_data.loc[start_view:actual_end]
    
    # Obliczenia zwrotów
    perf = []
    for t in selected_tickers:
        if t in window.columns:
            ret = ((window[t].iloc[-1] / window[t].iloc[0]) - 1) * 100
            perf.append({'ticker': t, 'return': ret, 'series': window[t]})
    
    # Sortowanie (najlepszy wynik pierwszy)
    perf = sorted(perf, key=lambda x: x['return'], reverse=True)

    # LOGIKA SYGNAŁU GEM
    best_asset = perf[0]
    xeon_return = next((x['return'] for x in perf if x['ticker'] == "XEON.DE"), -999)
    
    st.subheader("📢 Sygnał Systemowy")
    if best_asset['ticker'] == "XEON.DE" or best_asset['return'] < xeon_return:
        st.error(f"SYGNAŁ: UCIECZKA DO GOTÓWKI (XEON). Żaden indeks nie pokonuje stopy wolnej od ryzyka.")
    else:
        st.success(f"SYGNAŁ: INVEST (Kupuj {best_asset['ticker']}). Aktywo ma najwyższe momentum.")

    # 1. WYKRES LINIOWY (Skumulowany zwrot)
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
        xaxis=dict(tickformat="%m.%Y"),
        yaxis=dict(ticksuffix="%"),
        hovermode="x unified",
        legend=dict(orientation="h", y=1.1)
    )
    st.plotly_chart(fig, use_container_width=True)

    # 2. TABELA RANKINGOWA
    st.markdown(f"### 🏆 Ranking 12m na dzień {actual_end.strftime('%d.%m.%Y')}")
    df_rank = pd.DataFrame([{"Ticker": i['ticker'], "Wynik 12m": f"{i['return']:+.2f}%"} for i in perf])
    st.table(df_rank)

    # 3. MOMENTUM MIESIĘCZNE
    st.markdown("---")
    st.markdown("#### 📊 Miesięczna zmienność")
    monthly_rets = window.resample('ME').last().pct_change().dropna() * 100
    fig_bar = go.Figure()
    for item in perf:
        t = item['ticker']
        fig_bar.add_trace(go.Bar(
            x=monthly_rets.index.strftime('%m.%Y'),
            y=monthly_rets[t],
            name=t,
            marker_color=color_map.get(t)
        ))
    fig_bar.update_layout(template="plotly_dark", height=350, barmode='group')
    st.plotly_chart(fig_bar, use_container_width=True)

else:
    st.info("Zaznacz instrumenty w menu bocznym.")
