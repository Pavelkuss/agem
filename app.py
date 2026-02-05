import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="GEM: Kreator Listy", layout="wide")

# Inicjalizacja listy wybranych aktywów w sesji (żeby nie znikała po odświeżeniu)
if 'selected_assets' not in st.session_state:
    st.session_state.selected_assets = []

st.title("🔍 Kreator Listy ETF/ETC")
st.markdown("Wyszukaj instrumenty na Yahoo Finance i dodaj je do swojej bazy do obliczeń.")

# --- SEKCJA WYSZUKIWANIA ---
query = st.text_input("Wpisz nazwę (np. 'S&P 500', 'Nasdaq', 'Gold') lub ticker:", "")
search_button = st.button("Szukaj")

if search_button and query:
    # API Yahoo Finance Autocomplete
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}&quotesCount=10"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        quotes = data.get('quotes', [])
        
        if not quotes:
            st.warning("Nie znaleziono pasujących instrumentów.")
        else:
            # Filtrowanie tylko dla ETF/ETC i giełd europejskich (opcjonalnie, pokazujemy wszystko do wyboru)
            results = []
            for q in quotes:
                # Interesują nas głównie ETF (Equity) i giełdy z kropką (np. .DE, .AS)
                results.append({
                    "Symbol": q.get('symbol'),
                    "Nazwa": q.get('longname'),
                    "Giełda": q.get('exchDisp'),
                    "Typ": q.get('quoteType')
                })
            
            df_results = pd.DataFrame(results)
            
            st.subheader("Wyniki wyszukiwania:")
            
            # Tworzymy tabelę z przyciskami
            for index, row in df_results.iterrows():
                col1, col2, col3, col4 = st.columns([2, 5, 2, 2])
                with col1:
                    st.write(f"**{row['Symbol']}**")
                with col2:
                    st.write(row['Nazwa'])
                with col3:
                    st.write(row['Giełda'])
                with col4:
                    if st.button("Dodaj", key=f"add_{row['Symbol']}"):
                        if row['Symbol'] not in st.session_state.selected_assets:
                            st.session_state.selected_assets.append(row['Symbol'])
                            st.success(f"Dodano {row['Symbol']}")
                        else:
                            st.info("Ten symbol jest już na liście.")
                            
    except Exception as e:
        st.error(f"Błąd podczas wyszukiwania: {e}")

st.divider()

# --- SEKCJA TWOJEJ LISTY ---
st.subheader("📋 Twoja Lista do Obliczeń")

if st.session_state.selected_assets:
    # Wyświetlamy aktualną listę z możliwością usuwania
    for asset in st.session_state.selected_assets:
        c1, c2 = st.columns([8, 2])
        with c1:
            st.info(asset)
        with c2:
            if st.button("Usuń", key=f"remove_{asset}"):
                st.session_state.selected_assets.remove(asset)
                st.rerun()
    
    st.write("---")
    if st.button("Zatwierdź listę i przejdź do danych"):
        st.success("Lista gotowa! Tickers: " + ", ".join(st.session_state.selected_assets))
        # Tutaj w przyszłości dodamy przejście do Klocka 2
else:
    st.write("Twoja lista jest pusta. Użyj wyszukiwarki powyżej.")
