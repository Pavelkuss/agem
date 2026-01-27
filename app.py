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
    data = yf.download(tickers, start=start, multi_level_index=False, progress=False)['Close']
    return data

# Konfiguracja danych
tickers = ["EIMI.L", "SWDA.L", "CBU0.L", "IB01.L", "CNDX.L", "SXRT.DE"]
start_download = datetime.now() - timedelta(days=5*365)

with st.spinner('Pobieranie danych...'):
    all_data = get_data(tickers, start_download)
    asset_names = get_ticker_names(tickers)

if not all_data.empty:
    # 1. PRZYGOTOWANIE WYBORU DATY (Zamiast suwaka)
    month_ends = pd.date_range(start=all_data.index.min(), end=all_data.index.max(), freq='ME')
    
    st.write("### Wybierz miesiąc końcowy analizy:")
    
    # Tworzymy czytelne etykiety dla listy: "Styczeń 2024" itp.
    polish_months = {1:"Styczeń", 2:"Luty", 3:"Marzec", 4:"Kwiecień", 5:"Maj", 6:"Czerwiec", 
                     7:"Lipiec", 8:"Sierpień", 9:"Wrzesień", 10:"Październik", 11:"Listopad", 12:"Grudzień"}
    
    date_options = {d: f"{polish_months[d.month]} {d.year}" for d in month_ends}
    
    # Lista rozwijana (Selectbox)
    selected_end = st.selectbox(
        "Miesiąc końcowy okna 12m:",
        options=list(date_options.keys()),
        index=len(month_ends)-1,
        format_func=lambda x: date_options[x]
    )

    start_view = selected_end - timedelta(days=365)
    
    # 2. WYKRES
    fig = go.Figure()
    performance_results = []

    for ticker in tickers:
        if ticker in all_data.columns:
            series = all_data[ticker].dropna()
            mask = (series.index >= pd.Timestamp(start_view)) & (series.index <= pd.Timestamp(selected_end))
            window_data = series.loc[mask]
            
            if not window_data.empty:
                base_price = float(window_data.iloc[0])
                current_return = ((window_data.iloc[-1] / base_price) - 1) * 100
                returns_series = ((window_data / base_price) - 1) * 100
                
                fig.add_trace(go.Scatter(
                    x=window_data.index, y=returns_series, mode='lines', 
                    name=ticker, line=dict(width=3)
                ))
                
                performance_results.append({
                    "Ticker": ticker,
                    "Nazwa": asset_names.get(ticker, ticker),
                    "Wynik %": round(current_return, 2)
                })

    fig.update_layout(
        template="plotly_dark", height=500,
        xaxis=dict(gridcolor='rgba(255,255,255,0.1)', range=[start_view, selected_end]),
        yaxis=dict(ticksuffix="%", gridcolor='rgba(255,255,255,0.1)'),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5)
    )
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    st.plotly_chart(fig, use_container_width=True)

    # 3. RANKING (Wyjustowany i czytelny na mobile)
    if performance_results:
        st.markdown("""
            <style>
                table { width: 100%; border-collapse: collapse; }
                th, td { 
                    white-space: normal !important; 
                    word-wrap: break-word !important; 
                    padding: 8px !important;
                    text-align: left !important;
                }
                .centered-title { text-align: center; margin-top: 20px; }
            </style>
        """, unsafe_allow_html=True)

        df_perf = pd.DataFrame(performance_results).sort_values(by="Wynik %", ascending=False)
        df_perf["Wynik %"] = df_perf["Wynik %"].apply(lambda x: f"{x:+.2f}%")

        # Centrowanie kontenera tabeli
        col1, col2, col3 = st.columns([0.1, 4, 0.1])
        with col2:
            st.markdown(f"<h4 class='centered-title'>🏆 Ranking: {selected_end.strftime('%m/%Y')} (12m)</h4>", unsafe_allow_html=True)
            st.table(df_perf)

else:
    st.error("Błąd ładowania danych.")
