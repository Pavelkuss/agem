import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="Monitor ETF", layout="wide")

@st.cache_data(ttl=3600)
def get_data(tickers, start):
    return yf.download(tickers, start=start, multi_level_index=False)

# Konfiguracja danych
tickers = ["EIMI.L", "SWDA.L", "CBU0.L", "IB01.L", "CNDX.L"]
# Pobieramy 5 lat, aby suwak na dole miał szeroki zakres
start_date = datetime.now() - timedelta(days=5*365)

all_data = get_data(tickers, start_date)

if not all_data.empty:
    fig = go.Figure()
    
    # Określamy domyślne okno 12m (ostatni rok)
    end_view = all_data.index.max()
    start_view = end_view - timedelta(days=365)

    for ticker in tickers:
        if ticker in all_data['Close']:
            # Obliczamy zwrot względem CAŁEGO okresu, 
            # Plotly sam przeskaluje oś Y przy przesuwaniu
            series = all_data['Close'][ticker].dropna()
            initial_price = series.iloc[0]
            returns = ((series / initial_price) - 1) * 100
            
            fig.add_trace(go.Scatter(
                x=series.index, 
                y=returns, 
                mode='lines', 
                name=ticker,
                line=dict(width=2)
            ))

    # Konfiguracja suwaka pod wykresem (na wzór JustETF)
    fig.update_layout(
        template="plotly_dark",
        height=600,
        xaxis=dict(
            rangeselector=dict(
                buttons=list([
                    dict(count=6, label="6m", step="month", stepmode="backward"),
                    dict(count=1, label="1y", step="year", stepmode="backward"),
                    dict(step="all", label="MAX")
                ]),
                bgcolor="#222",
                font=dict(color="white")
            ),
            # To jest suwak na dole
            rangeslider=dict(visible=True, thickness=0.08),
            type="date",
            # Ustawienie sztywnego widoku startowego na 12 msc
            range=[start_view, end_view]
        ),
        yaxis=dict(ticksuffix="%", fixedrange=False),
        margin=dict(l=50, r=50, t=50, b=50),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    st.plotly_chart(fig, use_container_width=True)
else:
    st.error("Błąd pobierania danych.")
