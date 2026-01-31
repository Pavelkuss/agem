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
    month_ends = pd.date_range(start=all_data.index.min(), end=all_data.index.max(), freq='ME')
    selected_month = st.selectbox("Miesiąc końcowy okna 12m:", options=list(month_ends[::-1]), format_func=lambda x: x.strftime('%m.%Y'))
    
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

    # --- TABELA HISTORYCZNA (Same strzałki) ---
    st.markdown("---")
    st.subheader("🗓️ Historia Rankingu Momentum")
    
    current_idx = list(month_ends).index(pd.Timestamp(selected_month))
    past_months = month_ends[max(0, current_idx-6):current_idx+1]
    
    monthly_rankings = []
    for m in past_months:
        m_end = all_data.index[all_data.index <= m][-1]
        m_start = m_end - timedelta(days=365)
        m_window = all_data.loc[m_start:m_end]
        m_perf = sorted([(t, ((m_window[t].iloc[-1]/m_window[t].iloc[0])-1)*100) for t in selected_tickers if t in m_window.columns], key=lambda x: x[1], reverse=True)
        monthly_rankings.append({t[0]: i+1 for i, t in enumerate(m_perf)})
        monthly_rankings[-1]['_data'] = m_perf
        monthly_rankings[-1]['_date'] = m.strftime('%m/%Y')

    history_rows = []
    for i in range(1, len(monthly_rankings)):
        curr = monthly_rankings[i]
        prev = monthly_rankings[i-1]
        row = {"Miesiąc": curr['_date']}
        for rank_idx in range(min(4, len(curr['_data']))):
            ticker, val = curr['_data'][rank_idx]
            old_rank = prev.get(ticker, 99)
            new_rank = rank_idx + 1
            
            indicator = ""
            if new_rank < old_rank: indicator = " ↑"
            elif new_rank > old_rank: indicator = " ↓"
            
            row[f"#{new_rank}"] = f"{ticker} ({val:+.2f}%){indicator}"
        history_rows.append(row)

    hist_df = pd.DataFrame(history_rows).set_index("Miesiąc").T
    st.table(hist_df)

    # --- STOPKA ---
    st.markdown("---")
    c1, c2 = st.columns([1, 4])
    c1.image("https://s.yimg.com/rz/p/yahoo_finance_en-US_h_p_finance_2.png", width=150)
    c2.markdown("Aplikacja korzysta z darmowych danych dostarczanych przez **[Yahoo Finance](https://finance.yahoo.com)**.")

else:
    st.info("Zaznacz instrumenty w menu bocznym.")
