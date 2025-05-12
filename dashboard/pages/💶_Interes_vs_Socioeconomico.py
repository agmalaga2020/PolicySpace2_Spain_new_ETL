import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import os
import plotly.express as px

st.set_page_config(page_title="Interés y Variables Socioeconómicas", page_icon="💶")

st.title("💶 Impacto de los Tipos de Interés en Variables Socioeconómicas")
st.markdown(
    """
    Este informe analiza cómo la evolución de los tipos de interés se relaciona con la renta, la vivienda o el crecimiento poblacional.
    Puedes explorar la correlación entre interés nominal, real y otras variables económicas.
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

def load_interest_data(_engine):
    if not _engine:
        return pd.DataFrame()
    try:
        df_interest = pd.read_sql_table('interest_data_ETL', _engine)
        st.subheader("Vista previa de tipos de interés y variables asociadas")
        st.dataframe(df_interest.head())
        return df_interest
    except Exception as e:
        st.error(f"Error crítico al cargar datos de interés: {e}")
        return pd.DataFrame()

if engine:
    df_interest = load_interest_data(engine)

    if not df_interest.empty:
        st.header("Evolución de los tipos de interés y variables asociadas")
        variables = ['interest_fixed', 'interest_nominal', 'interest_real', 'mortgage', 'mortgage_x', 'mortgage_y']
        selected_vars = st.multiselect("Selecciona variables a visualizar:", variables, default=['interest_nominal', 'interest_real'])

        fig = px.line(
            df_interest,
            x='date',
            y=selected_vars,
            labels={'value': 'Valor', 'date': 'Fecha', 'variable': 'Variable'},
            title="Evolución de tipos de interés y variables asociadas"
        )
        st.plotly_chart(fig, use_container_width=True)

        st.header("Datos detallados")
        st.dataframe(df_interest)
    else:
        st.warning("No se pudieron cargar los datos de interés.")
else:
    st.error("No se pudo conectar a la base de datos.")
