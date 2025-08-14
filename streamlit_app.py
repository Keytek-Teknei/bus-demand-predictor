import pandas as pd
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestRegressor
import joblib

# Cargar los archivos históricos
vuelos = pd.read_excel('Históricos.xlsx', sheet_name='Vuelos')
buses = pd.read_excel('buses_historicos.xlsx')

# Unificar fecha y hora real del vuelo
vuelos['datetime_real'] = pd.to_datetime(vuelos['Fecha'] + ' ' + vuelos['Real'])

# Estimar tiempo de espera según origen
def tiempo_espera(origen):
    if origen.upper() in ['MADRID', 'BCN', 'PARIS', 'ROMA', 'LISBOA', 'FRA']:
        return 30
    else:
        return 45

vuelos['Min_Espera'] = vuelos['ORIGEN'].apply(tiempo_espera)
vuelos['datetime_abordan'] = vuelos['datetime_real'] + pd.to_timedelta(vuelos['Min_Espera'], unit='m')

# Crear lista de expediciones con fecha y hora
buses['datetime_expedicion'] = pd.to_datetime(buses['Fecha'] + ' ' + buses['Hora'])

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
df_final = pd.merge(resumen, buses[['datetime_expedicion', 'Pasajeros Bus']], on='datetime_expedicion', how='inner')
df_final['minutos_dia'] = df_final['datetime_expedicion'].dt.hour * 60 + df_final['datetime_expedicion'].dt.minute

# Entrenar modelo
X = df_final[['minutos_dia', 'vuelos_conectados', 'capacidad_total']]
y = df_final['Pasajeros Bus']

modelo = RandomForestRegressor(n_estimators=100, random_state=42)
modelo.fit(X, y)

# Guardar modelo
joblib.dump(modelo, 'modelo_prediccion_bus_v3.pkl')
print('✅ Modelo actualizado y guardado correctamente')
