import json
import os
import requests
import pandas as pd
import streamlit as st

# CONFIGURASI HALAMAN STREAMLIT
st.set_page_config(
    page_title="RP Labs | Macro Quant Terminal", page_icon="🧪", layout="wide"
)

# TEMA KUSTOM: DARK CHARCOAL & NEON GREEN
st.markdown(
    """
    <style>
    .main { background-color: #0E1117; }
    h1, h2, h3 { color: #00FF66 !important; font-family: 'Courier New', monospace; }
    .stMetric { background-color: #161B22; padding: 12px; border-radius: 8px; border: 1px solid #30363D; }
    </style>
""",
    unsafe_allow_html=True,
)

# URL RAW JSON DI GITHUB (Untuk nanti jika sudah di-deploy)
GITHUB_JSON_URL = (
    "https://raw.githubusercontent.com/USERNAME/REPO_NAME/main/macro_bias.json"
)


@st.cache_data(ttl=10)  # Refresh cepat saat pengujian lokal
def load_terminal_data():
  # 1. Cek apakah file lokal macro_bias.json ada di folder
  if os.path.exists("macro_bias.json"):
    try:
      with open("macro_bias.json", "r") as f:
        return json.load(f)
    except Exception as e:
      pass

  # 2. Jika file lokal tidak ada, coba ambil dari GitHub URL
  try:
    res = requests.get(GITHUB_JSON_URL, timeout=5)
    if res.status_code == 200:
      return res.json()
  except Exception as e:
    pass

  return None


data = load_terminal_data()

# HEADER TERMINAL
st.markdown(
    """
    <div style="background-color: #161B22; padding: 20px; border-radius: 10px; border-left: 5px solid #00FF66;">
        <h1 style="margin:0;">🧪 RP LABS</h1>
        <h3 style="color: #FFFFFF !important; margin: 4px 0 0 0; font-weight: normal;">Macro Quant Terminal</h3>
        <p style="color: #00E5FF; margin-top: 5px; font-style: italic; font-size: 14px;">
            "In the financial jungle, RP Labs brings absolute clarity."
        </p>
    </div>
""",
    unsafe_allow_html=True,
)

st.write("")

if data is None:
  st.warning(
      "⚠️ File 'macro_bias.json' belum ditemukan. Pastikan Anda sudah menjalankan"
      " 'python generate_macro_data.py' terlebih dahulu di folder yang sama."
  )
else:
  st.caption(f"⏱️ Last Auto-Updated: {data.get('last_updated', 'N/A')}")
  st.divider()

  # TABULAR NAVIGATION
  tab1, tab2 = st.tabs([
      "🏆 XAU/USD (Gold) Real Yield Engine",
      "📊 Currency & Inflation Bias Matrix",
  ])

  # TAB 1: GOLD REAL YIELD
  with tab1:
    st.subheader("10-Year Real Yield Analysis (XAU/USD)")
    gold = data.get("gold_real_yield_engine", {})

    c1, c2, c3 = st.columns(3)
    with c1:
      st.metric("10Y UST Real Yield", f"{gold.get('us_10y_real_rate', 0)}%")
    with c2:
      st.metric("Real Yield Z-Score (20D)", f"{gold.get('z_score_20d', 0)}")
    with c3:
      st.metric("Macro Directional Bias", gold.get("macro_strength", "N/A"))

    st.info(f"💡 **Quant Insight:** {gold.get('interpretation', '')}")

  # TAB 2: CURRENCY INFLATION PROBABILITIES
  with tab2:
    st.subheader("Leading Indicators vs Central Bank Policy Bias")

    currencies = data.get("currency_probabilities", {})
    if currencies:
      df_curr = pd.DataFrame.from_dict(currencies, orient="index")
      df_curr.columns = [
          "Leading Indicator",
          "Prob. CPI > Consensus",
          "Central Bank Stance",
          "Pair Directional Bias",
      ]

      # Format kolom probabilitas menjadi persen
      df_curr["Prob. CPI > Consensus"] = df_curr[
          "Prob. CPI > Consensus"
      ].apply(lambda x: f"{x*100:.0f}%" if isinstance(x, (int, float)) else x)

      st.dataframe(df_curr, use_container_width=True)

st.divider()
st.caption(
    "© 2026 RimbaPips Labs (RP Labs). Designed for quantitative market research"
    " and educational purpose."
)