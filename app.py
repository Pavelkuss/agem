import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd

st.set_page_config(page_title="Monitor Trendu ETF (EUR)", layout="wide")
st.title("📈 Analiza Trendu (Okno 12m) - Waluta: EUR")

@st.cache_data(ttl=86400)
def get_ticker_names(ticker_list):
    names = {}
    for t in ticker_list:
        try:
            ticker_obj = yf.Ticker(t)
            full_name = ticker_obj.info.get('longName') or ticker_obj.info.get('shortName') or t
            names[t] = full_name
        except:
            names[t] = t
    return names

@st.cache_data(ttl=3600)
def get_data_safe(tickers, start):
    combined = pd.DataFrame()
    for t in tickers:
        try:
            df = yf.download(t, start=start, progress=False, multi_level_index=False)
            if not df.empty and 'Close' in df.columns:
                combined[t] = df['Close']
        except:
            continue
    return combined.dropna()

# TWOJE AKTUALNE TICKERY
tickers = ["IS3N.DE", "SXRV.DE", "SXRT.DE", "2B7S.DE", "DBXP.DE"]

# 1. TRWAŁE PRZYPISANIE KOLORÓW
color_map = {
    "IS3N.DE": "#E41A1C", # Czerwony
    "SXRV.DE": "#4DAF4A", # Zielony
    "SXRT.DE": "#984EA3", # Fioletowy
    "2B7S.DE": "#FF7F00", # Pomarańczowy
    "DBXP.DE": "#377EB8"  # Niebieski
}

start_download = datetime.now() - timedelta(days=5*365)

with st.spinner('Synchronizacja danych...'):
    all_data = get_data_safe(tickers, start_download)
    asset_names = get_ticker_names(tickers)

if not all_data.empty:
    month_ends = pd.date_range(start=all_data.index.min(), end=all_data.index.max(), freq='ME')[::-1]
    date_options = {d: f"{d.strftime('%m.%Y')}" for d in month_ends}
    
    selected_end = st.selectbox("Miesiąc końcowy:", options=list(date_options.keys()), format_func=lambda x: date_options[x])

    mask_month = (all_data.index <= pd.Timestamp(selected_end))
    actual_end_date = all_data.index[mask_month][-1]
    start_view = actual_end_date - timedelta(days=365)
    
    window_data = all_data.loc[(all_data.index >= pd.Timestamp(start_view)) & (all_data.index <= actual_end_date)]

    # Przygotowanie wyników do sortowania legendy
    performance_list = []
    for ticker in tickers:
        if ticker in window_data.columns:
            series = window_data[ticker]
            base_price = float(series.iloc[0])
            current_return = ((series.iloc[-1] / base_price) - 1) * 100
            performance_list.append({
                "ticker": ticker,
                "return": current_return,
                "series": series
            })

    # 2. SORTOWANIE LISTY WEDŁUG ZWROTU (DLA LEGENDY)
    performance_list = sorted(performance_list, key=lambda x: x['return'], reverse=True)

    fig = go.Figure()
    performance_results = []

    for item in performance_list:
        t = item['ticker']
        s = item['series']
        ret = item['return']
        base_p = float(s.iloc[0])
        returns_series = ((s / base_p) - 1) * 100
        
        fig.add_trace(go.Scatter(
            x=s.index, 
            y=returns_series, 
            mode='lines', 
            name=t, 
            line=dict(width=3, color=color_map.get(t, "white"))
        ))
        
        performance_results.append({
            "Ticker": t, 
            "Nazwa": asset_names.get(t, t), 
            "Wynik %": round(ret, 2)
        })

    fig.update_layout(
        template="plotly_dark", height=500,
        xaxis=dict(gridcolor='rgba(255,255,255,0.1)', tickformat="%m.%Y", dtick="M1"),
        yaxis=dict(ticksuffix="%", gridcolor='rgba(255,255,255,0.1)'),
        hovermode="x unified",
        legend=dict(
            orientation="h", 
            yanchor="bottom", y=1.05, 
            xanchor="center", x=0.5,
            traceorder="normal" # Legenda podąża za kolejnością dodawania trace'ów
        )
    )
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    st.plotly_chart(fig, use_container_width=True)

    if performance_results:
        st.markdown("<style>table {width: 100%;} td {white-space: normal !important; word-wrap: break-word !important;}</style>", unsafe_allow_html=True)
        # Tabela zawsze posortowana od najlepszego (już jest dzięki kolejności dodawania)
        df_perf = pd.DataFrame(performance_results)
        df_perf["Wynik %"] = df_perf["Wynik %"].apply(lambda x: f"{x:+.2f}%")
        
        col1, col2, col3 = st.columns([0.1, 4, 0.1])
        with col2:
            st.markdown(f"<h4 style='text-align: center;'>🏆 Ranking (stan na {actual_end_date.strftime('%d.%m.%Y')}):</h4>", unsafe_allow_html=True)
            st.table(df_perf)
