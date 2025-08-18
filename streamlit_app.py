import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import joblib

# Cargar el modelo ya entrenado
model = joblib.load("modelo_prediccion_bus_v3.pkl")

st.title("Predicción de saturación del bus en el aeropuerto de Bilbao")

# Subida de archivo
uploaded_file = st.file_uploader("Sube tu archivo Excel (.xlsx)", type=["xlsx"])

# Si se ha subido un archivo
if uploaded_file:
    try:
        # Leer la hoja correcta del Excel
        df_vuelos = pd.read_excel(uploaded_file, sheet_name="Vuelos")

        # Campos requeridos
        required_cols = ["F. Vuelo", "Real", "ORIGEN", "Asientos Promedio"]
        if not all(col in df_vuelos.columns for col in required_cols):
            st.error(f"El archivo debe contener las columnas: {required_cols}")
        else:
            # Conversión de campos a datetime
            df_vuelos["datetime_llegada"] = pd.to_datetime(df_vuelos["F. Vuelo"].astype(str).str[:10] + " " + df_vuelos["Real"].astype(str))

            # Clasificación UE / No UE (simplificada por ahora)
            paises_ue = ["BCN", "ALC", "MAD"]  # ejemplo
            df_vuelos["tiempo_caminata"] = df_vuelos["ORIGEN"].apply(lambda x: timedelta(minutes=30) if x in paises_ue else timedelta(minutes=45))

            # Calcular cuando están listos para abordar
            df_vuelos["datetime_abordan"] = df_vuelos["datetime_llegada"] + df_vuelos["tiempo_caminata"]

from datetime import datetime, timedelta

# Generar lista de horas desde 06:00 hasta 23:30 cada 15 minutos
inicio = datetime.strptime("06:00", "%H:%M")
fin = datetime.strptime("23:30", "%H:%M")
opciones_horas = []

while inicio <= fin:
    opciones_horas.append(inicio.strftime("%H:%M"))
    inicio += timedelta(minutes=15)

            hora_str = st.selectbox("Hora teórica de expedición", opciones_horas)
            fecha_str = st.date_input("Fecha de expedición", value=datetime.today()).strftime("%Y-%m-%d")

            # Convertir a datetime
            datetime_expedicion = pd.to_datetime(f"{fecha_str} {hora_str}")

            # Filtrar los vuelos que llegan a tiempo a esa expedición
            vuelos_aptos = df_vuelos[df_vuelos["datetime_abordan"] <= datetime_expedicion]

            if vuelos_aptos.empty:
                st.write("No hay vuelos que lleguen a tiempo para esta expedición")
            else:
                capacidad_total = vuelos_aptos["Asientos Promedio"].sum()

                # Realizar la predicción con el modelo
                input_modelo = pd.DataFrame({"capacidad_avion": [capacidad_total]})
                prediccion = model.predict(input_modelo)[0]

                st.subheader("Resultado de la predicción")
                st.markdown(f"El modelo predice que abordaran aproximadamente **{int(prediccion)} pasajeros**")

                if prediccion >= 100:
                    st.error("Se espera saturación del servicio de autobús")
                elif prediccion >= 90:
                    st.warning("Riesgo de saturación, revisar capacidad")
                else:
                    st.success("No se prevé saturación")

    except Exception as e:
        st.error(f"Error al procesar el archivo: {e}")

else:
    st.warning("Aún no has subido ningún archivo")

