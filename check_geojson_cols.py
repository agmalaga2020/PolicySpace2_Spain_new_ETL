import geopandas as gpd
import os

SCRIPT_DIR_TEMP = os.path.dirname(os.path.realpath(__file__))
ETL_DATA_PATH_TEMP = os.path.join(SCRIPT_DIR_TEMP, "ETL")
geojson_path = os.path.join(ETL_DATA_PATH_TEMP, "GeoRef_Spain/georef-spain-municipio.geojson")

try:
    gdf = gpd.read_file(geojson_path, rows=5)
    print("GeoJSON loaded successfully.")
    print("Columns:", gdf.columns.tolist())
    print("Sample data for potential INE code columns:")
    for col in gdf.columns:
        if "COD" in col.upper() or "MUN" in col.upper() or "INE" in col.upper() or "NATCODE" in col.upper():
            print(f"Column '{col}': {gdf[col].head().tolist()}")
except Exception as e:
    print(f"Error loading or inspecting GeoJSON: {e}")
