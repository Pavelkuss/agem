import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd

st.set_page_config(page_title="Monitor Trendu ETF (EUR)", layout="wide")
st.title("📈 Analiza Trendu (Okno 12m) - Baza: EUR")

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
def get_data_debug(tickers, start):
    combined = pd.DataFrame()
    failed = []
    for t in tickers:
        try:
            # Pobieramy dane bez Adj Close, samo Close jest stabilniejsze
            df = yf.download(t, start=start, progress=False, multi_level_index=False)
            if not df.empty and 'Close' in df.columns:
                combined[t] = df['Close']
            else:
                failed.append(t)
        except:
            failed.append(t)
    return combined, failed

# LISTA: Zamieniłem IBGL.DE na EUNH.DE (to ten sam ETF na Xetra)
tickers = ["IWDA.AS", "IS3N.DE", "SXRV.DE", "SXRT.DE", "CBU0.DE", "EUNH.DE", "IB01.DE"]
start_download = datetime.now() - timedelta(days=5*365)

with st.spinner('Pobieranie danych rynkowych...'):
    all_data, failed_tickers = get_data_debug(tickers, start_download)
    asset_names = get_ticker_names(tickers)

# Diagnostyka dla Ciebie
if failed_tickers:
    st.warning(f"⚠️ Nie udało się pobrać danych dla: {', '.join(failed_tickers)}. Sprawdź połączenie lub tickery.")

if not all_data.empty:
    month_ends = pd.date_range(start=all_data.index.min(), end=all_data.index.max(), freq='ME')[::-1]
    
    polish_months = {1:"Styczeń", 2:"Luty", 3:"Marzec", 4:"Kwiecień", 5:"Maj", 6:"Czerwiec", 
                     7:"Lipiec", 8:"Sierpień", 9:"Wrzesień", 10:"Październik", 11:"Listopad", 12:"Grudzień"}
    
    date_options = {d: f"{polish_months[d.month]} {d.year}" for d in month_ends}
    selected_end = st.selectbox("Miesiąc końcowy:", options=list(date_options.keys()), format_func=lambda x: date_options[x])

    start_view = selected_end - timedelta(days=365)
    fig = go.Figure()
    performance_results = []

    for ticker in all_data.columns:
        series = all_data[ticker].dropna()
        mask = (series.index >= pd.Timestamp(start_view)) & (series.index <= pd.Timestamp(selected_end))
        window_data = series.loc[mask]
        
        if not window_data.empty:
            base_price = float(window_data.iloc[0])
            current_return = ((window_data.iloc[-1] / base_price) - 1) * 100
            returns_series = ((window_data / base_price) - 1) * 100
            
            fig.add_trace(go.Scatter(x=window_data.index, y=returns_series, mode='lines', name=ticker, line=dict(width=3)))
            performance_results.append({
                "Ticker": ticker, 
                "Nazwa": asset_names.get(ticker, ticker), 
                "Wynik %": round(current_return, 2)
            })

    fig.update_layout(
        template="plotly_dark", height=500,
        xaxis=dict(gridcolor='rgba(255,255,255,0.1)', range=[start_view, selected_end]),
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
            st.markdown(f"<h4 style='text-align: center;'>🏆 Ranking w EUR: {selected_end.strftime('%m/%Y')} (12m)</h4>", unsafe_allow_html=True)
            st.table(df_perf)
else:
    st.error("Błąd: Żaden z tickerów nie zwrócił danych. Spróbuj zmienić zakres dat.")
