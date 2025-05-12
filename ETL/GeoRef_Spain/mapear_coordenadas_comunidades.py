import geopandas as gpd
import pandas as pd
import os

# Define file paths
geojson_path = 'georef-spain-comunidad-autonoma.geojson'
output_csv_path = 'comunidades_coordenadas.csv'  # MODIFIED HERE

print("DEBUG: Script para mapear coordenadas de Comunidades Autónomas iniciado.")

def main():
    print(f"Iniciando el script para mapear coordenadas de Comunidades Autónomas.")
    print(f"Intentando leer el archivo GeoJSON: {geojson_path}")
    print(f"Ruta actual de trabajo: {os.getcwd()}")

    # Check if GeoJSON file exists
    if not os.path.exists(geojson_path):
        print(f"Error: El archivo GeoJSON '{geojson_path}' no se encontró.")
        print(f"Asegúrate de que el archivo '{geojson_path}' esté en la carpeta '{os.getcwd()}'.")
        exit()
    print(f"DEBUG: El archivo GeoJSON '{geojson_path}' existe.")

    try:
        print(f"DEBUG: Intentando cargar '{geojson_path}' con geopandas...")
        gdf = gpd.read_file(geojson_path)
        print("DEBUG: GeoJSON cargado exitosamente con geopandas.")
    except Exception as e:
        print(f"Error al leer el archivo GeoJSON '{geojson_path}': {e}")
        print("Asegúrate de que la librería geopandas y sus dependencias estén instaladas.")
        exit()

    print(f"El GeoJSON tiene {len(gdf)} Comunidades Autónomas.")
    print("Primeras filas del GeoDataFrame (para inspección de columnas):")
    print(gdf.head())
    print("\nColumnas disponibles en el GeoJSON:", gdf.columns.tolist())

    # --- User may need to adjust these column names based on the actual GeoJSON structure ---
    # Directly assign column names based on observed GeoJSON structure from execution
    community_code_col = 'acom_code'  # CORRECTED based on output
    community_name_col = 'acom_name'  # CORRECTED based on output

    print(f"DEBUG: Columna de código de C.A. asignada: '{community_code_col}'")
    print(f"DEBUG: Columna de nombre de C.A. asignada: '{community_name_col}'")

    # Attempt to identify common column names (case-insensitive)
    # This is a basic attempt, direct assignment after inspection is often more reliable.
    # possible_code_cols = ['ca_code', 'ine_ccaa', 'COD_CCAA', 'CODIGO_AUTONOMICO', 'NATCODE', 'acom_code'] # Added acom_code
    # possible_name_cols = ['ca_name', 'NOMBRE_AUTONOMICO', 'NOMBRE_CCAA', 'CCAA', 'name', 'acom_name'] # Added acom_name

    # identified_code_col = None
    # identified_name_col = None
    # available_cols_upper = [col.upper() for col in gdf.columns]

    # for p_col in possible_code_cols:
    #     if p_col.upper() in available_cols_upper:
    #         identified_code_col = gdf.columns[available_cols_upper.index(p_col.upper())]
    #         print(f"Columna de código de C.A. identificada automáticamente: '{identified_code_col}'")
    #         break

    # for p_col in possible_name_cols:
    #     if p_col.upper() in available_cols_upper:
    #         identified_name_col = gdf.columns[available_cols_upper.index(p_col.upper())]
    #         print(f"Columna de nombre de C.A. identificada automáticamente: '{identified_name_col}'")
    #         break
    
    # if identified_code_col:
    #     community_code_col = identified_code_col
    # else:
    #     print(f"ADVERTENCIA: No se pudo identificar automáticamente la columna de código de C.A. Usando por defecto: '{community_code_col}'. Por favor, verifica.")

    # if identified_name_col:
    #     community_name_col = identified_name_col
    # else:
    #     print(f"ADVERTENCIA: No se pudo identificar automáticamente la columna de nombre de C.A. Usando por defecto: '{community_name_col}'. Por favor, verifica.")

    if community_code_col not in gdf.columns:
        print(f"Error: La columna de código de C.A. '{community_code_col}' no se encontró en el GeoJSON.")
        print(f"Columnas disponibles: {gdf.columns.tolist()}")
        print("Edita la variable 'community_code_col' en el script.")
        exit()

    if community_name_col not in gdf.columns:
        print(f"Error: La columna de nombre de C.A. '{community_name_col}' no se encontró en el GeoJSON.")
        print(f"Columnas disponibles: {gdf.columns.tolist()}")
        print("Edita la variable 'community_name_col' en el script.")
        exit()

    if 'geometry' not in gdf.columns:
        print("Error: La columna 'geometry' no se encuentra en el GeoJSON. Esta columna es esencial.")
        exit()
    print("DEBUG: Columna 'geometry' encontrada.")

    print(f"\nSe usarán las siguientes columnas (verifica que sean correctas):")
    print(f"  - Para el código de C.A.: '{community_code_col}'")
    print(f"  - Para el nombre de la C.A.: '{community_name_col}'")

    print("\nDEBUG: Iniciando cálculo de centroides...")
    try:
        print("DEBUG: Aplicando buffer(0) a las geometrías...")
        gdf['geometry'] = gdf.geometry.buffer(0)
        print("DEBUG: Proyectando a EPSG:4326...")
        gdf_proj = gdf.to_crs(epsg=4326)
        print("DEBUG: Calculando centroides geométricos...")
        gdf_proj['centroid'] = gdf_proj.geometry.centroid
        print("DEBUG: Centroides calculados.")
    except Exception as e:
        print(f"Error calculando centroides: {e}")
        exit()

    print("DEBUG: Extrayendo longitud y latitud de los centroides...")
    gdf_proj['longitud'] = gdf_proj['centroid'].x
    gdf_proj['latitud'] = gdf_proj['centroid'].y
    print("Centroides calculados y coordenadas extraídas.")

    print("DEBUG: Creando DataFrame para el CSV...")
    df_output = pd.DataFrame({
        'codigo_comunidad_autonoma': gdf_proj[community_code_col],
        'nombre_comunidad_autonoma': gdf_proj[community_name_col],
        'latitud': gdf_proj['latitud'],
        'longitud': gdf_proj['longitud']
    })
    print("DEBUG: DataFrame para CSV creado.")

    try:
        print(f"DEBUG: Intentando guardar el CSV en '{output_csv_path}'...")
        df_output.to_csv(output_csv_path, index=False, encoding='utf-8')
        print(f"\nArchivo CSV '{output_csv_path}' generado exitosamente con {len(df_output)} registros.")
        print("Primeras filas del CSV generado:")
        print(df_output.head())
    except Exception as e:
        print(f"Error al guardar el archivo CSV '{output_csv_path}': {e}")

    print(f"\nEl script ha finalizado. Revisa el archivo '{output_csv_path}'.")
    print("Si las columnas de código o nombre de C.A. no son las correctas, revisa la salida de 'Columnas disponibles en el GeoJSON' y ajusta las variables 'community_code_col' y 'community_name_col' en el script.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR GENERAL NO CAPTURADO EN MAIN: {e}")
        import traceback
        traceback.print_exc()

print("DEBUG: Script para mapear C.A. finalizado completamente.")
