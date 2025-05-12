import pandas as pd
import folium
import os

# Define file paths
# Assumes the script is in ETL/GeoRef_Spain/
csv_path = 'municipios_coordenadas.csv'
output_map_path = 'mapa_municipios.html'

print(f"Iniciando el script para visualizar municipios en un mapa.")
print(f"Intentando leer el archivo CSV: {csv_path}")
print(f"Ruta actual de trabajo: {os.getcwd()}")

# Check if CSV file exists
if not os.path.exists(csv_path):
    print(f"Error: El archivo CSV '{csv_path}' no se encontró en la carpeta actual.")
    print("Asegúrate de que el archivo CSV (municipios_coordenadas.csv) esté en la misma carpeta que este script (ETL/GeoRef_Spain/).")
    print("Debes ejecutar primero el script 'mapear_coordenadas.py' para generar este archivo.")
    exit()

print(f"DEBUG: El archivo CSV '{csv_path}' existe.")

# Load the CSV file
try:
    print(f"DEBUG: Intentando cargar '{csv_path}' con pandas...")
    # Ensure correct dtypes, especially for codes if they can be purely numeric
    df_municipios = pd.read_csv(csv_path, dtype={'codigo_municipio': str})
    print(f"DEBUG: CSV cargado exitosamente con pandas. {len(df_municipios)} registros leídos.")
except Exception as e:
    print(f"Error al leer el archivo CSV '{csv_path}': {e}")
    exit()

# Verify required columns
required_cols = ['latitud', 'longitud', 'nombre_municipio', 'codigo_municipio'] # CORRECTED column names to match CSV
for col in required_cols:
    if col not in df_municipios.columns:
        print(f"Error: La columna requerida '{col}' no se encuentra en el archivo CSV.")
        print(f"Columnas disponibles: {df_municipios.columns.tolist()}")
        exit()
print("DEBUG: Columnas requeridas verificadas.")

# Drop rows with missing latitude or longitude, if any
df_municipios.dropna(subset=['latitud', 'longitud'], inplace=True)
print(f"DEBUG: {len(df_municipios)} registros después de eliminar filas sin latitud/longitud.")

if df_municipios.empty:
    print("Error: No hay datos de municipios para mostrar después de limpiar valores nulos de coordenadas.")
    exit()

# Create a map centered around Spain
# Approximate center of Spain (latitude, longitude)
spain_center = [40.416775, -3.703790]
mapa = folium.Map(location=spain_center, zoom_start=6)
print("DEBUG: Mapa base de Folium creado.")

# Add markers for each municipality
print(f"DEBUG: Añadiendo {len(df_municipios)} marcadores al mapa...")
for index, row in df_municipios.iterrows():
    try:
        lat = float(row['latitud'])
        lon = float(row['longitud'])
        nombre = row['nombre_municipio'] # CORRECTED column name to match CSV
        codigo = row['codigo_municipio'] # CORRECTED column name to match CSV
        
        # Create popup text
        popup_text = f"<b>{nombre}</b><br>Código: {codigo}<br>Lat: {lat:.4f}, Lon: {lon:.4f}"
        
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_text, max_width=300),
            tooltip=nombre  # Show municipality name on hover
        ).add_to(mapa)
    except ValueError as ve:
        print(f"ADVERTENCIA: Saltando fila {index} debido a un error de valor en lat/lon: {ve}. Datos: Lat='{row['latitud']}', Lon='{row['longitud']}'")
        continue
    except Exception as e:
        print(f"ADVERTENCIA: Error inesperado al procesar fila {index} para el marcador: {e}")
        continue

print("DEBUG: Marcadores añadidos al mapa.")

# Save the map to an HTML file
try:
    mapa.save(output_map_path)
    print(f"\nMapa guardado exitosamente como '{output_map_path}'.")
    print(f"Puedes abrir este archivo en tu navegador web para ver el mapa.")
except Exception as e:
    print(f"Error al guardar el mapa HTML '{output_map_path}': {e}")

print("DEBUG: Script de visualización finalizado.")

