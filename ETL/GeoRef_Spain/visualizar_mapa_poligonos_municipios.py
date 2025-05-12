import geopandas as gpd
import folium
import os

# Define base directory for the script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Define file paths relative to the script's directory
geojson_path = os.path.join(script_dir, 'georef-spain-municipio.geojson')
output_map_path = os.path.join(script_dir, 'mapa_poligonos_municipios.html')

print("DEBUG: Script para visualizar polígonos de municipios iniciado.")

def main():
    print(f"Iniciando el script para visualizar polígonos de municipios.")
    print(f"Intentando leer el archivo GeoJSON: {geojson_path}")
    print(f"Ruta actual de trabajo: {os.getcwd()}")

    # Check if GeoJSON file exists
    if not os.path.exists(geojson_path):
        print(f"Error: El archivo GeoJSON '{geojson_path}' no se encontró.")
        print(f"Asegúrate de que el archivo '{geojson_path}' esté en la carpeta '{os.getcwd()}'.")
        exit()
    print(f"DEBUG: El archivo GeoJSON '{geojson_path}' existe.")

    try:
        print(f"DEBUG: Intentando cargar \'{geojson_path}\' con geopandas...")
        gdf = gpd.read_file(geojson_path)
        print(f"DEBUG: GeoJSON cargado exitosamente con geopandas. {len(gdf)} municipios encontrados.")
        print(f"DEBUG: GeoDataFrame loaded. CRS: {gdf.crs}. Number of features: {len(gdf)}") # ADDED
    except Exception as e:
        print(f"Error al leer el archivo GeoJSON '{geojson_path}': {e}")
        exit()

    print("Primeras filas del GeoDataFrame (para inspección de columnas):")
    print(gdf.head())
    print("\nColumnas disponibles en el GeoJSON:", gdf.columns.tolist())

    # Define column names for municipality code and name (based on previous scripts)
    municipality_code_col = 'mun_code'
    municipality_name_col = 'mun_name'

    # Verify essential columns exist
    if 'geometry' not in gdf.columns:
        print("Error: La columna 'geometry' es esencial y no se encontró.")
        exit()
    if municipality_code_col not in gdf.columns:
        print(f"Error: La columna de código de municipio '{municipality_code_col}' no se encontró.")
        print(f"Columnas disponibles: {gdf.columns.tolist()}")
        exit()
    if municipality_name_col not in gdf.columns:
        print(f"Error: La columna de nombre de municipio '{municipality_name_col}' no se encontró.")
        print(f"Columnas disponibles: {gdf.columns.tolist()}")
        exit()
    
    print(f"DEBUG: Usando '{municipality_code_col}' para códigos y '{municipality_name_col}' para nombres.")

    # Create a map centered around Spain
    spain_center = [40.416775, -3.703790]
    mapa = folium.Map(location=spain_center, zoom_start=6)
    print("DEBUG: Mapa base de Folium creado.")

    # Simplify geometries slightly for better performance if needed, though user mentioned it's already simplified.
    # gdf['geometry'] = gdf.geometry.simplify(0.001) # Optional: 0.001 tolerance in degrees

    # Project to WGS84 if not already (Folium expects lat/lon)
    if gdf.crs and gdf.crs.to_epsg() != 4326:
        print(f"DEBUG: Proyectando GeoDataFrame de {gdf.crs} a EPSG:4326...")
        gdf = gdf.to_crs(epsg=4326)
        print(f"DEBUG: Proyección completada. New CRS: {gdf.crs}. Number of features after reprojection: {len(gdf)}") # MODIFIED
    elif not gdf.crs:
        print("ADVERTENCIA: El GeoDataFrame no tiene un CRS definido. Asumiendo EPSG:4326 (lat/lon). Si el mapa se ve incorrecto, verifica la proyección original del GeoJSON.")
        # gdf.set_crs(epsg=4326, inplace=True) # Uncomment if you are sure it is EPSG:4326
        print(f"DEBUG: GeoDataFrame CRS is None. Number of features before adding to map: {len(gdf)}") # ADDED
    else: # Already EPSG:4326
        print(f"DEBUG: GeoDataFrame CRS is {gdf.crs}. Number of features before adding to map: {len(gdf)}") # ADDED

    print(f"DEBUG: Añadiendo {len(gdf)} polígonos al mapa...")
    if gdf.empty: # ADDED BLOCK
        print("ERROR: El GeoDataFrame está vacío antes de añadirlo al mapa. No se generará contenido.")
        exit()
    
    # Add GeoJson layer to the map
    # This is generally more performant for a large number of polygons
    geojson_layer = folium.GeoJson(
        gdf, # Pass the GeoDataFrame
        name='Municipios',
        style_function=lambda feature: {
            'fillColor': 'blue',
            'color': 'black',
            'weight': 0.5,
            'fillOpacity': 0.3,
        },
        tooltip=folium.features.GeoJsonTooltip(
            fields=[municipality_name_col, municipality_code_col],
            aliases=['Nombre:', 'Código:'],
            localize=True,
            sticky=False,
            labels=True,
            style=(
                "background-color: white; color: #333333; font-family: arial; font-size: 12px; padding: 10px;"
            )
        ),
        popup=folium.features.GeoJsonPopup(
            fields=[municipality_name_col, municipality_code_col],
            aliases=['<strong>Nombre:</strong>', '<strong>Código:</strong>'],
            localize=True,
            labels=True,
            style="width:200px",
        )
    ).add_to(mapa)

    print("DEBUG: Polígonos añadidos al mapa como una capa GeoJson.")

    # Add layer control to toggle the GeoJson layer
    folium.LayerControl().add_to(mapa)
    print("DEBUG: Control de capas añadido.")

    # Save the map to an HTML file
    try:
        print(f"DEBUG: Intentando guardar el mapa en \'{output_map_path}\'...") # ADDED
        mapa.save(output_map_path)
        print(f"\\nMapa de polígonos guardado exitosamente como \'{output_map_path}\'.")
        print(f"Puedes abrir este archivo en tu navegador web para ver el mapa.")
    except Exception as e:
        print(f"Error al guardar el mapa HTML '{output_map_path}': {e}")

    print("DEBUG: Script de visualización de polígonos finalizado.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR GENERAL NO CAPTURADO EN MAIN: {e}")
        import traceback
        traceback.print_exc()

print("DEBUG: Script finalizado completamente.")
