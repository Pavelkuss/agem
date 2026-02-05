import streamlit as st
import yfinance as yf
import pandas as pd
import requests

st.set_page_config(page_title="GEM: Asset Selector v2", layout="wide")

if 'selected_assets' not in st.session_state:
    st.session_state.selected_assets = []

st.title("🔍 Krok 1: Wyszukiwarka (Zoptymalizowana)")

query = st.text_input("Wpisz nazwę, ticker lub ISIN:")

if query:
    # 1. Szybkie wyszukiwanie nazw i tickerów (lekkie zapytanie)
    search_url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}&quotesCount=15"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        resp = requests.get(search_url, headers=headers).json()
        quotes = resp.get('quotes', [])
        
        if quotes:
            # Tworzymy czystą tabelę wyników bez ciężkich zapytań o AUM
            results_list = []
            for q in quotes:
                results_list.append({
                    "Ticker": q.get('symbol'),
                    "Nazwa": q.get('longname', 'N/A'),
                    "Giełda": q.get('exchDisp', 'N/A'),
                    "Typ": q.get('quoteType', 'N/A')
                })
            
            df_search = pd.DataFrame(results_list)
            st.subheader("Wyniki wyszukiwania")
            st.dataframe(df_search, use_container_width=True, hide_index=True)

            # 2. SEKCJA SZCZEGÓŁÓW (Tylko dla jednego, wybranego tickera)
            st.divider()
            col_a, col_b = st.columns([2, 1])
            
            with col_a:
                to_inspect = st.selectbox("Wybierz ticker, aby sprawdzić detale i dodać:", df_search["Ticker"])
            
            if to_inspect:
                # Pobieramy info TYLKO dla tego jednego wybranego instrumentu
                with st.spinner(f'Pobieram dane dla {to_inspect}...'):
                    t = yf.Ticker(to_inspect)
                    info = t.info
                    
                    # Logika wyciągania wielkości (AUM)
                    aum = info.get('totalAssets') or info.get('marketCap') or 0
                    currency = info.get('currency', '???')
                    
                    st.write(f"### Detale dla {to_inspect}:")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Wielkość funduszu", f"{aum/1e9:.2f} B {currency}" if aum else "Brak danych")
                    c2.metric("Waluta funduszu", currency)
                    c3.metric("Giełda", info.get('exchange', 'N/A'))

                if st.button(f"Dodaj {to_inspect} do strategii"):
                    if to_inspect not in st.session_state.selected_assets:
                        st.session_state.selected_assets.append(to_inspect)
                        st.success(f"Dodano {to_inspect}")
                        st.rerun()

    except Exception as e:
        st.error(f"Błąd wyszukiwania: {e}")

# --- TWOJA LISTA ---
st.divider()
st.subheader("📋 Twoja Lista")
if st.session_state.selected_assets:
    for asset in st.session_state.selected_assets:
        c1, c2 = st.columns([5, 1])
        c1.code(asset)
        if c2.button("Usuń", key=f"del_{asset}"):
            st.session_state.selected_assets.remove(asset)
            st.rerun()
