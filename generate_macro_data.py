from datetime import datetime
import json
import numpy as np
import pandas as pd
import requests
import os

# Membaca dari environment variable (GitHub Secrets) atau fallback ke string jika dites lokal
FRED_API_KEY = os.environ.get("FRED_API_KEY", "77dd5415d0e40b020f478650246f561e")



def get_fred_series(series_id, api_key):
  """Menarik data historis dari FRED API"""
  url = "https://api.stlouisfed.org/fred/series/observations"
  params = {
      "series_id": series_id,
      "api_key": api_key,
      "file_type": "json",
      "sort_order": "desc",
      "limit": 12,  # Ambil 12 data bulanan terakhir
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


def calculate_logistic_inflation_probability(series, beta_0=0.0, beta_1=1.5):
  """LOGISTIC REGRESSION ENGINE

  Menghitung laju perubahan indikator (delta MoM) dan memasukkannya ke Fungsi
  Sigmoid untuk mengkalkulasi Probabilitas P(CPI > Consensus)
  """
  if series is None or len(series) < 2:
    return 0.50  # Probabilitas netral jika data tidak tersedia

  # 1. Hitung Laju Perubahan Biaya Input (Delta MoM)
  latest_val = series.iloc[-1]
  prev_val = series.iloc[-2]

  # Percentage change (delta)
  delta = (
      (latest_val - prev_val) / (abs(prev_val) + 1e-6)
      if prev_val != 0
      else 0.0
  )

  # 2. Linear Combination z = beta_0 + beta_1 * delta
  z = beta_0 + (beta_1 * delta * 10)  # Scaling factor untuk variansi kecil

  # 3. Sigmoid Function -> Transformasi ke Probabilitas [0.0 - 1.0]
  prob = 1 / (1 + np.exp(-z))

  return round(float(prob), 2)


def generate_rplabs_data():
  print(">>> [RP LABS] Calculating Inflation Probabilities via Logistic Engine...")

  # 1. GOLD REAL YIELD ENGINE (Tetap memakai Z-score untuk deviasi Emas)
  s_real_rate = get_fred_series("DFII10", FRED_API_KEY)
  if s_real_rate is not None and len(s_real_rate) > 0:
    latest_rr = float(s_real_rate.iloc[-1])
    ma20 = float(s_real_rate.mean())
    std20 = float(s_real_rate.std())
    z_rr = (latest_rr - ma20) / (std20 + 1e-6)
  else:
    latest_rr, z_rr = 1.85, 0.0

  gold_bias = (
      "BULLISH" if latest_rr < 1.5 else ("BEARISH" if latest_rr > 2.5 else "NEUTRAL")
  )

  # 2. LOGISTIC REGRESSION PROBABILITIES UNTUK CURRENCY INFLATION (G7)
  # JPY: Japan CSPI / Services CPI
  s_jpy = get_fred_series("JPNCPIALLMINMEI", FRED_API_KEY)
  prob_jpy = calculate_logistic_inflation_probability(
      s_jpy, beta_0=-0.1, beta_1=2.0
  )

  # EUR: Germany Industrial PPI
  s_eur = get_fred_series("DEUPPIALLMINMEI", FRED_API_KEY)
  prob_eur = calculate_logistic_inflation_probability(
      s_eur, beta_0=-0.2, beta_1=1.8
  )

  # GBP: UK Industrial PPI
  s_gbp = get_fred_series("GBRPPIALLMINMEI", FRED_API_KEY)
  prob_gbp = calculate_logistic_inflation_probability(
      s_gbp, beta_0=-0.05, beta_1=1.9
  )

  # USD: ISM Services Prices Paid Index
  s_usd = get_fred_series("NAPMPI", FRED_API_KEY)
  prob_usd = calculate_logistic_inflation_probability(
      s_usd, beta_0=-0.1, beta_1=1.5
  )

  # 3. CONSTRUCT OUTPUT JSON
  macro_output = {
      "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
      "gold_real_yield_engine": {
          "us_10y_real_rate": round(latest_rr, 2),
          "z_score_20d": round(z_rr, 2),
          "macro_strength": gold_bias,
          "interpretation": (
              "Mengukur deviasi suku bunga riil terhadap rata-rata bergerak"
              " untuk sentiment Emas."
          ),
      },
      "currency_probabilities": {
          "GBP": {
              "leading_metric": "UK Industrial PPI MoM",
              "prob_cpi_above_consensus": prob_gbp,
              "central_bank_stance": (
                  "Hawkish Stance" if prob_gbp >= 0.55 else "Dovish / Neutral"
              ),
              "recommended_bias": (
                  "GBP/USD Bullish" if prob_gbp >= 0.55 else "GBP/USD Range/Bear"
              ),
          },
          "JPY": {
              "leading_metric": "Japan Services CSPI MoM",
              "prob_cpi_above_consensus": prob_jpy,
              "central_bank_stance": (
                  "Hawkish (Rate Hike Risk)"
                  if prob_jpy >= 0.55
                  else "Dovish / Neutral"
              ),
              "recommended_bias": (
                  "USD/JPY Bearish" if prob_jpy >= 0.55 else "USD/JPY Range"
              ),
          },
          "EUR": {
              "leading_metric": "Germany Industrial PPI MoM",
              "prob_cpi_above_consensus": prob_eur,
              "central_bank_stance": (
                  "Hawkish Stance" if prob_eur >= 0.55 else "Dovish / Neutral"
              ),
              "recommended_bias": (
                  "EUR/USD Bullish" if prob_eur >= 0.55 else "EUR/USD Range/Bear"
              ),
          },
          "USD": {
              "leading_metric": "ISM Services Prices Paid",
              "prob_cpi_above_consensus": prob_usd,
              "central_bank_stance": (
                  "Hawkish Hold" if prob_usd >= 0.55 else "Dovish / Rate Cut"
              ),
              "recommended_bias": (
                  "DXY Bullish" if prob_usd >= 0.55 else "DXY Bearish"
              ),
          },
      },
  }

  with open("macro_bias.json", "w") as f:
    json.dump(macro_output, f, indent=4)

  print(
      "[SUCCESS] Probabilitas inflasi berhasil dihitung menggunakan Model"
      " Regresi Logistik!"
  )


if __name__ == "__main__":
  generate_rplabs_data()