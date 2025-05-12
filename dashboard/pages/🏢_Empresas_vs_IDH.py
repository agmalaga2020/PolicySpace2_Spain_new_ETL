import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import os
import plotly.express as px

st.set_page_config(page_title="Empresas y Desarrollo Humano", page_icon="🏢")

st.title("🏢 Relación entre Empresas y Desarrollo Humano Municipal")
st.markdown(
    """
    Este informe analiza si los municipios con mayor número de empresas tienen un IDH más alto o mayor renta per cápita.
    Puedes explorar la relación entre empresas, IDH y renta a nivel municipal.
    """
)

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

def load_data(_engine):
    if not _engine:
        return pd.DataFrame(), pd.DataFrame()
    try:
        df_emp = pd.read_sql_table('empresas_municipio_actividad_principal', _engine)
        df_idh = pd.read_sql_table('idhm_indice_desarrollo_humano_municipal', _engine)
        st.subheader("Vista previa de empresas por municipio")
        st.dataframe(df_emp.head())
        st.subheader("Vista previa de IDH municipal")
        st.dataframe(df_idh.head())
        return df_emp, df_idh
    except Exception as e:
        st.error(f"Error crítico al cargar datos: {e}")
        return pd.DataFrame(), pd.DataFrame()

if engine:
    df_emp, df_idh = load_data(engine)

    if not df_emp.empty and not df_idh.empty:
        st.header("Relación entre empresas y desarrollo humano")
        # Usar el último año disponible en ambas tablas
        latest_year_emp = df_emp['year'].max()
        latest_year_idh = df_idh['year'].max()
        df_emp_latest = df_emp[df_emp['year'] == latest_year_emp].copy()
        df_idh_latest = df_idh[df_idh['year'] == latest_year_idh].copy()

        # Unir por código de municipio
        df_merged = pd.merge(
            df_emp_latest,
            df_idh_latest,
            left_on='mun_code',
            right_on='mun_code',
            how='inner',
            suffixes=('_emp', '_idh')
        )

        st.subheader(f"Datos combinados para el año empresas: {latest_year_emp}, IDH: {latest_year_idh}")
        st.dataframe(df_merged[['municipio_name', 'total_empresas', 'IDHM', 'renta_disponible_per_capita']].head(20))

        st.markdown("### Dispersión: Empresas vs IDH")
        fig = px.scatter(
            df_merged,
            x='total_empresas',
            y='IDHM',
            hover_name='municipio_name',
            labels={'total_empresas': 'Total Empresas', 'IDHM': 'IDH Municipal'},
            title='Relación entre número de empresas y IDH municipal'
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### Dispersión: Empresas vs Renta Disponible per cápita")
        fig2 = px.scatter(
            df_merged,
            x='total_empresas',
            y='renta_disponible_per_capita',
            hover_name='municipio_name',
            labels={'total_empresas': 'Total Empresas', 'renta_disponible_per_capita': 'Renta Disponible per cápita'},
            title='Relación entre número de empresas y renta disponible per cápita'
        )
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.warning("No se pudieron cargar los datos de empresas o IDH municipal.")
else:
    st.error("No se pudo conectar a la base de datos.")
