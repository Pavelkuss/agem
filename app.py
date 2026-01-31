import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd
import json
import os

# --- LOGIKA TRWAŁEGO ZAPISU ---
SETTINGS_FILE = "user_settings.json"

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    return {"tickers": ["SXR8.DE", "EXSA.DE", "IS3N.DE", "XEON.DE"], "month_idx": 0}

def save_settings(tickers, month_idx):
    with open(SETTINGS_FILE, "w") as f:
        json.dump({"tickers": tickers, "month_idx": month_idx}, f)

# Inicjalizacja ustawień przy starcie
if 'user_prefs' not in st.session_state:
    st.session_state.user_prefs = load_settings()

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="GEM Monitor (EUR)", layout="wide")

st.markdown("""
    <style>
    .stPlotlyChart { pointer-events: none; }
    .main-title { font-size: 2.2rem; font-weight: bold; margin-bottom: 0; text-align: center; }
    .custom-table { width: 100%; border-collapse: collapse; font-size: 11px; color: white; margin-top: 10px; }
    /* Stylizacja multiselect dla lepszej widoczności na mobile */
    .stMultiSelect span { font-size: 14px !important; }
    </style>
    """, unsafe_allow_html=True)

# Nagłówek
st.markdown("""
    <div style="text-align: center; margin-bottom: 20px;">
        <h1 class="main-title">📈 GEM Momentum: USA - EU - EM</h1>
        <p style="color: #888; margin: 0;">Smart Momentum. Safe Haven.</p>
    </div>
    """, unsafe_allow_html=True)

# Biblioteka (płaska lista dla multiselecta)
etf_data = {
    "SXR8.DE": "iShares S&P 500", "SXRV.DE": "iShares Nasdaq 100", "XRS2.DE": "Xtrackers Russell 2000",
    "EXSA.DE": "iShares STOXX 600", "SXRT.DE": "iShares EURO STOXX 50",
    "IS3N.DE": "iShares MSCI EM IMI", "XEON.DE": "Overnight Rate (EUR)", "DBXP.DE": "Govt Bond 1-3y"
}

color_map = {
    "SXR8.DE": "#377EB8", "SXRV.DE": "#4DAF4A", "XRS2.DE": "#FFFF33",
    "EXSA.DE": "#4DBEEE", "SXRT.DE": "#984EA3",
    "IS3N.DE": "#E41A1C", "XEON.DE": "#FF7F00", "DBXP.DE": "#F781BF"
}

# --- SIDEBAR: NOWOCZESNE MENU ---
st.sidebar.header("⚙️ Konfiguracja")

# Wybór instrumentów jako Multiselect (pobiera domyślne z pliku)
selected_tickers = st.sidebar.multiselect(
    "Wybierz instrumenty do analizy:",
    options=list(etf_data.keys()),
    default=st.session_state.user_prefs["tickers"],
    format_func=lambda x: f"{x} ({etf_data[x]})"
)

# Przycisk zapisu "Na stałe"
if st.sidebar.button("Zapisz jako domyślne 💾"):
    # Pobieramy aktualny indeks miesiąca z widgetu (jeśli istnieje)
    m_idx = st.session_state.get('sel_month_idx', 0)
    save_settings(selected_tickers, m_idx)
    st.sidebar.success("Ustawienia zapisane!")

# --- ANALIZA ---
start_date = datetime.now() - timedelta(days=5*365)
all_data = get_data(selected_tickers, start_date) # funkcja get_data musi być w kodzie

if not all_data.empty:
    month_ends = pd.date_range(start=all_data.index.min(), end=all_data.index.max(), freq='ME')
    dates_list = list(month_ends[::-1])
    
    # Wybór miesiąca (pamięta indeks z pliku/sesji)
    selected_month = st.selectbox(
        "Miesiąc końcowy:", 
        options=dates_list, 
        index=st.session_state.user_prefs["month_idx"] if st.session_state.user_prefs["month_idx"] < len(dates_list) else 0,
        format_func=lambda x: x.strftime('%m.%Y'),
        key="sel_month_widget"
    )
    st.session_state.sel_month_idx = dates_list.index(selected_month)

    # ... (reszta kodu obliczeniowego, wykresu i tabeli pozostaje bez zmian) ...
