import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd

st.set_page_config(page_title="GEM Monitor (EUR)", layout="wide")
st.title("🛡️ Advanced GEM Momentum")

# --- ZAKTUALIZOWANA BIBLIOTEKA (Dodano XRS2) ---
etf_library = {
    "USA": {
        "SXR8.DE": "iShares Core S&P 500 Acc",
        "SXRV.DE": "iShares Nasdaq 100 Acc",
        "XRS2.DE": "Xtrackers Russell 2000 Acc (Small Cap)"
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

# Mapowanie kolorów
color_map = {
    "SXR8.DE": "#377EB8", "SXRV.DE": "#4DAF4A", "XRS2.DE": "#FFFF33", # Żółty dla Russell 2000
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
st.sidebar.header("🔍 Wybór ETF")
selected_tickers = []
for cat, items in etf_library.items():
    st.sidebar.subheader(cat)
    for ticker, name in items.items():
        # Domyślnie zaznaczamy m.in. nowy Russell 2000
        default = ticker in ["SXR8.DE", "XRS2.DE", "EXSA.DE", "XEON.DE"]
        if st.sidebar.checkbox(f"{ticker} ({name})", value=default):
            selected_tickers.append(ticker)

# --- ANALIZA ---
start_date = datetime.now() - timedelta(days=5*365)
all_data = get_data(selected_tickers, start_date)

if not all_data.empty:
    month_ends = pd.date_range(start=all_data.index.min(), end=all_data.index.max(), freq='ME')[::-1]
    selected_month = st.selectbox("Wybierz miesiąc końcowy okna 12m:", options=list(month_ends), format_func=lambda x: x.strftime('%m.%Y'))
    
    actual_end = all_data.index[all_data.index <= pd.Timestamp(selected_month)][-1]
    start_view = actual_end - timedelta(days=365)
    window = all_data.loc[start_view:actual_end]
    
    perf = []
    for t in selected_tickers:
        if t in window.columns:
            ret = ((window[t].iloc[-1] / window[t].iloc[0]) - 1) * 100
            perf.append({'ticker': t, 'return': ret, 'series': window[t]})
    
    perf = sorted(perf, key=lambda x: x['return'], reverse=True)

    # SYGNAŁ GEM
    best_asset = perf[0]
    xeon_return = next((x['return'] for x in perf if x['ticker'] == "XEON.DE"), -999)
    
    st.subheader("📢 Sygnał Systemowy")
    if best_asset['ticker'] == "XEON.DE" or best_asset['return'] < xeon_return:
        st.error(f"SYGNAŁ: GOTÓWKA (XEON). Momentum akcji jest ujemne względem bazy.")
    else:
        st.success(f"SYGNAŁ: INVEST ({best_asset['ticker']}).")

    # WYKRES
    fig = go.Figure()
    for item in perf:
        t = item['ticker']
        fig.add_trace(go.Scatter(x=item['series'].index, y=((item['series']/item['series'].iloc[0])-1)*100, 
                                 name=t, line=dict(width=3, color=color_map.get(t))))
    fig.update_layout(template="plotly_dark", height=450, hovermode="x unified", legend=dict(orientation="h", y=1.1))
    st.plotly_chart(fig, use_container_width=True)

    # TABELA
    st.markdown(f"### 🏆 Ranking 12m ({actual_end.strftime('%d.%m.%Y')})")
    st.table(pd.DataFrame([{"Ticker": i['ticker'], "Wynik 12m": f"{i['return']:+.2f}%"} for i in perf]))

else:
    st.info("Zaznacz instrumenty w menu bocznym.")

