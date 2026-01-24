import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd

st.set_page_config(page_title="Monitor Trendu 12m", layout="wide")
st.title("📈 Przesuwne okno 12-miesięczne")

@st.cache_data(ttl=3600)
def get_data(tickers, start):
    data = yf.download(tickers, start=start, multi_level_index=False)
    return data

# Sidebar
st.sidebar.header("Ustawienia")
default_tickers = "EIMI.L, SWDA.L, CBU0.L, IB01.L, CNDX.L"
tickers_input = st.sidebar.text_input("Wpisz tickery:", default_tickers)
ticker_list = [t.strip().upper() for t in tickers_input.split(",")]

# Zmieniamy na 3 lata, aby suwak był czytelny (więcej miejsca na podpisy)
start_download = datetime.now() - timedelta(days=3*365)

with st.spinner('Pobieranie danych...'):
    all_data = get_data(ticker_list, start_download)

if not all_data.empty:
    # Generujemy listę końców miesięcy
    month_ends = pd.date_range(start=all_data.index.min(), end=all_data.index.max(), freq='ME')

    st.write("### Przesuń suwak (okno 12m)")
    
    # Suwak z pionowymi kreskami i podpisami MM/YY
    selected_end_date = st.select_slider(
        "Wybierz miesiąc końcowy wykresu:",
        options=month_ends,
        value=month_ends[-1],
        format_func=lambda x: x.strftime('%m/%y')
    )

    selected_start_date = selected_end_date - timedelta(days=365)
    
    fig = go.Figure()

    for ticker in ticker_list:
        try:
            if len(ticker_list) > 1:
                ticker_series = all_data['Close'][ticker].dropna()
            else:
                ticker_series = all_data['Close'].dropna()
            
            mask = (ticker_series.index >= pd.Timestamp(selected_start_date)) & \
                   (ticker_series.index <= pd.Timestamp(selected_end_date))
            window_data = ticker_series.loc[mask]
            
            if not window_data.empty:
                # Filtr pików
                diff = window_data.pct_change().abs()
                window_data = window_data[diff < 0.3]
                
                initial_price = float(window_data.iloc[0])
                returns = ((window_data / initial_price) - 1) * 100
                
                fig.add_trace(go.Scatter(
                    x=window_data.index, 
                    y=returns, 
                    mode='lines', 
                    name=ticker,
                    line=dict(width=3),
                    hovertemplate='%{y:.2f}%'
                ))
        except Exception as e:
            st.error(f"Błąd przy {ticker}: {e}")

    fig.update_layout(
        title=f"Wynik w oknie: {selected_start_date.strftime('%d/%m/%Y')} - {selected_end_date.strftime('%d/%m/%Y')}",
        template="plotly_dark",
        hovermode="x unified",
        yaxis=dict(ticksuffix="%", gridcolor='rgba(255, 255, 255, 0.1)'),
        xaxis=dict(range=[selected_start_date, selected_end_date], gridcolor='rgba(255, 255, 255, 0.1)'),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.error("Brak danych.")
