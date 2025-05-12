import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import os
import plotly.express as px

st.set_page_config(page_title="Nivel Educativo y Renta/IDH", page_icon="🎓")

st.title("🎓 Nivel Educativo, Renta e IDH por Comunidad Autónoma")
st.markdown(
    """
    Este informe relaciona el nivel educativo medio de las comunidades con la renta disponible per cápita y el IDH.
    Puedes comparar la evolución y correlación entre educación, ingresos y desarrollo humano.
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
        df_edu = pd.read_sql_table('nivel_educativo_comunidades', _engine)
        df_idh = pd.read_sql_table('idhm_indice_desarrollo_humano_municipal', _engine)
        st.subheader("Vista previa de nivel educativo por comunidad")
        st.dataframe(df_edu.head())
        st.subheader("Vista previa de IDH municipal")
        st.dataframe(df_idh.head())
        return df_edu, df_idh
    except Exception as e:
        st.error(f"Error crítico al cargar datos: {e}")
        return pd.DataFrame(), pd.DataFrame()

if engine:
    df_edu, df_idh = load_data(engine)

    if not df_edu.empty and not df_idh.empty:
        st.header("Relación entre nivel educativo, renta e IDH")
        # Agrupar IDH y renta por comunidad y año
        df_idh_grouped = df_idh.groupby(['CODAUTO', 'year']).agg({
            'IDHM': 'mean',
            'renta_disponible_per_capita': 'mean'
        }).reset_index()

        # Unir con datos educativos por código de comunidad y año
        df_edu['ccaa_code'] = df_edu['ccaa_code'].astype(str)
        df_idh_grouped['CODAUTO'] = df_idh_grouped['CODAUTO'].astype(str)
        df_merged = pd.merge(
            df_edu,
            df_idh_grouped,
            left_on=['ccaa_code', 'año'],
            right_on=['CODAUTO', 'year'],
            how='inner'
        )

        st.subheader("Datos combinados de educación, renta e IDH")
        st.dataframe(df_merged.head(20))

        st.markdown("### Evolución del nivel educativo y renta/IDH por comunidad")
        comunidades = sorted(df_merged['ccaa_name'].dropna().unique())
        selected_ccaa = st.selectbox("Selecciona una comunidad autónoma:", comunidades)
        df_ccaa = df_merged[df_merged['ccaa_name'] == selected_ccaa]

        fig = px.line(
            df_ccaa,
            x='año',
            y=['media_total', 'renta_disponible_per_capita', 'IDHM'],
            labels={'value': 'Valor', 'año': 'Año', 'variable': 'Indicador'},
            title=f"Evolución de nivel educativo, renta e IDH en {selected_ccaa}"
        )
        st.plotly_chart(fig, use_container_width=True)

        st.header("Datos detallados de la comunidad seleccionada")
        st.dataframe(df_ccaa)
    else:
        st.warning("No se pudieron cargar los datos de educación o IDH.")
else:
    st.error("No se pudo conectar a la base de datos.")
