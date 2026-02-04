import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="Multi-Asset GEM (EUR)", layout="wide")

st.title("🚀 Multi-Asset Momentum Strategy (EUR)")
st.markdown("Strategia wybiera co miesiąc **najsilniejszy** z dostępnych ETF-ów, o ile jego momentum jest wyższe niż bezpiecznej gotówki.")

# --- KONFIGURACJA AKTYWÓW ---
ASSETS = {
    "S&P 500": "SXR8.DE",
    "Nasdaq 100": "SXRV.DE",
    "STOXX 600": "EXSA.DE",
    "STOXX 50": "EUN2.DE",
    "Emerging Markets": "IS3N.DE"
}
SAFE_ASSET = "XEON.DE"
BENCHMARK = "SXR8.DE" # S&P 500 jako baza do porównania

# --- POBIERANIE DANYCH ---
@st.cache_data
def get_all_data(assets_dict, safe_ticker):
    all_tickers = list(assets_dict.values()) + [safe_ticker]
    data = yf.download(all_tickers, period="max", auto_adjust=False)['Adj Close']
    
    # Obsługa MultiIndex i czyszczenie
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(1)
    
    monthly = data.resample('ME').last().ffill().dropna()
    return monthly

# --- LOGIKA STRATEGII ---
def backtest_multi_asset(df, assets_dict, safe_ticker):
    risky_tickers = list(assets_dict.values())
    
    # 1. Obliczamy momentum (12m) dla wszystkich
    momentum = df[risky_tickers].pct_change(12)
    safe_momentum = df[safe_ticker].pct_change(12)
    
    # 2. Wybieramy najlepszy ticker ryzykowny w każdym miesiącu
    best_risky_ticker = momentum.idxmax(axis=1)
    best_risky_value = momentum.max(axis=1)
    
    # 3. Decyzja: Najlepszy Risky vs Safe
    # Sygnał: jeśli najlepsze akcje > safe asset, wybierz ten ticker. Inaczej wybierz safe.
    choices = []
    for date, value in best_risky_value.items():
        if value > safe_momentum.loc[date]:
            choices.append(best_risky_ticker.loc[date])
        else:
            choices.append(safe_ticker)
            
    df['Target_Asset'] = choices
    df['Selected_Asset'] = df['Target_Asset'].shift(1) # Reakcja z opóźnieniem 1 m-ca
    
    # 4. Obliczanie zwrotów
    returns = df.pct_change()
    
    strategy_returns = []
    for i in range(len(df)):
        asset = df['Selected_Asset'].iloc[i]
        if pd.isna(asset):
            strategy_returns.append(0)
        else:
            strategy_returns.append(returns[asset].iloc[i])
            
    df['Strategy_Ret'] = strategy_returns
    df['Benchmark_Ret'] = returns[BENCHMARK]
    
    return df.dropna()

# --- URUCHOMIENIE ---
try:
    df_raw = get_all_data(ASSETS, SAFE_ASSET)
    df_results = backtest_multi_asset(df_raw.copy(), ASSETS, SAFE_ASSET)

    # Sidebar: Wybór okresu
    min_date, max_date = df_results.index.min().date(), df_results.index.max().date()
    with st.sidebar:
        st.header("Ustawienia")
        start_date, end_date = st.date_input("Zakres dat", [min_date, max_date])

    # Filtrowanie i normalizacja
    df_view = df_results.loc[start_date:end_date].copy()
    df_view['Equity_Strategy'] = (1 + df_view['Strategy_Ret']).cumprod() * 1000
    df_view['Equity_Benchmark'] = (1 + df_view['Benchmark_Ret']).cumprod() * 1000

    # Wykres
    fig = go.Figure()
    # Cieniowanie okresów Safe Asset
    df_view['Is_Safe'] = (df_view['Selected_Asset'] == SAFE_ASSET).astype(int)
    
    fig.add_trace(go.Scatter(x=df_view.index, y=df_view['Equity_Strategy'], name="Multi-Asset Momentum", line=dict(color='gold', width=3)))
    fig.add_trace(go.Scatter(x=df_view.index, y=df_view['Equity_Benchmark'], name="Buy & Hold S&P 500", line=dict(color='white', dash='dot')))
    
    fig.update_layout(template="plotly_dark", title="Wyniki Strategii vs S&P 500")
    st.plotly_chart(fig, use_container_width=True)

    # Tabela historii
    st.subheader("Historia wyborów portfela")
    # Odwracamy nazwy tickerów na czytelne nazwy
    inv_assets = {v: k for k, v in ASSETS.items()}
    inv_assets[SAFE_ASSET] = "🛡️ SAFE ASSET (Gotówka)"
    
    display_df = df_view[['Selected_Asset', 'Strategy_Ret']].copy()
    display_df['Aktywo w portfelu'] = display_df['Selected_Asset'].map(inv_assets)
    display_df['Miesięczny Wynik'] = display_df['Strategy_Ret'].map('{:.2%}'.format)
    
    st.dataframe(display_df[['Aktywo w portfelu', 'Miesięczny Wynik']].sort_index(ascending=False), use_container_width=True)

except Exception as e:
    st.error(f"Błąd: {e}")
