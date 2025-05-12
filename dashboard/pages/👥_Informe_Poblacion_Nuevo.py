import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import os

st.set_page_config(page_title="Nuevo Informe: Población Municipal", page_icon="👥")

st.title("👥 Nuevo Informe: Análisis de Población Municipal")
st.markdown("Este informe muestra datos y visualizaciones sobre la población, revisando los datos y el merge antes de mostrar resultados.")

DB_FILENAME = "datawarehouse.db"
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data base", DB_FILENAME)

@st.cache_resource
def get_engine():
    if not os.path.exists(DB_PATH):
        st.error(f"Error: No se encontró el archivo de la base de datos: {DB_PATH}")
        return None
    try:
        engine = create_engine(f"sqlite:///{DB_PATH}")
        return engine
    except Exception as e:
        st.error(f"Error al conectar: {e}")
        return None

engine = get_engine()

def load_population_data(_engine):
    if not _engine:
        return pd.DataFrame(), pd.DataFrame()
    try:
        # Cargar datos de población
        df_pop = pd.read_sql_table('cifras_poblacion_municipio', _engine)
        # Revisar los primeros registros
        st.subheader("Vista previa de datos de población")
        st.dataframe(df_pop.head())

        # Convertir mun_code a string con ceros a la izquierda (3 dígitos)
        df_pop['mun_code_str'] = df_pop['mun_code'].astype(float).astype(int).astype(str).str.zfill(3)

        # Cargar equivalencias
        df_eq = pd.read_sql_query('SELECT * FROM vista_equivalencias_unicas', _engine)
        st.subheader("Vista previa de equivalencias")
        st.dataframe(df_eq.head())

        # Merge
        df_merged = pd.merge(df_pop, df_eq, left_on='mun_code_str', right_on='CMUN', how='left')
        st.subheader("Vista previa del merge")
        st.dataframe(df_merged[['mun_code', 'mun_code_str', 'CMUN', 'NOMBRE']].head())

        return df_merged, df_eq
    except Exception as e:
        st.error(f"Error crítico en load_population_data: {e}")
        return pd.DataFrame(), pd.DataFrame()

if engine:
    df_pop_merged, df_equivalencias = load_population_data(engine)

    if not df_pop_merged.empty:
        st.header("Evolución de Población por Municipio")

        municipios = []
        if 'NOMBRE' in df_equivalencias.columns:
            municipios = sorted(df_equivalencias['NOMBRE'].dropna().unique())

        if municipios:
            selected_municipio = st.selectbox("Selecciona un municipio:", municipios)
        else:
            selected_municipio = None
            st.warning("No se encontraron municipios en los datos de equivalencias.")

        if selected_municipio:
            df_mun_filtered = df_pop_merged[df_pop_merged['NOMBRE'] == selected_municipio].copy()
            if df_mun_filtered.empty:
                st.warning(f"No hay datos para el municipio seleccionado: {selected_municipio}.")
            else:
                # Mostrar evolución por años
                years = [col for col in df_mun_filtered.columns if col.isdigit()]
                df_evolucion = df_mun_filtered.melt(id_vars=['NOMBRE'], value_vars=years, var_name='Año', value_name='Población')
                df_evolucion = df_evolucion.dropna(subset=['Población'])
                st.line_chart(df_evolucion.set_index('Año')['Población'])

                st.header("Datos Detallados (Años)")
                st.dataframe(df_evolucion)
    else:
        st.warning("No se pudieron cargar los datos de población iniciales ('cifras_poblacion_municipio').")
else:
    st.error("No se pudo conectar a la base de datos.")
