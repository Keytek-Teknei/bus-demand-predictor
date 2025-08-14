import streamlit as st
import pandas as pd
import joblib
from datetime import datetime, timedelta

st.set_page_config(page_title="Predicción de saturación del bus", page_icon="🚌")

st.title("🚌 Predicción de saturación del bus en el aeropuerto de Bilbao")
st.write("Sube una tanda de vuelos y elige una hora de expedición para saber si hay riesgo de saturación.")

st.markdown("### 📄 Sube un archivo Excel o CSV con vuelos")
uploaded_file = st.file_uploader("Sube un archivo", type=["xlsx", "csv"])

hora_bus = st.selectbox("🕒 Hora teórica de expedición del bus", options=[f"{h:02d}:{m:02d}" for h in range(24) for m in (0, 15, 30, 45)])
fecha_bus = st.date_input("📅 Fecha de expedición", value=datetime.now().date())

if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith(".xlsx"):
            df_vuelos = pd.read_excel(uploaded_file)
        else:
            df_vuelos = pd.read_csv(uploaded_file)

        st.success("✅ Archivo cargado correctamente")

        # Asegurar formatos de columnas de fecha
        df_vuelos["F. Vuelo"] = pd.to_datetime(df_vuelos["F. Vuelo"])
        df_vuelos["Real"] = pd.to_datetime(df_vuelos["Real"]).dt.time
        df_vuelos["datetime_llegada"] = df_vuelos.apply(lambda x: datetime.combine(x["F. Vuelo"], x["Real"]), axis=1)

        # Estimar hora a la que cada vuelo aborda el bus
        def calcular_abordan(row):
            origen = row["ORIGEN"].upper()
            return row["datetime_llegada"] + timedelta(minutes=30 if origen in ue else 45)

        ue = ["PAR", "AMS", "FRA", "BCN", "MAD", "LIS", "ROM", "DUB", "VIE", "BER"]
        df_vuelos["datetime_abordan"] = df_vuelos.apply(calcular_abordan, axis=1)

        # Filtrar por expedición seleccionada
        fecha_hora_bus = datetime.combine(fecha_bus, datetime.strptime(hora_bus, "%H:%M").time())
        df_abordan = df_vuelos[df_vuelos["datetime_abordan"] == fecha_hora_bus]

        st.write("✈️ Vuelos que abordan en esta expedición:", df_abordan.shape[0])
        st.dataframe(df_abordan[["F. Vuelo", "ORIGEN", "datetime_llegada", "datetime_abordan"]])

        capacidad_total = df_abordan["Asientos Promedio"].sum()
        st.write(f"👥 Capacidad total estimada de los vuelos que abordan: **{capacidad_total}**")

        # Cargar el modelo
        model = joblib.load("modelo_prediccion_bus_v3.pkl")
        input_modelo = pd.DataFrame({"capacidad_avion": [capacidad_total]})
        prediccion = model.predict(input_modelo[["capacidad_avion"]])[0]

        st.markdown("## 📊 Resultado de la predicción")
        st.write(f"🧠 El modelo predice que abordarán aproximadamente **{round(prediccion)}** pasajeros")

        if prediccion > 100:
            st.error("❌ ¡Saturación del autobús!")
        elif prediccion > 90:
            st.warning("⚠️ Riesgo de saturación (más del 90%)")
        else:
            st.success("✅ No se prevé saturación")
    except Exception as e:
        st.error(f"Ocurrió un error procesando el archivo: {e}")
else:
    st.info("📥 Esperando archivo... El archivo debe tener columnas: 'F. Vuelo', 'Real', 'ORIGEN', 'Asientos Promedio'")
