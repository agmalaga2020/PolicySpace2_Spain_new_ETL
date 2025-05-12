import os
import pandas as pd
import geopandas as gpd
import logging
from shapely.geometry import shape # Not strictly needed if GeoPandas handles geometry objects directly
import json # Only if dealing with GeoJSON properties directly, GeoPandas handles this

logger = logging.getLogger(__name__)

# Define base paths consistently relative to this script's location (world/)
SCRIPT_DIR_SHAPES = os.path.dirname(os.path.realpath(__file__))
PROJECT_ROOT_SHAPES = os.path.join(SCRIPT_DIR_SHAPES, "..")
ETL_DATA_PATH_SHAPES = os.path.join(PROJECT_ROOT_SHAPES, "ETL")

# Original prepare_shapes_2010 - might need adaptation or removal if not used for Spanish context
# For now, keeping it to avoid breaking other parts if they call it, but it's likely Brazil-specific.
def prepare_shapes_2010(geo):
    # This function is specific to the Brazilian 2010 data structure and ACPs.
    # It will likely not work correctly for the Spanish adaptation without significant changes.
    # If the simulation year is not 2010, this function might not be called.
    logger.warning("prepare_shapes_2010 is likely not adapted for Spanish data and may cause errors if used.")
    # Placeholder: return empty structures to avoid crashes if called unexpectedly.
    # A proper adaptation would require understanding its exact role and Spanish equivalents.
    # For now, let's assume it's not critical if sim.geo.year is not 2010.
    if geo.year != 2010:
         return {}, [] # Return empty dict and list if not 2010

    # --- Original Brazil-specific code below ---
    # This part needs to be fully reviewed and adapted if 2010 simulations for Spain are needed
    # and if this function is indeed called.
    urban_path_2010 = os.path.join(PROJECT_ROOT_SHAPES, 'input/shapes/2010/urban_mun_2010.shp')
    urban_df = gpd.read_file(urban_path_2010)
    # Filter for mun_codes in geo.mun_codes
    urban_df_filtered = urban_df[urban_df.CD_MUN.isin(geo.mun_codes)]
    urban_shapes_dict = {
        row.CD_MUN: row.geometry for _, row in urban_df_filtered.iterrows()
    }
    
    # Shapes (municipalities or APs) - this part is very Brazil-specific with state-wise shapefiles
    # This needs a complete rethink for Spain.
    # For now, returning empty list for shapes if this function is called for 2010.
    logger.error("prepare_shapes_2010: Municipal/AP shape loading for 2010 is not adapted for Spain.")
    my_shapes = [] 
    return urban_shapes_dict, my_shapes


def prepare_shapes(geo_obj):
    """
    Loads and prepares municipal shapes for Spain.
    'geo_obj' is an instance of the Geography class, providing 'mun_codes' to process.
    Returns:
        - urban_geometries: A dict mapping mun_code (5-digit INE) to its Shapely geometry.
                            (Currently, this is the full municipal geometry, not specific urban areas).
        - municipal_data_list: A list of objects/namedtuples, each representing a municipality,
                               with attributes 'id' (5-digit INE) and 'geometry'.
    """
    logger.info("Preparing Spanish municipal shapes...")

    # Path to the Spanish municipal GeoJSON file
    geojson_path = os.path.join(ETL_DATA_PATH_SHAPES, "GeoRef_Spain/georef-spain-municipio.geojson")

    try:
        gdf_municipalities_all = gpd.read_file(geojson_path)
        logger.info(f"Successfully loaded GeoJSON for all Spanish municipalities from {geojson_path}. Found {len(gdf_municipalities_all)} features.")
    except Exception as e:
        logger.error(f"CRITICAL ERROR: Could not load Spanish municipal GeoJSON from {geojson_path}. Error: {e}")
        return {}, [] # Return empty structures

    # Ensure the column with INE codes is consistently named and formatted
    # Common names are 'CODIGO_INE', 'NATCODE', 'mun_code', etc. Inspect your GeoJSON.
    # Assuming 'CODIGO_INE' is the column name in georef-spain-municipio.geojson
    # Based on check_geojson_cols.py, the column is 'mun_code' for INE and 'mun_name' for name.
    ine_code_col = None
    name_col = None

    if 'mun_code' in gdf_municipalities_all.columns:
        ine_code_col = 'mun_code'
    elif 'CODIGO_INE' in gdf_municipalities_all.columns:
        ine_code_col = 'CODIGO_INE'
    elif 'NATCODE' in gdf_municipalities_all.columns: 
        ine_code_col = 'NATCODE'
    # Add other potential column names if necessary
    
    if 'mun_name' in gdf_municipalities_all.columns:
        name_col = 'mun_name'
    elif 'NOMBRE' in gdf_municipalities_all.columns:
        name_col = 'NOMBRE'
    elif 'NAME' in gdf_municipalities_all.columns:
        name_col = 'NAME'

    if not ine_code_col:
        logger.error("CRITICAL ERROR: Could not find a suitable INE code column in GeoJSON (tried mun_code, CODIGO_INE, NATCODE).")
        return {}, []
        
    gdf_municipalities_all[ine_code_col] = gdf_municipalities_all[ine_code_col].astype(str).str.zfill(5)

    # Filter municipalities based on geo_obj.mun_codes (which are the ones to be processed in the simulation)
    if geo_obj.mun_codes: # If specific municipalities are selected
        gdf_processed_municipalities = gdf_municipalities_all[
            gdf_municipalities_all[ine_code_col].isin(geo_obj.mun_codes)
        ].copy()
        if len(gdf_processed_municipalities) != len(geo_obj.mun_codes):
            logger.warning("Not all municipalities specified in SPANISH_MUNICIPALITIES_TO_PROCESS were found in the GeoJSON.")
    else: # If 'ALL' was specified, or list was empty
        gdf_processed_municipalities = gdf_municipalities_all.copy()
        logger.info("Processing all municipalities found in GeoJSON as per geo_obj.mun_codes being empty or 'ALL'.")

    if gdf_processed_municipalities.empty:
        logger.warning("No municipalities selected or found after filtering. Returning empty shapes.")
        return {}, []

    # Prepare the 'shapes' list for Generator.create_regions()
    # Each item needs 'id' and 'geometry', and optionally 'NAME' or 'NOMBRE' for Region class
    municipal_data_list = []
    for _, row in gdf_processed_municipalities.iterrows():
        # Create a simple object or namedtuple that mimics the expected structure for 'item' in create_regions
        class ShapeItem:
            def __init__(self, id_val, geom_val, name_val=None):
                self.id = str(id_val) # Ensure ID is string
                self.geometry = geom_val
                # Region class checks for NAME then NOMBRE. Set both if name_val is provided.
                if name_val: 
                    self.NAME = str(name_val) 
                    self.NOMBRE = str(name_val)
                else: # Fallback if no name column found
                    self.NAME = f"Region_{self.id}"
                    self.NOMBRE = f"Region_{self.id}"

        name_col_value_from_row = row[name_col] if name_col and name_col in row else f"Mun_{row[ine_code_col]}"
        
        municipal_data_list.append(ShapeItem(id_val=row[ine_code_col], geom_val=row['geometry'], name_val=name_col_value_from_row))

    # Prepare 'urban_geometries' dictionary
    # For Spain, we don't have separate urban area shapefiles in this structure.
    # As a placeholder, use the full municipal geometry for 'urban'.
    # The distinction will rely on 'prob_urban' in the Generator.
    urban_geometries = {
        row[ine_code_col]: row['geometry'] for _, row in gdf_processed_municipalities.iterrows()
    }
    
    logger.info(f"Prepared {len(municipal_data_list)} municipal shapes and {len(urban_geometries)} urban geometry entries for processing.")
    return urban_geometries, municipal_data_list

# Note: The original ShapeObject class might not be needed if GeoPandas rows (or custom objects like ShapeItem)
# provide .id and .geometry attributes directly as expected by the Region class.
# If OGR Feature objects were expected, ShapeItem mimics that.
