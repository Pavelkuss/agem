import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="Monitor Aktywów - % Zwrotu", layout="wide")
st.title("📈 Procentowa Stopa Zwrotu (Skumulowana)")

st.sidebar.header("Ustawienia")
tickers_input = st.sidebar.text_input("Wpisz tickery:", "EIMI.L, SWDA.L ,CBU0.L ,IB01.L ,CNDX.L ")
timeframe = st.sidebar.selectbox("Wybierz okno czasowe:", 
                                ["1 msc", "3 msc", "6 msc", "12 msc", "2 lata"], 
                                index=3)

mapping = {"1 msc": 30, "3 msc": 90, "6 msc": 180, "12 msc": 365, "2 lata": 730}
start_date = datetime.now() - timedelta(days=mapping[timeframe])

ticker_list = [t.strip().upper() for t in tickers_input.split(",")]

fig = go.Figure()

for ticker in ticker_list:
    try:
        data = yf.download(ticker, start=start_date, multi_level_index=False)
        if not data.empty and len(data) > 1:
            # Usuwanie błędnych danych (pików) - usuwamy dni, gdzie skok ceny jest nierealny
            data['Pct_Change'] = data['Close'].pct_change()
            data = data[data['Pct_Change'].abs() < 0.5] # Ignoruj skoki > 50% dziennie
            
            initial_price = data['Close'].iloc[0]
            returns = ((data['Close'] / initial_price) - 1) * 100
            
            fig.add_trace(go.Scatter(
                x=data.index, 
                y=returns, 
                mode='lines', 
                name=ticker,
                fill='tozeroy',
                hovertemplate='%{y:.2f}%'
            ))

fig.update_layout(
    title=f"Porównanie % zwrotu od początku okresu ({timeframe})",
    xaxis_title="Data",
    yaxis_title="Zmiana procentowa (%)",
    template="plotly_dark",
    hovermode="x unified",
    yaxis_ticksuffix="%" # Dodaje symbol % do osi Y
)

# Dodanie linii poziomej na poziomie 0% dla czytelności
fig.add_hline(y=0, line_dash="dash", line_color="gray")

st.plotly_chart(fig, use_container_width=True)


