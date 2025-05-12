import streamlit as st
import folium
import geopandas as gpd
from streamlit_folium import st_folium
import os
import pandas as pd # Added import
import json # Added import

# Configuración de la página
st.set_page_config(page_title="Mapa Simple de Municipios", layout="wide")

st.title("🗺️ Mapa Simple de Municipios de España (TopoJSON)") # Updated title
st.markdown("Este mapa muestra los polígonos de los municipios de España directamente desde un archivo TopoJSON.") # Updated markdown

# --- Constantes ---\n# Updated to TopoJSON
TOPOJSON_FILENAME = "georef-spain-municipio.topojson"
TOPOJSON_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "ETL",
    "GeoRef_Spain",
    "TopoJSON", # Added TopoJSON directory
    TOPOJSON_FILENAME
)

# --- Funciones de Carga de Datos ---\n@st.cache_data
def load_spatial_data(path): # Renamed function
    """Carga los datos espaciales (TopoJSON) de los municipios.""" # Updated docstring
    try:
        if not os.path.exists(path):
            st.error(f"Error: No se encontró el archivo TopoJSON en la ruta: {path}") # Updated message
            return None

        gdf = gpd.read_file(path)
        
        if gdf.crs is None:
            gdf.set_crs("EPSG:4326", inplace=True)
        elif gdf.crs != "EPSG:4326":
            gdf = gdf.to_crs("EPSG:4326")

        code_col_options = ['mun_code', 'ine.ine_cod_municipio', 'natcode', 'cartodb_id']
        name_col_options = ['mun_name', 'nameunit', 'nombre']

        mun_code_col = None
        for col in code_col_options:
            if col in gdf.columns:
                mun_code_col = col
                break
        
        mun_name_col = None
        for col in name_col_options:
            if col in gdf.columns:
                mun_name_col = col
                break

        if not mun_code_col:
            st.error(f"No se pudo encontrar una columna de código municipal adecuada en el TopoJSON. Columnas disponibles: {gdf.columns.tolist()}")
            return None

        if pd.api.types.is_numeric_dtype(gdf[mun_code_col]):
             gdf[mun_code_col] = gdf[mun_code_col].astype(float).astype(int).astype(str).str.zfill(5)
        else:
             gdf[mun_code_col] = gdf[mun_code_col].astype(str).str.split('.').str[0].str.zfill(5)

        if mun_code_col != 'mun_code':
            gdf = gdf.rename(columns={mun_code_col: 'mun_code'})
        
        if mun_name_col and mun_name_col != 'mun_name':
            gdf = gdf.rename(columns={mun_name_col: 'mun_name'})
        elif not mun_name_col:
            gdf['mun_name'] = gdf['mun_code']

        gdf = gdf[gdf.is_valid]
        
        return gdf

    except Exception as e:
        st.error(f"Error al cargar o procesar el archivo TopoJSON: {e}")
        return None

# --- Cargar Datos ---
gdf_municipios = load_spatial_data(TOPOJSON_PATH) # Updated function call and path variable

if gdf_municipios is not None and not gdf_municipios.empty:
    st.subheader("Visualización del Mapa de Municipios (desde TopoJSON)") # Updated subheader

    # Crear mapa base centrado en España
    # Coordenadas aproximadas del centro de España
    map_center = [40.416775, -3.703790] 
    m = folium.Map(location=map_center, zoom_start=6, tiles="cartodbpositron")

    # Añadir capa TopoJSON al mapa
    tooltip_fields = []
    if 'mun_name' in gdf_municipios.columns:
        tooltip_fields.append('mun_name')
    if 'mun_code' in gdf_municipios.columns:
        tooltip_fields.append('mun_code')
    
    if not tooltip_fields: # Fallback si ninguna columna esperada está
        st.warning("Columnas 'mun_name' o 'mun_code' no encontradas para el tooltip. Usando las primeras dos columnas disponibles.")
        available_cols = [col for col in gdf_municipios.columns if col != gdf_municipios.geometry.name]
        tooltip_fields = available_cols[:2]

    try:
        # Leer el contenido del archivo TopoJSON
        with open(TOPOJSON_PATH, 'r', encoding='utf-8') as f:
            topojson_data = json.load(f)

        folium.TopoJson(
            topojson_data,
            object_path='objects.municipios', # Basado en object_name="municipios" en el script de conversión
            name="Municipios de España (TopoJSON)",
            style_function=lambda feature: {
                'fillColor': '#FFEDA0', 
                'color': 'black',       
                'weight': 0.5,          
                'fillOpacity': 0.7,
            },
            tooltip=folium.features.GeoJsonTooltip(
                fields=tooltip_fields,
                aliases=[f"{field.replace('_',' ').title()}:" for field in tooltip_fields],
                localize=True,
                sticky=False,
                labels=True,
                style="""
                    background-color: #F0EFEF;
                    border: 2px solid black;
                    border-radius: 3px;
                    box-shadow: 3px;
                """,
                max_width=800,
            )
        ).add_to(m)

        # Mostrar el mapa en Streamlit
        st_folium(m, width=None, height=700, use_container_width=True)
        st.caption("Pasa el ratón sobre un municipio para ver su nombre y código.")

    except Exception as e:
        st.error(f"Error al generar la capa TopoJson para Folium: {e}") # Updated message
        st.error("Esto podría deberse a problemas con el object_path, los nombres de las columnas para los tooltips o con los datos de geometría.")
        st.error(f"Columnas disponibles en gdf_municipios (usadas para inferir propiedades de tooltip): {gdf_municipios.columns.tolist()}")
        st.error(f"Campos seleccionados para tooltip: {tooltip_fields}")
        st.error(f"Asegúrate de que el archivo TopoJSON en '{TOPOJSON_PATH}' es válido y que el object_path 'objects.municipios' es correcto.")

else:
    st.warning("No se pudieron cargar los datos geoespaciales de los municipios o el archivo está vacío.")
    st.info(f"Ruta intentada para el TopoJSON: {TOPOJSON_PATH}") # Updated message

st.sidebar.info("Este es un mapa de prueba para verificar la carga y visualización de polígonos municipales desde un archivo TopoJSON.") # Updated sidebar info
