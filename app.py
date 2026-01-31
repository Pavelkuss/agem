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
        "SXR8.DE": "iShares Core S&P 500 Acc",
        "SXRV.DE": "iShares Nasdaq 100 Acc",
        "XRS2.DE": "Xtrackers Russell 2000 Acc"
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
st.sidebar.header("🔍 Wybór ETF")
selected_tickers = []
for cat, items in etf_library.items():
    st.sidebar.subheader(cat)
    for ticker, name in items.items():
        default = ticker in ["SXR8.DE", "XRS2.DE", "EXSA.DE", "XEON.DE"]
        if st.sidebar.checkbox(f"{ticker} ({name})", value=default):
            selected_tickers.append(ticker)

# --- ANALIZA ---
start_date = datetime.now() - timedelta(days=5*365)
all_data = get_data(selected_tickers, start_date)

if not all_data.empty:
    month_ends = pd.date_range(start=all_data.index.min(), end=all_data.index.max(), freq='ME')[::-1]
    selected_month = st.selectbox("Miesiąc końcowy okna 12m:", options=list(month_ends), format_func=lambda x: x.strftime('%m.%Y'))
    
    actual_end = all_data.index[all_data.index <= pd.Timestamp(selected_month)][-1]
    start_view = actual_end - timedelta(days=365)
    window = all_data.loc[start_view:actual_end]
    
    perf = []
    for t in selected_tickers:
        if t in window.columns:
            ret = ((window[t].iloc[-1] / window[t].iloc[0]) - 1) * 100
            perf.append({'ticker': t, 'return': ret, 'series': window[t]})
    
    perf = sorted(perf, key=lambda x: x['return'], reverse=True)

    # SYGNAŁ
    best_asset = perf[0]
    xeon_return = next((x['return'] for x in perf if x['ticker'] == "XEON.DE"), -999)
    
    st.subheader(f"📢 Sygnał na dzień {actual_end.strftime('%d.%m.%Y')}")
    if best_asset['ticker'] == "XEON.DE" or best_asset['return'] < xeon_return:
        st.error(f"SYGNAŁ: GOTÓWKA (XEON). Żaden indeks nie pokonuje bazy EUR.")
    else:
        st.success(f"SYGNAŁ: INVEST ({best_asset['ticker']}) z wynikiem {best_asset['return']:+.2f}%.")

    # --- WYKRES ---
    fig = go.Figure()
    for item in perf:
        t = item['ticker']
        r = item['return']
        fig.add_trace(go.Scatter(x=item['series'].index, y=((item['series']/item['series'].iloc[0])-1)*100, 
                                 name=f"{t} ({r:+.2f}%)", line=dict(width=3, color=color_map.get(t))))
    
    fig.update_layout(template="plotly_dark", height=500, xaxis=dict(tickformat="%m.%Y", fixedrange=True),
                      yaxis=dict(ticksuffix="%", fixedrange=True), hovermode="x unified",
                      legend=dict(orientation="h", y=1.08, xanchor="center", x=0.5))
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    # --- NOWA TABELA HISTORYCZNA (Wzór z obrazka) ---
    st.markdown("---")
    st.subheader("🗓️ Historia Rankingu Momentum")
    
    history_data = []
    # Generujemy ranking dla ostatnich 6 miesięcy widocznych na wykresie
    past_months = month_ends[month_ends <= pd.Timestamp(selected_month)][:6]
    
    for m in past_months:
        m_end = all_data.index[all_data.index <= m][-1]
        m_start = m_end - timedelta(days=365)
        m_window = all_data.loc[m_start:m_end]
        
        m_perf = []
        for t in selected_tickers:
            if t in m_window.columns:
                r = ((m_window[t].iloc[-1] / m_window[t].iloc[0]) - 1) * 100
                m_perf.append((t, r))
        
        m_perf = sorted(m_perf, key=lambda x: x[1], reverse=True)
        history_data.append({
            "Miesiąc": m.strftime('%m/%Y'),
            "#1": f"{m_perf[0][0]} ({m_perf[0][1]:+.2f}%)",
            "#2": f"{m_perf[1][0]} ({m_perf[1][1]:+.2f}%)",
            "#3": f"{m_perf[2][0]} ({m_perf[2][1]:+.2f}%)",
            "#4": f"{m_perf[3][0]} ({m_perf[3][1]:+.2f}%)" if len(m_perf) > 3 else "-"
        })

    hist_df = pd.DataFrame(history_data).set_index("Miesiąc").T
    st.dataframe(hist_df, use_container_width=True)

else:
    st.info("Zaznacz instrumenty w menu bocznym.")
