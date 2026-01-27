import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd

st.set_page_config(page_title="Monitor ETF (EUR)", layout="wide")
st.title("📈 Analiza Trendu (Okno 12m) - Waluta: EUR")

# 1. Definicja etykiet suwaka na samym początku
def smart_label(date):
    if date.month == 1:
        return date.strftime('%Y')
    elif date.month == 7:
        return date.strftime('%m/%y')
    return ""

@st.cache_data(ttl=3600)
def get_data_individually(ticker_list, start):
    """Pobiera dane dla każdego tickera osobno, aby uniknąć błędów struktury DataFrame"""
    combined_data = pd.DataFrame()
    for t in ticker_list:
        try:
            # Pobieramy Adj Close (uwzględnia dywidendy, jak na JustETF)
            df = yf.download(t, start=start, progress=False)['Adj Close']
            if not df.empty:
                combined_data[t] = df
        except Exception as e:
            st.warning(f"Nie udało się pobrać danych dla {t}: {e}")
    return combined_data

@st.cache_data(ttl=86400)
def get_ticker_names(ticker_list):
    names = {}
    for t in ticker_list:
        try:
            ticker_obj = yf.Ticker(t)
            # Próba pobrania długiej nazwy
            full_name = ticker_obj.info.get('longName') or ticker_obj.info.get('shortName') or t
            names[t] = full_name
        except:
            names[t] = t
    return names

# LISTA TICKERÓW (Giełdy: Euronext Amsterdam .AS, Xetra .DE - wszystko w EUR)
tickers = ["IWDA.AS", "IS3N.DE", "SXRT.DE", "SXRV.DE", "CBU0.DE", "IB01.DE"]
start_download = datetime.now() - timedelta(days=5*365)

with st.spinner('Pobieranie danych z rynków europejskich...'):
    all_data = get_data_individually(tickers, start_download)
    asset_names = get_ticker_names(tickers)

if not all_data.empty:
    # Przygotowanie osi czasu
    month_ends = pd.date_range(start=all_data.index.min(), end=all_data.index.max(), freq='ME')

    st.write("### Przesuń suwak (okno 12m)")
    selected_end = st.select_slider(
        "Wybierz koniec okresu:",
        options=month_ends,
        value=month_ends[-1],
        format_func=smart_label
    )

    start_view = selected_end - timedelta(days=365)
    fig = go.Figure()
    performance_results = []

    for ticker in all_data.columns:
        try:
            series = all_data[ticker].dropna()
            # Wycinamy okno 12m
            mask = (series.index >= pd.Timestamp(start_view)) & (series.index <= pd.Timestamp(selected_end))
            window_data = series.loc[mask]
            
            if not window_data.empty:
                # Obliczamy zwrot względem pierwszego dnia w oknie (0%)
                base_price = float(window_data.iloc[0])
                current_return = ((window_data.iloc[-1] / base_price) - 1) * 100
                returns_series = ((window_data / base_price) - 1) * 100
                
                performance_results.append({
                    "Ticker": ticker,
                    "Nazwa": asset_names.get(ticker, ticker),
                    "Wynik %": round(current_return, 2)
                })
                
                fig.add_trace(go.Scatter(
                    x=window_data.index, 
                    y=returns_series, 
                    mode='lines', 
                    name=ticker,
                    line=dict(width=3),
                    hovertemplate='<b>' + ticker + '</b><br>Wynik: %{y:.2f}%'
                ))
        except:
            continue

    # Estetyka wykresu
    fig.update_layout(
        template="plotly_dark",
        height=600,
        xaxis=dict(gridcolor='rgba(255,255,255,0.1)', range=[start_view, selected_end]),
        yaxis=dict(ticksuffix="%", gridcolor='rgba(255,255,255,0.1)'),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5)
    )
    
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    st.plotly_chart(fig, use_container_width=True)

    # Ranking
    st.write("### 🏆 Ranking wyników w oknie 12m (EUR)")
    if performance_results:
        df_perf = pd.DataFrame(performance_results).sort_values(by="Wynik %", ascending=False)
        st.table(df_perf)

    st.info(f"Analizowany okres: {start_view.strftime('%d.%m.%Y')} — {selected_end.strftime('%d.%m.%Y')}")

else:
    st.error("Błąd: Nie udało się pobrać żadnych danych. Sprawdź połączenie lub spróbuj odświeżyć stronę.")
