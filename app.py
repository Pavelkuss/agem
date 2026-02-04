import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd

# --- 1. KONFIGURACJA STRONY (Musi być pierwsza) ---
st.set_page_config(page_title="GEM Strategy", layout="wide", initial_sidebar_state="collapsed")

# --- 2. CSS: "MOBILE FIRST" LAYOUT ---
st.markdown("""
    <style>
    /* Ukrycie domyślnego nagłówka i stopki Streamlit */
    #MainMenu, header, footer {visibility: hidden;}
    .block-container { padding-top: 1rem; padding-bottom: 2rem; }

    /* --- KLUCZ DO SUKCESU: WYMUSZENIE POZIOMU NAWIGACJI --- */
    /* Celujemy w pierwszy poziomy blok (gdzie są przyciski) i zabraniamy mu się łamać */
    [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important; /* Zawsze rząd, nigdy kolumna */
        flex-wrap: nowrap !important;   /* Nigdy nie zawijaj */
        align-items: center !important;
        gap: 5px !important;
    }

    /* Ustawienia kolumn w nawigacji: [ - ] [ DATA ] [ + ] */
    /* Kolumny skrajne (przyciski) - stała szerokość */
    [data-testid="column"]:nth-of-type(1), 
    [data-testid="column"]:nth-of-type(3) {
        flex: 0 0 50px !important; /* Sztywna szerokość 50px */
        min-width: 50px !important;
    }
    /* Kolumna środkowa (Data) - zajmuje resztę */
    [data-testid="column"]:nth-of-type(2) {
        flex: 1 1 auto !important;
        min-width: 100px !important;
    }

    /* Styl przycisków nawigacyjnych */
    .stButton button {
        width: 100% !important;
        height: 45px !important; /* Wysokie, wygodne pod kciuk */
        font-size: 20px !important;
        padding: 0px !important;
        line-height: 1 !important;
        border-radius: 8px !important;
        background-color: #262730 !important;
        border: 1px solid #444 !important;
    }

    /* Blokada klawiatury w polu daty i stylizacja */
    div[data-baseweb="select"] { width: 100%; }
    div[data-baseweb="select"] input { pointer-events: none !important; } /* Tylko wybór, brak pisania */
    
    /* Stylizacja tabeli */
    .custom-table { width: 100%; border-collapse: collapse; font-size: 11px; color: #ddd; }
    .custom-table th { background-color: #262730; padding: 8px 2px; border-bottom: 2px solid #555; }
    .custom-table td { padding: 8px 2px; border-bottom: 1px solid #333; text-align: center; }
    
    </style>
    """, unsafe_allow_html=True)

# --- 3. DANE I LOGIKA ---
@st.cache_data(ttl=86400)
def get_dates():
    try:
        df = yf.download("SXR8.DE", period="5y", progress=False, multi_level_index=False)
        return list(pd.date_range(start=df.index.min(), end=df.index.max(), freq='ME')[::-1])
    except:
        return [datetime.now().replace(day=1) - timedelta(days=i*30) for i in range(60)]

dates_list = get_dates()
if 'date_idx' not in st.session_state:
    st.session_state.date_idx = 0

# --- 4. MENU BOCZNE (SIDEBAR) ---
# To jest Twoje menu konfiguracji. Dostępne pod strzałką w lewym górnym rogu.
with st.sidebar:
    st.header("⚙️ Konfiguracja")
    st.write("Wybierz fundusze do analizy:")
    
    etf_data = {
        "SXR8.DE": "S&P 500", "SXRV.DE": "Nasdaq 100", "XRS2.DE": "Russell 2000",
        "EXSA.DE": "Stoxx 600", "SXRT.DE": "Euro Stoxx 50", "IS3N.DE": "MSCI EM",
        "XEON.DE": "Gotówka (XEON)", "DBXP.DE": "Obligacje 1-3Y"
    }
    color_map = {
        "SXR8.DE": "#377EB8", "SXRV.DE": "#4DAF4A", "XRS2.DE": "#FFFF33",
        "EXSA.DE": "#4DBEEE", "SXRT.DE": "#984EA3", "IS3N.DE": "#E41A1C",
        "XEON.DE": "#FF7F00", "DBXP.DE": "#F781BF"
    }
    
    # Pobieranie z URL lub domyślne
    params = st.query_params.to_dict()
    current_tickers = params.get("t", "SXR8.DE,EXSA.DE,IS3N.DE,XEON.DE").split(",")
    
    selected_tickers = []
    for t, label in etf_data.items():
        if st.checkbox(f"{label} ({t})", value=(t in current_tickers)):
            selected_tickers.append(t)
            
    if st.button("Zapisz zmiany", type="primary"):
        st.query_params["t"] = ",".join(selected_tickers)
        st.rerun()

# --- 5. GŁÓWNA NAWIGACJA (TO CO NIE DZIAŁAŁO) ---
# Układ: [ < ] [ DATA ] [ > ]
c_prev, c_date, c_next = st.columns([1, 4, 1])

with c_prev:
    if st.button("◀", key="btn_prev"):
        if st.session_state.date_idx < len(dates_list) - 1:
            st.session_state.date_idx += 1
            st.rerun()

with c_date:
    selected_month = st.selectbox(
        "Wybierz datę", 
        options=dates_list, 
        index=st.session_state.date_idx,
        format_func=lambda x: x.strftime('%B %Y'), # Np. Grudzień 2024
        label_visibility="collapsed"
    )
    # Aktualizacja indeksu jeśli użytkownik wybierze z listy
    if dates_list.index(selected_month) != st.session_state.date_idx:
        st.session_state.date_idx = dates_list.index(selected_month)
        st.rerun()

with c_next:
    if st.button("▶", key="btn_next"):
        if st.session_state.date_idx > 0:
            st.session_state.date_idx -= 1
            st.rerun()

# --- 6. ANALIZA I WYKRESY ---
# Jeśli nie ma wybranych tickerów
if not selected_tickers:
    selected_tickers = ["SXR8.DE", "XEON.DE"] # Fallback

@st.cache_data(ttl=3600)
def fetch_data(tickers):
    if not tickers: return pd.DataFrame()
    data = yf.download(tickers, start=datetime.now()-timedelta(days=5*365), progress=False, multi_level_index=False)['Close']
    return data.dropna()

prices = fetch_data(selected_tickers)

if not prices.empty:
    target_dt = pd.Timestamp(selected_month)
    actual_end = prices.index[prices.index <= target_dt][-1]
    window = prices.loc[actual_end - timedelta(days=365):actual_end]
    
    # Obliczanie wyników
    perf = []
    for t in selected_tickers:
        if t in window.columns:
            r = ((window[t].iloc[-1] / window[t].iloc[0]) - 1) * 100
            perf.append({'t': t, 'r': r, 'series': window[t]})
    
    perf = sorted(perf, key=lambda x: x['r'], reverse=True)
    best = perf[0]
    
    # Karta Sygnału (Wizualnie oddzielona)
    xeon_res = next((x['r'] for x in perf if x['t'] == "XEON.DE"), -99)
    
    st.markdown("---")
    if best['t'] == "XEON.DE" or best['r'] < xeon_res:
         st.error(f"🛡️ SYGNAŁ: **GOTÓWKA (XEON)**")
    else:
         st.success(f"🚀 SYGNAŁ: **{best['t']}** ({best['r']:+.2f}%)")
    
    # Wykres
    fig = go.Figure()
    for p in perf:
        norm = ((p['series'] / p['series'].iloc[0]) - 1) * 100
        fig.add_trace(go.Scatter(
            x=norm.index, y=norm, name=p['t'], 
            line=dict(width=2, color=color_map.get(p['t'], "#888"))
        ))
    fig.update_layout(
        template="plotly_dark", 
        height=250, 
        margin=dict(l=0, r=0, t=20, b=0),
        legend=dict(orientation="h", y=1.1, font=dict(size=10)),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="#333"),
        hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    # Tabela w stylu mobilnym (tylko 4 ostatnie miesiące + aktualny)
    st.markdown("#### 📅 Historia Sygnałów")
    
    history_months = dates_list[st.session_state.date_idx : st.session_state.date_idx + 5][::-1]
    
    html = "<table class='custom-table'><thead><tr><th>#</th>"
    for m in history_months: html += f"<th>{m.strftime('%m/%y')}</th>"
    html += "</tr></thead><tbody>"
    
    # Pokazujemy tylko TOP 5 instrumentów, żeby tabela nie była za długa
    for i in range(min(len(selected_tickers), 5)):
        html += f"<tr><td>{i+1}</td>"
        for m in history_months:
            try:
                m_end = prices.index[prices.index <= m][-1]
                m_win = prices.loc[m_end-timedelta(days=365):m_end]
                ranks = sorted([(t, ((m_win[t].iloc[-1]/m_win[t].iloc[0])-1)*100) for t in selected_tickers], key=lambda x: x[1], reverse=True)
                
                curr_t, curr_r = ranks[i]
                color = color_map.get(curr_t, "#ddd")
                # Pogrubienie tylko dla lidera (i=0)
                weight = "bold" if i == 0 else "normal"
                
                html += f"<td style='color:{color}; font-weight:{weight}'>{curr_t}<br><span style='font-size:9px; color:#aaa'>{curr_r:+.1f}%</span></td>"
            except: html += "<td>-</td>"
        html += "</tr>"
    st.write(html + "</tbody></table>", unsafe_allow_html=True)

else:
    st.info("Otwórz menu (↖) i wybierz fundusze, aby rozpocząć.")
