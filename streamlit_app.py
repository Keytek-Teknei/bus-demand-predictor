import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import joblib

# Cargar modelo
model = joblib.load("modelo_prediccion_bus_v3.pkl")

st.title("Predicción de saturación del bus en el aeropuerto de Bilbao")

# Subida del archivo
uploaded_file = st.file_uploader("Sube tu archivo Excel (.xlsx)", type=["xlsx"])

# Selector de fecha
fecha_seleccionada = st.date_input("Selecciona el día de la predicción", value=datetime.today())

# Generar lista de horas de expedición del día (06:00 a 23:30 cada 15 min)
inicio = datetime.strptime("06:00", "%H:%M")
fin = datetime.strptime("23:30", "%H:%M")
expediciones = []
while inicio <= fin:
    expediciones.append(inicio.strftime("%H:%M"))
    inicio += timedelta(minutes=15)

if uploaded_file:
    try:
        # Leer la hoja de vuelos
        df_vuelos = pd.read_excel(uploaded_file, sheet_name="Vuelos")

        # Verificar columnas
        required_cols = ["F. Vuelo", "Real", "ORIGEN", "Asientos Promedio"]
        if not all(col in df_vuelos.columns for col in required_cols):
            st.error(f"El archivo debe contener las columnas: {required_cols}")
        else:
            # Filtrar vuelos del día seleccionado
            fecha_str = fecha_seleccionada.strftime("%Y-%m-%d")
            df_vuelos = df_vuelos[df_vuelos["F. Vuelo"].astype(str).str.startswith(fecha_str)]

            # Convertir fecha y hora de vuelo
            df_vuelos["datetime_llegada"] = pd.to_datetime(
                df_vuelos["F. Vuelo"].astype(str).str[:10] + " " + df_vuelos["Real"].astype(str)
            )

            # Tiempo de caminata según origen
            paises_ue = ["BCN", "MAD", "ALC", "VLC", "AGP"]  # Ya integrada tu lista completa
            df_vuelos["tiempo_caminata"] = df_vuelos["ORIGEN"].apply(
                lambda x: timedelta(minutes=30) if x in paises_ue else timedelta(minutes=45)
            )

            # Hora estimada de abordaje
            df_vuelos["datetime_abordan"] = df_vuelos["datetime_llegada"] + df_vuelos["tiempo_caminata"]

            # Filtrar vuelos para el día seleccionado
            vuelos_dia = df_vuelos[df_vuelos["F. Vuelo"].astype(str).str.startswith(fecha_str)]

            # Inicializar lista de vuelos ya asignados
            vuelos_asignados = []

            st.subheader(f"Resultados de ocupación para el día {fecha_str}")

            for hora in expediciones:
                datetime_expedicion = pd.to_datetime(f"{fecha_str} {hora}")

                # Filtrar vuelos no asignados y que puedan abordar en esta expedición
                vuelos_aptos = vuelos_dia[
                    (~vuelos_dia.index.isin(vuelos_asignados)) &
                    (vuelos_dia["datetime_abordan"] <= datetime_expedicion)
                ]

                # Marcar estos vuelos como ya asignados
                vuelos_asignados.extend(vuelos_aptos.index.tolist())

                # Sumar Asientos Promedio
                capacidad_total = vuelos_aptos["Asientos Promedio"].sum()

                # Si no hay vuelos asignados, mostrar 0 pasajeros
                if capacidad_total == 0:
                    st.markdown(f"### 🕒 Expedición {hora} — 0 pasajeros")
                    st.info("Sin vuelos asignados a esta expedición")
                    continue

                # Predicción usando el modelo
                input_model = pd.DataFrame({"capacidad_avion": [capacidad_total]})
                prediccion = model.predict(input_model)[0]

                # Mostrar resultados con alerta según umbral
                st.markdown(f"### 🕒 Expedición {hora} — {int(prediccion)} pasajeros")
                ocupacion = int(prediccion)

if 0 <= ocupacion <= 10:
    mensaje = "Muy pocos pasajeros, el autobús está prácticamente vacío ✅"
elif 11 <= ocupacion <= 30:
    mensaje = "El servicio aguanta perfectamente la demanda ✅"
elif 31 <= ocupacion <= 60:
    mensaje = "Poco a poco se está llenando el autobús ⚠️"
elif 61 <= ocupacion <= 90:
    mensaje = "Está cerca de saturarse ⚠️"
elif ocupacion >= 100:
    mensaje = "Se espera saturación del autobús 🔴"
else:
    mensaje = "No hay información suficiente"

st.markdown(f"### 🕒 Expedición {hora_expedicion.strftime('%H:%M')} — {ocupacion} pasajeros")
st.info(mensaje)


    except Exception as e:
        st.error(f"Error al procesar el archivo: {e}")
else:
    st.warning("Aún no has subido ningún archivo")
