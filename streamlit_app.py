import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import joblib

# Cargar modelo entrenado
model = joblib.load("modelo_prediccion_bus_v3.pkl")

st.title("Predicción de saturación del bus en el aeropuerto de Bilbao")

# Utilidad para evitar errores de codificación
def texto_seguro(texto):
    try:
        return str(texto).encode("utf-8", errors="replace").decode("utf-8")
    except:
        return "[Error al mostrar texto]"

# Subida del archivo Excel
uploaded_file = st.file_uploader("Sube tu archivo Excel (.xlsx)", type=["xlsx"])

if uploaded_file:
    try:
        df_vuelos = pd.read_excel(uploaded_file, sheet_name="Vuelos")

        # Verificar columnas necesarias
        required_cols = ["F. Vuelo", "Real", "ORIGEN", "Asientos Promedio"]
        if not all(col in df_vuelos.columns for col in required_cols):
            st.error(texto_seguro(f"El archivo debe contener las columnas: {required_cols}"))
        else:
            # Conversión de columnas a datetime
            df_vuelos["datetime_llegada"] = pd.to_datetime(df_vuelos["F. Vuelo"].astype(str).str[:10] + " " + df_vuelos["Real"].astype(str))

            # Tiempo de caminata por origen
            paises_ue = ["BCN", "ALC", "MAD"]  # simplificado
            df_vuelos["tiempo_caminata"] = df_vuelos["ORIGEN"].apply(lambda x: timedelta(minutes=30) if x in paises_ue else timedelta(minutes=45))
            df_vuelos["datetime_abordan"] = df_vuelos["datetime_llegada"] + df_vuelos["tiempo_caminata"]

            # Selección de fecha
            fechas_disponibles = sorted(df_vuelos["datetime_llegada"].dt.date.unique())
            fecha_seleccionada = st.date_input("Selecciona el día de la predicción", value=fechas_disponibles[0])

            vuelos_dia = df_vuelos[df_vuelos["datetime_llegada"].dt.date == fecha_seleccionada]

            if vuelos_dia.empty:
                st.warning("No hay vuelos para ese día en el archivo.")
            else:
                # Generar todas las expediciones
                inicio = datetime.strptime("06:00", "%H:%M")
                fin = datetime.strptime("23:30", "%H:%M")
                hora_actual = inicio

                while hora_actual <= fin:
                    datetime_expedicion = datetime.combine(fecha_seleccionada, hora_actual.time())
                    vuelos_aptos = vuelos_dia[vuelos_dia["datetime_abordan"] <= datetime_expedicion]
                    capacidad_total = vuelos_aptos["Asientos Promedio"].sum()
                    input_modelo = pd.DataFrame({"capacidad_avion": [capacidad_total]})
                    prediccion = model.predict(input_modelo)[0]

                    mensaje = texto_seguro(f"\ud83d\udd52 Expedición {hora_actual.strftime('%H:%M')} — {int(prediccion)} pasajeros")
                    st.subheader(mensaje)

                    if prediccion >= 100:
                        st.error(texto_seguro("\ud83d\udd34 Se espera saturación del autobús"))
                    elif prediccion >= 90:
                        st.warning(texto_seguro("\ud83d\udd39 Riesgo de saturación"))
                    else:
                        st.success(texto_seguro("\u2705 No se prevé saturación"))

                    hora_actual += timedelta(minutes=15)

    except Exception as e:
        st.error(texto_seguro(f"Error al procesar el archivo: {e}"))
else:
    st.warning("Aún no has subido ningún archivo")
