import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="Rygorystyczny GEM Multi-Asset", layout="wide")

# --- KONFIGURACJA ---
ASSETS = {
    "S&P 500": "SXR8.DE",
    "Nasdaq 100": "SXRV.DE",
    "STOXX 600": "EXSA.DE",
    "STOXX 50": "EUN2.DE",
    "Emerging Markets": "IS3N.DE"
}
SAFE_ASSET = "XEON.DE"
BENCHMARK = "SXR8.DE"

@st.cache_data
def get_data():
    tickers = list(ASSETS.values()) + [SAFE_ASSET]
    # Pobieramy dane OHLC i wyciągamy Adj Close
    raw = yf.download(tickers, period="max", auto_adjust=True)['Close']
    
    # Naprawa struktury po yfinance
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    
    # Konwersja na liczby i czyszczenie
    df = raw.apply(pd.to_numeric, errors='coerce').ffill()
    # Resampling do Month-End
    return df.resample('ME').last().dropna()

def run_gem_logic(df):
    tickers = list(ASSETS.values())
    
    # 1. Obliczamy Momentum 12-miesięczne (12-m ROC)
    # Wykorzystujemy ceny z okresu T, aby podjąć decyzję na okres T+1
    momentum = df[tickers].pct_change(12)
    safe_momentum = df[SAFE_ASSET].pct_change(12)
    
    # 2. Wybór najlepszego aktywa (Sygnał generowany na koniec miesiąca)
    best_risky_ticker = momentum.idxmax(axis=1)
    best_risky_val = momentum.max(axis=1)
    
    # Logika GEM: Best Risky vs Safe Asset
    decision = []
    for date in df.index:
        if best_risky_val.loc[date] > safe_momentum.loc[date] and best_risky_val.loc[date] > 0:
            decision.append(best_risky_ticker.loc[date])
        else:
            decision.append(SAFE_ASSET)
            
    df['Signal_Asset'] = decision
    # KLUCZOWE: Przesuwamy sygnał. Decyzja z końca stycznia obowiązuje na luty.
    df['Position'] = df['Signal_Asset'].shift(1)
    
    # 3. Obliczanie zwrotów miesięcznych
    returns = df[tickers + [SAFE_ASSET]].pct_change()
    
    # Obliczanie zwrotu strategii (Mnożymy zwrot z T przez pozycję wybraną w T-1)
    strat_returns = []
    for i in range(len(df)):
        pos = df['Position'].iloc[i]
        if pd.isna(pos):
            strat_returns.append(0)
        else:
            strat_returns.append(returns[pos].iloc[i])
            
    df['Strategy_Ret'] = strat_returns
    df['Benchmark_Ret'] = returns[BENCHMARK]
    
    return df.dropna()

# --- WYŚWIETLANIE ---
try:
    data = get_data()
    results = run_gem_logic(data.copy())
    
    st.title("💶 GEM Multi-Asset: Poprawiona Logika")

    # Zakres dat
    dates = results.index.date
    start_d, end_d = st.select_slider("Wybierz okres", options=dates, value=(dates[0], dates[-1]))
    
    mask = (results.index.date >= start_d) & (results.index.date <= end_d)
    df_v = results.loc[mask].copy()
    
    # Kapitalizacja (start 1000 EUR)
    df_v['Strat_Cum'] = (1 + df_v['Strategy_Ret']).cumprod() * 1000
    df_v['Bench_Cum'] = (1 + df_v['Benchmark_Ret']).cumprod() * 1000

    # Wykres
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_v.index, y=df_v['Strat_Cum'], name="Strategia GEM", line=dict(color='#00FF00', width=3)))
    fig.add_trace(go.Scatter(x=df_v.index, y=df_v['Bench_Cum'], name="S&P 500 B&H", line=dict(color='white', dash='dot')))
    
    # Cieniowanie okresów Safe
    safe_mask = df_v['Position'] == SAFE_ASSET
    for i in range(1, len(df_v)):
        if safe_mask.iloc[i]:
            fig.add_vrect(x0=df_v.index[i-1], x1=df_v.index[i], fillcolor="rgba(255,100,0,0.15)", line_width=0)

    fig.update_layout(template="plotly_dark", height=600, title="Porównanie wyników (EUR)")
    st.plotly_chart(fig, use_container_width=True)

    # --- DIAGNOSTYKA ---
    st.subheader("🕵️ Diagnostyka: Dlaczego taki wybór?")
    inv_map = {v: k for k, v in ASSETS.items()}
    inv_map[SAFE_ASSET] = "🛡️ Safe Asset"
    
    diag_df = df_v.tail(12).copy()
    diag_df['Aktualny Portfel'] = diag_df['Position'].map(inv_map)
    diag_df['Miesięczny Wynik'] = diag_df['Strategy_Ret'].map('{:.2%}'.format)
    
    st.table(diag_df[['Aktualny Portfel', 'Miesięczny Wynik']])

except Exception as e:
    st.error(f"Błąd krytyczny: {e}")
