import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd

st.set_page_config(page_title="Monitor ETF (EUR)", layout="wide")
st.title("📈 Analiza Trendu (Okno 12m) - Waluta: EUR")

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
    # Pobieramy ceny zamknięcia (Adjusted Close uwzględnia dywidendy/splity)
    data = yf.download(tickers, start=start, multi_level_index=False)['Adj Close']
    return data

# TICKERY W EUR (XETRA/EURONEXT)
# IWDA.AS (Euronext Amsterdam - World), IS3N.DE (Xetra - EM), 
# SXRT.DE (Xetra - Stoxx50), SXRV.DE (Xetra - Nasdaq100)
tickers = ["IWDA.AS", "IS3N.DE", "SXRT.DE", "SXRV.DE", "CBU0.DE", "IB01.DE"]
start_download = datetime.now() - timedelta(days=5*365)

with st.spinner('Synchronizacja z rynkami EUR...'):
    all_data = get_data(tickers, start_download)
    asset_names = get_ticker_names(tickers)

if not all_data.empty:
    month_ends = pd.date_range(start=all_data.index.min(), end=all_data.index.max(), freq='ME')

    def smart_label(date):
        if date.month == 1: return date.strftime('%Y')
        if date.month == 7: return date.strftime('%m/%y')
        return ""

    selected_end = st.select_slider("Wybierz koniec okna:", options=month_ends, 
                                    value=month_ends[-1], format_func=smart_label)

    start_view = selected_end - timedelta(days=365)
    fig = go.Figure()
    performance_results = []

    for ticker in tickers:
        try:
            series = all_data[ticker].dropna()
            mask = (series.index >= pd.Timestamp(start_view)) & (series.index <= pd.Timestamp(selected_end))
            window_data = series.loc[mask]
            
            if not window_data.empty:
                # BAZA 0% na początku wybranego okna
                base_price = float(window_data.iloc[0])
                current_return = ((window_data.iloc[-1] / base_price) - 1) * 100
                returns_series = ((window_data / base_price) - 1) * 100
                
                performance_results.append({
                    "Ticker": ticker,
                    "Nazwa": asset_names.get(ticker, ticker),
                    "Wynik % (12m)": round(current_return, 2)
                })
                
                fig.add_trace(go.Scatter(x=window_data.index, y=returns_series, 
                                         mode='lines', name=ticker, line=dict(width=3)))
        except: continue

    fig.update_layout(template="plotly_dark", height=600, hovermode="x unified",
                      yaxis=dict(ticksuffix="%", gridcolor='rgba(255,255,255,0.1)'),
                      legend=dict(orientation="h", y=1.05, x=0.5, xanchor="center"))
    
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    st.plotly_chart(fig, use_container_width=True)

    st.write("### 🏆 Ranking (wyniki w EUR)")
    st.table(pd.DataFrame(performance_results).sort_values(by="Wynik % (12m)", ascending=False))

else:
    st.error("Błąd pobierania danych.")
