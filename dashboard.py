import streamlit as st
import pandas as pd
import numpy as np
import ccxt
from datetime import datetime, timedelta

# ===========================================
# 🔹 Configuración inicial
# ===========================================
st.set_page_config(page_title="BBWP Dashboard - Criptomonedas", layout="wide")
st.title("📊 BBWP Dashboard - Criptomonedas")
st.markdown("Calcula el indicador **BBWP** para criptomonedas en temporalidad 4h, 1D o 1W usando datos de Binance.")

# ===========================================
# 🔹 Lista de criptomonedas
# ===========================================
tickers = [
    "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT",
    "DOGE/USDT", "ADA/USDT", "AVAX/USDT", "DOT/USDT", "MATIC/USDT",
    "LINK/USDT", "LTC/USDT", "UNI/USDT", "ATOM/USDT", "NEAR/USDT",
    "ETC/USDT", "OP/USDT", "ARB/USDT", "FIL/USDT", "APT/USDT, XLM/USDT"
]

# ===========================================
# 🔹 Inicializar exchange (Binance)
# ===========================================
exchange = ccxt.binance()

# ===========================================
# 🔹 Función para descargar datos OHLCV
# ===========================================
@st.cache_data(show_spinner=False)
def descargar_datos_ccxt(symbol, timeframe="1d", limit=500):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=["Datetime", "Open", "High", "Low", "Close", "Volume"])
        df["Datetime"] = pd.to_datetime(df["Datetime"], unit="ms")
        df.set_index("Datetime", inplace=True)
        return df
    except Exception as e:
        print(f"Error con {symbol}: {e}")
        return None

# ===========================================
# 🔹 Función para calcular BBWP
# ===========================================
def calcular_bbwp(df, periodo=20):
    if len(df) < periodo:
        return pd.Series([np.nan] * len(df), index=df.index)
    rango = df["Close"].rolling(periodo).max() - df["Close"].rolling(periodo).min()
    ancho = (df["Close"] - df["Close"].rolling(periodo).min()) / rango * 100
    return ancho.reindex(df.index)

# ===========================================
# 🔹 Selector de intervalo
# ===========================================
intervalo = st.radio(
    "Selecciona intervalo de análisis:",
    ["4h (4 horas)", "1d (diario)", "1w (semanal)"]
)
intervalo = intervalo.split(" ")[0]  # '4h', '1d' o '1w'

st.info(f"⏳ Descargando datos y calculando BBWP ({intervalo}) para {len(tickers)} criptos...")

# ===========================================
# 🔹 Procesamiento principal
# ===========================================
resultados = []
total = len(tickers)
barra = st.progress(0)
exitosos, fallidos = 0, 0

for i, ticker in enumerate(tickers):
    df = descargar_datos_ccxt(ticker, timeframe=intervalo)
    if df is None or df.empty:
        fallidos += 1
        continue

    try:
        df["BBWP"] = calcular_bbwp(df)
        if "BBWP" not in df or df["BBWP"].isna().all():
            continue

        ultimos6 = df["BBWP"].tail(6)
        bbwp_ultimo = df["BBWP"].iloc[-1]
        conteo_bajo = (ultimos6 < 15).sum()

        resultados.append({
            "Criptomoneda": ticker,
            "Último BBWP": round(bbwp_ultimo, 2),
            "Periodos <15 (últimos 6)": int(conteo_bajo)
        })
        exitosos += 1

    except Exception:
        fallidos += 1
        continue

    barra.progress((i + 1) / total)

# ===========================================
# 🔹 Resultados y descarga
# ===========================================
if resultados:
    df_resultados = pd.DataFrame(resultados).sort_values("Último BBWP")
    st.dataframe(df_resultados, use_container_width=True)

    excel_name = f"bbwp_resultados_{intervalo}_cripto.xlsx"
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
