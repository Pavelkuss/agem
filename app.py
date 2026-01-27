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
    # SYNCHRONIZACJA: Usuwamy dni, w których brakuje choćby jednej ceny (rozwiązuje problem z obrazka)
    return combined.dropna()

tickers = ["IS3N.DE", "SXRV.DE", "SXRT.DE", "SXRL.DE", "SXRQ.DE"]
start_download = datetime.now() - timedelta(days=5*365)

with st.spinner('Synchronizacja danych...'):
    all_data = get_data_safe(tickers, start_download)
    asset_names = get_ticker_names(tickers)

if not all_data.empty:
    month_ends = pd.date_range(start=all_data.index.min(), end=all_data.index.max(), freq='ME')[::-1]
    date_options = {d: f"{d.strftime('%m.%Y')}" for d in month_ends}
    
    selected_end = st.selectbox("Wybierz miesiąc końcowy:", options=list(date_options.keys()), format_func=lambda x: date_options[x])

    # Wyznaczenie faktycznej daty końcowej dla wszystkich
    mask_month = (all_data.index <= pd.Timestamp(selected_end))
    actual_end_date = all_data.index[mask_month][-1]
    start_view = actual_end_date - timedelta(days=365)
    
    fig = go.Figure()
    performance_results = []
    window_data = all_data.loc[(all_data.index >= pd.Timestamp(start_view)) & (all_data.index <= actual_end_date)]

    for ticker in tickers:
        if ticker in window_data.columns:
            series = window_data[ticker]
            base_price = float(series.iloc[0])
            current_return = ((series.iloc[-1] / base_price) - 1) * 100
            returns_series = ((series / base_price) - 1) * 100
            
            fig.add_trace(go.Scatter(x=series.index, y=returns_series, mode='lines', name=ticker, line=dict(width=3)))
            performance_results.append({"Ticker": ticker, "Nazwa": asset_names.get(ticker, ticker), "Wynik %": round(current_return, 2)})

    # FORMATOWANIE OSI: Daty liczbowe (DD.MM.YYYY)
    fig.update_layout(
        template="plotly_dark", height=500,
        xaxis=dict(
            gridcolor='rgba(255,255,255,0.1)',
            tickformat="%m.%Y",  # Format liczbowy na osi
            dtick="M1"           # Pokazuj co miesiąc
        ),
        yaxis=dict(ticksuffix="%", gridcolor='rgba(255,255,255,0.1)'),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5)
    )
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    st.plotly_chart(fig, use_container_width=True)

    if performance_results:
        st.markdown("<style>table {width: 100%;} td {white-space: normal !important; word-wrap: break-word !important;}</style>", unsafe_allow_html=True)
        df_perf = pd.DataFrame(performance_results).sort_values(by="Wynik %", ascending=False)
        df_perf["Wynik %"] = df_perf["Wynik %"].apply(lambda x: f"{x:+.2f}%")
        
        col1, col2, col3 = st.columns([0.1, 4, 0.1])
        with col2:
            st.markdown(f"<h4 style='text-align: center;'>🏆 Ranking (stan na {actual_end_date.strftime('%d.%m.%Y')}):</h4>", unsafe_allow_html=True)
            st.table(df_perf)

