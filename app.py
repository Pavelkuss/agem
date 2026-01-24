import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="Monitor Aktywów", layout="wide")
st.title("📈 Advanced Global Equity Momentum Strategy")

st.sidebar.header("Ustawienia")
default_tickers = "EIMI.L, SWDA.L, CBU0.L, IB01.L, CNDX.L"
tickers_input = st.sidebar.text_input("Wpisz tickery:", default_tickers)
timeframe = st.sidebar.selectbox("Wybierz okno czasowe:", 
                                ["1 msc", "3 msc", "6 msc", "12 msc", "2 lata", "5 lat"], 
                                index=3)

mapping = {"1 msc": 30, "3 msc": 90, "6 msc": 180, "12 msc": 365, "2 lata": 730, "5 lat": 1825}
start_date = datetime.now() - timedelta(days=mapping[timeframe])

ticker_list = [t.strip().upper() for t in tickers_input.split(",")]

fig = go.Figure()

for ticker in ticker_list:
    try:
        # Pobieranie danych
        data = yf.download(ticker, start=start_date, multi_level_index=False)
        
        if not data.empty and len(data) > 2:
            # FILTR PIKÓW: Obliczamy zmianę procentową dzień do dnia
            # Jeśli zmiana jest większa niż 30% w jeden dzień, traktujemy to jako błąd danych
            data['Diff'] = data['Close'].pct_change().abs()
            data = data[data['Diff'] < 0.3].copy()
            
            if not data.empty:
                initial_price = float(data['Close'].iloc[0])
                returns = ((data['Close'] / initial_price) - 1) * 100
                
                fig.add_trace(go.Scatter(
                    x=data.index, 
                    y=returns, 
                    mode='lines', 
                    name=ticker,
                    fill='tozeroy',
                    hovertemplate='%{y:.2f}%'
                ))
    except Exception as e:
        st.error(f"Problem z {ticker}: {e}")

# Ustawienia wyglądu
fig.update_layout(
    title=f"Skumulowany zwrot (%) - {timeframe}",
    xaxis_title="Data",
    yaxis_title="Zmiana (%)",
    template="plotly_dark",
    hovermode="x unified",
    yaxis_ticksuffix="%",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

fig.add_hline(y=0, line_dash="solid", line_color="white", line_width=1)

st.plotly_chart(fig, use_container_width=True)

