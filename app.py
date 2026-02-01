import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd
from streamlit_local_storage import LocalStorage

# --- KONFIGURACJA ---
st.set_page_config(page_title="Advanced GEM Strategy", layout="wide")
localS = LocalStorage()

# --- CSS ---
st.markdown("""
    <style>
    .stPlotlyChart { pointer-events: none; }
    .custom-table { width: 100%; border-collapse: collapse; font-size: 10px; color: white; table-layout: fixed; }
    .custom-table th { border-bottom: 2px solid #444; padding: 4px 1px; text-align: center; background-color: #1E1E1E; }
    .custom-table td { border-bottom: 1px solid #333; padding: 4px 0px; text-align: center; line-height: 1.2; }
    .col-rank { width: 22px; color: #888; font-weight: bold; }
    .block-container { padding-top: 1rem; padding-bottom: 1rem; }
    #MainMenu, footer, header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- BIBLIOTEKA ---
etf_data = {
    "SXR8.DE": "iShares S&P 500", "SXRV.DE": "iShares Nasdaq 100", "XRS2.DE": "Xtrackers Russell 2000",
    "EXSA.DE": "iShares STOXX 600", "SXRT.DE": "iShares EURO STOXX 50",
    "IS3N.DE": "iShares MSCI EM IMI", "XEON.DE": "Overnight Rate (EUR)", "DBXP.DE": "Govt Bond 1-3y"
}
color_map = {
    "SXR8.DE": "#377EB8", "SXRV.DE": "#4DAF4A", "XRS2.DE": "#FFFF33",
    "EXSA.DE": "#4DBEEE", "SXRT.DE": "#984EA3", "IS3N.DE": "#E41A1C", "XEON.DE": "#FF7F00", "DBXP.DE": "#F781BF"
}

# --- LOGO ---
col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
with col_l2:
    try: st.image("agemlogo.png", use_container_width=True)
    except: st.title("Advanced GEM")

# --- ZARZĄDZANIE PAMIĘCIĄ (Local Storage) ---
# Pobieramy zapisane dane przy starcie
saved_data = localS.getItem("gem_portfolio")
default_selection = ["SXR8.DE", "EXSA.DE", "IS3N.DE", "XEON.DE"]

if saved_data:
    # saved_data to string, musimy go zamienić na listę
    default_selection = saved_data.split(",")

# --- INTERFEJS WYBORU ---
with st.expander("⚙️ Ustawienia portfela"):
    selected_tickers = st.multiselect(
        "Twoje instrumenty:", 
        options=list(etf_data.keys()), 
        default=default_selection,
        format_func=lambda x: f"{x} ({etf_data[x]})"
    )

    if st.button("Zapisz w pamięci urządzenia 💾"):
        localS.setItem("gem_portfolio", ",".join(selected_tickers))
        st.success("Zapisano! Ustawienia zostaną zachowane w tej przeglądarce.")
        st.rerun()

# --- ANALIZA I POBIERANIE ---
@st.cache_data(ttl=3600)
def get_data(tickers, start):
    if not tickers: return pd.DataFrame()
    combined = pd.DataFrame()
    for t in tickers:
        try:
            df = yf.download(t, start=start, progress=False, multi_level_index=False)
            if not df.empty: combined[t] = df['Close']
        except: continue
    return combined.dropna()

all_data = get_data(selected_tickers, datetime.now() - timedelta(days=5*365))

if not all_data.empty:
    month_ends = pd.date_range(start=all_data.index.min(), end=all_data.index.max(), freq='ME')
    dates_list = list(month_ends[::-1])
    selected_month = st.selectbox("Miesiąc końcowy:", options=dates_list, format_func=lambda x: x.strftime('%m.%Y'))
    
    actual_end = all_data.index[all_data.index <= pd.Timestamp(selected_month)][-1]
    window = all_data.loc[actual_end - timedelta(days=365):actual_end]
    
    perf = sorted([{'ticker': t, 'return': ((window[t].iloc[-1]/window[t].iloc[0])-1)*100, 'series': window[t]} 
                   for t in selected_tickers if t in window.columns], key=lambda x: x['return'], reverse=True)

    # SYGNAŁ
    best = perf[0]
    xeon_ret = next((x['return'] for x in perf if x['ticker'] == "XEON.DE"), -999.0)
    if (best['ticker'] == "XEON.DE" or best['return'] < xeon_ret):
        st.error(f"🚨 SYGNAŁ: GOTÓWKA (XEON)")
    else:
        st.success(f"🚀 SYGNAŁ: {best['ticker']} ({best['return']:+.2f}%)")

    # --- WYKRES ---
    fig = go.Figure()
    for item in perf:
        fig.add_trace(go.Scatter(x=item['series'].index, y=((item['series']/item['series'].iloc[0])-1)*100, 
                                 name=f"{item['ticker']} ({item['return']:+.1f}%)", 
                                 line=dict(width=2, color=color_map.get(item['ticker']))))
    fig.update_layout(template="plotly_dark", height=280, margin=dict(l=5, r=5, t=10, b=0),
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(size=9)),
                      xaxis=dict(fixedrange=True, showgrid=False), yaxis=dict(fixedrange=True, ticksuffix="%"), hovermode=False)
    st.plotly_chart(fig, use_container_width=True, config={'staticPlot': True, 'displayModeBar': False})

    # --- TABELA ---
    st.markdown("---")
    curr_idx = dates_list.index(selected_month)
    display_months = dates_list[curr_idx:curr_idx+5][::-1] 
    rank_history = []
    for m in display_months:
        m_e = all_data.index[all_data.index <= m][-1]
        m_w = all_data.loc[m_e - timedelta(days=365):m_e]
        r = sorted([(t, ((m_w[t].iloc[-1]/m_w[t].iloc[0])-1)*100) for t in selected_tickers], key=lambda x: x[1], reverse=True)
        rank_history.append({'date': m.strftime('%m/%y'), 'ranks': {x[0]: i+1 for i, x in enumerate(r)}, 'data': r})

    html = "<table class='custom-table'><tr><th class='col-rank'>#</th>"
    for rh in rank_history: html += f"<th>{rh['date']}</th>"
    html += "</tr>"
    for i in range(len(selected_tickers)):
        html += f"<tr><td class='col-rank'>#{i+1}</td>"
        for j in range(len(rank_history)):
            if i < len(rank_history[j]['data']):
                curr_t, curr_v = rank_history[j]['data'][i]
                t_color = color_map.get(curr_t, "white")
                trend_color = "white"; icon = ""
                if j > 0:
                    old_pos = rank_history[j-1]['ranks'].get(curr_t, 99)
                    if i+1 < old_pos: trend_color = "#00ff00"; icon = "↑"
                    elif i+1 > old_pos: trend_color = "#ff4b4b"; icon = "↓"
                html += f"<td><b style='color: {t_color};'>{curr_t}</b><br><span style='color: {trend_color};'>{curr_v:+.1f}%{icon}</span></td>"
            else: html += "<td>-</td>"
        html += "</tr>"
    st.write(html + "</table>", unsafe_allow_html=True)

    # --- STOPKA ---
    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2 = st.columns([1, 4])
    c1.image("https://s.yimg.com/rz/p/yahoo_finance_en-US_h_p_finance_2.png", width=80)
    c2.markdown("<p style='font-size: 9px; color: #777; margin-top:10px;'>Dane: Yahoo Finance. Pamiętaj o weryfikacji sygnałów.</p>", unsafe_allow_html=True)
else:
    st.info("Dodaj instrumenty w ustawieniach.")
