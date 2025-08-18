import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import joblib

# Cargar modelo
model = joblib.load("modelo_prediccion_bus_v3.pkl")

st.title("Predicción de saturación del bus en el aeropuerto de Bilbao")

uploaded_file = st.file_uploader("Sube tu archivo Excel (.xlsx)", type=["xlsx"])

# Selector de día
fecha_seleccionada = st.date_input("Selecciona el día de la predicción", value=datetime.today())

# Generar lista de horas desde 06:00 hasta 23:30 cada 15 minutos
inicio = datetime.strptime("06:00", "%H:%M")
fin = datetime.strptime("23:30", "%H:%M")
expediciones = []
while inicio <= fin:
    expediciones.append(inicio.strftime("%H:%M"))
    inicio += timedelta(minutes=15)

if uploaded_file:
    try:
        df_vuelos = pd.read_excel(uploaded_file, sheet_name="Vuelos")

        # Validar columnas
        required_cols = ["F. Vuelo", "Real", "ORIGEN", "Asientos Promedio"]
        if not all(col in df_vuelos.columns for col in required_cols):
            st.error(f"El archivo debe contener las columnas: {required_cols}")
        else:
            # Procesar vuelos del día seleccionado
            fecha_str = fecha_seleccionada.strftime("%Y-%m-%d")
            df_vuelos = df_vuelos[df_vuelos["F. Vuelo"].astype(str).str.startswith(fecha_str)]

            # Calcular fecha y hora real del vuelo
            df_vuelos["datetime_llegada"] = pd.to_datetime(df_vuelos["F. Vuelo"].astype(str).str[:10] + " " + df_vuelos["Real"].astype(str))

            # Tiempo de caminata
            paises_ue = ["BCN", "MAD", "ALC"]  # Origenes considerados UE
            df_vuelos["tiempo_caminata"] = df_vuelos["ORIGEN"].apply(lambda x: timedelta(minutes=30) if x in paises_ue else timedelta(minutes=45))

            # Hora en la que llegan listos al bus
            df_vuelos["datetime_abordan"] = df_vuelos["datetime_llegada"] + df_vuelos["tiempo_caminata"]

            resultados = []
            for hora in expediciones:
                datetime_expedicion = pd.to_datetime(f"{fecha_str} {hora}")
                # Filtrar pasajeros que abordan hasta esta hora
                pasajeros_vuelos = df_vuelos[df_vuelos["datetime_abordan"] <= datetime_expedicion]

                # Evitar contar dobles: eliminar vuelos ya usados en expediciones previas
                df_vuelos = df_vuelos[~df_vuelos.index.isin(pasajeros_vuelos.index)]

                capacidad_total = pasajeros_vuelos["Asientos Promedio"].sum()
                input_modelo = pd.DataFrame({"capacidad_avion": [capacidad_total]})
                prediccion = model.predict(input_modelo)[0]

                resultados.append({
                    "hora": hora,
                    "capacidad": int(prediccion)
                })

            # Mostrar resultados
            for r in resultados:
                st.subheader(f"🕐 Expedición {r['hora']} — {r['capacidad']} pasajeros")
                if r['capacidad'] >= 100:
                    st.error("🔴 Se espera saturación del autobús")
                elif r['capacidad'] >= 90:
                    st.warning("⚠️ Riesgo de saturación, revisar capacidad")
                else:
                    st.success("✅ No se prevé saturación")

    except Exception as e:
        st.error(f"Error al procesar el archivo: {e}")
