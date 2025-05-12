import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import os
import json
import plotly.express as px
import numpy as np
from io import BytesIO # Para descarga Excel

# --- Configuración y Conexión ---
st.set_page_config(page_title="Informes Guardados", page_icon="📂")

st.title("📂 Informes Guardados")
st.markdown("Carga y visualiza las configuraciones de informes guardadas.")

DB_FILENAME = "datawarehouse.db"
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data base", DB_FILENAME)
REPORTS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "saved_reports.json")

@st.cache_resource
def get_engine():
    if not os.path.exists(DB_PATH):
        st.error(f"Error: No se encontró el archivo de la base de datos: {DB_PATH}")
        return None
    try:
        return create_engine(f"sqlite:///{DB_PATH}")
    except Exception as e:
        st.error(f"Error al conectar: {e}")
        return None

engine = get_engine()

def load_saved_reports():
    """Carga los informes guardados desde el archivo JSON."""
    if os.path.exists(REPORTS_FILE):
        try:
            with open(REPORTS_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            st.warning("El archivo de informes guardados está corrupto o vacío.")
            return {}
    else:
        st.info("No hay informes guardados todavía.")
        return {}

@st.cache_data
def load_data(_engine, table_name):
    """Carga los datos de una tabla específica."""
    if not _engine: return pd.DataFrame()
    try:
        return pd.read_sql_table(table_name, _engine)
    except Exception as e:
        st.error(f"Error al cargar la tabla '{table_name}': {e}")
        return pd.DataFrame()

# Funciones de descarga (copiadas de app.py para reutilizar)
@st.cache_data
def convert_df_to_csv(df_to_convert):
    return df_to_convert.to_csv(index=False).encode('utf-8')

@st.cache_data
def convert_df_to_excel(df_to_convert):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_to_convert.to_excel(writer, index=False, sheet_name='Datos')
    processed_data = output.getvalue()
    return processed_data

# --- Cargar y Mostrar Informes Guardados ---
saved_reports = load_saved_reports()

if engine and saved_reports:
    report_names = list(saved_reports.keys())
    selected_report_name = st.selectbox("Selecciona un informe guardado para cargar:", report_names, index=None, placeholder="Elige un informe...")

    if selected_report_name:
        st.header(f"Informe: {selected_report_name}")
        config = saved_reports[selected_report_name]
        
        # Cargar datos de la tabla del informe
        table_name = config.get("table")
        if not table_name:
            st.error("La configuración del informe no especifica una tabla.")
        else:
            df_report = load_data(engine, table_name)

            if not df_report.empty:
                # Aplicar filtros guardados
                filters = config.get("filters", {})
                df_filtered_report = df_report.copy()
                st.write("Filtros aplicados en este informe:")
                st.json(filters)

                for col_name_display, selected_values in filters.items():
                     # Encontrar el código de columna original (necesitamos mapeo inverso o buscar por valor)
                     # Esto es un poco frágil, sería mejor guardar el col_code en el JSON
                     col_code = None
                     filter_columns_map = { # Recrear mapa (o importarlo de un utils)
                         'Año': 'year', 'Código Municipio': 'mun_code', 'Código Provincia': 'cpro',
                         'Código CCAA': 'ccaa_code', 'Sexo': 'sex', 'CNAE (Act. Principal)': 'CNAE'
                     }
                     col_code = filter_columns_map.get(col_name_display)

                     if col_code and col_code in df_filtered_report.columns and selected_values:
                         # Reaplicar lógica de filtrado (similar a app.py)
                         if pd.api.types.is_numeric_dtype(df_filtered_report[col_code].dropna()):
                             try:
                                 # Intentar convertir los valores guardados al tipo original
                                 original_dtype = df_report[col_code].dropna().dtype
                                 selected_values_typed = [original_dtype.type(v) for v in selected_values]
                                 df_filtered_report = df_filtered_report[df_filtered_report[col_code].isin(selected_values_typed)]
                             except:
                                 df_filtered_report = df_filtered_report[df_filtered_report[col_code].astype(str).isin(map(str, selected_values))]
                         else:
                             df_filtered_report = df_filtered_report[df_filtered_report[col_code].astype(str).isin(map(str, selected_values))]


                st.subheader("📊 Datos del Informe")
                st.dataframe(df_filtered_report)

                # Descargar datos del informe
                csv_report_data = convert_df_to_csv(df_filtered_report)
                st.download_button(f"Descargar CSV ({selected_report_name})", csv_report_data, f"{selected_report_name}.csv", "text/csv", key=f"csv_{selected_report_name}")
                excel_report_data = convert_df_to_excel(df_filtered_report)
                st.download_button(f"Descargar Excel ({selected_report_name})", excel_report_data, f"{selected_report_name}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"excel_{selected_report_name}")


                # Regenerar gráfico guardado
                chart_config = config.get("chart_config", {})
                x_axis = chart_config.get("x_axis")
                y_axis = chart_config.get("y_axis")
                chart_type = chart_config.get("chart_type")

                if x_axis and y_axis and chart_type:
                    st.subheader("📈 Gráfico del Informe")
                    try:
                        title = f"{y_axis} vs {x_axis} ({chart_type}) - Informe: {selected_report_name}"
                        if chart_type == "Dispersión (Scatter)":
                            fig = px.scatter(df_filtered_report, x=x_axis, y=y_axis, title=title, hover_data=df_filtered_report.columns)
                        elif chart_type == "Líneas":
                            df_plot = df_filtered_report.sort_values(by=x_axis) if x_axis in df_filtered_report.columns else df_filtered_report
                            fig = px.line(df_plot, x=x_axis, y=y_axis, title=title)
                        elif chart_type == "Barras":
                            fig = px.bar(df_filtered_report, x=x_axis, y=y_axis, title=title)
                        
                        st.plotly_chart(fig, use_container_width=True)
                    except Exception as e:
                        st.error(f"Error al regenerar el gráfico guardado: {e}")
                else:
                    st.info("Este informe no tenía una configuración de gráfico guardada.")

            else:
                st.warning(f"No se pudieron cargar los datos para la tabla '{table_name}' de este informe.")

elif not saved_reports:
    st.info("Aún no has guardado ningún informe desde la página principal.")
else:
     st.error("No se pudo conectar a la base de datos.")
