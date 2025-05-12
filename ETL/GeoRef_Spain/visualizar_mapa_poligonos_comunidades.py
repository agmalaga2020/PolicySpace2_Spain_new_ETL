import geopandas as gpd
import folium
import os

# Define base directory for the script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Define file paths relative to the script's directory
geojson_path = os.path.join(script_dir, 'georef-spain-comunidad-autonoma.geojson')
output_map_path = os.path.join(script_dir, 'mapa_poligonos_comunidades.html')

print("DEBUG: Script para visualizar polígonos de comunidades autónomas iniciado.")

def main():
    print(f"Iniciando el script para visualizar polígonos de comunidades autónomas.")
    print(f"Intentando leer el archivo GeoJSON: {geojson_path}")
    print(f"Ruta actual de trabajo: {os.getcwd()}")

    # Check if GeoJSON file exists
    if not os.path.exists(geojson_path):
        print(f"Error: El archivo GeoJSON '{geojson_path}' no se encontró.")
        exit()
    print(f"DEBUG: El archivo GeoJSON '{geojson_path}' existe.")

    try:
        print(f"DEBUG: Intentando cargar '{geojson_path}' con geopandas...") # MODIFIED
        gdf = gpd.read_file(geojson_path)
        print(f"DEBUG: GeoJSON cargado exitosamente con geopandas. {len(gdf)} comunidades encontradas.")
        print(f"DEBUG: GeoDataFrame loaded. CRS: {gdf.crs}. Number of features: {len(gdf)}")
    except Exception as e:
        print(f"Error al leer el archivo GeoJSON '{geojson_path}': {e}")
        exit()

    print("Primeras filas del GeoDataFrame (para inspección de columnas):")
    print(gdf.head())
    print("\nColumnas disponibles en el GeoJSON:", gdf.columns.tolist())

    # Define column names for community code and name
    community_code_col = 'acom_code'  # Updated for communities
    community_name_col = 'acom_name'  # Updated for communities

    # Verify essential columns exist
    if 'geometry' not in gdf.columns:
        print("Error: La columna 'geometry' es esencial y no se encontró.")
        exit()
    if community_code_col not in gdf.columns:
        print(f"Error: La columna de código de comunidad '{community_code_col}' no se encontró.")
        print(f"Columnas disponibles: {gdf.columns.tolist()}")
        exit()
    if community_name_col not in gdf.columns:
        print(f"Error: La columna de nombre de comunidad '{community_name_col}' no se encontró.")
        print(f"Columnas disponibles: {gdf.columns.tolist()}")
        exit()
    
    print(f"DEBUG: Usando '{community_code_col}' para códigos y '{community_name_col}' para nombres.")

    # Create a map centered around Spain
    spain_center = [40.416775, -3.703790]
    mapa = folium.Map(location=spain_center, zoom_start=5) # Adjusted zoom for communities
    print("DEBUG: Mapa base de Folium creado.")

    # Project to WGS84 if not already (Folium expects lat/lon)
    if gdf.crs and gdf.crs.to_epsg() != 4326:
        print(f"DEBUG: Proyectando GeoDataFrame de {gdf.crs} a EPSG:4326...")
        gdf = gdf.to_crs(epsg=4326)
        print(f"DEBUG: Proyección completada. New CRS: {gdf.crs}. Number of features after reprojection: {len(gdf)}") # MODIFIED
    elif not gdf.crs:
        print("ADVERTENCIA: El GeoDataFrame no tiene un CRS definido. Asumiendo EPSG:4326 (lat/lon).")
        # gdf.set_crs(epsg=4326, inplace=True) # Uncomment if you are sure it is EPSG:4326
        print(f"DEBUG: GeoDataFrame CRS is None. Number of features before adding to map: {len(gdf)}") # ADDED
    else: # Already EPSG:4326
        print(f"DEBUG: GeoDataFrame CRS is {gdf.crs}. Number of features before adding to map: {len(gdf)}") # ADDED

    print(f"DEBUG: Añadiendo {len(gdf)} polígonos al mapa...")
    if gdf.empty: # ADDED BLOCK
        print("ERROR: El GeoDataFrame está vacío antes de añadirlo al mapa. No se generará contenido.")
        exit()
    
    # Add GeoJson layer to the map
    geojson_layer = folium.GeoJson(
        gdf,
        name='Comunidades Autónomas', # Updated name
        style_function=lambda feature: {
            'fillColor': 'green', # Changed color for distinction
            'color': 'black',
            'weight': 1, # Slightly thicker border for communities
            'fillOpacity': 0.4,
        },
        tooltip=folium.features.GeoJsonTooltip(
            fields=[community_name_col, community_code_col],
            aliases=['Nombre:', 'Código:'],
            localize=True,
            sticky=False,
            labels=True,
            style=(
                "background-color: white; color: #333333; font-family: arial; font-size: 12px; padding: 10px;"
            )
        ),
        popup=folium.features.GeoJsonPopup(
            fields=[community_name_col, community_code_col],
            aliases=['<strong>Nombre:</strong>', '<strong>Código:</strong>'],
            localize=True,
            labels=True,
            style="width:250px", # Adjusted width
        )
    ).add_to(mapa)

    print("DEBUG: Polígonos añadidos al mapa como una capa GeoJson.")

    # Add layer control to toggle the GeoJson layer
    folium.LayerControl().add_to(mapa)
    print("DEBUG: Control de capas añadido.")

    # Save the map to an HTML file
    try:
        print(f"DEBUG: Intentando guardar el mapa en '{output_map_path}'...") # ADDED
        mapa.save(output_map_path)
        print(f"\\nMapa de polígonos guardado exitosamente como '{output_map_path}'.")
        print(f"Puedes abrir este archivo en tu navegador web para ver el mapa.")
    except Exception as e:
        print(f"Error al guardar el mapa HTML '{output_map_path}': {e}")

    print("DEBUG: Script de visualización de polígonos de comunidades finalizado.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR GENERAL NO CAPTURADO EN MAIN: {e}")
        import traceback
        traceback.print_exc()

print("DEBUG: Script finalizado completamente.")
