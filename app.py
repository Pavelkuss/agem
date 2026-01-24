import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd

st.set_page_config(page_title="Analiza Trendu 12m", layout="wide")
st.title("📈 Przesuwne okno 12-miesięczne")

# Sidebar
st.sidebar.header("Ustawienia")
default_tickers = "EIMI.L, SWDA.L, CBU0.L, IB01.L, CNDX.L"
tickers_input = st.sidebar.text_input("Wpisz tickery:", default_tickers)

# Pobieramy 5 lat danych
start_download = datetime.now() - timedelta(days=5*365)
ticker_list = [t.strip().upper() for t in tickers_input.split(",")]

# SUWAK DO PRZESUWANIA (Wybierasz datę końcową widoku)
st.write("### Przesuń suwak, aby zmienić okres (okno zawsze 12 msc)")
selected_end_date = st.slider(
    "Data końcowa wykresu:",
    min_value=datetime.now() - timedelta(days=4*365),
    max_value=datetime.now(),
    value=datetime.now(),
    format="DD/MM/YYYY"
)

# Obliczamy stały start (12 miesięcy wstecz od suwaka)
selected_start_date = selected_end_date - timedelta(days=365)

fig = go.Figure()

for ticker in ticker_list:
    try:
        data = yf.download(ticker, start=start_download, multi_level_index=False)
        if not data.empty:
            # Filtr pików
            data['Diff'] = data['Close'].pct_change().abs()
            data = data[data['Diff'] < 0.2].copy()
            
            # Wycinamy dane tylko dla wybranego okna 12m, aby przeliczyć % od zera w tym oknie
            mask = (data.index >= pd.Timestamp(selected_start_date)) & (data.index <= pd.Timestamp(selected_end_date))
            window_data = data.loc[mask]
            
            if not window_data.empty:
                initial_price = float(window_data['Close'].iloc[0])
                returns = ((window_data['Close'] / initial_price) -
