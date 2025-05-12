import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import os
import plotly.express as px

st.set_page_config(page_title="Ranking IDH Municipal", page_icon="🏆")

st.title("🏆 Ranking de Municipios por IDH")
st.markdown(
    """
    Este informe muestra el ranking de municipios según el Índice de Desarrollo Humano (IDH), 
    permite comparar los municipios con mayor y menor IDH, ver la evolución temporal y analizar los componentes: salud, educación e ingresos.
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

def load_idh_data(_engine):
    if not _engine:
        return pd.DataFrame()
    try:
        df_idh = pd.read_sql_table('idhm_indice_desarrollo_humano_municipal', _engine)
        st.subheader("Vista previa de datos IDH municipal")
        st.dataframe(df_idh.head())
        return df_idh
    except Exception as e:
        st.error(f"Error crítico al cargar datos IDH: {e}")
        return pd.DataFrame()

if engine:
    df_idh = load_idh_data(engine)

    if not df_idh.empty:
        st.header("Ranking de Municipios por IDH")
        latest_year = df_idh['year'].max()
        df_latest = df_idh[df_idh['year'] == latest_year].copy()
        df_latest = df_latest.sort_values(by='IDHM', ascending=False)

        st.markdown(f"### Top 10 municipios con mayor IDH ({latest_year})")
        st.dataframe(df_latest[['NOMBRE', 'IDHM', 'I_salud', 'I_educ', 'I_ingresos', 'population', 'renta_disponible_per_capita']].head(10))

        st.markdown(f"### 10 municipios con menor IDH ({latest_year})")
        st.dataframe(df_latest[['NOMBRE', 'IDHM', 'I_salud', 'I_educ', 'I_ingresos', 'population', 'renta_disponible_per_capita']].tail(10))

        st.header("Evolución temporal del IDH de un municipio")
        municipios = sorted(df_idh['NOMBRE'].dropna().unique())
        selected_municipio = st.selectbox("Selecciona un municipio para ver su evolución:", municipios)
        df_mun = df_idh[df_idh['NOMBRE'] == selected_municipio].sort_values(by='year')

        fig = px.line(df_mun, x='year', y=['IDHM', 'I_salud', 'I_educ', 'I_ingresos'],
                      labels={'value': 'Índice', 'year': 'Año', 'variable': 'Componente'},
                      title=f"Evolución del IDH y sus componentes en {selected_municipio}")
        st.plotly_chart(fig, use_container_width=True)

        st.header("Datos detallados del municipio seleccionado")
        st.dataframe(df_mun[['year', 'IDHM', 'I_salud', 'I_educ', 'I_ingresos', 'population', 'renta_disponible_per_capita']])
    else:
        st.warning("No se pudieron cargar los datos de IDH municipal.")
else:
    st.error("No se pudo conectar a la base de datos.")
