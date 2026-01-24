import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd

st.set_page_config(page_title="Analiza Trendu 12m", layout="wide")
st.title("📈 Przesuwne okno 12-miesięczne")

# Funkcja pobierająca dane z pamięcią podręczną (cache)
@st.cache_data(ttl=3600)  # Dane będą pamiętane przez godzinę
def get_data(tickers, start):
    data = yf.download(tickers, start=start, multi_level_index=False)
    return data

# Sidebar
st.sidebar.header("Ustawienia")
default_tickers = "EIMI.L, SWDA.L, CBU0.L, IB01.L, CNDX.L"
tickers_input = st.sidebar.text_input("Wpisz tickery:", default_tickers)
ticker_list = [t.strip().upper() for t in tickers_input.split(",")]

# Pobieramy dane raz (5 lat wstecz)
start_download = datetime.now() - timedelta(days=5*365)

# Załadowanie danych do cache
with st.spinner('Pobieranie danych z Yahoo Finance...'):
    all_data = get_data(ticker_list, start_download)

if not all_data.empty:
    # Suwak daty
    st.write("### Przesuń suwak, aby zmienić okres (okno zawsze 12 msc)")
    selected_end_date = st.slider(
        "Data końcowa wykresu:",
        min_value=all_data.index.min().to_pydatetime(),
        max_value=all_data.index.max().to_pydatetime(),
        value=all_data.index.max().to_pydatetime(),
        format="DD/MM/YYYY"
    )

    selected_start_date = selected_end_date - timedelta(days=365)
    fig = go.Figure()

    for ticker in ticker_list:
        try:
            # Pobieramy dane dla konkretnego tickera z już załadowanej tabeli
            if len(ticker_list) > 1:
                ticker_data = all_data['Close'][ticker].dropna()
            else:
                ticker_data = all_data['Close'].dropna()
            
            # Wycinamy okno 12m
            mask = (ticker_data.index >= pd.Timestamp(selected_start_date)) & \
                   (ticker_data.index <= pd.Timestamp(selected_end_date))
            window_data = ticker_data.loc[mask]
            
            if not window_data.empty:
                # Filtr błędnych danych (pików)
                diff = window_data.pct_change().abs()
                window_data = window_data[diff < 0.3]
                
                initial_price = float(window_data.iloc[0])
                returns = ((window_data / initial_price) - 1) * 100
                
                fig.add_trace(go.Scatter(
                    x=window_data.index, 
                    y=returns, 
                    mode='lines', 
                    name=ticker,
                    fill='none'
                ))
        except Exception as e:
            st.error(f"Błąd przy {ticker}: {e}")

    fig.update_layout(
        title=f"Wynik w oknie: {selected_start_date.strftime('%d/%m/%Y')} - {selected_end_date.strftime('%d/%m/%Y')}",
        template="plotly_dark",
        hovermode="x unified",
        yaxis=dict(ticksuffix="%"),
        xaxis=dict(range=[selected_start_date, selected_end_date])
    )

    st.plotly_chart(fig, use_container_width=True)
else:
    st.error("Nie udało się pobrać żadnych danych. Sprawdź tickery.")

