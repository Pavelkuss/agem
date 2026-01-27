import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd

# Konfiguracja strony
st.set_page_config(page_title="Monitor ETF (EUR)", layout="wide")
st.title("📈 Analiza Trendu (Okno 12m) - Waluta: EUR")

# 1. Funkcja etykiet (musi być na górze)
def smart_label(date):
    if date.month == 1:
        return date.strftime('%Y')
    elif date.month == 7:
        return date.strftime('%m/%y')
    return ""

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
def get_data_stable(ticker_list, start):
    """Pobiera dane w sposób odporny na zmiany w strukturze yfinance"""
    data = yf.download(ticker_list, start=start, progress=False)
    # Wybieramy 'Adj Close' jeśli istnieje, w przeciwnym razie 'Close'
    if 'Adj Close' in data.columns:
        return data['Adj Close']
    return data['Close']

# LISTA TICKERÓW (Xetra/Euronext - EUR)
tickers = ["IWDA.AS", "IS3N.DE", "SXRT.DE", "SXRV.DE", "CBU0.DE", "IB01.DE"]
start_download = datetime.now() - timedelta(days=5*365)

with st.spinner('Pobieranie danych z Yahoo Finance...'):
    all_data = get_data_stable(tickers, start_download)
    asset_names = get_ticker_names(tickers)

if not all_data.empty:
    # Czyszczenie danych (usuniecie ewentualnych MultiIndex)
    if isinstance(all_data.columns, pd.MultiIndex):
        all_data.columns = all_data.columns.get_level_values(-1)

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

    for ticker in tickers:
        if ticker in all_data.columns:
            series = all_data[ticker].dropna()
            mask = (series.index >= pd.Timestamp(start_view)) & (series.index <= pd.Timestamp(selected_end))
            window_data = series.loc[mask]
            
            if not window_data.empty:
                # Obliczamy zwrot (pierwszy dzień w oknie = 0%)
                base_price = float(window_data.iloc[0])
                current_return = ((window_data.iloc[-1] / base_price) - 1) * 100
                returns_series = ((window_data / base_price) - 1) * 100
                
                name_in_legend = asset_names.get(ticker, ticker)
                
                fig.add_trace(go.Scatter(
                    x=window_data.index, 
                    y=returns_series, 
                    mode='lines', 
                    name=f"{ticker} ({name_in_legend[:30]}...)",
                    line=dict(width=3),
                    hovertemplate='<b>' + ticker + '</b><br>Wynik: %{y:.2f}%'
                ))
                
                performance_results.append({
                    "Ticker": ticker,
                    "Pełna Nazwa": name_in_legend,
                    "Wynik % (12m)": round(current_return, 2)
                })

    fig.update_layout(
        template="plotly_dark",
        height=600,
        xaxis=dict(gridcolor='rgba(255,255,255,0.1)', range=[start_view, selected_end]),
        yaxis=dict(ticksuffix="%", gridcolor='rgba(255,255,255,0.1)'),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
    )
    
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    st.plotly_chart(fig, use_container_width=True)

    # Ranking
    if performance_results:
        st.write("### 🏆 Ranking wyników w wybranym oknie")
        df_perf = pd.DataFrame(performance_results).sort_values(by="Wynik % (12m)", ascending=False)
        st.table(df_perf)

    st.info(f"Zakres: {start_view.strftime('%d.%m.%Y')} — {selected_end.strftime('%d.%m.%Y')}")
else:
    st.error("Błąd pobierania danych. Spróbuj odświeżyć stronę (R).")
