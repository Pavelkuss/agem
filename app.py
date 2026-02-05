import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="GEM: Asset Selector", layout="wide")

# Inicjalizacja listy wybranych tickerów
if 'selected_assets' not in st.session_state:
    st.session_state.selected_assets = []

st.title("🔍 Krok 1: Wyszukiwarka Aktywów")

# --- SEKCJA WYSZUKIWANIA ---
query = st.text_input("Wpisz nazwę instrumentu lub ticker (np. 'iShares Core', 'SXR8', 'Gold'):", placeholder="Np. Nasdaq 100")

if query:
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}&quotesCount=15"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        quotes = data.get('quotes', [])
        
        if quotes:
            # Budowanie listy danych do tabeli
            search_results = []
            for q in quotes:
                symbol = q.get('symbol')
                # Przeliczanie marketCap na miliardy dla czytelności
                raw_cap = q.get('marketCap', 0)
                cap_display = f"{raw_cap / 1_000_000_000:.2f} B" if raw_cap else "N/A"
                
                search_results.append({
                    "Ticker": symbol,
                    "Nazwa": q.get('longname', 'N/A'),
                    "Giełda": q.get('exchDisp', 'N/A'),
                    "Typ": q.get('quoteType', 'N/A'),
                    "Wielkość (Cap)": cap_display,
                    "Raw_Cap": raw_cap # Ukryta kolumna do sortowania
                })
            
            df_search = pd.DataFrame(search_results)
            
            st.subheader("Wyniki wyszukiwania (Kliknij nagłówek, aby posortować)")
            
            # Wyświetlanie tabeli (interaktywnej)
            # Używamy st.data_editor lub st.dataframe, aby umożliwić sortowanie
            st.dataframe(
                df_search[["Ticker", "Nazwa", "Giełda", "Typ", "Wielkość (Cap)"]],
                use_container_width=True,
                hide_index=True
            )
            
            # --- PANEL DODAWANIA ---
            # Ponieważ st.dataframe nie obsługuje bezpośrednio przycisków w rzędach w sposób prosty,
            # używamy selectboxa do finalnego wyboru z wyników powyżej
            selected_to_add = st.selectbox(
                "Wybierz ticker z tabeli powyżej, aby dodać go do listy:",
                options=df_search["Ticker"].tolist(),
                index=None,
                placeholder="Wybierz ticker..."
            )
            
            if st.button("Dodaj wybrany do listy") and selected_to_add:
                if selected_to_add not in st.session_state.selected_assets:
                    st.session_state.selected_assets.append(selected_to_add)
                    st.success(f"Dodano {selected_to_add}")
                    st.rerun()
                else:
                    st.warning("Już jest na liście.")

        else:
            st.info("Brak wyników.")
    except Exception as e:
        st.error(f"Błąd wyszukiwania: {e}")

st.divider()

# --- TWOJA LISTA ---
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📋 Twoja Lista")
    if st.session_state.selected_assets:
        for asset in st.session_state.selected_assets:
            c_label, c_del = st.columns([4, 1])
            c_label.code(asset)
            if c_del.button("❌", key=f"del_{asset}"):
                st.session_state.selected_assets.remove(asset)
                st.rerun()
    else:
        st.write("Lista pusta.")

with col2:
    st.subheader("⚙️ Akcje")
    if st.session_state.selected_assets:
        if st.button("Wyczyść wszystko"):
            st.session_state.selected_assets = []
            st.rerun()
        
        st.write("")
        if st.button("Zatwierdź i przejdź do danych ➡️"):
            st.session_state.step = 2
            st.balloons()
