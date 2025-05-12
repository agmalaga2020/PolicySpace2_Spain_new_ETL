import geopandas as gpd
import pandas as pd
import os

# Define file paths
# Assumes the script is in ETL/GeoRef_Spain/
geojson_path = 'georef-spain-municipio.geojson'
output_csv_path = 'municipios_coordenadas.csv'

# Path to the equivalencias CSV (for context, not directly processed here for coordinate extraction)
# equivalencias_path = os.path.join(os.path.dirname(__file__), '..', '..', 'equivalencias_datos_espana.csv')

print("DEBUG: Script iniciado.")

def main():
    print(f"Iniciando el script para mapear coordenadas de municipios.")
    print(f"Intentando leer el archivo GeoJSON: {geojson_path}")
    print(f"Ruta actual de trabajo: {os.getcwd()}")

    # Check if GeoJSON file exists
    if not os.path.exists(geojson_path):
        print(f"Error: El archivo GeoJSON '{geojson_path}' no se encontró en la carpeta actual.")
        print("Asegúrate de que el archivo GeoJSON esté en la misma carpeta que este script (ETL/GeoRef_Spain/).")
        exit()
    print(f"DEBUG: El archivo GeoJSON '{geojson_path}' existe.")

    # Load the GeoJSON file containing municipality boundaries
    # This file can be large, so this step might take some time and memory.
    try:
        print(f"DEBUG: Intentando cargar '{geojson_path}' con geopandas...")
        gdf = gpd.read_file(geojson_path)
        print("DEBUG: GeoJSON cargado exitosamente con geopandas.")
    except Exception as e:
        print(f"Error al leer el archivo GeoJSON '{geojson_path}': {e}")
        print("Asegúrate de que la librería geopandas y sus dependencias (fiona, pyproj, shapely, rtree) estén instaladas.")
        print("Puedes instalarlas con: pip install geopandas")
        exit()

    print(f"El GeoJSON tiene {len(gdf)} municipios.")
    print("Primeras filas del GeoDataFrame (para inspección de columnas):")
    print(gdf.head())
    print("\\nColumnas disponibles en el GeoJSON:", gdf.columns.tolist())

    # --- User may need to adjust these column names based on the actual GeoJSON structure ---
    # Directly assign column names based on observed GeoJSON structure
    municipality_code_col = 'mun_code'
    municipality_name_col = 'mun_name'

    print(f"DEBUG: Columna de código de municipio asignada: '{municipality_code_col}'")
    print(f"DEBUG: Columna de nombre de municipio asignada: '{municipality_name_col}'")

    # Attempt to identify common column names (case-insensitive)
    # possible_code_cols = ['ine_cod', 'COD_INE', 'CODIGO_INE', 'cod_mun', 'CMUM', 'NATCODE', 'cartodb_id', 'ID_INE', 'mun_code'] # Added mun_code
    # possible_name_cols = ['NOMBRE', 'NOM_MUN', 'name', 'LIBNOM', 'MUNICIPIO', 'mun_name'] # Added mun_name

    # available_cols_upper = [col.upper() for col in gdf.columns]
    # print(f"DEBUG: Columnas disponibles en mayúsculas: {available_cols_upper}")

    # for p_col in possible_code_cols:
    #     if p_col.upper() in available_cols_upper:
    #         municipality_code_col = gdf.columns[available_cols_upper.index(p_col.upper())]
    #         print(f"Columna de código de municipio identificada automáticamente: '{municipality_code_col}'")
    #         break

    # for p_col in possible_name_cols:
    #     if p_col.upper() in available_cols_upper:
    #         municipality_name_col = gdf.columns[available_cols_upper.index(p_col.upper())]
    #         print(f"Columna de nombre de municipio identificada automáticamente: '{municipality_name_col}'")
    #         break

    if not municipality_code_col or municipality_code_col not in gdf.columns:
        print(f"ADVERTENCIA: La columna de código de municipio '{municipality_code_col}' no es válida o no se encontró.")
        print(f"Por favor, revisa las columnas disponibles ({gdf.columns.tolist()}) y ajusta 'municipality_code_col' en el script.")
        # Fallback: use the first column if available, user MUST verify this
        if not gdf.columns.empty: # Corrected condition here
            municipality_code_col = gdf.columns[0] 
            print(f"Usando '{municipality_code_col}' como columna de código por defecto. ¡ES MUY IMPORTANTE QUE VERIFIQUES ESTO!")
        else:
            print("Error: El GeoJSON no tiene columnas.")
            exit()

    if not municipality_name_col or municipality_name_col not in gdf.columns:
        print(f"ADVERTENCIA: La columna de nombre de municipio '{municipality_name_col}' no es válida o no se encontró.")
        print(f"Por favor, revisa las columnas disponibles ({gdf.columns.tolist()}) y ajusta 'municipality_name_col' en el script.")
        # Fallback: use the second column if available, or first if only one, user MUST verify
        if len(gdf.columns) > 1: # Corrected condition here (len > 0 would also work if not gdf.columns.empty)
            municipality_name_col = gdf.columns[1] 
            print(f"Usando '{municipality_name_col}' como columna de nombre por defecto. ¡ES MUY IMPORTANTE QUE VERIFIQUES ESTO!")
        elif not gdf.columns.empty: # Corrected condition here
            municipality_name_col = gdf.columns[0]
            print(f"Usando '{municipality_name_col}' como columna de nombre por defecto (misma que código). ¡VERIFICA ESTO!")
        else: # Should be caught by previous check
            print("Error: El GeoJSON no tiene columnas.")
            exit()

    # Ensure geometry column exists
    if 'geometry' not in gdf.columns:
        print("Error: La columna 'geometry' no se encuentra en el GeoJSON. Esta columna es esencial.")
        exit()
    print("DEBUG: Columna 'geometry' encontrada.")

    print(f"\nSe usarán las siguientes columnas (verifica que sean correctas):")
    print(f"  - Para el código de municipio: '{municipality_code_col}'")
    print(f"  - Para el nombre del municipio: '{municipality_name_col}'")
    print(f"  - Para la geometría: 'geometry'")

    # Calculate centroids
    # Note: centroid might not always be within the polygon for complex shapes.
    # to_crs EPSG:4326 ensures coordinates are in latitude/longitude (WGS84)
    print("\nDEBUG: Iniciando cálculo de centroides...")
    try:
        # Ensure the geometry is valid before calculating centroid
        print("DEBUG: Aplicando buffer(0) a las geometrías...")
        gdf['geometry'] = gdf.geometry.buffer(0)
        print("DEBUG: Proyectando a EPSG:4326...")
        gdf_proj = gdf.to_crs(epsg=4326) # Project to WGS84 for lat/lon
        print("DEBUG: Calculando centroides geométricos...")
        gdf_proj['centroid'] = gdf_proj.geometry.centroid
        print("DEBUG: Centroides calculados.")
    except Exception as e:
        print(f"Error calculando centroides: {e}")
        print("Asegúrate de que las geometrías en el GeoJSON son válidas.")
        exit()

    # Extract latitude and longitude
    print("DEBUG: Extrayendo longitud y latitud de los centroides...")
    gdf_proj['longitud'] = gdf_proj['centroid'].x
    gdf_proj['latitud'] = gdf_proj['centroid'].y
    print("Centroides calculados y coordenadas extraídas.")

    # Select relevant columns for the output CSV
    # Create a new DataFrame for the CSV
    print("DEBUG: Creando DataFrame para el CSV...")
    output_df_data = {}

    # Add code column
    if municipality_code_col in gdf_proj.columns:
        output_df_data['codigo_municipio'] = gdf_proj[municipality_code_col]
    else:
        print(f"Advertencia: La columna de código '{municipality_code_col}' no se encontró después de la proyección. Se usará N/A.")
        output_df_data['codigo_municipio'] = 'N/A'

    # Add name column
    if municipality_name_col in gdf_proj.columns:
        output_df_data['nombre_municipio'] = gdf_proj[municipality_name_col]
    else:
        print(f"Advertencia: La columna de nombre '{municipality_name_col}' no se encontró después de la proyección. Se usará N/A.")
        output_df_data['nombre_municipio'] = 'N/A'
        
    output_df_data['latitud'] = gdf_proj['latitud']
    output_df_data['longitud'] = gdf_proj['longitud']

    df_output = pd.DataFrame(output_df_data)
    print("DEBUG: DataFrame para CSV creado.")

    # Reorder columns for clarity
    final_columns = ['codigo_municipio', 'nombre_municipio', 'latitud', 'longitud']
    # Ensure all expected columns are present, add if missing (e.g. if original code/name col was problematic)
    for col in final_columns:
        if col not in df_output.columns:
            df_output[col] = 'N/A' # Should not happen with current logic but good safeguard
    df_output = df_output[final_columns]
    print("DEBUG: Columnas del DataFrame final reordenadas.")


    # Save to CSV
    try:
        print(f"DEBUG: Intentando guardar el CSV en '{output_csv_path}'...")
        df_output.to_csv(output_csv_path, index=False, encoding='utf-8')
        print(f"\nArchivo CSV '{output_csv_path}' generado exitosamente con {len(df_output)} registros.")
        print("Primeras filas del CSV generado:")
        print(df_output.head())
    except Exception as e:
        print(f"Error al guardar el archivo CSV '{output_csv_path}': {e}")

    print(f"\nEl script ha finalizado. Revisa el archivo '{output_csv_path}' en la carpeta ETL/GeoRef_Spain/.")
    print("Si las columnas de código o nombre de municipio no son las correctas en el CSV, o si hay errores, por favor:")
    print("1. Revisa la salida de 'Columnas disponibles en el GeoJSON' que imprimió el script.")
    print("2. Edita las variables 'possible_code_cols' y 'possible_name_cols' al inicio del script para incluir los nombres correctos, o asigna directamente los nombres a 'municipality_code_col' y 'municipality_name_col' después de la carga del GeoJSON.")
    print("3. Asegúrate de tener instaladas las librerías necesarias: pip install pandas geopandas")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR GENERAL NO CAPTURADO EN MAIN: {e}")
        import traceback
        traceback.print_exc()

print("DEBUG: Script finalizado completamente.")
