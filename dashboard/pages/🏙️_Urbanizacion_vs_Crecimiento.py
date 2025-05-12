import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import os
import plotly.express as px

st.set_page_config(page_title="Urbanización y Crecimiento Poblacional", page_icon="🏙️")

st.title("🏙️ Urbanización y Crecimiento Poblacional")
st.markdown(
    """
    Este informe relaciona la proporción urbana de cada municipio con el crecimiento de su población y su desarrollo humano.
    Puedes explorar cómo la urbanización influye en el crecimiento y el IDH municipal.
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
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    try:
        df_urb = pd.read_sql_table('distribucion_urbana', _engine)
        df_pop = pd.read_sql_table('cifras_poblacion_municipio', _engine)
        df_idh = pd.read_sql_table('idhm_indice_desarrollo_humano_municipal', _engine)
        st.subheader("Vista previa de urbanización")
        st.dataframe(df_urb.head())
        st.subheader("Vista previa de población")
        st.dataframe(df_pop.head())
        st.subheader("Vista previa de IDH municipal")
        st.dataframe(df_idh.head())
        return df_urb, df_pop, df_idh
    except Exception as e:
        st.error(f"Error crítico al cargar datos: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

if engine:
    df_urb, df_pop, df_idh = load_data(engine)

    if not df_urb.empty and not df_pop.empty and not df_idh.empty:
        st.header("Relación entre urbanización, crecimiento poblacional e IDH")
        # Usar el último año disponible en urbanización y población
        latest_year_urb = df_urb['year'].max()
        latest_year_pop = max([int(c) for c in df_pop.columns if c.isdigit()])
        latest_year_idh = df_idh['year'].max()

        df_urb_latest = df_urb[df_urb['year'] == latest_year_urb].copy()

        # Normalizar mun_code de población a string sin decimales
        df_pop_latest = df_pop[['mun_code', str(latest_year_pop)]].copy()
        df_pop_latest['mun_code'] = df_pop_latest['mun_code'].astype(float).astype(int).astype(str)
        df_pop_latest = df_pop_latest.rename(columns={str(latest_year_pop): 'poblacion'})

        # Normalizar mun_code de IDH a string
        df_idh_latest = df_idh[df_idh['year'] == latest_year_idh][['mun_code', 'IDHM']].copy()
        df_idh_latest['mun_code'] = df_idh_latest['mun_code'].astype(str)

        # Merge
        df_merged = pd.merge(df_urb_latest, df_pop_latest, on='mun_code', how='inner')
        df_merged = pd.merge(df_merged, df_idh_latest, on='mun_code', how='left')

        st.subheader(f"Datos combinados para el año {latest_year_urb}")
        st.dataframe(df_merged.head(20))

        st.markdown("### Dispersión: Proporción urbana vs Crecimiento poblacional")
        fig = px.scatter(
            df_merged,
            x='proporcion_urbana',
            y='poblacion',
            color='IDHM',
            labels={'proporcion_urbana': 'Proporción Urbana', 'poblacion': 'Población', 'IDHM': 'IDH Municipal'},
            title='Relación entre urbanización, población e IDH',
            hover_data=['mun_code']
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No se pudieron cargar los datos de urbanización, población o IDH.")
else:
    st.error("No se pudo conectar a la base de datos.")
