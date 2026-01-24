import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="Analiza Trendu", layout="wide")
st.title("📈 Zaawansowany Monitor Trendu")

# Sidebar
st.sidebar.header("Ustawienia")
default_tickers = "EIMI.L, SWDA.L, CBU0.L, IB01.L, CNDX.L"
tickers_input = st.sidebar.text_input("Wpisz tickery:", default_tickers)

# Pobieramy 5 lat danych, żeby mieć z czego przesuwać
start_download = datetime.now() - timedelta(days=5*365)
ticker_list = [t.strip().upper() for t in tickers_input.split(",")]

fig = go.Figure()

for ticker in ticker_list:
    try:
        data = yf.download(ticker, start=start_download, multi_level_index=False)
        if not data.empty and len(data) > 10:
            # Filtr błędnych danych (pików)
            data['Diff'] = data['Close'].pct_change().abs()
            data = data[data['Diff'] < 0.2].copy()
            
            # Punkt odniesienia: 0% to początek POBRANYCH danych
            # (Suwak pozwoli Ci to okno przesuwać)
            initial_price = float(data['Close'].iloc[0])
            returns = ((data['Close'] / initial_price) - 1) * 100
            
            fig.add_trace(go.Scatter(
                x=data.index, 
                y=returns, 
                mode='lines', 
                name=ticker,
                fill='tonexty', # Zmienione na tonexty dla lepszej stabilności przy suwaku
                hovertemplate='%{y:.2f}%'
            ))
    except Exception as e:
        st.error(f"Błąd {ticker}: {e}")

# Domyślne ustawienie widoku na ostatnie 12 miesięcy
end_date = datetime.now()
start_view = end_date - timedelta(days=365)

fig.update_layout(
    template="plotly_dark",
    hovermode="x unified",
    xaxis=dict(
        rangeslider=dict(visible=True),
        type="date",
        range=[start_view, end_date] # To ustawia początkowe 12m
    ),
    yaxis=dict(ticksuffix="%"),
    legend=dict(orientation="h", y=1.1)
)

st.plotly_chart(fig, use_container_width=True)
