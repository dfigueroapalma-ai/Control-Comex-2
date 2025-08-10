import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
import plotly.express as px
import os

st.set_page_config(page_title="Control Documental Exportaciones V2", layout="wide")

# --------------------------
# Cargar comentarios previos
# --------------------------
COMENTARIOS_FILE = "comentarios.json"

if os.path.exists(COMENTARIOS_FILE):
    with open(COMENTARIOS_FILE, "r", encoding="utf-8") as f:
        comentarios_guardados = json.load(f)
else:
    comentarios_guardados = {}

# --------------------------
# Función para asignar estado documental
# --------------------------
def calcular_estado(row):
    if pd.notna(row["DHL #"]) and str(row["DHL #"]).strip() != "":
        return "Documentos Despachados"
    else:
        dias_para_eta = (row["ETA"] - datetime.now().date()).days
        if dias_para_eta > 16:
            return "A Tiempo"
        elif 11 <= dias_para_eta <= 15:
            return "Alerta"
        else:
            return "Crítico"

# --------------------------
# Función para detectar fuera de plazo facturación
# --------------------------
def fuera_plazo_facturacion(row):
    if pd.isna(row["Invoice #"]) or str(row["Invoice #"]).strip() == "":
        if (datetime.now().date() - row["ETD"]).days > 4:
            return True
    return False

# --------------------------
# Subida de archivo Excel
# --------------------------
st.sidebar.header("📂 Cargar archivo Excel")
archivo_excel = st.sidebar.file_uploader("Subir archivo", type=["xlsx"])

if archivo_excel:
    df = pd.read_excel(archivo_excel)
    
    # Convertir fechas
    df["ETD"] = pd.to_datetime(df["ETD"], errors="coerce").dt.date
    df["ETA"] = pd.to_datetime(df["ETA"], errors="coerce").dt.date
    
    # Agregar estado documental
    df["Estado Documental"] = df.apply(calcular_estado, axis=1)
    
    # Agregar columna fuera de plazo facturación
    df["Fuera Plazo Facturación"] = df.apply(fuera_plazo_facturacion, axis=1)
    
    # Restaurar comentarios guardados
    df["Comentarios"] = df["Doc Entry SAP"].astype(str).map(comentarios_guardados).fillna("")
    
    # --------------------------
    # FILTROS
    # --------------------------
    st.sidebar.header("🔍 Filtros")
    periodos = st.sidebar.multiselect("Period", sorted(df["Period"].dropna().unique()))
    empresas = st.sidebar.multiselect("Empresa", sorted(df["Empresa"].dropna().unique()))
    estados = st.sidebar.multiselect("Estado Documental", sorted(df["Estado Documental"].unique()))
    
    fecha_etd = st.sidebar.date_input("Filtrar ETD", [])
    fecha_eta = st.sidebar.date_input("Filtrar ETA", [])
    
    df_filtrado = df.copy()
    if periodos:
        df_filtrado = df_filtrado[df_filtrado["Period"].isin(periodos)]
    if empresas:
        df_filtrado = df_filtrado[df_filtrado["Empresa"].isin(empresas)]
    if estados:
        df_filtrado = df_filtrado[df_filtrado["Estado Documental"].isin(estados)]
    if fecha_etd:
        df_filtrado = df_filtrado[df_filtrado["ETD"].isin(fecha_etd)]
    if fecha_eta:
        df_filtrado = df_filtrado[df_filtrado["ETA"].isin(fecha_eta)]
    
    # --------------------------
    # KPIs
    # --------------------------
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📦 Total Referencias", len(df_filtrado))
    col2.metric("✅ Documentos Despachados", (df_filtrado["Estado Documental"] == "Documentos Despachados").sum())
    col3.metric("⚠️ En Alerta", (df_filtrado["Estado Documental"] == "Alerta").sum())
    col4.metric("🚨 Críticos", (df_filtrado["Estado Documental"] == "Crítico").sum())
    
    # --------------------------
    # Tabla con edición de comentarios
    # --------------------------
    st.subheader("📊 Estado Documental de Exportaciones")
    edited_df = st.data_editor(
        df_filtrado,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_config={
            "Comentarios": st.column_config.TextColumn("Comentarios", help="Notas adicionales sobre la referencia")
        }
    )
    
    # Guardar comentarios
    for _, row in edited_df.iterrows():
        comentarios_guardados[str(row["Doc Entry SAP"])] = row["Comentarios"]
    with open(COMENTARIOS_FILE, "w", encoding="utf-8") as f:
        json.dump(comentarios_guardados, f, ensure_ascii=False, indent=2)
    
    # --------------------------
    # Resaltar filas fuera de plazo facturación
    # --------------------------
    def resaltar_fila(row):
        if row["Fuera Plazo Facturación"]:
            return ['background-color: #ffcccc'] * len(row)
        else:
            return [''] * len(row)
    
    st.write("📌 Filas en **rojo** indican facturación fuera de plazo")
    st.dataframe(df_filtrado.style.apply(resaltar_fila, axis=1), use_container_width=True)
    
    # --------------------------
    # Gráficos
    # --------------------------
    st.subheader("📈 Distribución por Estado Documental")
    fig_estado = px.histogram(df_filtrado, x="Estado Documental", color="Estado Documental")
    st.plotly_chart(fig_estado, use_container_width=True)
    
    st.subheader("📈 Distribución por Period")
    fig_period = px.histogram(df_filtrado, x="Period", color="Estado Documental")
    st.plotly_chart(fig_period, use_container_width=True)

else:
    st.warning("Por favor, sube un archivo Excel para comenzar.")
