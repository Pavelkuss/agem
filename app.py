import streamlit as st
import yfinance as yf
import pandas as pd
import requests

st.set_page_config(page_title="GEM: Asset Selector", layout="wide")

if 'selected_assets' not in st.session_state:
    st.session_state.selected_assets = []

st.title("🔍 Krok 1: Wyszukiwarka z danymi o wielkości funduszu")

query = st.text_input("Wpisz nazwę lub ticker (np. 'iShares S&P 500', 'Xtrackers'):")

if query:
    # 1. Szukanie tickerów przez API Yahoo
    search_url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}&quotesCount=10"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        resp = requests.get(search_url, headers=headers).json()
        quotes = resp.get('quotes', [])
        
        if quotes:
            results_data = []
            
            # Pobieramy same tickery, aby jednym zapytaniem wyciągnąć detale
            tickers_found = [q['symbol'] for q in quotes]
            
            # 2. Pobieranie detali (Wielkość funduszu) przez yfinance
            # Używamy st.spinner, bo to może zająć chwilę
            with st.spinner('Pobieram szczegóły funduszy...'):
                for q in quotes:
                    sym = q['symbol']
                    t_info = yf.Ticker(sym).info
                    
                    # Dla ETF wielkość jest w 'totalAssets', dla akcji w 'marketCap'
                    size = t_info.get('totalAssets') or t_info.get('marketCap') or 0
                    
                    results_data.append({
                        "Ticker": sym,
                        "Nazwa": q.get('longname', 'N/A'),
                        "Giełda": q.get('exchDisp', 'N/A'),
                        "Typ": q.get('quoteType', 'N/A'),
                        "Wielkość (Mld EUR/USD)": round(size / 1_000_000_000, 2) if size else 0,
                        "Waluta": t_info.get('currency', 'N/A')
                    })
            
            df_search = pd.DataFrame(results_data)
            
            # Sortowanie domyślne po wielkości
            df_search = df_search.sort_values(by="Wielkość (Mld EUR/USD)", ascending=False)
            
            st.subheader("Wyniki wyszukiwania")
            st.dataframe(
                df_search,
                use_container_width=True,
                hide_index=True
            )
            
            # Dodawanie do listy
            to_add = st.selectbox("Wybierz ticker do dodania:", df_search["Ticker"])
            if st.button("Dodaj do mojej strategii"):
                if to_add not in st.session_state.selected_assets:
                    st.session_state.selected_assets.append(to_add)
                    st.success(f"Dodano {to_add}")
                    st.rerun()

    except Exception as e:
        st.error(f"Błąd: {e}")

st.divider()
# Sekcja Twojej Listy (pozostaje bez zmian)
st.subheader("📋 Twoja Lista")
for asset in st.session_state.selected_assets:
    c1, c2 = st.columns([5, 1])
    c1.code(asset)
    if c2.button("Usuń", key=f"del_{asset}"):
        st.session_state.selected_assets.remove(asset)
        st.rerun()
