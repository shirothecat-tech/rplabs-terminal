import streamlit as st
import requests
import pandas as pd

# CONFIGURASI HALAMAN STREAMLIT
st.set_page_config(
    page_title="RP Labs | Macro Quant Terminal", 
    page_icon="🧪", 
    layout="wide"
)

# TEMA KUSTOM: DARK CHARCOAL & NEON GREEN
st.markdown("""
    <style>
    .main { background-color: #0E1117; }
    h1, h2, h3 { color: #00FF66 !important; font-family: 'Courier New', monospace; }
    .stMetric { background-color: #161B22; padding: 12px; border-radius: 8px; border: 1px solid #30363D; }
    </style>
""", unsafe_allow_html=True)

# URL RAW JSON DARI REPOSITORY GITHUB ANDA
# Ganti USERNAME dan REPO_NAME dengan detail GitHub Anda
GITHUB_JSON_URL = "https://raw.githubusercontent.com/USERNAME/REPO_NAME/main/macro_bias.json"

@st.cache_data(ttl=600)
def load_terminal_data():
    try:
        res = requests.get(GITHUB_JSON_URL)
        return res.json()
    except Exception as e:
        return None

data = load_terminal_data()

# HEADER TERMINAL
st.markdown("""
    <div style="background-color: #161B22; padding: 20px; border-radius: 10px; border-left: 5px solid #00FF66;">
        <h1 style="margin:0;">🧪 RP LABS</h1>
        <h3 style="color: #FFFFFF !important; margin: 4px 0 0 0; font-weight: normal;">Macro Quant Terminal</h3>
        <p style="color: #00E5FF; margin-top: 5px; font-style: italic; font-size: 14px;">
            "In the financial jungle, RP Labs brings absolute clarity."
        </p>
    </div>
""", unsafe_allow_html=True)

st.write("")

if data is None:
    st.warning("⚠️ Menghubungkan ke server data RP Labs... Pastikan URL Raw JSON di GitHub sudah benar.")
else:
    st.caption(f"⏱️ Last Auto-Updated: {data['last_updated']}")
    st.divider()

    # TABULAR NAVIGATION
    tab1, tab2 = st.tabs(["🏆 XAU/USD (Gold) Real Yield Engine", "📊 Currency & Inflation Bias Matrix"])

    # TAB 1: GOLD REAL YIELD
    with tab1:
        st.subheader("10-Year Real Yield Analysis (XAU/USD)")
        gold = data['gold_engine']
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("10Y UST Real Yield", f"{gold['real_yield_10y']}%")
        with c2:
            st.metric("Real Yield Z-Score (20D)", f"{gold['z_score_20d']}")
        with c3:
            st.metric("Macro Directional Bias", gold['directional_bias'])

        st.info(f"💡 **Quant Insight:** Probabilitas Koreksi / Konsolidasi Harga: **{gold['prob_price_correction']*100:.0f}%**. {gold['summary_note']}")

    # TAB 2: CURRENCY INFLATION PROBABILITIES
    with tab2:
        st.subheader("Leading Indicators vs Central Bank Policy Bias")
        
        currencies = data['currency_matrix']
        df_curr = pd.DataFrame.from_dict(currencies, orient='index')
        df_curr.columns = ["Leading Indicator", "Prob. CPI > Consensus", "Central Bank Stance", "Pair Directional Bias"]
        
        # Format kolom probabilitas menjadi persen
        df_curr["Prob. CPI > Consensus"] = df_curr["Prob. CPI > Consensus"].apply(lambda x: f"{x*100:.0f}%")
        
        st.dataframe(df_curr, use_container_width=True)

st.divider()
st.caption("© 2026 RimbaPips Labs (RP Labs). Designed for quantitative market research and educational purpose.")