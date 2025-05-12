import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import os
import plotly.express as px

st.set_page_config(page_title="Fecundidad y Envejecimiento", page_icon="👶")

st.title("👶 Tasas de Fecundidad y Envejecimiento")
st.markdown(
    """
    Este informe compara la evolución de la fecundidad por provincia y comunidad, y su impacto en la estructura poblacional.
    Puedes analizar tendencias de natalidad y envejecimiento a nivel regional.
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

def load_fecundidad_data(_engine):
    if not _engine:
        return pd.DataFrame()
    try:
        df_fec = pd.read_sql_table('indicadores_fecundidad_municipio_provincias', _engine)
        st.subheader("Vista previa de tasas de fecundidad")
        st.dataframe(df_fec.head())
        return df_fec
    except Exception as e:
        st.error(f"Error crítico al cargar datos de fecundidad: {e}")
        return pd.DataFrame()

if engine:
    df_fec = load_fecundidad_data(engine)

    if not df_fec.empty:
        st.header("Evolución de la fecundidad por provincia")
        provincias = sorted(df_fec['provincias_name'].dropna().unique())
        selected_prov = st.selectbox("Selecciona una provincia:", provincias)
        edades = sorted(df_fec['edad'].dropna().unique())
        selected_edades = st.multiselect("Selecciona grupo(s) de edad:", edades, default=edades)

        df_prov = df_fec[
            (df_fec['provincias_name'] == selected_prov) &
            (df_fec['edad'].isin(selected_edades))
        ]

        fig = px.line(
            df_prov,
            x='year',
            y='tasa_fert_prov',
            color='edad',
            labels={'tasa_fert_prov': 'Tasa de Fecundidad', 'year': 'Año', 'edad': 'Edad'},
            title=f"Evolución de la tasa de fecundidad en {selected_prov}"
        )
        st.plotly_chart(fig, use_container_width=True)

        st.header("Evolución de la fecundidad por comunidad autónoma")
        comunidades = sorted(df_fec['Comunidad Autónoma'].dropna().unique())
        selected_ccaa = st.selectbox("Selecciona una comunidad autónoma:", comunidades)
        selected_edades_ccaa = st.multiselect("Selecciona grupo(s) de edad (CCAA):", edades, default=edades, key="edad_ccaa")

        df_ccaa = df_fec[
            (df_fec['Comunidad Autónoma'] == selected_ccaa) &
            (df_fec['edad'].isin(selected_edades_ccaa))
        ]

        fig2 = px.line(
            df_ccaa,
            x='year',
            y='tasa_fert_prov',
            color='edad',
            labels={'tasa_fert_prov': 'Tasa de Fecundidad', 'year': 'Año', 'edad': 'Edad'},
            title=f"Evolución de la tasa de fecundidad en {selected_ccaa}"
        )
        st.plotly_chart(fig2, use_container_width=True)

        st.header("Datos detallados")
        st.dataframe(df_fec)
    else:
        st.warning("No se pudieron cargar los datos de fecundidad.")
else:
    st.error("No se pudo conectar a la base de datos.")
