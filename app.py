import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd

st.set_page_config(page_title="Monitor ETF", layout="wide")

@st.cache_data(ttl=3600)
def get_data(tickers, start):
    return yf.download(tickers, start=start, multi_level_index=False)

tickers = ["EIMI.L", "SWDA.L", "CBU0.L", "IB01.L", "CNDX.L"]
start_download = datetime.now() - timedelta(days=5*365)

with st.spinner('Pobieranie danych...'):
    all_data = get_data(tickers, start_download)

if not all_data.empty:
    # 1. Definiujemy punkty na suwaku (co miesiąc)
    month_ends = pd.date_range(start=all_data.index.min(), end=all_data.index.max(), freq='ME')

    # 2. Suwak pod tytułem, który steruje oknem 12m
    selected_end = st.select_slider(
        "Przesuń, aby zobaczyć trend (okno 12m):",
        options=month_ends,
        value=month_ends[-1],
        format_func=lambda x: x.strftime('%m/%Y')
    )

    # Obliczamy okno
    start_view = selected_end - timedelta(days=365)
    
    fig = go.Figure()

    for ticker in tickers:
        try:
            # Wycinamy dane dla widocznego okna
            series = all_data['Close'][ticker].dropna()
            mask = (series.index >= pd.Timestamp(start_view)) & (series.index <= pd.Timestamp(selected_end))
            window_data = series.loc[mask]
            
            if not window_data.empty:
                # PRZELICZENIE: Pierwsza cena w wybranym oknie staje się bazą (0%)
                base_price = float(window_data.iloc[0])
                returns = ((window_data / base_price) - 1) * 100
                
                fig.add_trace(go.Scatter(
                    x=window_data.index, 
                    y=returns, 
                    mode='lines', 
                    name=ticker,
                    line=dict(width=3)
                ))
        except:
            continue

    fig.update_layout(
        template="plotly_dark",
        height=500,
        xaxis=dict(title="Data", gridcolor='rgba(255,255,255,0.1)'),
        yaxis=dict(title="Zwrot % (relatywny)", ticksuffix="%", gridcolor='rgba(255,255,255,0.1)'),
        hovermode="x unified",
        legend=dict(orientation="h", y=1.1)
    )
    
    # Linia zero
    fig.add_hline(y=0, line_dash="dash", line_color="gray")

    st.plotly_chart(fig, use_container_width=True)

    # 3. Miniaturowy podgląd całego okresu (jako pasek postępu)
    st.write(f"🔍 Widok od **{start_view.strftime('%d/%m/%Y')}** do **{selected_end.strftime('%d/%m/%Y')}**")

else:
    st.error("Brak danych.")
