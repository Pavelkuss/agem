import streamlit as st
import requests
import pandas as pd

# Ustawienia strony
st.set_page_config(page_title="GEM Builder: Krok 1", layout="wide")

# Inicjalizacja pamięci sesji dla wybranych tickerów
if 'selected_assets' not in st.session_state:
    st.session_state.selected_assets = []

st.title("🔍 Krok 1: Budowanie bazy aktywów")
st.markdown("""
Wyszukaj ETF-y i ETC, które będą bazą Twojej strategii. 
Jako rezydent w Holandii, szukaj najlepiej tickerów z końcówką **.DE** (Xetra) lub **.AS** (Amsterdam).
""")

# --- INTERFEJS WYSZUKIWANIA ---
col_search, col_list = st.columns([1, 1])

with col_search:
    st.subheader("Wyszukiwarka Yahoo Finance")
    query = st.text_input("Wpisz nazwę lub ticker (np. 'iShares', 'SXR8', 'Gold'):")
    
    if query:
        # API Autocomplete od Yahoo
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}&quotesCount=10"
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        try:
            response = requests.get(url, headers=headers)
            data = response.json()
            quotes = data.get('quotes', [])
            
            if quotes:
                # Przygotowanie wyników w tabeli
                for q in quotes:
                    symbol = q.get('symbol')
                    name = q.get('longname', 'Brak nazwy')
                    exch = q.get('exchDisp', 'Brak giełdy')
                    type_ = q.get('quoteType', 'Unknown')
                    
                    with st.expander(f"➕ {symbol} | {name}"):
                        st.write(f"**Giełda:** {exch} | **Typ:** {type_}")
                        if st.button(f"Dodaj {symbol} do listy", key=f"btn_{symbol}"):
                            if symbol not in st.session_state.selected_assets:
                                st.session_state.selected_assets.append(symbol)
                                st.rerun()
            else:
                st.info("Brak wyników dla tej frazy.")
        except Exception as e:
            st.error(f"Problem z połączeniem: {e}")

with col_list:
    st.subheader("📋 Twoja wybrana lista")
    if not st.session_state.selected_assets:
        st.info("Twoja lista jest pusta. Dodaj aktywa po lewej stronie.")
    else:
        for asset in st.session_state.selected_assets:
            c1, c2 = st.columns([4, 1])
            with c1:
                st.code(asset)
            with c2:
                if st.button("❌", key=f"del_{asset}"):
                    st.session_state.selected_assets.remove(asset)
                    st.rerun()
        
        if len(st.session_state.selected_assets) > 1:
            st.success(f"Masz {len(st.session_state.selected_assets)} aktywów. Możemy przejść do pobierania danych.")
            if st.button("Zapisz i przejdź dalej ➡️"):
                st.session_state.step = 2 # Przygotowanie pod kolejny klocek
