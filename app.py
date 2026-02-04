import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="Multi-Asset GEM (EUR)", layout="wide")

st.title("🚀 Multi-Asset Momentum Strategy (EUR)")

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

# --- POBIERANIE DANYCH (NAPRAWIONE) ---
@st.cache_data
def get_clean_data(assets_dict, safe_ticker):
    tickers = list(assets_dict.values()) + [safe_ticker]
    # Pobieramy dane
    raw_data = yf.download(tickers, period="max", auto_adjust=True)
    
    # Wybieramy tylko Close/Adj Close i czyścimy strukturę
    if 'Close' in raw_data.columns:
        df = raw_data['Close']
    else:
        df = raw_data
        
    # Jeśli yfinance zwrócił MultiIndex (np. Tickers na górze), upraszczamy
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0) if len(df.columns.levels[0]) > 1 else df.columns.get_level_values(1)

    # KLUCZOWE: Konwersja na liczby i usunięcie błędów
    df = df.apply(pd.to_numeric, errors='coerce')
    
    # Resampling do miesięcy
    monthly = df.resample('ME').last().ffill()
    return monthly.dropna()

# --- LOGIKA STRATEGII ---
def run_strategy(df, assets_dict, safe_ticker):
    tickers = list(assets_dict.values())
    
    # Momentum 12-miesięczne
    mom = df[tickers].pct_change(12)
    safe_mom = df[safe_ticker].pct_change(12)
    
    # Wybór najlepszego aktywa
    # Wybieramy ticker z max momentum
    best_ticker = mom.idxmax(axis=1)
    best_val = mom.max(axis=1)
    
    # Sygnał: Jeśli najlepszy risky > safe, bierzemy risky. Inaczej safe.
    signals = []
    for i in range(len(df)):
        date = df.index[i]
        if best_val.iloc[i] > safe_mom.iloc[i]:
            signals.append(best_ticker.iloc[i])
        else:
            signals.append(safe_ticker)
            
    df['Selected_Asset'] = pd.Series(signals, index=df.index).shift(1)
    
    # Obliczanie zwrotów
    returns = df[tickers + [safe_ticker]].pct_change()
    
    strat_rets = []
    for i in range(len(df)):
        asset = df['Selected_Asset'].iloc[i]
        if pd.isna(asset) or asset not in returns.columns:
            strat_rets.append(0)
        else:
            strat_rets.append(returns[asset].iloc[i])
            
    df['Strategy_Ret'] = strat_rets
    df['Bench_Ret'] = returns[BENCHMARK]
    return df.dropna()

# --- UI I WYKRESY ---
try:
    data = get_clean_data(ASSETS, SAFE_ASSET)
    if data.empty:
        st.warning("Nie udało się pobrać danych. Spróbuj odświeżyć stronę.")
    else:
        results = run_strategy(data.copy(), ASSETS, SAFE_ASSET)
        
        # Slider daty
        min_d, max_d = results.index.min().date(), results.index.max().date()
        start_date, end_date = st.sidebar.select_slider("Wybierz zakres", options=results.index.date, value=(min_d, max_d))
        
        df_v = results.loc[str(start_date):str(end_date)].copy()
        df_v['Equity_Strat'] = (1 + df_v['Strategy_Ret']).cumprod() * 1000
        df_v['Equity_Bench'] = (1 + df_v['Bench_Ret']).cumprod() * 1000
        
        # Wykres
        fig = go.Figure()
        
        # Cieniowanie okresów Safe Asset
        df_v['Is_Safe'] = (df_v['Selected_Asset'] == SAFE_ASSET).astype(int)
        for i in range(1, len(df_v)):
            if df_v['Is_Safe'].iloc[i] == 1:
                fig.add_vrect(x0=df_v.index[i-1], x1=df_v.index[i], fillcolor="rgba(255,165,0,0.1)", line_width=0)

        fig.add_trace(go.Scatter(x=df_v.index, y=df_v['Equity_Strat'], name="Strategy", line=dict(color='#00FF00', width=3)))
        fig.add_trace(go.Scatter(x=df_v.index, y=df_v['Equity_Bench'], name="S&P 500 B&H", line=dict(color='gray', dash='dot')))
        
        fig.update_layout(template="plotly_dark", title="Krzywa kapitału (Start: 1000 EUR)")
        st.plotly_chart(fig, use_container_width=True)
        
        # Tabela
        st.subheader("Historia portfela")
        inv_map = {v: k for k, v in ASSETS.items()}
        inv_map[SAFE_ASSET] = "🛡️ CASH/BONDS"
        
        df_v['Asset_Name'] = df_v['Selected_Asset'].map(inv_map)
        st.dataframe(df_v[['Asset_Name', 'Strategy_Ret']].sort_index(ascending=False), use_container_width=True)

except Exception as e:
    st.error(f"Wystąpił błąd: {e}")
    st.info("Podpowiedź: Upewnij się, że biblioteka yfinance jest w najnowszej wersji.")
