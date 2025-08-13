
import streamlit as st
import pandas as pd
import joblib
from datetime import datetime, timedelta

# Cargar modelo
model = joblib.load("modelo_prediccion_bus.pkl")

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

    df_filtrados = df_vuelos[
        ((df_vuelos['UE']) & (df_vuelos['datetime_llegada'] <= hora_completa - timedelta(minutes=30))) |
        ((~df_vuelos['UE']) & (df_vuelos['datetime_llegada'] <= hora_completa - timedelta(minutes=45)))
    ]

    num_vuelos = len(df_filtrados)
    capacidad_total = df_filtrados['Asientos Promedio'].fillna(0).sum()
    vuelos_ue = df_filtrados[df_filtrados['UE']].shape[0]
    vuelos_no_ue = num_vuelos - vuelos_ue
    hora_decimal = hora_completa.hour + hora_completa.minute / 60

    input_modelo = pd.DataFrame([{
        'hora': hora_decimal,
        'num_vuelos_previos': num_vuelos,
        'suma_capacidades_previas': capacidad_total,
        'vuelos_origen_UE': vuelos_ue,
        'vuelos_origen_no_UE': vuelos_no_ue
    }])

    prediccion = model.predict(input_modelo)[0]
    alerta = "⚠️ SATURACIÓN PREVISTA" if prediccion >= 90 else "✅ Sin saturación"

    st.subheader("📊 Resultado de la predicción:")
    st.write(f"**Pasajeros estimados:** {round(prediccion, 1)}")
    st.write(f"**Número de vuelos válidos:** {num_vuelos}")
    st.write(f"**Capacidad total estimada:** {int(capacidad_total)}")
    st.write(f"**Vuelos UE / no UE:** {vuelos_ue} / {vuelos_no_ue}")
    st.markdown(f"### {alerta}")

    st.markdown("---")
    st.markdown("**Nota:** se considera umbral de alerta a partir de 90 pasajeros (capacidad máxima: 100 pax).")

else:
    st.info("🔄 Esperando archivo... El archivo debe tener columnas: 'F. Vuelo', 'Real', 'ORIGEN', 'Asientos Promedio'")
