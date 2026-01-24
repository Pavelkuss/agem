import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Konfiguracja strony
st.set_page_config(page_title="Monitor Aktywów", layout="wide")
st.title("📈 Mój Dashboard Giełdowy")

# Panel boczny - sterowanie
st.sidebar.header("Ustawienia")
tickers_input = st.sidebar.text_input("Wpisz tickery (oddzielone przecinkiem):", "AAPL, TSLA, BTC-USD")
timeframe = st.sidebar.selectbox("Wybierz okno czasowe:", 
                                ["1 msc", "3 msc", "6 msc", "12 msc", "2 lata", "5 lat"], 
                                index=3)

# Mapowanie okna czasowego na dni
mapping = {"1 msc": 30, "3 msc": 90, "6 msc": 180, "12 msc": 365, "2 lata": 730, "5 lat": 1825}
days = mapping[timeframe]
start_date = datetime.now() - timedelta(days=days)

# Przetwarzanie tickerów
ticker_list = [t.strip().upper() for t in tickers_input.split(",")]

# Generowanie wykresów
for ticker in ticker_list:
    try:
        data = yf.download(ticker, start=start_date)
        if not data.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=data.index, y=data['Close'], mode='lines', name=ticker))
            fig.update_layout(title=f"Cena {ticker} - ostatnie {timeframe}", 
                              xaxis_title="Data", yaxis_title="Cena (USD)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning(f"Brak danych dla symbolu: {ticker}")
    except Exception as e:
        st.error(f"Błąd przy pobieraniu {ticker}: {e}")