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
    all_assets = tickers + [SAFE_ASSET]
    
    # 1. Obliczamy Momentum 12-miesięczne na cenach zamknięcia
    momentum = df[tickers].pct_change(12)
    safe_momentum = df[SAFE_ASSET].pct_change(12)
    
    # 2. Sygnał na koniec miesiąca T
    best_risky_ticker = momentum.idxmax(axis=1)
    best_risky_val = momentum.max(axis=1)
    
    signals = []
    for date in df.index:
        # GEM: Wybierz najlepszy ryzykowny, jeśli bije Safe Asset i jest > 0
        if best_risky_val.loc[date] > safe_momentum.loc[date] and best_risky_val.loc[date] > 0:
            signals.append(best_risky_ticker.loc[date])
        else:
            signals.append(SAFE_ASSET)
            
    df['Signal_Asset'] = signals
    # Pozycja w miesiącu T to sygnał wygenerowany na koniec miesiąca T-1
    df['Position'] = df['Signal_Asset'].shift(1)
    
    # 3. OBLICZANIE ZWROTÓW (NAPRAWIONE)
    # Pobieramy zwroty wszystkich aktywów
    returns = df[all_assets].pct_change()
    
    # Inicjalizacja kapitału
    strat_rets = []
    
    for i in range(len(df)):
        current_date = df.index[i]
        asset_to_hold = df['Position'].iloc[i]
        
        if pd.isna(asset_to_hold):
            strat_rets.append(0.0)
        else:
            # Pobieramy zwrot aktywa, które faktycznie trzymaliśmy w tym miesiącu
            actual_return = returns.loc[current_date, asset_to_hold]
            strat_rets.append(actual_return)
            
    df['Strategy_Ret'] = strat_rets
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

# --- ZAAWANSOWANA DIAGNOSTYKA ---
    st.subheader("🕵️ Szczegółowa Analiza Decyzji (Momentum 12m)")
    st.markdown("Tabela pokazuje wartości momentum, na podstawie których system wybrał aktywo na **następny** miesiąc.")

    # Przygotowanie tabeli z nazwami czytelnymi dla człowieka
    inv_map = {v: k for k, v in ASSETS.items()}
    inv_map[SAFE_ASSET] = "🛡️ Safe Asset"

    # Wybieramy kolumny momentum dla wszystkich aktywów
    tickers = list(ASSETS.values())
    diag_cols = tickers + [SAFE_ASSET]
    
    # Pobieramy momentum z wyników (użyliśmy pct_change(12) wcześniej)
    momentum_table = results[diag_cols].pct_change(12).tail(15) 
    
    # Dodajemy informację o dokonanym wyborze
    momentum_table['WYBRANY SYGNAŁ'] = results['Signal_Asset'].tail(15).map(inv_map)
    
    # Formatowanie dla czytelności
    styled_diag = momentum_table.sort_index(ascending=False).style.format({
        col: '{:.2%}' for col in diag_cols
    }).highlight_max(subset=tickers + [SAFE_ASSET], color='#004d00', axis=1)

    st.dataframe(styled_diag, use_container_width=True)

    st.info("""
    **Jak czytać tę tabelę?**
    * Kolory **zielone** wskazują najwyższe momentum w danym miesiącu.
    * Jeśli najwyższe momentum jest w kolumnie bezpiecznej (lub wszystkie są ujemne), system powinien wybrać Safe Asset.
    * Pamiętaj: Sygnał wygenerowany w dacie X jest realizowany (widoczny w portfelu) w dacie X+1.
    """)

except Exception as e:
    st.error(f"Błąd krytyczny: {e}")


