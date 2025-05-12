import geopandas as gpd
import topojson as tp
import os
import json
import traceback

# --- Rutas de Archivos ---
print("--- Script de Conversión a TopoJSON Iniciado ---")
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
print(f"Directorio actual del script: {CURRENT_DIR}")

GEOJSON_FILENAME = "georef-spain-municipio.geojson"
TOPOJSON_FILENAME = "georef-spain-municipio.topojson"

# Ruta al GeoJSON original
GEOJSON_PATH = os.path.join(
    os.path.dirname(CURRENT_DIR), 
    GEOJSON_FILENAME
)
print(f"Ruta calculada para GeoJSON de entrada: {GEOJSON_PATH}")

# Ruta para guardar el TopoJSON
TOPOJSON_PATH = os.path.join(CURRENT_DIR, TOPOJSON_FILENAME)
print(f"Ruta calculada para TopoJSON de salida: {TOPOJSON_PATH}")

# --- Parámetros de Conversión ---
SIMPLIFICATION_TOLERANCE = 0.0001 
QUANTIZATION = 1e5 
print(f"Parámetros: Tolerancia de Simplificación={SIMPLIFICATION_TOLERANCE}, Cuantización={QUANTIZATION}")

def convert_geojson_to_topojson(geojson_path, topojson_path, simplification_tolerance=0.0001, quantization=1e5):
    """
    Convierte un archivo GeoJSON a TopoJSON, aplicando simplificación y cuantización.
    """
    try:
        print(f"Intentando convertir GeoJSON: {geojson_path} a TopoJSON: {topojson_path}")

        print(f"Verificando existencia de GeoJSON en: {geojson_path}...")
        if not os.path.exists(geojson_path):
            print(f"Error Crítico: No se encontró el archivo GeoJSON en {geojson_path}")
            return
        print("Archivo GeoJSON encontrado.")

        print("Cargando GeoJSON con GeoPandas...")
        gdf = gpd.read_file(geojson_path)
        print(f"GeoJSON cargado. Número de geometrías: {len(gdf)}. CRS inicial: {gdf.crs}")
        if gdf.empty:
            print("Error Crítico: El GeoDataFrame cargado está vacío.")
            return
        print("Primeras 5 filas del GeoDataFrame:")
        print(gdf.head())

        if gdf.crs != "EPSG:4326":
            print(f"Convirtiendo CRS de {gdf.crs} a EPSG:4326...")
            gdf = gdf.to_crs("EPSG:4326")
            print(f"CRS convertido a {gdf.crs}.")

        print("Iniciando conversión a TopoJSON con la biblioteca 'topojson'...")
        topo = tp.Topology(
            gdf, 
            object_name="municipios",
            prequantize=quantization if quantization > 0 else False,
            toposimplify=simplification_tolerance if simplification_tolerance > 0 else False
        )
        print(f"Conversión a objeto TopoJSON completada.")

        # Guardar el TopoJSON
        print(f"Preparando para guardar TopoJSON en: {topojson_path}...")
        
        # Cambio: Intentar con topo.to_json() que devuelve un string JSON
        topo_json_string = topo.to_json() 
        
        output_dir = os.path.dirname(topojson_path)
        if not os.path.exists(output_dir):
            print(f"El directorio de salida {output_dir} no existe. Creándolo...")
            os.makedirs(output_dir)
            print(f"Directorio {output_dir} creado.")

        with open(topojson_path, 'w', encoding='utf-8') as f:
            f.write(topo_json_string) # Escribir el string JSON directamente
        print(f"Archivo TopoJSON guardado exitosamente en {topojson_path}")

        if os.path.exists(topojson_path):
            print("Verificación: El archivo TopoJSON existe en el disco.")
            file_size_geojson = os.path.getsize(geojson_path) / (1024 * 1024)
            file_size_topojson = os.path.getsize(topojson_path) / (1024 * 1024)
            print(f"Tamaño GeoJSON original: {file_size_geojson:.2f} MB")
            print(f"Tamaño TopoJSON nuevo: {file_size_topojson:.2f} MB")
            reduction = ((file_size_geojson - file_size_topojson) / file_size_geojson) * 100 if file_size_geojson > 0 else 0
            print(f"Reducción de tamaño: {reduction:.2f}%")
        else:
            print("Error Crítico: El archivo TopoJSON no se encontró en el disco después de intentar guardarlo.")

    except Exception as e:
        print(f"Ocurrió un error CRÍTICO durante la conversión: {e}")
        print("--- Traceback ---")
        traceback.print_exc()
        print("--- Fin Traceback ---")

if __name__ == "__main__":
    print("Ejecutando bloque __main__ del script...")
    output_dir_main = os.path.dirname(TOPOJSON_PATH)
    if not os.path.exists(output_dir_main):
        print(f"Bloque __main__: Creando directorio de salida {output_dir_main} si no existe...")
        os.makedirs(output_dir_main)
        print(f"Bloque __main__: Directorio {output_dir_main} creado.")

    convert_geojson_to_topojson(
        GEOJSON_PATH, 
        TOPOJSON_PATH,
        simplification_tolerance=SIMPLIFICATION_TOLERANCE,
        quantization=QUANTIZATION
    )
    print("\n--- Script de Conversión a TopoJSON Finalizado ---")
    print("Recordatorio: Asegúrate de tener la biblioteca 'topojson' instalada (`pip install topojson`).")
    print("También necesitarás 'geopandas' (`pip install geopandas`).")
