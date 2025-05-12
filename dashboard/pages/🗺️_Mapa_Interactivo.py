import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import sqlite3
import os
import json # Ensure json is imported
from topojson import Topology # MODIFIED: Import Topology directly
import numpy as np # ADDED: Import NumPy

# Configuración de la página
st.set_page_config(page_title="Mapa de Densidad Poblacional", layout="wide")

st.title("Mapa Interactivo de Densidad de Población Municipal")

# --- Rutas a los archivos ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "data base", "datawarehouse.db")
# GEOJSON_PATH = os.path.join(BASE_DIR, "ETL", "GeoRef_Spain", "georef-spain-municipio.geojson") # Old path
TOPOJSON_PATH = os.path.join(BASE_DIR, "ETL", "GeoRef_Spain", "TopoJSON", "georef-spain-municipio.topojson") # New path to TopoJSON


# --- Funciones de carga de datos ---
@st.cache_data
def get_available_years(_conn):
    """Obtiene los años disponibles de la tabla de población."""
    try:
        # Intenta obtener información de las columnas de la tabla de población
        cursor = _conn.cursor()
        cursor.execute("PRAGMA table_info(cifras_poblacion_municipio)")
        columns_info = cursor.fetchall()
        # Filtra las columnas que son años (numéricas) y las ordena
        year_columns = sorted([info[1] for info in columns_info if info[1].isdigit()], reverse=True)
        return year_columns
    except sqlite3.Error as e:
        st.error(f"Error al obtener años de la base de datos: {e}")
        return []

@st.cache_data
def load_population_data(_conn, selected_year_str):
    """Carga datos de población para un año específico directamente de cifras_poblacion_municipio."""
    try:
        query_poblacion = f"SELECT mun_code, `{selected_year_str}` AS poblacion FROM cifras_poblacion_municipio WHERE `{selected_year_str}` IS NOT NULL"
        df_pop = pd.read_sql_query(query_poblacion, _conn)
        
        df_pop['mun_code'] = df_pop['mun_code'].astype(str).str.split('.').str[0].str.zfill(5)
        df_pop['poblacion'] = pd.to_numeric(df_pop['poblacion'], errors='coerce').fillna(0)
        
        return df_pop
    except sqlite3.Error as e:
        st.error(f"Error al cargar datos de población: {e}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Un error inesperado ocurrió al cargar datos de población: {e}")
        return pd.DataFrame()

@st.cache_data
def load_spatial_data(path):
    """
    Carga los datos espaciales TopoJSON.
    Retorna un GeoDataFrame procesado (para fusiones y tooltips) y 
    un diccionario GeoJSON FeatureCollection (para la capa Choropleth) 
    con códigos municipales estandarizados.
    """
    # t_start_func = time.time() # REMOVED
    try:
        if not os.path.exists(path):
            st.error(f"Archivo TopoJSON no encontrado en la ruta: {path}")
            return None, None

        # 1. Cargar TopoJSON como diccionario Python para modificación y uso en Choropleth
        # t_before_json_load = time.time() # REMOVED
        with open(path, 'r', encoding='utf-8') as f:
            topo_data_dict = json.load(f)
        # st.write(f"[load_spatial_data] Diccionario TopoJSON cargado en {time.time() - t_before_json_load:.2f}s") # REMOVED

        # 2. Cargar con GeoPandas para crear el GeoDataFrame (para fusionar, tooltips, cálculo de área)
        # t_before_gdf_load = time.time() # REMOVED
        gdf = gpd.read_file(path)
        # st.write(f"[load_spatial_data] GeoDataFrame cargado desde TopoJSON en {time.time() - t_before_gdf_load:.2f}s. Columnas iniciales: {gdf.columns.tolist()[:10]}...") # REMOVED

        # 3. Manejo de CRS para GDF
        # t_before_crs = time.time() # REMOVED
        if gdf.crs is None:
            gdf.set_crs("EPSG:4326", inplace=True)
        elif gdf.crs != "EPSG:4326":
            gdf = gdf.to_crs("EPSG:4326")
        # st.write(f"[load_spatial_data] Manejo de CRS completado en {time.time() - t_before_crs:.2f}s") # REMOVED

        # 4. Identificar el nombre original de la columna del código municipal en GDF (y, por lo tanto, en las propiedades de TopoJSON)
        code_col_options = ['mun_code', 'ine.ine_cod_municipio', 'natcode', 'cartodb_id']
        mun_code_col_original_name = None
        for col in code_col_options:
            if col in gdf.columns:
                mun_code_col_original_name = col
                break
        
        if not mun_code_col_original_name:
            st.error(f"No se pudo encontrar una columna de código municipal adecuada en el TopoJSON. Columnas disponibles: {gdf.columns.tolist()}")
            return None, None 
        # st.write(f"[load_spatial_data] Columna de código municipal original identificada como: '{mun_code_col_original_name}'") # REMOVED

        # 5. Estandarizar mun_code en el GDF (para fusionar con datos de población)
        # t_before_gdf_mun_code_std = time.time() # REMOVED
        temp_standardized_col_name = "__temp_standardized_mun_code__"
        if pd.api.types.is_numeric_dtype(gdf[mun_code_col_original_name]):
            gdf[temp_standardized_col_name] = gdf[mun_code_col_original_name].astype(float).astype(int).astype(str).str.zfill(5)
        else:
            gdf[temp_standardized_col_name] = gdf[mun_code_col_original_name].astype(str).str.split('.').str[0].str.zfill(5)
        
        if 'mun_code' in gdf.columns and 'mun_code' != mun_code_col_original_name:
            gdf.drop(columns=['mun_code'], inplace=True) 
        if mun_code_col_original_name != temp_standardized_col_name and mun_code_col_original_name in gdf.columns: 
             gdf.drop(columns=[mun_code_col_original_name], inplace=True) 
        gdf.rename(columns={temp_standardized_col_name: 'mun_code'}, inplace=True)
        # st.write(f"[load_spatial_data] Estandarización de 'mun_code' en GDF completada en {time.time() - t_before_gdf_mun_code_std:.2f}s. GDF tiene ahora {len(gdf)} filas.") # REMOVED

        # 6. Estandarizar códigos y nombre de propiedad EN EL DICCIONARIO TOPOJSON
        # t_before_dict_mun_code_std = time.time() # REMOVED
        object_key = "municipios" 
        if 'objects' not in topo_data_dict or object_key not in topo_data_dict.get('objects', {}):
            if 'objects' in topo_data_dict and isinstance(topo_data_dict['objects'], dict):
                 potential_keys = list(topo_data_dict['objects'].keys())
                 if potential_keys:
                     object_key = potential_keys[0] 
                     # st.warning(f"[load_spatial_data] Clave de objeto TopoJSON '{object_key}' no encontrada. Usando la primera clave disponible: '{object_key}'") # REMOVED
                 else:
                     st.error("[load_spatial_data] No se encontraron objetos en el TopoJSON.")
                     return None, None 
            else:
                st.error("[load_spatial_data] Estructura de TopoJSON inválida: falta 'objects' o no es un diccionario.")
                return None, None 
        # else: # REMOVED
            # st.write(f"[load_spatial_data] Usando clave de objeto TopoJSON: '{object_key}'") # REMOVED

        if 'geometries' not in topo_data_dict.get('objects', {}).get(object_key, {}):
            st.error(f"La capa de objetos '{object_key}' en TopoJSON no contiene 'geometries'.")
            return None, None 

        geometries = topo_data_dict['objects'][object_key]['geometries']
        # st.write(f"[load_spatial_data] Total de geometrías encontradas en TopoJSON ('{object_key}'): {len(geometries)}") # REMOVED

        num_features_processed_dict = 0
        num_features_missing_properties = 0
        num_features_properties_is_none = 0

        for i, feature in enumerate(geometries):
            if 'properties' not in feature:
                num_features_missing_properties += 1
                continue 
            
            if feature.get('properties') is None:
                num_features_properties_is_none +=1
                continue 

            if mun_code_col_original_name in feature['properties']:
                raw_code = feature['properties'][mun_code_col_original_name]
                raw_code_str = str(raw_code)
                standardized_code = raw_code_str.split('.')[0].zfill(5)
                feature['properties']['mun_code'] = standardized_code 
                if mun_code_col_original_name != 'mun_code': 
                    del feature['properties'][mun_code_col_original_name]
                num_features_processed_dict += 1
        
        if num_features_missing_properties > 0:
            st.warning(f"[load_spatial_data] {num_features_missing_properties} características no tenían la clave 'properties'.")
        if num_features_properties_is_none > 0:
            st.warning(f"[load_spatial_data] {num_features_properties_is_none} características tenían 'properties' establecido a None.")

        # st.write(f"[load_spatial_data] Estandarización de 'mun_code' en diccionario TopoJSON completada en {time.time() - t_before_dict_mun_code_std:.2f}s. {num_features_processed_dict} características procesadas.") # REMOVED

        # 6.1 Convertir el TopoJSON modificado (o su capa relevante) a GeoJSON FeatureCollection
        # t_before_topo_to_geojson = time.time() # REMOVED
        geojson_feature_collection = None
        if topo_data_dict and 'objects' in topo_data_dict and object_key in topo_data_dict['objects']:
            try:
                topology_instance = Topology(topo_data_dict, object_name=object_key)
                converted_geojson = topology_instance.to_geojson() 
                
                # st.write(f"[load_spatial_data] TopoJSON layer '{object_key}' conversion attempt with Topology class took {time.time() - t_before_topo_to_geojson:.2f}s") # REMOVED

                if isinstance(converted_geojson, str):
                    try:
                        geojson_feature_collection = json.loads(converted_geojson)
                        # st.write("[load_spatial_data] Conversión de cadena JSON a diccionario GeoJSON exitosa.") # REMOVED
                    except json.JSONDecodeError as e_json:
                        st.error(f"[load_spatial_data] Error al decodificar la cadena GeoJSON: {e_json}")
                        geojson_feature_collection = topo_data_dict 
                elif isinstance(converted_geojson, dict):
                    geojson_feature_collection = converted_geojson 
                    # st.write("[load_spatial_data] Conversion returned a dictionary directly.") # REMOVED
                else:
                    st.warning(f"[load_spatial_data] Topology().to_geojson() returned an unexpected type: {type(converted_geojson)}. Fallback.")
                    geojson_feature_collection = topo_data_dict 

                if isinstance(geojson_feature_collection, dict) and geojson_feature_collection.get('type') == 'FeatureCollection':
                    num_features = len(geojson_feature_collection.get('features', []))
                    # st.write(f"[load_spatial_data] Successfully processed/loaded GeoJSON FeatureCollection. Number of features: {num_features}") # REMOVED
                    if num_features == 0 and len(topo_data_dict.get('objects', {}).get(object_key, {}).get('geometries', [])) > 0:
                        st.warning("[load_spatial_data] GeoJSON FeatureCollection tiene 0 características, pero el TopoJSON original tenía geometrías. Verifique la conversión.")
                elif geojson_feature_collection is not topo_data_dict: 
                    st.warning(f"[load_spatial_data] Processed data is not a valid GeoJSON FeatureCollection dictionary. Type: {type(geojson_feature_collection)}. Will attempt to use TopoJSON dict directly if this was the result of conversion.")
                    if not isinstance(geojson_feature_collection, dict): 
                         geojson_feature_collection = topo_data_dict 
            
            except Exception as e_topo_convert:
                st.error(f"[load_spatial_data] Error al convertir la capa TopoJSON '{object_key}' a GeoJSON usando Topology().to_geojson(): {e_topo_convert}")
                st.exception(e_topo_convert) 
                geojson_feature_collection = topo_data_dict 
                st.warning("[load_spatial_data] Fallback: Se usará el diccionario TopoJSON modificado directamente para Folium.")
        else:
            st.error("[load_spatial_data] No se pudo encontrar la capa de objetos para convertir a GeoJSON. Se usará el diccionario TopoJSON original si está disponible.")
            geojson_feature_collection = topo_data_dict 

        if geojson_feature_collection is None: 
             st.error("[load_spatial_data] geojson_feature_collection es None después del intento de conversión. Fallback a topo_data_dict.")
             geojson_feature_collection = topo_data_dict


        # 7. Estandarizar mun_name en GDF
        # t_before_gdf_mun_name_std = time.time() # REMOVED
        name_col_options = ['mun_name', 'nameunit', 'nombre']
        mun_name_col_original = None
        for col in name_col_options:
            if col in gdf.columns:
                mun_name_col_original = col
                break
        if mun_name_col_original:
            if mun_name_col_original != 'mun_name': 
                if 'mun_name' in gdf.columns: 
                    gdf.drop(columns=['mun_name'], inplace=True)
                gdf.rename(columns={mun_name_col_original: 'mun_name'}, inplace=True)
        elif 'mun_code' in gdf.columns: 
            gdf['mun_name'] = gdf['mun_code']
        # st.write(f"[load_spatial_data] Estandarización de 'mun_name' en GDF completada en {time.time() - t_before_gdf_mun_name_std:.2f}s") # REMOVED
        
        # 8. Validar geometrías en GDF
        # t_before_gdf_geom_val = time.time() # REMOVED
        initial_gdf_rows = len(gdf)
        gdf = gdf[gdf.is_valid & ~gdf.is_empty] 
        rows_after_validation = len(gdf)
        # st.write(f"[load_spatial_data] Validación de geometría GDF completada en {time.time() - t_before_gdf_geom_val:.2f}s. Filas antes: {initial_gdf_rows}, Filas después: {rows_after_validation}") # REMOVED
        if gdf.empty:
            st.warning("El GeoDataFrame está vacío después de la validación de geometría.")
            return gdf, geojson_feature_collection 

        # 9. Seleccionar y retornar columnas necesarias del GDF
        gdf_cols_to_return = ['mun_code', 'geometry']
        
        if 'mun_name' in gdf.columns:
            gdf_cols_to_return.append('mun_name')
        elif 'mun_code' in gdf.columns: 
            gdf['mun_name'] = gdf['mun_code'] 
            gdf_cols_to_return.append('mun_name')

        if 'prov_name' in gdf.columns:
            gdf_cols_to_return.append('prov_name')
        if 'acom_code' in gdf.columns: 
            gdf_cols_to_return.append('acom_code')
        if 'acom_name' in gdf.columns:
            gdf_cols_to_return.append('acom_name')

        gdf_cols_to_return = list(dict.fromkeys(gdf_cols_to_return))

        missing_cols = [col for col in gdf_cols_to_return if col not in gdf.columns]
        if missing_cols:
            st.error(f"Columnas GDF faltantes después del procesamiento: {missing_cols}. Columnas disponibles: {gdf.columns.tolist()}")
            safe_cols = [col for col in ['mun_code', 'geometry'] if col in gdf.columns]
            if not safe_cols: 
                 return None, geojson_feature_collection
            final_gdf = gdf[safe_cols]
        else:
            final_gdf = gdf[gdf_cols_to_return]
        
        # st.write(f"[load_spatial_data] Finalizando. GDF final con {len(final_gdf)} filas y columnas: {final_gdf.columns.tolist()}. Tiempo total de la función: {time.time() - t_start_func:.2f}s") # REMOVED
        return final_gdf, geojson_feature_collection 

    except Exception as e:
        st.error(f"Error crítico al cargar o procesar datos espaciales: {e}")
        st.exception(e) 
        return None, None

# --- Conexión a la base de datos ---
try:
    conn = sqlite3.connect(DB_PATH)
except sqlite3.Error as e:
    st.error(f"Error al conectar con la base de datos: {e}")
    st.stop() 

# --- Sidebar para selección de año ---
available_years = get_available_years(conn)
if not available_years:
    st.sidebar.error("No hay años disponibles para mostrar.")
    st.stop()

selected_year = st.sidebar.selectbox("Seleccione Año:", available_years)

# --- Carga de Datos Espaciales y Filtros de Sidebar (CCAA, Provincia) ---
# t_spatial_and_filter_load_start = time.time() # REMOVED

# t_spatial_load_start = time.time() # REMOVED
gdf_municipalities, geojson_feature_collection_for_map = load_spatial_data(TOPOJSON_PATH)
# st.write(f"Datos espaciales (load_spatial_data) completados en {time.time() - t_spatial_load_start:.2f}s.") # REMOVED

if gdf_municipalities is None or geojson_feature_collection_for_map is None:
    st.warning("No se pudieron cargar los datos espaciales necesarios para los filtros y el mapa.")
    if gdf_municipalities is None:
        st.info("Detalle: El GeoDataFrame de municipios no se cargó correctamente.")
    if geojson_feature_collection_for_map is None:
        st.info("Detalle: El GeoJSON FeatureCollection para el mapa no se generó/procesó correctamente.")
    st.stop()

# st.write(f"Forma de gdf_municipalities ANTES de filtros CCAA/Prov: {gdf_municipalities.shape if gdf_municipalities is not None else 'N/A'}") # REMOVED
# st.write(f"Columnas en gdf_municipalities: {gdf_municipalities.columns.tolist() if gdf_municipalities is not None else 'N/A'}") # REMOVED
# st.write(f"Tipo de geojson_feature_collection_for_map: {type(geojson_feature_collection_for_map) if geojson_feature_collection_for_map is not None else 'N/A'}") # REMOVED

# --- Sidebar para filtros adicionales (CCAA y Provincia) ---
gdf_municipalities_original_for_filters = gdf_municipalities.copy() 

selected_acom = []
selected_prov = []

if gdf_municipalities_original_for_filters is not None and not gdf_municipalities_original_for_filters.empty:
    if 'acom_name' in gdf_municipalities_original_for_filters.columns:
        available_acom = sorted(gdf_municipalities_original_for_filters['acom_name'].dropna().unique())
        selected_acom = st.sidebar.multiselect("Seleccione Comunidad Autónoma:", available_acom, default=[]) 
        if selected_acom:
            gdf_municipalities = gdf_municipalities[gdf_municipalities['acom_name'].isin(selected_acom)]
            # st.write(f"GDF filtrado por CCAA: {selected_acom}. Filas restantes: {len(gdf_municipalities)}") # REMOVED
    else:
        st.sidebar.warning("Columna 'acom_name' no disponible para filtro de CCAA.")

    if 'prov_name' in gdf_municipalities_original_for_filters.columns:
        prov_options_source_df = gdf_municipalities if selected_acom else gdf_municipalities_original_for_filters
        available_prov = sorted(prov_options_source_df['prov_name'].dropna().unique())
        
        default_provinces_to_select = ['Madrid', 'Málaga']
        actual_default_provinces = [prov for prov in default_provinces_to_select if prov in available_prov]
        
        selected_prov = st.sidebar.multiselect("Seleccione Provincia:", available_prov, default=actual_default_provinces) 
        if selected_prov:
            gdf_municipalities = gdf_municipalities[gdf_municipalities['prov_name'].isin(selected_prov)]
            # st.write(f"GDF filtrado por Provincias: {selected_prov}. Filas restantes: {len(gdf_municipalities)}") # REMOVED
    else:
        st.sidebar.warning("Columna 'prov_name' no disponible para filtro de Provincia.")

    if selected_acom or selected_prov:
        # st.write(f"Forma de gdf_municipalities DESPUÉS de filtros CCAA/Prov: {gdf_municipalities.shape if gdf_municipalities is not None else 'N/A'}") # REMOVED
        if gdf_municipalities is not None and not gdf_municipalities.empty and 'mun_code' in gdf_municipalities.columns:
            filtered_mun_codes = set(gdf_municipalities['mun_code'].unique())
            if geojson_feature_collection_for_map and 'features' in geojson_feature_collection_for_map:
                original_feature_count = len(geojson_feature_collection_for_map['features'])
                geojson_feature_collection_for_map['features'] = [
                    feature for feature in geojson_feature_collection_for_map['features']
                    if feature.get('properties', {}).get('mun_code') in filtered_mun_codes
                ]
                filtered_feature_count = len(geojson_feature_collection_for_map['features'])
                # st.write(f"GeoJSON filtrado. Características originales: {original_feature_count}, filtradas: {filtered_feature_count}") # REMOVED
            else:
                st.warning("GeoJSON no disponible o sin 'features' para filtrar.") 
        elif gdf_municipalities is not None and gdf_municipalities.empty: 
            st.warning("gdf_municipalities está vacío después de los filtros CCAA/Prov, el mapa estará vacío.")
            if geojson_feature_collection_for_map and 'features' in geojson_feature_collection_for_map:
                 geojson_feature_collection_for_map['features'] = [] 
else:
    st.sidebar.info("Datos espaciales iniciales no disponibles o vacíos para mostrar filtros de CCAA/Provincia.")

# st.write(f"Carga de datos espaciales y definición de filtros geográficos completada en {time.time() - t_spatial_and_filter_load_start:.2f}s") # REMOVED

# --- Carga de Datos de Población (depende del año seleccionado) ---
# st.write("--- Iniciando Carga de Datos de Población ---") # REMOVED
# t_pop_load_start = time.time() # REMOVED
df_population = load_population_data(conn, selected_year)
# st.write(f"Datos de población cargados en {time.time() - t_pop_load_start:.2f}s. {len(df_population)} filas cargadas.") # REMOVED

if df_population.empty:
    st.warning(f"No se pudieron cargar los datos de población para el año {selected_year}. El mapa podría no mostrar datos de población.")

# --- Unión de Datos, Cálculo de Densidad y Preparación del Mapa ---
# st.write("--- Iniciando Unión de Datos y Cálculos Finales ---") # REMOVED
# t_main_processing_start = time.time() # REMOVED

# st.write("Uniendo datos de población con GDF espacial (posiblemente filtrado)...") # REMOVED
# t_merge_start = time.time() # REMOVED

if gdf_municipalities is None: 
    st.error("Error crítico: gdf_municipalities es None antes de la fusión. No se puede continuar.")
    st.stop()

merged_gdf = gdf_municipalities.merge(df_population, on="mun_code", how="left")
# st.write(f"Unión completada en {time.time() - t_merge_start:.2f}s. Filas en merged_gdf: {len(merged_gdf)}") # REMOVED

merged_gdf.dropna(subset=['poblacion', 'geometry'], inplace=True) 
# st.write(f"Filas en merged_gdf después de dropna (poblacion, geometry): {len(merged_gdf)}") # REMOVED

if merged_gdf.empty:
    st.warning(f"No hay datos combinados para el año {selected_year} y los filtros seleccionados después de la unión y limpieza. El mapa puede aparecer vacío o sin datos de coropletas.")

# st.write(f"Unión de datos y cálculos iniciales completados en {time.time() - t_main_processing_start:.2f}s") # REMOVED

# --- Cálculo de Área y Densidad ---
# st.write("--- Iniciando Cálculo de Área y Densidad ---") # REMOVED
# t_area_calc_start = time.time() # REMOVED
try:
    # st.write("Reproyectando GDF para cálculo de área (EPSG:25830)...") # REMOVED
    # t_reproject_start = time.time() # REMOVED
    merged_gdf_projected = merged_gdf.to_crs(epsg=25830)
    # st.write(f"Reproyección completada en {time.time() - t_reproject_start:.2f}s") # REMOVED
    merged_gdf['area_km2'] = merged_gdf_projected.area / 1_000_000  
except Exception as e:
    st.error(f"Error al calcular el área con EPSG:25830: {e}. Intentando con el área original (puede ser menos precisa).")
    merged_gdf['area_km2'] = merged_gdf.area * 10000 # Esto es una aproximación muy burda y probablemente incorrecta. Considerar eliminar o mejorar.
# st.write(f"Cálculo de 'area_km2' completado.") # REMOVED

merged_gdf['densidad_poblacion'] = merged_gdf['poblacion'] / merged_gdf['area_km2']
merged_gdf['densidad_poblacion'].fillna(0, inplace=True) 
merged_gdf.loc[merged_gdf['area_km2'] == 0, 'densidad_poblacion'] = 0 
merged_gdf.replace([float('inf'), float('-inf')], 0, inplace=True) 
# st.write(f"Cálculo de 'densidad_poblacion' completado.") # REMOVED
# st.write(f"Cálculo de Área y Densidad completado en {time.time() - t_area_calc_start:.2f}s") # REMOVED

# --- Enriqueciendo GeoJSON para Tooltips ---
# st.write("--- Enriqueciendo GeoJSON para Tooltips ---") # REMOVED
# t_enrich_geojson_start = time.time() # REMOVED

tooltip_cols = ['mun_name', 'poblacion', 'area_km2', 'densidad_poblacion']
for col in tooltip_cols:
    if col not in merged_gdf.columns:
        if col == 'mun_name':
            merged_gdf[col] = "N/D" 
        else:
            merged_gdf[col] = 0 
    else:
        if col == 'mun_name':
            merged_gdf[col] = merged_gdf[col].fillna("N/D")
        else:
            merged_gdf[col] = merged_gdf[col].fillna(0)


if merged_gdf['mun_code'].duplicated().any():
    # st.warning(f"Se encontraron {merged_gdf['mun_code'].duplicated().sum()} códigos 'mun_code' duplicados en merged_gdf ANTES de la eliminación. Se mantendrá la primera aparición.") # REMOVED
    merged_gdf = merged_gdf.drop_duplicates(subset=['mun_code'], keep='first')
    # st.write(f"merged_gdf después de eliminar duplicados de 'mun_code': {len(merged_gdf)} filas.") # REMOVED

tooltip_data = merged_gdf.set_index('mun_code')[tooltip_cols].copy() 

if geojson_feature_collection_for_map and 'features' in geojson_feature_collection_for_map:
    # st.write(f"Número de características en GeoJSON ANTES del enriquecimiento: {len(geojson_feature_collection_for_map['features'])}") # REMOVED
    enriched_feature_count = 0
    features_missing_mun_code_in_props = 0
    features_mun_code_not_in_tooltip_data = 0

    for feature in geojson_feature_collection_for_map['features']:
        feature_mun_code = feature.get('properties', {}).get('mun_code')
        if feature_mun_code:
            if feature_mun_code in tooltip_data.index:
                data_row = tooltip_data.loc[feature_mun_code]
                feature['properties']['mun_name'] = data_row['mun_name']
                feature['properties']['poblacion'] = float(data_row['poblacion']) if pd.notnull(data_row['poblacion']) else 0
                feature['properties']['area_km2'] = round(float(data_row['area_km2']), 2) if pd.notnull(data_row['area_km2']) else 0
                feature['properties']['densidad_poblacion'] = round(float(data_row['densidad_poblacion']), 2) if pd.notnull(data_row['densidad_poblacion']) else 0
                enriched_feature_count += 1
            else:
                features_mun_code_not_in_tooltip_data +=1
                feature['properties']['mun_name'] = feature.get('properties', {}).get('mun_name', 'Desconocido') 
                feature['properties']['poblacion'] = 0
                feature['properties']['area_km2'] = 0
                feature['properties']['densidad_poblacion'] = 0
        else:
            features_missing_mun_code_in_props += 1
            feature['properties']['mun_name'] = feature.get('properties', {}).get('mun_name', 'Sin Código Mun.')
            feature['properties']['poblacion'] = 0
            feature['properties']['area_km2'] = 0
            feature['properties']['densidad_poblacion'] = 0

    # st.write(f"Características GeoJSON enriquecidas: {enriched_feature_count}") # REMOVED
    if features_missing_mun_code_in_props > 0:
        st.warning(f"{features_missing_mun_code_in_props} características en GeoJSON no tenían 'mun_code' en sus propiedades.")
    if features_mun_code_not_in_tooltip_data > 0:
        st.warning(f"{features_mun_code_not_in_tooltip_data} características en GeoJSON tenían un 'mun_code' no encontrado en los datos de tooltip (merged_gdf).")
else:
    st.warning("No se pudo enriquecer GeoJSON: 'features' no encontrado o geojson_feature_collection_for_map es None.")

# st.write(f"Enriquecimiento de GeoJSON completado en {time.time() - t_enrich_geojson_start:.2f}s") # REMOVED

# --- Creación del Mapa Folium ---
# st.write("--- Iniciando Creación del Mapa Folium ---") # REMOVED
# t_map_creation_start = time.time() # REMOVED

if merged_gdf.empty or geojson_feature_collection_for_map is None or not geojson_feature_collection_for_map.get('features'):
    st.info(f"No hay datos suficientes para mostrar el mapa para el año {selected_year} con los filtros aplicados. Por favor, ajuste los filtros o seleccione otro año.")
    # st.write(f"Debug: merged_gdf empty: {merged_gdf.empty}, geojson_feature_collection_for_map is None: {geojson_feature_collection_for_map is None}") # REMOVED
    if geojson_feature_collection_for_map is not None:
        # st.write(f"Debug: geojson_feature_collection_for_map features empty: {not geojson_feature_collection_for_map.get('features')}") # REMOVED
        pass
    st.stop()

map_center = [40.416775, -3.703790] 
m = folium.Map(location=map_center, zoom_start=6, tiles="cartodbpositron")

min_density = merged_gdf['densidad_poblacion'].min() if not merged_gdf.empty else 0
max_density = merged_gdf['densidad_poblacion'].replace([float('inf'), float('-inf')], 0).max() if not merged_gdf.empty else 1
# st.write(f"Min Densidad: {min_density}, Max Densidad: {max_density}") # REMOVED

# Asegurarse de que min_density no sea igual a max_density para evitar problemas con la leyenda
if min_density == max_density:
    if max_density == 0: # Si todo es 0
        bins = [0, 1] # Un bin simple para mostrar que todo es 0
    else: # Si todo tiene el mismo valor > 0
        bins = [min_density * 0.9, min_density * 1.1] # Crear un pequeño rango
else:
    # Crear bins logarítmicos o cuantiles si la distribución es muy sesgada
    try:
        # Intentar con cuantiles si hay suficientes datos diversos
        if merged_gdf['densidad_poblacion'].nunique() > 5: # Necesita al menos k+1 valores únicos para k cuantiles
            bins = list(merged_gdf['densidad_poblacion'].quantile([0, 0.2, 0.4, 0.6, 0.8, 1]))
            bins = sorted(list(set(bins))) # Eliminar duplicados y ordenar
            if len(bins) < 2: # Si los cuantiles resultan en muy pocos bins (datos muy concentrados)
                bins = np.linspace(min_density, max_density, num=6).tolist()
        else: # Usar linspace si no hay suficientes datos únicos para cuantiles
            bins = np.linspace(min_density, max_density, num=6).tolist()
    except Exception as e_bins:
        # st.warning(f"Error al calcular bins para la leyenda: {e_bins}. Usando linspace simple.") # REMOVED
        bins = np.linspace(min_density, max_density, num=6).tolist()

# Asegurar que los bins sean únicos y ordenados, y al menos dos
bins = sorted(list(set(map(lambda x: round(x, 2), bins))))
if len(bins) < 2:
    bins = [round(min_density,2), round(max_density,2) + 0.01] # Asegurar al menos dos bins
if bins[0] == bins[-1] and bins[0] == 0: # Caso especial si todo es cero
    bins = [0, 1]
elif bins[0] == bins[-1]: # Si todos los valores son iguales y no cero
    bins = [bins[0] * 0.9, bins[0] * 1.1]


# st.write(f"Bins para leyenda: {bins}") # REMOVED

try:
    choropleth = folium.Choropleth(
        geo_data=geojson_feature_collection_for_map, # Usar el GeoJSON FeatureCollection
        name="Densidad de Población",
        data=merged_gdf,
        columns=["mun_code", "densidad_poblacion"],
        key_on="feature.properties.mun_code", # Clave en el GeoJSON
        fill_color="YlOrRd",
        fill_opacity=0.7,
        line_opacity=0.2,
        legend_name="Densidad de Población (hab/km²)",
        bins=bins, 
        highlight=True,
        nan_fill_color="lightgray", # Color para municipios sin datos
        nan_fill_opacity=0.4
    ).add_to(m)

    folium.GeoJsonTooltip(
        fields=['mun_name', 'poblacion', 'area_km2', 'densidad_poblacion'],
        aliases=['Municipio:', 'Población:', 'Área (km²):', 'Densidad (hab/km²):'],
        localize=True,
        sticky=False,
        labels=True,
        style="""
            background-color: #F0EFEF;
            border: 2px solid black;
            border-radius: 3px;
            box-shadow: 3px;
        """
    ).add_to(choropleth.geojson)

except ValueError as ve:
    st.error(f"Error al crear la capa Choropleth: {ve}")
    st.info("Esto puede ocurrir si no hay suficientes variaciones en los datos de densidad para los 'bins' definidos, o si los datos espaciales no se cargaron correctamente.")
    st.info(f"Detalles: merged_gdf tiene {len(merged_gdf)} filas. geojson_feature_collection_for_map tiene {len(geojson_feature_collection_for_map.get('features', [])) if geojson_feature_collection_for_map else 'N/A'} características.")
    # st.dataframe(merged_gdf[['mun_code', 'densidad_poblacion']].head()) # REMOVED
    st.stop()
except Exception as e_choropleth:
    st.error(f"Un error inesperado ocurrió al crear el mapa Choropleth: {e_choropleth}")
    st.exception(e_choropleth)
    st.stop()


folium.LayerControl().add_to(m)
# st.write(f"Creación del mapa Folium completada en {time.time() - t_map_creation_start:.2f}s") # REMOVED

# --- Mostrar el Mapa en Streamlit ---
# t_st_folium_start = time.time() # REMOVED
st_folium(m, width=None, height=700, returned_objects=[]) 
# st.write(f"Mapa mostrado por st_folium en {time.time() - t_st_folium_start:.2f}s") # REMOVED

# --- Cerrar conexión a la base de datos ---
if conn:
    conn.close()
    # st.write("Conexión a la base de datos cerrada.") # REMOVED

st.markdown("---")
st.markdown("#### Notas:")
st.markdown("- La densidad de población se calcula como `población / área_km2`.")
st.markdown("- El área se calcula reproyectando las geometrías a EPSG:25830 (ETRS89 / UTM Zone 30N). Esto es más preciso para la península. Las islas pueden tener ligeras distorsiones.")
st.markdown("- Los municipios sin datos de población para el año seleccionado o sin geometría válida no se muestran.")

# Código original comentado para referencia (mapa de puntos simulados)
# ... (se omite el código anterior de puntos simulados)
