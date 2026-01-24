import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd

st.set_page_config(page_title="Monitor ETF", layout="wide")

@st.cache_data(ttl=86400) # Nazwy pobieramy rzadziej (raz na dobę)
def get_ticker_names(ticker_list):
    names = {}
    for t in ticker_list:
        try:
            info = yf.Ticker(t).info
            # Próba pobrania długiej nazwy, jeśli brak - krótkiej, jeśli brak - zostaje ticker
            names[t] = info.get('shortName') or t
        except:
            names[t] = t
    return names

@st.cache_data(ttl=3600)
def get_data(tickers, start):
    return yf.download(tickers, start=start, multi_level_index=False)

tickers = ["EIMI.L", "SWDA.L", "CBU0.L", "IB01.L", "CNDX.L"]
start_download = datetime.now() - timedelta(days=5*365)

# Pobieranie danych i nazw
with st.spinner('Pobieranie danych i nazw aktywów...'):
    all_data = get_data(tickers, start_download)
    ticker_names = get_ticker_names(tickers)

if not all_data.empty:
    # Pobieramy wszystkie dostępne końce miesięcy
    month_ends = pd.date_range(start=all_data.index.min(), end=all_data.index.max(), freq='ME')

    st.write("### Przesuń suwak (okno 12m)")
    
    # Funkcja, która decyduje, co wyświetlić, by nie zapchać suwaka
    def smart_label(date):
        # Wyświetlaj etykietę tylko dla stycznia (początek roku) lub lipca (połowa)
        # To zwolni miejsce i wymusi pojawienie się kresek oraz napisów
        if date.month == 1:
            return date.strftime('styczeń %Y')
        elif date.month == 7:
            return date.strftime('%m/%y')
        return "" # Reszta punktów to same kreski bez tekstu

    selected_end = st.select_slider(
        "Data końcowa widoku:",
        options=month_ends,
        value=month_ends[-1],
        format_func=smart_label
    )

    # Obliczanie okna i reszta kodu bez zmian...

    start_view = selected_end - timedelta(days=365)
    fig = go.Figure()

    for ticker in tickers:
        try:
            series = all_data['Close'][ticker].dropna()
            mask = (series.index >= pd.Timestamp(start_view)) & (series.index <= pd.Timestamp(selected_end))
            window_data = series.loc[mask]
            
            if not window_data.empty:
                # Przeliczenie bazy na 0% dla początku okna
                base_price = float(window_data.iloc[0])
                returns = ((window_data / base_price) - 1) * 100
                
                # Pobranie pełnej nazwy ze słownika
                full_name = ticker_names.get(ticker, ticker)
                
                fig.add_trace(go.Scatter(
                    x=window_data.index, 
                    y=returns, 
                    mode='lines', 
                    name=f"{ticker} ({full_name})", # Nazwa w legendzie
                    line=dict(width=3),
                    hovertemplate='<b>' + ticker + '</b><br>%{y:.2f}%'
                ))
        except:
            continue

    fig.update_layout(
        template="plotly_dark",
        height=600,
        xaxis=dict(gridcolor='rgba(255,255,255,0.1)'),
        yaxis=dict(ticksuffix="%", gridcolor='rgba(255,255,255,0.1)'),
        hovermode="x unified",
        legend=dict(
            orientation="h", 
            yanchor="bottom", 
            y=1.02, 
            xanchor="center", 
            x=0.5,
            font=dict(size=10) # Mniejsza czcionka, by pomieścić długie nazwy
        )
    )
    
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.error("Błąd pobierania danych.")


