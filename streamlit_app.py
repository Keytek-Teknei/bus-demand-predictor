import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import joblib

# Cargar el modelo ya entrenado
model = joblib.load("modelo_prediccion_bus_v3.pkl")

st.title("Predicción de saturación del bus en el aeropuerto de Bilbao")

# Subida de archivo
uploaded_file = st.file_uploader("Sube tu archivo Excel (.xlsx)", type=["xlsx"])

if uploaded_file:
    try:
        # Leer la hoja correcta del Excel
        df_vuelos = pd.read_excel(uploaded_file, sheet_name="Vuelos")

        # Verificar columnas necesarias
        required_cols = ["F. Vuelo", "Real", "ORIGEN", "Asientos Promedio"]
        if not all(col in df_vuelos.columns for col in required_cols):
            st.error(f"El archivo debe contener las columnas: {required_cols}")
        else:
            # Procesar fechas y caminatas
            df_vuelos["datetime_llegada"] = pd.to_datetime(df_vuelos["F. Vuelo"].astype(str).str[:10] + " " + df_vuelos["Real"].astype(str))

            paises_ue = ["BCN", "ALC", "MAD", "VLC", "AGP"]
            df_vuelos["tiempo_caminata"] = df_vuelos["ORIGEN"].apply(
                lambda x: timedelta(minutes=30) if x in paises_ue else timedelta(minutes=45)
            )
            df_vuelos["datetime_abordan"] = df_vuelos["datetime_llegada"] + df_vuelos["tiempo_caminata"]

            # Generar todas las expediciones del día cada 15 min desde 06:00 hasta 23:30
            fecha_base = df_vuelos["datetime_llegada"].dt.date.min()
            hora_inicio = datetime.strptime("06:00", "%H:%M")
            hora_fin = datetime.strptime("23:30", "%H:%M")
            expediciones = []
            while hora_inicio <= hora_fin:
                expediciones.append(datetime.combine(fecha_base, hora_inicio.time()))
                hora_inicio += timedelta(minutes=15)

            # Asignar expedición a cada vuelo (la primera expedición posterior a datetime_abordan)
            def asignar_expedicion(hora_aborda):
                for e in expediciones:
                    if hora_aborda <= e:
                        return e
                return None

            df_vuelos["expedicion"] = df_vuelos["datetime_abordan"].apply(asignar_expedicion)
            df_expediciones = df_vuelos.dropna(subset=["expedicion"]).groupby("expedicion")["Asientos Promedio"].sum().reset_index()
            df_expediciones.rename(columns={"Asientos Promedio": "capacidad_avion"}, inplace=True)

            # Predecir para cada expedición
            df_expediciones["prediccion"] = model.predict(df_expediciones[["capacidad_avion"]])

            # Mostrar resultados
            for _, row in df_expediciones.iterrows():
                hora_exp = row["expedicion"].strftime("%H:%M")
                pasajeros = int(row["prediccion"])
                st.markdown(f"### 🕒 Expedición {hora_exp} — {pasajeros} pasajeros")
                if pasajeros >= 100:
                    st.error("🔴 Se espera saturación del autobús")
                elif pasajeros >= 90:
                    st.warning("🟠 Riesgo moderado de saturación")
                else:
                    st.success("🟢 No se prevé saturación")

    except Exception as e:
        st.error(f"Error al procesar el archivo: {e}")
else:
    st.warning("Aún no has subido ningún archivo")
