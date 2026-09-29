from datetime import datetime
import json
import numpy as np
import pandas as pd
import requests
import os

# Membaca dari environment variable (GitHub Secrets) atau fallback ke string jika dites lokal
FRED_API_KEY = os.environ.get("FRED_API_KEY", "77dd5415d0e40b020f478650246f561e")

def get_fred_series(series_id, api_key):
  url = "https://api.stlouisfed.org/fred/series/observations"
  params = {
      "series_id": series_id,
      "api_key": api_key,
      "file_type": "json",
      "sort_order": "desc",
      "limit": 24,  # Ambil 24 periode bulanan
  }
  try:
    res = requests.get(url, params=params, timeout=10)
    if res.status_code == 200:
      data = res.json()["observations"]
      df = pd.DataFrame(data)[["date", "value"]]
      df["value"] = pd.to_numeric(df["value"], errors="coerce")
      df = df.dropna().sort_values("date").reset_index(drop=True)
      return df["value"]
    return None
  except Exception:
    return None


def calculate_calibrated_inflation_probability(series):
  """Menghitung Z-Score laju pertumbuhan (pct_change) indikator terhadap histori

  12 bulan, lalu dikonversi ke probabilitas Sigmoid.
  """
  if series is None or len(series) < 13:
    return 0.50

  # Hitung perubahan bulanan (MoM percentage change)
  pct_change = series.pct_change().dropna()

  latest_change = pct_change.iloc[-1]
  mean_change = pct_change.tail(12).mean()
  std_change = pct_change.tail(12).std()

  if std_change == 0 or np.isnan(std_change):
    return 0.50

  # Z-score dari laju pertumbuhan terbaru terhadap tren 12 bulan
  z = (latest_change - mean_change) / std_change

  # Konversi ke Sigmoid Probability [0.0 - 1.0]
  prob = 1 / (1 + np.exp(-z))
  return round(float(prob), 2)


def generate_rplabs_data():
  print(">>> [RP LABS] Recalibrating Logistic Inflation Probabilities...")

  # 1. GOLD REAL YIELD ENGINE
  s_real_rate = get_fred_series("DFII10", FRED_API_KEY)
  if s_real_rate is not None and len(s_real_rate) > 0:
    latest_rr = float(s_real_rate.iloc[-1])
    ma20 = float(s_real_rate.tail(20).mean())
    std20 = float(s_real_rate.tail(20).std())
    z_rr = (latest_rr - ma20) / (std20 + 1e-6)
  else:
    latest_rr, z_rr = 1.85, 0.0

  gold_bias = (
      "BULLISH" if latest_rr < 1.5 else ("BEARISH" if latest_rr > 2.5 else "NEUTRAL")
  )

  # 2. CALIBRATED LOGISTIC PROBABILITIES FOR FOREX (G7)
  p_jpy = calculate_calibrated_inflation_probability(
      get_fred_series("JPNCPIALLMINMEI", FRED_API_KEY)
  )
  p_eur = calculate_calibrated_inflation_probability(
      get_fred_series("DEUPPIALLMINMEI", FRED_API_KEY)
  )
  p_gbp = calculate_calibrated_inflation_probability(
      get_fred_series("GBRPPIALLMINMEI", FRED_API_KEY)
  )
  p_usd = calculate_calibrated_inflation_probability(
      get_fred_series("NAPMPI", FRED_API_KEY)
  )

  def get_stance_and_bias(prob, pair_base):
    if prob >= 0.60:
      return "Hawkish / Tightening Risk", f"{pair_base} Bullish"
    elif prob <= 0.40:
      return "Dovish / Easing Expectations", f"{pair_base} Bearish"
    else:
      return "Neutral / Policy Hold", f"{pair_base} Rangebound"

  stance_gbp, bias_gbp = get_stance_and_bias(p_gbp, "GBP/USD")
  stance_eur, bias_eur = get_stance_and_bias(p_eur, "EUR/USD")
  stance_usd, bias_usd = get_stance_and_bias(p_usd, "DXY")
  # --- JPY LOGIC (Inverted Citation for USD/JPY Pair) ---
  if p_jpy >= 0.58:
    stance_jpy = "Hawkish / Tightening Risk"
    bias_jpy = "USD/JPY Bearish (JPY Bullish)"  # JPY menguat -> USD/JPY Turun
  elif p_jpy <= 0.42:
    stance_jpy = "Dovish / Easing Expectations"
    bias_jpy = "USD/JPY Bullish (JPY Bearish)"  # JPY melemah -> USD/JPY Naik
  else:
    stance_jpy = "Neutral / Policy Hold"
    bias_jpy = "USD/JPY Rangebound"

  macro_output = {
      "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
      "gold_real_yield_engine": {
          "us_10y_real_rate": round(latest_rr, 2),
          "z_score_20d": round(z_rr, 2),
          "macro_strength": gold_bias,
          "interpretation": (
              "Mengukur deviasi suku bunga riil terhadap rerata 20-hari."
          ),
      },
      "currency_probabilities": {
          "GBP": {
              "leading_metric": "UK Industrial PPI MoM",
              "prob_cpi_above_consensus": p_gbp,
              "central_bank_stance": stance_gbp,
              "recommended_bias": bias_gbp,
          },
          "JPY": {
              "leading_metric": "Japan Services CSPI MoM",
              "prob_cpi_above_consensus": p_jpy,
              "central_bank_stance": stance_jpy,
              "recommended_bias": bias_jpy,
          },
          "EUR": {
              "leading_metric": "Germany Industrial PPI MoM",
              "prob_cpi_above_consensus": p_eur,
              "central_bank_stance": stance_eur,
              "recommended_bias": bias_eur,
          },
          "USD": {
              "leading_metric": "ISM Services Prices Paid",
              "prob_cpi_above_consensus": p_usd,
              "central_bank_stance": stance_usd,
              "recommended_bias": bias_usd,
          },
      },
  }

  with open("macro_bias.json", "w") as f:
    json.dump(macro_output, f, indent=4)

  print("[SUCCESS] Model probabilitas berhasil dikalibrasi ulang!")


if __name__ == "__main__":
  generate_rplabs_data()