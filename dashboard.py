import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta

# ===========================================
# 🔹 Configuración inicial
# ===========================================
st.set_page_config(page_title="BBWP Dashboard - Criptomonedas (Binance REST)", layout="wide")
st.title("📊 BBWP Dashboard - Criptomonedas")
st.markdown("Calcula el indicador **BBWP** para criptomonedas en temporalidad 4h, 1D o 1W usando la API pública de Binance (no requiere ccxt).")

# ===========================================
# 🔹 Lista de criptomonedas (pares en Binance)
# ===========================================
tickers = [
    "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT",
    "DOGE/USDT", "ADA/USDT", "AVAX/USDT", "DOT/USDT", "MATIC/USDT",
    "LINK/USDT", "LTC/USDT", "UNI/USDT", "ATOM/USDT", "NEAR/USDT",
    "ETC/USDT", "OP/USDT", "ARB/USDT", "FIL/USDT", "APT/USDT", "XLM/USDT" 
]

# ===========================================
# 🔹 Mapeo intervalos Streamlit -> Binance
# ===========================================
interval_map = {
    "4h": "4h",
    "1d": "1d",
    "1w": "1w"
}

# ===========================================
# 🔹 Función para descargar datos desde Binance REST
# ===========================================
@st.cache_data(show_spinner=False)
def descargar_datos_binance(symbol, interval="1d", limit=1000):
    pair = symbol.replace("/", "")
    url = "https://api.binance.us/api/v3/klines"   # ✅ versión US, sin bloqueo regional
    params = {"symbol": pair, "interval": interval, "limit": limit}
    try:
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()

        if not isinstance(data, list) or len(data) == 0:
            st.warning(f"⚠️ Binance US no devolvió datos para {pair} ({interval})")
            return None

        df = pd.DataFrame(data, columns=[
            "open_time", "Open", "High", "Low", "Close", "Volume",
            "close_time", "qav", "num_trades", "taker_base_av", "taker_quote_av", "ignore"
        ])
        df["Datetime"] = pd.to_datetime(df["open_time"], unit="ms")
        df.set_index("Datetime", inplace=True)
        df[["Open","High","Low","Close","Volume"]] = df[["Open","High","Low","Close","Volume"]].astype(float)
        df = df[["Open","High","Low","Close","Volume"]]
        return df

    except Exception as e:
        st.error(f"Error descargando {pair}: {e}")
        return None

# ===========================================
# 🔹 Función para calcular BBWP
# ===========================================
def calcular_bbwp(df, periodo=20):
    if df is None or len(df) < periodo:
        return pd.Series([np.nan] * (0 if df is None else len(df)), index=(df.index if df is not None else []))
    rango = df["Close"].rolling(periodo).max() - df["Close"].rolling(periodo).min()
    ancho = (df["Close"] - df["Close"].rolling(periodo).min()) / rango * 100
    return ancho.reindex(df.index)

# ===========================================
# 🔹 Selector de intervalo
# ===========================================
intervalo_radio = st.radio(
    "Selecciona intervalo de análisis:",
    ["4h (4 horas)", "1d (diario)", "1w (semanal)"]
)
intervalo_key = intervalo_radio.split(" ")[0]  # '4h' / '1d' / '1w'
binance_interval = interval_map[intervalo_key]

st.info(f"⏳ Descargando datos y calculando BBWP ({binance_interval}) para {len(tickers)} criptos...")

# ===========================================
# 🔹 Procesamiento principal
# ===========================================
resultados = []
total = len(tickers)
barra = st.progress(0)
exitosos, fallidos = 0, 0

for i, ticker in enumerate(tickers):
    df = descargar_datos_binance(ticker, interval=binance_interval, limit=1000)
    if df is None or df.empty:
        fallidos += 1
        barra.progress((i + 1) / total)
        continue

    try:
        df["BBWP"] = calcular_bbwp(df)
        if "BBWP" not in df or df["BBWP"].isna().all():
            fallidos += 1
            barra.progress((i + 1) / total)
            continue

        ultimos6 = df["BBWP"].tail(6)
        bbwp_ultimo = df["BBWP"].iloc[-1]
        conteo_bajo = int((ultimos6 < 15).sum())

        resultados.append({
            "Criptomoneda": ticker,
            "Último BBWP": round(float(bbwp_ultimo), 2) if not pd.isna(bbwp_ultimo) else np.nan,
            "Periodos <15 (últimos 6)": conteo_bajo
        })
        exitosos += 1

    except Exception as e:
        print(f"Error procesando {ticker}: {e}")
        fallidos += 1
        continue

    barra.progress((i + 1) / total)

# ===========================================
# 🔹 Resultados y descarga
# ===========================================
if resultados:
    df_resultados = pd.DataFrame(resultados).sort_values("Último BBWP")
    st.dataframe(df_resultados, use_container_width=True)

    excel_name = f"bbwp_resultados_{binance_interval}_cripto.xlsx"
    df_resultados.to_excel(excel_name, index=False)

    with open(excel_name, "rb") as f:
        st.download_button(
            label="📥 Descargar resultados en Excel",
            data=f,
            file_name=excel_name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    st.success(f"✅ Cálculo completado. {exitosos} criptos exitosas, {fallidos} fallidas.")
else:
    st.error("⚠️ No se pudo obtener información de ninguna criptomoneda.")
