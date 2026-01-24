import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="Monitor Aktywów", layout="wide")
st.title("📈 Mój Dashboard Giełdowy")

st.sidebar.header("Ustawienia")
tickers_input = st.sidebar.text_input("Wpisz tickery (np. AAPL, TSLA):", "AAPL, TSLA")
timeframe = st.sidebar.selectbox("Wybierz okno czasowe:", 
                                ["1 msc", "3 msc", "6 msc", "12 msc", "2 lata"], 
                                index=3)

mapping = {"1 msc": 30, "3 msc": 90, "6 msc": 180, "12 msc": 365, "2 lata": 730}
start_date = datetime.now() - timedelta(days=mapping[timeframe])

ticker_list = [t.strip().upper() for t in tickers_input.split(",")]

for ticker in ticker_list:
    try:
        # Pobieranie danych z wymuszeniem braku multi-indexu
        data = yf.download(ticker, start=start_date, multi_level_index=False)
        
        if not data.empty:
            fig = go.Figure()
            # Używamy data.index dla dat i data['Close'] dla ceny
            fig.add_trace(go.Scatter(x=data.index, y=data['Close'], mode='lines', name=ticker))
            
            fig.update_layout(
                title=f"Cena {ticker} - ostatnie {timeframe}",
                xaxis_title="Data",
                yaxis_title="Cena (USD)",
                template="plotly_dark"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning(f"Brak danych dla: {ticker}")
    except Exception as e:
        st.error(f"Błąd: {e}")
