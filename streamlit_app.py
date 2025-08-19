import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import joblib

# Cargar modelo
model = joblib.load("modelo_prediccion_bus_v3.pkl")

st.title("Predicción de saturación del bus en el aeropuerto de Bilbao")

uploaded_file = st.file_uploader("Sube tu archivo Excel (.xlsx)", type=["xlsx"])

if uploaded_file:
    try:
        df_vuelos = pd.read_excel(uploaded_file, sheet_name="Vuelos")

        required_cols = ["F. Vuelo", "Real", "ORIGEN", "Asientos Promedio"]
        if not all(col in df_vuelos.columns for col in required_cols):
            st.error(f"El archivo debe contener las columnas: {required_cols}")
        else:
            df_vuelos["datetime_llegada"] = pd.to_datetime(
                df_vuelos["F. Vuelo"].astype(str).str[:10] + " " + df_vuelos["Real"].astype(str)
            )

            paises_ue = ["BCN", "ALC", "MAD"]
            df_vuelos["tiempo_caminata"] = df_vuelos["ORIGEN"].apply(
                lambda x: timedelta(minutes=30) if x in paises_ue else timedelta(minutes=45)
            )

            df_vuelos["datetime_abordan"] = df_vuelos["datetime_llegada"] + df_vuelos["tiempo_caminata"]

            fechas_disponibles = df_vuelos["F. Vuelo"].dt.date.unique()
            fecha_seleccionada = st.date_input("Selecciona el día de la predicción", value=fechas_disponibles[0])

            inicio = datetime.strptime("06:00", "%H:%M")
            fin = datetime.strptime("23:30", "%H:%M")
            horarios_expediciones = []
            while inicio <= fin:
                horarios_expediciones.append(inicio.time())
                inicio += timedelta(minutes=15)

            vuelos_dia = df_vuelos[df_vuelos["F. Vuelo"].dt.date == fecha_seleccionada]

            for hora in horarios_expediciones:
                hora_str = hora.strftime("%H:%M")
                datetime_expedicion = datetime.combine(fecha_seleccionada, hora)

                vuelos_aptos = vuelos_dia[vuelos_dia["datetime_abordan"] <= datetime_expedicion]
                capacidad_total = vuelos_aptos["Asientos Promedio"].sum()

                if capacidad_total == 0:
                    st.markdown(f"### 🕒 Expedición {hora_str} — 0 pasajeros")
                    st.info("Sin vuelos asignados a esta expedición")
                else:
                    input_model = pd.DataFrame({"capacidad_avion": [capacidad_total]})
                    prediccion = model.predict(input_model)[0]

                    st.markdown(f"### 🕒 Expedición {hora_str} — {int(prediccion)} pasajeros")

                    if prediccion >= 100:
                        st.error("🔴 Se espera saturación del autobús")
                    elif prediccion >= 90:
                        st.warning("🟠 Riesgo de saturación, revisar capacidad")
                    else:
                        st.success("🟢 No se prevé saturación")

    except Exception as e:
        st.error(f"Error al procesar el archivo: {e}")
else:
    st.warning("Aún no has subido ningún archivo")
