import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Advanced GEM Strategy", layout="wide")

# --- FUNKCJA DAT ---
@st.cache_data(ttl=86400)
def get_dates():
    try:
        df = yf.download("SXR8.DE", period="5y", progress=False, multi_level_index=False)
        return list(pd.date_range(start=df.index.min(), end=df.index.max(), freq='ME')[::-1])
    except:
        return [datetime.now().replace(day=1) - timedelta(days=i*30) for i in range(60)]

# --- CSS: TWARDE PRZYCIĄGANIE ELEMENTÓW ---
st.markdown("""
    <style>
    /* Wymuszenie braku zawijania i centrowanie rzędu */
    [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 0px !important; /* Całkowity brak luki między kolumnami */
    }

    /* Kolumna 1: ⚙️ */
    [data-testid="stHorizontalBlock"] > div:nth-child(1) {
        flex: 0 0 12% !important;
        min-width: 12% !important;
    }

    /* Kolumna 2: Minus - PRZYCIĄGANIE DO PRAWEJ */
    [data-testid="stHorizontalBlock"] > div:nth-child(2) {
        flex: 0 0 10% !important;
        min-width: 10% !important;
        display: flex !important;
        justify-content: flex-end !important;
    }
    [data-testid="stHorizontalBlock"] > div:nth-child(2) button {
        margin-right: -15px !important; /* Fizyczne przesunięcie w prawo poza krawędź kolumny */
    }

    /* Kolumna 3: DATA */
    [data-testid="stHorizontalBlock"] > div:nth-child(3) {
        flex: 0 0 56% !important;
        min-width: 56% !important;
        z-index: 10; /* Aby data była nad przesuniętymi przyciskami */
    }

    /* Kolumna 4: Plus - PRZYCIĄGANIE DO LEWEJ */
    [data-testid="stHorizontalBlock"] > div:nth-child(4) {
        flex: 0 0 10% !important;
        min-width: 10% !important;
        display: flex !important;
        justify-content: flex-start !important;
    }
    [data-testid="stHorizontalBlock"] > div:nth-child(4) button {
        margin-left: -15px !important; /* Fizyczne przesunięcie w lewo do daty */
    }

    /* Stylizacja samych przycisków, aby były węższe */
    .stButton button {
        width: 35px !important; /* Stała szerokość dla symboli +/- */
        height: 40px !important;
        padding: 0px !important;
        border-radius: 4px !important;
    }

    /* Blokada klawiatury i styl selectboxa */
    div[data-baseweb="select"] input { pointer-events: none !important; }
    
    .stExpander { border: none !important; background: transparent !important; }
    .stExpander > div:first-child { padding: 0 !important; width: 40px !important; }
    
    .block-container { padding-top: 0.5rem; padding-bottom: 1rem; }
    #MainMenu, footer, header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- LOGIKA ---
dates_list = get_dates()
if 'date_idx' not in st.session_state: st.session_state.date_idx = 0

# --- PASEK NAWIGACJI ---
c1, c2, c3, c4 = st.columns(4)

with c1:
    cfg_menu = st.expander("⚙️")
with c2:
    if st.button("－"):
        if st.session_state.date_idx < len(dates_list) - 1:
            st.session_state.date_idx += 1
            st.rerun()
with c3:
    selected_month = st.selectbox("D", options=dates_list, index=st.session_state.date_idx,
                                  format_func=lambda x: x.strftime('%m.%Y'),
                                  label_visibility="collapsed")
    st.session_state.date_idx = dates_list.index(selected_month)
with c4:
    if st.button("＋"):
        if st.session_state.date_idx > 0:
            st.session_state.date_idx -= 0
            st.rerun()

# --- DALSZA CZĘŚĆ KODU (Portfel, Analiza, Wykresy) ---
# ... (Zastosuj poprzednią logikę obliczeń i wyświetlania sygnału)
