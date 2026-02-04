import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="GEM Strategy Calculator (EUR)", layout="wide")

st.title("💶 GEM Strategy Calculator (EUR)")
st.markdown("""
Aplikacja do analizy strategii **Global Equities Momentum** na bazie instrumentów notowanych w EUR.
Strategia porównuje 12-miesięczne momentum wybranego aktywa ryzykownego z bezpiecznym aktywem (Cash/Bonds).
""")

# --- DEFINICJA TICKERÓW ---
RISKY_ASSETS = {
    "S&P 500 (SXR8.DE)": "SXR8.DE",
    "Nasdaq 100 (SXRV.DE)": "SXRV.DE",
    "STOXX 600 (EXSA.DE)": "EXSA.DE",
    "STOXX 50 (EUN2.DE)": "EUN2.DE",
    "Emerging Markets (IS3N.DE)": "IS3N.DE"
}

SAFE_ASSET = "XEON.DE"  # Xtrackers II EUR Overnight Rate Swap

# --- POBIERANIE DANYCH (WERSJA NAPRAWIONA) ---
@st.cache_data
def get_data(risky_ticker, safe_ticker):
    # Pobieramy dane OSOBNO dla bezpieczeństwa
    # auto_adjust=False jest kluczowe dla niektórych europejskich tickerów
    try:
        data_risky = yf.download(risky_ticker, period="max", auto_adjust=False, progress=False)
        data_safe = yf.download(safe_ticker, period="max", auto_adjust=False, progress=False)
        
        # Sprawdzenie czy pobrano dane
        if data_risky.empty or data_safe.empty:
            return pd.DataFrame()

        # Wyciągamy tylko ceny zamknięcia (obsługa różnych wersji yfinance)
        # Czasem yfinance zwraca kolumny jako ('Adj Close', 'TICKER'), a czasem tylko 'Adj Close'
        try:
            p_risky = data_risky['Adj Close']
            if isinstance(p_risky, pd.DataFrame): # Fix dla MultiIndex
                p_risky = p_risky.iloc[:, 0]
                
            p_safe = data_safe['Adj Close']
            if isinstance(p_safe, pd.DataFrame): # Fix dla MultiIndex
                p_safe = p_safe.iloc[:, 0]
        except KeyError:
            # Fallback jeśli nie ma 'Adj Close', bierzemy 'Close'
            p_risky = data_risky['Close']
            p_safe = data_safe['Close']

        # Łączymy w jeden DataFrame
        df = pd.DataFrame({
            risky_ticker: p_risky,
            safe_ticker: p_safe
        })
        
        # Resampling do danych miesięcznych (ostatnia cena w miesiącu)
        monthly_data = df.resample('ME').last() # 'ME' to nowy standard pandas zamiast 'M'
        
        # Usuwamy wiersze tylko jeśli brakuje obu danych, lub uzupełniamy braki w historii (ffill)
        # Strategia potrzebuje ciągłości. Używamy ffill na wypadek dziur w danych.
        monthly_data = monthly_data.ffill().dropna()
        
        return monthly_data
        
    except Exception as e:
        st.error(f"Szczegóły błędu yfinance: {e}")
        return pd.DataFrame()

# --- OBLICZENIA STRATEGII ---
def calculate_strategy(df, risky_col, safe_col):
    # Obliczamy zwroty miesięczne
    df['Risky_Ret'] = df[risky_col].pct_change()
    df['Safe_Ret'] = df[safe_col].pct_change()
    
    # Obliczamy momentum (zwrot z ostatnich 12 miesięcy)
    # Używamy shift(1), aby uniknąć look-ahead bias (decyzja na koniec miesiąca dotyczy następnego)
    df['Risky_Mom_12m'] = df[risky_col].pct_change(12)
    df['Safe_Mom_12m'] = df[safe_col].pct_change(12)
    
    # LOGIKA GEM:
    # Jeśli Momentum ryzykowne > Momentum bezpieczne (lub Safe Yield), wchodzimy w ryzykowne.
    # W klasycznej wersji porównujemy do stopy wolnej od ryzyka (bill return).
    # Tutaj porównujemy momentum obu aktywów.
    
    df['Signal'] = np.where(df['Risky_Mom_12m'] > df['Safe_Mom_12m'], 1, 0)
    
    # Przesuwamy sygnał o 1 miesiąc w przód (sygnał z końca marca działa na kwiecień)
    df['Position'] = df['Signal'].shift(1)
    
    # Obliczamy zwrot strategii
    # Jeśli pozycja 1 -> zwrot z ryzykownego, jeśli 0 -> zwrot z bezpiecznego
    df['Strategy_Ret'] = np.where(df['Position'] == 1, df['Risky_Ret'], df['Safe_Ret'])
    
    return df.dropna()

# --- METRYKI ---
def calculate_metrics(series):
    total_return = (series.iloc[-1] / series.iloc[0]) - 1
    
    # Max Drawdown
    running_max = series.cummax()
    drawdown = (series - running_max) / running_max
    max_dd = drawdown.min()
    
    # Sharpe Ratio (zakładając Rf=0 dla uproszczenia w porównaniu względnym lub używając średniej)
    # Roczny Sharpe
    returns = series.pct_change().dropna()
    sharpe = (returns.mean() / returns.std()) * np.sqrt(12) if returns.std() != 0 else 0
    
    return total_return, max_dd, sharpe

# --- SIDEBAR ---
with st.sidebar:
    st.header("Konfiguracja")
    selected_asset_name = st.selectbox("Wybierz Aktywo Ryzykowne", list(RISKY_ASSETS.keys()))
    risky_ticker = RISKY_ASSETS[selected_asset_name]
    
    st.info(f"Aktywo bezpieczne: {SAFE_ASSET} (EUR Overnight)")

# --- GŁÓWNA LOGIKA ---
try:
    # 1. Pobierz dane
    df_raw = get_data(risky_ticker, SAFE_ASSET)
    
    if df_raw.empty:
        st.error("Brak danych. Spróbuj wybrać inny instrument lub sprawdź połączenie.")
    else:
        # 2. Oblicz strategię na pełnym zakresie
        df_strat = calculate_strategy(df_raw.copy(), risky_ticker, SAFE_ASSET)
        
        # 3. Interfejs zakresu dat (po obliczeniach, aby nie psuć momentum)
        min_date = df_strat.index.min().date()
        max_date = df_strat.index.max().date()
        
        st.subheader("Wybierz okres analizy")
        start_date, end_date = st.slider(
            "Zakres dat:",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            format="YYYY-MM"
        )
        
        # Filtrowanie danych do wyświetlenia
        mask = (df_strat.index.date >= start_date) & (df_strat.index.date <= end_date)
        df_view = df_strat.loc[mask].copy()
        
        # Normalizacja do 1000 EUR na start wybranego okresu
        df_view['Equity_Strategy'] = (1 + df_view['Strategy_Ret']).cumprod() * 1000
        df_view['Equity_BuyHold'] = (1 + df_view['Risky_Ret']).cumprod() * 1000
        
        # --- PREZENTACJA WYNIKÓW ---
        
        # Kolumny metryk
        col1, col2, col3 = st.columns(3)
        
        strat_ret, strat_dd, strat_sharpe = calculate_metrics(df_view['Equity_Strategy'])
        bh_ret, bh_dd, bh_sharpe = calculate_metrics(df_view['Equity_BuyHold'])
        
        with col1:
            st.metric("Całkowity Zwrot (Strategy)", f"{strat_ret:.2%}", delta=f"{strat_ret-bh_ret:.2%}")
            st.caption(f"Buy & Hold: {bh_ret:.2%}")
            
        with col2:
            st.metric("Max Drawdown (Strategy)", f"{strat_dd:.2%}", delta=f"{strat_dd-bh_dd:.2%}")
            st.caption(f"Buy & Hold: {bh_dd:.2%}")
            
        with col3:
            st.metric("Sharpe Ratio", f"{strat_sharpe:.2f}")
            st.caption(f"Buy & Hold: {bh_sharpe:.2f}")

# --- ULEPSZONY WYKRES Z ZAZNACZENIEM POZYCJI ---
        fig = go.Figure()
        
        # Dodanie tła dla okresów Safe Asset (Cash)
        # Szukamy grup dni, gdzie Position == 0
        df_view['Is_Safe'] = (df_view['Position'] == 0).astype(int)
        change_points = df_view['Is_Safe'].diff().fillna(0)
        
        # Logika rysowania prostokątów tła
        safe_periods = []
        start_p = None
        for i, (date, is_safe) in enumerate(df_view['Is_Safe'].items()):
            if is_safe == 1 and start_p is None:
                start_p = date
            elif is_safe == 0 and start_p is not None:
                safe_periods.append((start_p, date))
                start_p = None
        if start_p is not None:
            safe_periods.append((start_p, df_view.index[-1]))

        for start_p, end_p in safe_periods:
            fig.add_vrect(
                x0=start_p, x1=end_p,
                fillcolor="rgba(255, 0, 0, 0.1)", # Delikatny czerwony/pomarańczowy
                layer="below", line_width=0,
                annotation_text="SAFE", annotation_position="top left"
            )

        # Linie kapitału
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view['Equity_Strategy'], name="GEM Strategy", line=dict(color='green', width=3)))
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view['Equity_BuyHold'], name="Buy & Hold", line=dict(color='gray', dash='dot')))
        
        fig.update_layout(
            title=f"Krzywa Kapitału (Jasne tło = okresy w Safe Asset)",
            xaxis_title="Data",
            yaxis_title="Wartość (EUR)",
            hovermode="x unified",
            template="plotly_white"
        )
        st.plotly_chart(fig, use_container_width=True)
        
       # --- PEŁNA TABELA HISTORII DECYZJI ---
        st.subheader("Pełna historia decyzji i momentum")
        
        # Przygotowanie czytelnej tabeli
        history_df = df_view[['Risky_Mom_12m', 'Safe_Mom_12m', 'Position']].copy()
        history_df['Decyzja'] = np.where(history_df['Position'] == 1, "📈 AKCJE", "🛡️ SAFE ASSET")
        
        # Dodanie kolumny wyjaśniającej "Dlaczego?"
        history_df['Powód'] = np.where(
            history_df['Risky_Mom_12m'] > history_df['Safe_Mom_12m'], 
            "Momentum Akcji > Momentum Safe", 
            "Momentum Akcji < Momentum Safe"
        )
        
        # Sortowanie od najnowszych
        st.dataframe(
            history_df.sort_index(ascending=False).style.format({
                'Risky_Mom_12m': '{:.2%}', 
                'Safe_Mom_12m': '{:.2%}'
            }).applymap(
                lambda x: 'color: green;' if x == "📈 AKCJE" else ('color: red;' if x == "🛡️ SAFE ASSET" else ''),
                subset=['Decyzja']
            ),
            use_container_width=True
        )

except Exception as e:
    st.error(f"Wystąpił błąd: {e}")


