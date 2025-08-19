import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import joblib

# Cargar el modelo entrenado
model = joblib.load("modelo_prediccion_bus_v3.pkl")

st.title("Predicción de saturación del bus en el aeropuerto de Bilbao")

# Subir archivo Excel
uploaded_file = st.file_uploader("Sube tu archivo Excel (.xlsx)", type=["xlsx"])

# Selector de fecha
fecha_prediccion = st.date_input("Selecciona el día de la predicción", value=datetime.today())

if uploaded_file:
    try:
        df_vuelos = pd.read_excel(uploaded_file, sheet_name="Vuelos")

        # Validar columnas requeridas
        columnas_necesarias = ["F. Vuelo", "Real", "ORIGEN", "Asientos Promedio"]
        if not all(col in df_vuelos.columns for col in columnas_necesarias):
            st.error(f"El archivo debe contener las columnas: {columnas_necesarias}")
        else:
            # Convertir a datetime
            df_vuelos["F. Vuelo"] = pd.to_datetime(df_vuelos["F. Vuelo"], errors='coerce')
            df_vuelos["Real"] = pd.to_datetime(df_vuelos["Real"].astype(str), format='%H:%M', errors='coerce').dt.time
            df_vuelos = df_vuelos.dropna(subset=["F. Vuelo", "Real"])  # eliminar filas con fechas u horas no convertibles

            # Crear datetime de llegada combinando fecha + hora
            df_vuelos["datetime_llegada"] = df_vuelos.apply(lambda row: datetime.combine(row["F. Vuelo"].date(), row["Real"]), axis=1)

            # Asignar tiempos de caminata
            paises_ue = ["BCN", "ALC", "MAD", "VLC"]  # orígenes de la UE
            df_vuelos["tiempo_caminata"] = df_vuelos["ORIGEN"].apply(lambda x: timedelta(minutes=30) if x in paises_ue else timedelta(minutes=45))
            df_vuelos["datetime_abordan"] = df_vuelos["datetime_llegada"] + df_vuelos["tiempo_caminata"]

            # Filtrar vuelos solo del día seleccionado
            vuelos_dia = df_vuelos[df_vuelos["F. Vuelo"].dt.date == fecha_prediccion]

            if vuelos_dia.empty:
                st.warning("No hay vuelos para ese día en el archivo.")
            else:
                # Crear lista de horarios desde 06:00 a 23:30
                inicio = datetime.combine(fecha_prediccion, datetime.strptime("06:00", "%H:%M").time())
                fin = datetime.combine(fecha_prediccion, datetime.strptime("23:30", "%H:%M").time())
                horarios = []
                while inicio <= fin:
                    horarios.append(inicio)
                    inicio += timedelta(minutes=15)

                for hora_expedicion in horarios:
                    # Pasajeros que llegan a tiempo exacto
                    abordajes = vuelos_dia[(vuelos_dia["datetime_abordan"] <= hora_expedicion)]

                    # Pero deben restarse los que ya abordaron antes
                    for h_prev in horarios:
                        if h_prev >= hora_expedicion:
                            break
                        ya_contados = vuelos_dia[(vuelos_dia["datetime_abordan"] <= h_prev)]
                        abordajes = abordajes[~abordajes.index.isin(ya_contados.index)]

                    pasajeros = abordajes["Asientos Promedio"].sum()

                    # Predecir ocupación
                    input_modelo = pd.DataFrame({"capacidad_avion": [pasajeros]})
                    prediccion = model.predict(input_modelo)[0]

                    # Mostrar resultados
                    st.markdown(f"### 🕒 Expedición {hora_expedicion.strftime('%H:%M')} — {int(pasajeros)} pasajeros")

                    if prediccion >= 100:
                        st.error("🔴 Se espera saturación del autobús")
                    elif prediccion >= 90:
                        st.warning("⚠️ Riesgo de saturación, revisar capacidad")
                    else:
                        st.success("🟢 No se prevé saturación")

    except Exception as e:
        st.error(f"Error al procesar el archivo: {e}")
