import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd

# Konfiguracja strony
st.set_page_config(page_title="Monitor Trendu ETF", layout="wide")
st.title("📈 Analiza Trendu (Okno 12m)")

# 1. Pobieranie czytelnych nazw aktywów
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

# 2. Pobieranie danych giełdowych
@st.cache_data(ttl=3600)
def get_data(tickers, start):
    data = yf.download(tickers, start=start, multi_level_index=False)
    return data

# Lista tickerów
tickers = ["EIMI.L", "SWDA.L", "CBU0.L", "IB01.L", "CNDX.L"]
start_download = datetime.now() - timedelta(days=5*365) # 5 lat wstecz

with st.spinner('Ładowanie danych...'):
    all_data = get_data(tickers, start_download)
    asset_names = get_ticker_names(tickers)

if not all_data.empty:
    # Przygotowanie osi czasu dla suwaka (końce miesięcy)
    month_ends = pd.date_range(start=all_data.index.min(), end=all_data.index.max(), freq='ME')

    st.write("### Przesuń suwak (okno 12m)")

    # 3. Definicja smart_label PRZED użyciem w suwaku
    def smart_label(date):
        # Wyświetlamy napis tylko dla stycznia i lipca, by wymusić pionowe kreski (ticks)
        if date.month == 1:
            return date.strftime('%Y')
        elif date.month == 7:
            return date.strftime('%m/%y')
        return "" 

    selected_end = st.select_slider(
        "Wybierz datę końcową widoku:",
        options=month_ends,
        value=month_ends[-1],
        format_func=smart_label
    )

    # Obliczanie okna 12m
    start_view = selected_end - timedelta(days=365)
    
    fig = go.Figure()

    for ticker in tickers:
        try:
            # Pobranie serii dla konkretnego tickera
            if len(tickers) > 1:
                series = all_data['Close'][ticker].dropna()
            else:
                series = all_data['Close'].dropna()
            
            # Filtrowanie danych do wybranego okna
            mask = (series.index >= pd.Timestamp(start_view)) & (series.index <= pd.Timestamp(selected_end))
            window_data = series.loc[mask]
            
            if not window_data.empty:
                # Filtr pików (błędnych danych)
                diff = window_data.pct_change().abs()
                window_data = window_data[diff < 0.3]
                
                # Przeliczenie na zwrot % od zera na początku okna
                base_price = float(window_data.iloc[0])
                returns = ((window_data / base_price) - 1) * 100
                
                # Dodanie czystej, pogrubionej linii
                fig.add_trace(go.Scatter(
                    x=window_data.index, 
                    y=returns, 
                    mode='lines', 
                    name=f"{ticker} - {asset_names.get(ticker, '')}",
                    line=dict(width=3),
                    hovertemplate='%{y:.2f}%'
                ))
        except:
            continue

    # Ustawienia wykresu
    fig.update_layout(
        template="plotly_dark",
        height=600,
        xaxis=dict(gridcolor='rgba(255,255,255,0.1)'),
        yaxis=dict(ticksuffix="%", gridcolor='rgba(255,255,255,0.1)'),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5)
    )
    
    # Dodanie linii bazowej 0%
    fig.add_hline(y=0, line_dash="dash", line_color="gray")

    st.plotly_chart(fig, use_container_width=True)
    st.info(f"Aktualny zakres: {start_view.strftime('%d.%m.%Y')} — {selected_end.strftime('%d.%m.%Y')}")

else:
    st.error("Nie udało się pobrać danych.")
