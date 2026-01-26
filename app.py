import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd

st.set_page_config(page_title="Monitor Trendu ETF", layout="wide")
st.title("📈 Analiza Trendu (Okno 12m)")

@st.cache_data(ttl=86400)
def get_ticker_names(ticker_list):
    names = {}
    for t in ticker_list:
        try:
            ticker_obj = yf.Ticker(t)
            full_name = ticker_obj.info.get('longName') or ticker_obj.info.get('shortName') or t
            names[t] = full_name
        except:
            names[t] = t
    return names

@st.cache_data(ttl=3600)
def get_data(tickers, start):
    data = yf.download(tickers, start=start, multi_level_index=False)
    return data

# Lista tickerów - MSE.PA zastępuje surowy indeks
tickers = ["EIMI.L", "SWDA.L", "CBU0.L", "IB01.L", "CNDX.L", "MSE.PA"]
start_download = datetime.now() - timedelta(days=5*365)

with st.spinner('Ładowanie danych...'):
    all_data = get_data(tickers, start_download)
    asset_names = get_ticker_names(tickers)

if not all_data.empty:
    month_ends = pd.date_range(start=all_data.index.min(), end=all_data.index.max(), freq='ME')

    st.write("### Przesuń suwak (okno 12m)")

    def smart_label(date):
        if date.month == 1:
            return date.strftime('%Y')
        elif date.month == 7:
            return date.strftime('%m/%y')
        return "" 

    selected_end = st.select_slider(
        "Wybierz datę końcową widoku:",
        options=month_ends,
        value=month_ends[-1],
        format_func=smart_label
    )

    start_view = selected_end - timedelta(days=365)
    fig = go.Figure()
    
    # Lista do rankingu
    performance_results = []

    for ticker in tickers:
        try:
            series = all_data['Close'][ticker].dropna()
            mask = (series.index >= pd.Timestamp(start_view)) & (series.index <= pd.Timestamp(selected_end))
            window_data = series.loc[mask]
            
            if not window_data.empty:
                base_price = float(window_data.iloc[0])
                current_return = ((window_data.iloc[-1] / base_price) - 1) * 100
                returns_series = ((window_data / base_price) - 1) * 100
                
                performance_results.append({
                    "Ticker": ticker,
                    "Nazwa": asset_names.get(ticker, ticker),
                    "Wynik %": round(current_return, 2)
                })
                
                fig.add_trace(go.Scatter(
                    x=window_data.index, 
                    y=returns_series, 
                    mode='lines', 
                    name=f"{ticker}",
                    line=dict(width=3),
                    hovertemplate='<b>' + ticker + '</b><br>Wynik: %{y:.2f}%'
                ))
        except:
            continue

    fig.update_layout(
        template="plotly_dark",
        height=600,
        xaxis=dict(gridcolor='rgba(255,255,255,0.1)'),
        yaxis=dict(ticksuffix="%", gridcolor='rgba(255,255,255,0.1)'),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5)
    )
    
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    st.plotly_chart(fig, use_container_width=True)

    # Ranking pod wykresem
    st.write("### 🏆 Ranking wyników w tym oknie")
    df_perf = pd.DataFrame(performance_results).sort_values(by="Wynik %", ascending=False)
    st.table(df_perf)

else:
    st.error("Błąd pobierania danych.")
