import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import joblib

# Cargar modelo entrenado
model = joblib.load("modelo_prediccion_bus_v3.pkl")

st.title("Predicción de saturación del bus en el aeropuerto de Bilbao")

# Subida de archivo Excel
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

            # Convertir a datetime
            df_vuelos["datetime_llegada"] = pd.to_datetime(df_vuelos["F. Vuelo"].astype(str).str[:10] + " " + df_vuelos["Real"].astype(str))

            # Tiempo de caminata según origen UE o no UE
            paises_ue = [  # Lista completa de aeropuertos UE ya integrada
               # España
    "MAD", "BCN", "AGP", "ALC", "BIO", "VLC", "SVQ", "SCQ", "PMI", "LPA", "TFN", "TFS", "FUE", "OVD", "RMU",
    # Alemania
    "FRA", "MUC", "DUS", "TXL", "HAM", "STR", "CGN", "HAJ", "LEJ", "NRN",
    # Francia
    "CDG", "ORY", "NCE", "LYS", "MRS", "TLS", "BOD", "NTE", "LIL", "BVA",
    # Italia
    "FCO", "CIA", "MXP", "LIN", "NAP", "VCE", "BLQ", "VRN", "PMO", "CTA",
    # Países Bajos
    "AMS", "EIN", "RTM", "MST", "GRQ",
    # Bélgica
    "BRU", "CRL", "ANR",
    # Portugal
    "LIS", "OPO", "FAO", "LPA", "PDL", "TER",
    # Suecia
    "ARN", "GOT", "MMX", "VXO", "BMA",
    # Dinamarca
    "CPH", "AAR", "BLL",
    # Finlandia
    "HEL", "TMP", "TKU", "QVY",
    # Grecia
    "ATH", "SKG", "HER", "RHO", "CFU",
    # Austria
    "VIE", "SZG", "GRZ", "INN", "LNZ",
    # Irlanda
    "DUB", "SNN", "ORK",
    # Polonia
    "WAW", "KRK", "GDN", "POZ", "KTW",

            ]
            df_vuelos["tiempo_caminata"] = df_vuelos["ORIGEN"].apply(lambda x: timedelta(minutes=30) if x in paises_ue else timedelta(minutes=45))

            # Hora en la que los pasajeros están listos para abordar
            df_vuelos["datetime_abordan"] = df_vuelos["datetime_llegada"] + df_vuelos["tiempo_caminata"]

            # Filtrar vuelos del día
            vuelos_dia = df_vuelos[df_vuelos["F. Vuelo"].astype(str).str.startswith(fecha_str)]

            # Inicializar lista para marcar vuelos ya asignados
            vuelos_asignados = []

            st.subheader(f"Resultados de ocupación para el día {fecha_str}")

            for hora in expediciones:
                datetime_expedicion = pd.to_datetime(f"{fecha_str} {hora}")

                # Filtrar vuelos que abordan hasta la expedición actual y que no hayan sido asignados
                vuelos_aptos = vuelos_dia[(
                    vuelos_dia["datetime_abordan"] <= datetime_expedicion
                ) & (~vuelos_dia.index.isin(vuelos_asignados))]

                # Marcar estos vuelos como ya asignados
                vuelos_asignados.extend(vuelos_aptos.index.tolist())

                capacidad_total = vuelos_aptos["Asientos Promedio"].sum()

                # Evitar predicciones por defecto: si no hay vuelos, capacidad_total = 0
                if capacidad_total == 0:
                    prediccion = 0
                else:
                    input_model = pd.DataFrame({"capacidad_avion": [capacidad_total]})
                    prediccion = model.predict(input_model)[0]

                # Mostrar resultados
                st.subheader(f"🕐 Expedición {hora} — {int(prediccion)} pasajeros")
                if prediccion >= 100:
                    st.error("🔴 Se espera saturación del autobús")
                elif prediccion >= 90:
                    st.warning("⚠️ Riesgo de saturación, revisar capacidad")
                else:
                    st.success("✅ No se prevé saturación")

    except Exception as e:
        st.error(f"Error al procesar el archivo: {e}")
