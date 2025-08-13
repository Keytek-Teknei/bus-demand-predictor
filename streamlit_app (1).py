
import streamlit as st
import pandas as pd
import joblib
from datetime import datetime, timedelta

# Cargar modelo actualizado
model = joblib.load("modelo_prediccion_bus_v3.pkl")

st.set_page_config(page_title="Predicción de saturación – Bizkaibus Aeropuerto", layout="centered")
st.title("🚌 Predicción de saturación del bus en el aeropuerto de Bilbao")
st.markdown("Sube una tanda de vuelos y elige una hora de expedición para saber si hay riesgo de saturación.")

# Subir archivo
uploaded_file = st.file_uploader("📄 Sube un archivo Excel o CSV con vuelos", type=["xlsx", "csv"])

# Selección de hora de expedición
hora_bus = st.time_input("🕒 Hora teórica de expedición del bus", value=datetime.now().time())
fecha_bus = st.date_input("📅 Fecha de expedición", value=datetime.today().date())

if uploaded_file:
    if uploaded_file.name.endswith(".csv"):
        df_vuelos = pd.read_csv(uploaded_file)
    else:
        df_vuelos = pd.read_excel(uploaded_file)

    try:
        df_vuelos['datetime_llegada'] = pd.to_datetime(df_vuelos['F. Vuelo'] + ' ' + df_vuelos['Real'], format='%Y-%m-%d %H:%M')
    except:
        st.error("❌ Asegúrate de que las columnas 'F. Vuelo' y 'Real' están en formato YYYY-MM-DD y HH:MM")

    hora_completa = datetime.combine(fecha_bus, hora_bus)

    df_vuelos['UE'] = df_vuelos['ORIGEN'].isin(['BCN', 'MAD', 'ALC'])

    df_vuelos['Min_Espera'] = df_vuelos['UE'].apply(lambda x: 30 if x else 45)
    df_vuelos['datetime_abordan'] = df_vuelos['datetime_llegada'] + df_vuelos['Min_Espera'].apply(lambda x: timedelta(minutes=x))

    df_filtrados = df_vuelos[
        (df_vuelos['datetime_abordan'] >= hora_completa - timedelta(minutes=10)) &
        (df_vuelos['datetime_abordan'] <= hora_completa)
    ]

    num_vuelos = len(df_filtrados)
    hora_decimal = hora_completa.hour * 60 + hora_completa.minute

    input_modelo = pd.DataFrame([{
        'minutos_dia': hora_decimal,
        'vuelos_conectados': num_vuelos
    }])

    prediccion = model.predict(input_modelo)[0]
    alerta = "⚠️ SATURACIÓN PREVISTA" if prediccion >= 90 else "✅ Sin saturación"

    st.subheader("📊 Resultado de la predicción:")
    st.write(f"**Pasajeros estimados:** {round(prediccion, 1)}")
    st.write(f"**Número de vuelos válidos:** {num_vuelos}")
    st.markdown(f"### {alerta}")

    st.markdown("---")
    st.markdown("**Nota:** se considera umbral de alerta a partir de 90 pasajeros (capacidad máxima: 100 pax).")

else:
    st.info("🔄 Esperando archivo... El archivo debe tener columnas: 'F. Vuelo', 'Real', 'ORIGEN', 'Asientos Promedio'")
