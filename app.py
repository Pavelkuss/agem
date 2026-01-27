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

# KONFIGURACJA
tickers = ["IS3N.DE", "SXRV.DE", "SXRT.DE", "2B7S.DE", "DBXP.DE"]
color_map = {
    "IS3N.DE": "#E41A1C", "SXRV.DE": "#4DAF4A", 
    "SXRT.DE": "#984EA3", "2B7S.DE": "#FF7F00", "DBXP.DE": "#377EB8"
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

    # Przygotowanie danych do głównego wykresu i rankingu
    performance_list = []
    for ticker in tickers:
        if ticker in window_data.columns:
            series = window_data[ticker]
            ret = ((series.iloc[-1] / series.iloc[0]) - 1) * 100
            performance_list.append({'ticker': ticker, 'return': ret, 'series': series})

    # Sortowanie legendy od najlepszego
    performance_list = sorted(performance_list, key=lambda x: x['return'], reverse=True)

    # 1. WYKRES LINIOWY (Trend skumulowany)
    fig_line = go.Figure()
    for item in performance_list:
        t, s, color = item['ticker'], item['series'], color_map.get(item['ticker'])
        fig_line.add_trace(go.Scatter(x=s.index, y=((s/s.iloc[0])-1)*100, mode='lines', name=t, line=dict(width=3, color=color)))

    fig_line.update_layout(template="plotly_dark", height=450, xaxis=dict(tickformat="%m.%Y", dtick="M1"),
                           yaxis=dict(ticksuffix="%"), hovermode="x unified",
                           legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5))
    st.plotly_chart(fig_line, use_container_width=True)

    # 2. TABELA RANKINGOWA
    df_perf = pd.DataFrame([{"Ticker": i['ticker'], "Nazwa": asset_names.get(i['ticker']), "Wynik %": f"{i['return']:+.2f}%"} for i in performance_list])
    col1, col2, col3 = st.columns([0.1, 4, 0.1])
    with col2:
        st.markdown(f"<h4 style='text-align: center;'>🏆 Ranking końcowy: {actual_end_date.strftime('%d.%m.%Y')}</h4>", unsafe_allow_html=True)
        st.table(df_perf)

    # 3. WYKRES MIESIĘCZNY (Momentum)
    st.markdown("---")
    st.markdown("<h4 style='text-align: center;'>📊 Miesięczne stopy zwrotu w analizowanym okresie</h4>", unsafe_allow_html=True)
    
    # Obliczanie stóp miesięcznych
    monthly_data = window_data.resample('ME').last()
    monthly_returns = monthly_data.pct_change().dropna() * 100

    fig_bar = go.Figure()
    for ticker in [i['ticker'] for i in performance_list]: # Kolejność zgodna z rankingiem
        if ticker in monthly_returns.columns:
            fig_bar.add_trace(go.Bar(
                x=monthly_returns.index.strftime('%m.%Y'),
                y=monthly_returns[ticker],
                name=ticker,
                marker_color=color_map.get(ticker)
            ))

    fig_bar.update_layout(
        template="plotly_dark", height=400, barmode='group',
        xaxis=dict(title="Miesiąc"), yaxis=dict(title="Zwrot %", ticksuffix="%"),
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5),
        hovermode="x unified"
    )
    st.plotly_chart(fig_bar, use_container_width=True)

else:
    st.error("Błąd pobierania danych. Wyczyść cache.")
