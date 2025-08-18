import streamlit as st
import pandas as pd
vuelos = None


st.write("Intentando leer archivo Excel...")

uploaded_file = st.file_uploader("Sube tu archivo Excel (.xlsx)", type=["xlsx"])

if uploaded_file is not None:
    st.success("Archivo leído correctamente")

    # Aquí ya sabes que el usuario ha subido un archivo
    # → puedes leer el Excel, mostrarlo y pedirle la hora/fecha

df_vuelos = pd.read_excel(uploaded_file, sheet_name="Sheet1")  # si se llama así
st.dataframe(df_vuelos.head())  # Opcional

    # Genera la lista de horas en intervalos de 15 minutos desde las 06:00 hasta las 23:45
opciones_horas = [f"{h:02d}:{m:02d}" for h in range(6, 24) for m in [0, 15, 30, 45]]
hora = st.selectbox("Hora teórica de expedición", opciones_horas)
fecha = st.date_input("Fecha de expedición")
    
    # Luego haces la predicción como siempre...
if vuelos is not None and not vuelos.empty:
    st.write("Vuelos disponibles")
else:
    st.write("No hay vuelos")

from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestRegressor
import joblib

# Cargar los archivos históricos
vuelos = pd.read_excel('Historicos.xlsx', sheet_name='Vuelos')
buses = pd.read_excel('Historicos.xlsx', sheet_name='Buses')

# Unificar fecha y hora real del vuelo
vuelos['datetime_real'] = vuelos['F. Vuelo'] + pd.to_timedelta(vuelos['Real'] + ':00')

# Estimar tiempo de espera según origen
def tiempo_espera(origen):
    if origen.upper() in ['MADRID', 'BCN', 'PARIS', 'ROMA', 'LISBOA', 'FRA']:
        return 30
    else:
        return 45

vuelos['Min_Espera'] = vuelos['ORIGEN'].apply(tiempo_espera)
vuelos['datetime_abordan'] = vuelos['datetime_real'] + pd.to_timedelta(vuelos['Min_Espera'], unit='m')

# Crear lista de expediciones con fecha y hora
buses['fechaServicio'] = pd.to_datetime(buses['fechaServicio'], format='%Y-%m-%d')
buses['horaTeoricaExpedicion'] = pd.to_datetime(buses['horaTeoricaExpedicion'], format='%H:%M:%S')

buses['datetime_expedicion'] = pd.to_datetime(
    buses['fechaServicio'].dt.strftime('%Y-%m-%d') + ' ' + buses['horaTeoricaExpedicion'].dt.strftime('%H:%M:%S')
)

# Asignar cada vuelo a la expedición más próxima (después de datetime_abordan)
def asignar_expedicion(abordan_time, lista_expediciones):
    futuras = lista_expediciones[lista_expediciones >= abordan_time]
    return futuras.min() if not futuras.empty else None

expediciones = buses['datetime_expedicion'].sort_values().unique()
vuelos['Expedicion Asignada'] = vuelos['datetime_abordan'].apply(lambda x: asignar_expedicion(x, pd.Series(expediciones)))

# Agrupar los vuelos por expedición asignada
resumen = vuelos.groupby('Expedicion Asignada').agg(
    vuelos_conectados=('ORIGEN', 'count'),
    capacidad_total=('Asientos Promedio', 'sum')
).reset_index().rename(columns={'Expedicion Asignada': 'datetime_expedicion'})

# Unir con datos reales de expediciones
df_final = pd.merge(resumen, buses[['datetime_expedicion', 'Viajes']], on='datetime_expedicion', how='inner')
df_final['minutos_dia'] = df_final['datetime_expedicion'].dt.hour * 60 + df_final['datetime_expedicion'].dt.minute

# Entrenar modelo
X = df_final[['minutos_dia', 'vuelos_conectados', 'capacidad_total']]
y = df_final['Viajes']

modelo = RandomForestRegressor(n_estimators=100, random_state=42)
modelo.fit(X, y)

# Guardar modelo
joblib.dump(modelo, 'modelo_prediccion_bus_v3.pkl')
print('✅ Modelo actualizado y guardado correctamente')
