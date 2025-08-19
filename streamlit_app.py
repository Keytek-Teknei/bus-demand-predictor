import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import joblib

# Cargar el modelo
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
            st.subheader("Selecciona el día de la predicción")
            fecha_prediccion = st.date_input("Fecha", value=datetime.today()).strftime("%Y-%m-%d")

            # Convertir campos a datetime
            df_vuelos["datetime_llegada"] = pd.to_datetime(df_vuelos["F. Vuelo"].astype(str).str[:10] + " " + df_vuelos["Real"].astype(str))

            # Tiempo de caminata según ORIGEN
            paises_ue = ["BCN", "MAD", "ALC"]
            df_vuelos["tiempo_caminata"] = df_vuelos["ORIGEN"].apply(lambda x: timedelta(minutes=30) if x in paises_ue else timedelta(minutes=45))

            # Hora a la que están listos para abordar
            df_vuelos["datetime_abordan"] = df_vuelos["datetime_llegada"] + df_vuelos["tiempo_caminata"]

            # Crear lista de horas de expedición del día seleccionado
            inicio = datetime.strptime("06:00", "%H:%M")
            fin = datetime.strptime("23:30", "%H:%M")
            expediciones = []

            while inicio <= fin:
                hora = inicio.strftime("%H:%M")
                datetime_expedicion = pd.to_datetime(f"{fecha_prediccion} {hora}")
                expediciones.append(datetime_expedicion)
                inicio += timedelta(minutes=15)

            # Para registrar qué vuelo ya ha sido asignado
            vuelos_asignados = []

            st.subheader(f"Resultados de ocupación para el día {fecha_prediccion}")

            for exp_time in expediciones:
                # Solo vuelos no asignados y que abordan antes de la expedición
                vuelos_disponibles = df_vuelos[
                    (~df_vuelos.index.isin(vuelos_asignados)) &
                    (df_vuelos["datetime_abordan"] <= exp_time)
                ]

                # Añadir los índices de estos vuelos como ya asignados
                vuelos_asignados.extend(vuelos_disponibles.index.tolist())

                capacidad_total = vuelos_disponibles["Asientos Promedio"].sum()

                # Realizar predicción
                input_model = pd.DataFrame({"capacidad_avion": [capacidad_total]})
                prediccion = model.predict(input_model)[0]

                hora_str = exp_time.strftime("%H:%M")
                st.markdown(f"### 🕒 Expedición {hora_str} — {int(prediccion)} pasajeros")

                # Mostrar resultado
                if prediccion >= 100:
                    st.error("🔴 Se espera saturación del autobús")
                elif prediccion >= 90:
                    st.warning("🟠 Riesgo de saturación, revisar capacidad")
                else:
                    st.success("🟢 No se prevé saturación")

    except Exception as e:
        st.error(f"Error al procesar el archivo: {e}")
