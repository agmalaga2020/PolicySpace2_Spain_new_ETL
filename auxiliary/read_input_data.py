"""
This script is adapted to read input data for PolicySpace2 using the Spanish dataset structure.
It focuses on loading municipal-level data and handling the absence of AP (Area Ponderada) data.
Updated to use the ETL data provided by the user from the project's ETL folder.
This version includes fine-tuning for municipal code matching and direct IDHM filtering using INE codes from equivalencias table.
"""
import os
import pandas as pd
import geopandas as gpd

# Define base paths for the Spanish data
# Corrected to be relative to the project root, assuming the script is run from the project root or auxiliary/
# If script is in auxiliary/, ETL is at ../ETL/
# If script is run from project root, ETL is at ./ETL/
# os.path.dirname(__file__) will give the directory of the script (auxiliary)
# os.path.join(os.path.dirname(__file__), '..', 'ETL') should be robust
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
NEW_ETL_ROOT = os.path.join(SCRIPT_DIR, "..", "ETL") # Path to ETL relative to auxiliary directory

def read_data(path, sep=";", file_type="csv", **kwargs):
    """Reads data from a given path. Supports CSV and Excel."""
    if file_type == "csv":
        return pd.read_csv(path, sep=sep, **kwargs)
    elif file_type == "excel":
        return pd.read_excel(path, **kwargs)
    else:
        raise ValueError(f"Unsupported file type: {file_type}")

def read_mun_data(df, municipalities_list, mun_col_name):
    """Filters a DataFrame to include only specified municipalities."""
    if municipalities_list is None: # If no list provided, return all
        return df
    if mun_col_name not in df.columns:
        print(f"Warning: Municipality column \'{mun_col_name}\' not found in DataFrame \'{list(df.columns)}\'. Returning unfiltered data.")
        return df
    df_filtered = df.copy()
    df_filtered.loc[:, mun_col_name] = df_filtered[mun_col_name].astype(str).str.strip().str.zfill(5) # Ensure 5-digit for INE
    municipalities_list_str = [str(m).strip().zfill(5) for m in municipalities_list]
    return df_filtered[df_filtered[mun_col_name].isin(municipalities_list_str)]

def descriptive_stats(data, col):
    print(f"Descriptive stats for column: {col}")
    if col not in data.columns:
        print(f"Column \'{col}\' not found in dataframe.")
        return
    if data.empty:
        print(f"DataFrame is empty, cannot provide stats for column \'{col}\".")
        return
    if pd.api.types.is_numeric_dtype(data[col]):
        print(f"max: {data[col].max()}")
        print(f"min: {data[col].min()}")
        print(f"mean: {data[col].mean()}")
        print(f"std: {data[col].std()}")
        print(f"obs: {len(data[col].dropna())}")
    else:
        print(f"Column \'{col}\' is not numeric. Value counts: {data[col].value_counts().head()}")
    print("\n")

if __name__ == "__main__":
    print("--- Reading Spanish Data for PolicySpace2 (Using Project ETL Folder - IDHM Direct INE Filter) ---")

    df_equivalencias = pd.DataFrame() 
    test_municipalities = None
    try:
        equivalencias_path = os.path.join(NEW_ETL_ROOT, "tabla_equivalencias/data/df_equivalencias_municipio_CORRECTO.csv")
        df_equivalencias = read_data(equivalencias_path, sep=",", dtype=str)
        # Rename 'codigo_ine' to 'ine_code' for consistency if it exists, or 'mun_code' if 'codigo_ine' is not present but 'mun_code' is (as potential 5-digit INE)
        if 'codigo_ine' in df_equivalencias.columns:
             df_equivalencias.rename(columns={'codigo_ine': 'ine_code'}, inplace=True)
        elif 'mun_code' in df_equivalencias.columns and 'ine_code' not in df_equivalencias.columns: # Assuming this mun_code could be the 5-digit INE
            df_equivalencias.rename(columns={'mun_code': 'ine_code'}, inplace=True)
        
        if 'ine_code' in df_equivalencias.columns:
            df_equivalencias.loc[:, "ine_code"] = df_equivalencias["ine_code"].str.strip().str.zfill(5)
        else:
            print("WARNING: 'ine_code' (or equivalent like 'codigo_ine' or 'mun_code' for 5-digit INE) not found in equivalencias table.")

        if 'CPRO' in df_equivalencias.columns and 'ine_code' in df_equivalencias.columns:
            df_equivalencias.loc[:, "CPRO"] = df_equivalencias["CPRO"].str.strip()
            test_municipalities = df_equivalencias[df_equivalencias["CPRO"] == "28"]["ine_code"].unique()[:5].tolist()
        else:
            print("WARNING: 'CPRO' or 'ine_code' not found in equivalencias, cannot select test municipalities from Madrid.")

        if not test_municipalities:
            print("No test municipalities found for Madrid (CPRO 28) or equivalencias table issue, using a fallback or all.")
            test_municipalities = None 
        print(f"Test municipalities (5-digit INE codes for Madrid): {test_municipalities if test_municipalities else 'All'}")
        
        # Create 'mun_code_short_equiv' for joining with IDHM and Firms data
        if 'CPRO' in df_equivalencias.columns and 'CMUN' in df_equivalencias.columns:
            df_equivalencias['CPRO_str'] = df_equivalencias['CPRO'].astype(str).str.zfill(2)
            df_equivalencias['CMUN_str'] = df_equivalencias['CMUN'].astype(str).str.zfill(3)
            # Creates codes like '1001' (from CPRO 01, CMUN 001) or '28001' (from CPRO 28, CMUN 001)
            df_equivalencias['mun_code_short_equiv'] = df_equivalencias['CPRO'].astype(int).astype(str) + df_equivalencias['CMUN_str']
            print(f"Successfully created 'mun_code_short_equiv'. Sample: {df_equivalencias['mun_code_short_equiv'].head().tolist()}")
        else:
            print("WARNING: 'CPRO' or 'CMUN' not found in equivalencias. Cannot create 'mun_code_short_equiv'. IDHM and Firms mapping might fail.")

    except Exception as e:
        print(f"Error loading equivalencias table: {e}")
        df_equivalencias = pd.DataFrame() 
        test_municipalities = None

    # 1. Proportion of Urban Population
    try:
        prop_urban_path = os.path.join(NEW_ETL_ROOT, "distribucion_urbana/data_final/distribucion_urbana_municipios_2003_to_2022.csv")
        df_prop_urban = read_data(prop_urban_path, sep=",", dtype={'municipio_code': str})
        df_prop_urban.loc[:, "municipio_code"] = df_prop_urban["municipio_code"].str.strip().str.zfill(5)
        df_prop_urban_filtered = read_mun_data(df_prop_urban, test_municipalities, mun_col_name="municipio_code")
        if "2022" in df_prop_urban_filtered.columns:
             descriptive_stats(df_prop_urban_filtered, "2022")
        else:
            print("Year '2022' not found in urban proportion data.")
    except Exception as e:
        print(f"Error loading urban proportion data: {e}")

    # 2. Population Data (Total)
    try:
        pop_total_path = os.path.join(NEW_ETL_ROOT, "cifras_poblacion_municipio/cifras_poblacion_municipio.csv")
        df_pop_total = read_data(pop_total_path, sep=",", dtype={'mun_code': str})
        # This mun_code is like '1.0', '2.0'. Needs mapping to 5-digit INE for proper filtering.
        # For now, we acknowledge this and filtering might not work as expected for test_municipalities.
        print(f"INFO: Population data ('{pop_total_path}') uses 'mun_code' like '1.0', '2.0'. Direct filtering with 5-digit INE codes in test_municipalities will likely not match.")
        df_pop_total_filtered = read_mun_data(df_pop_total, test_municipalities, mun_col_name="mun_code") # This will likely be empty for test_municipalities
        if "2022" in df_pop_total_filtered.columns:
            descriptive_stats(df_pop_total_filtered, "2022")
        else:
            print("Year '2022' not found in total population data or data is empty after filtering (expected if mun_code formats differ).")
    except Exception as e:
        print(f"Error loading total population data: {e}")

    # 3. Municipal Human Development Index (IDHM)
    try:
        idhm_path = os.path.join(NEW_ETL_ROOT, "idhm_indice_desarrollo_humano_municipal/IRPFmunicipios_final_IDHM.csv")
        df_idhm = read_data(idhm_path, sep=",", dtype={'mun_code': str, 'codigo_aeat': str})
        df_idhm.loc[:, "mun_code"] = df_idhm["mun_code"].str.strip() # This is the short mun_code like '4001'

        if not df_equivalencias.empty and 'mun_code_short_equiv' in df_equivalencias.columns and 'ine_code' in df_equivalencias.columns:
            # Merge IDHM data with equivalencias table to get the 5-digit INE code ('ine_code')
            df_idhm_merged = pd.merge(df_idhm, df_equivalencias[['mun_code_short_equiv', 'ine_code']], 
                                      left_on='mun_code', right_on='mun_code_short_equiv', how='left')
            df_idhm_filtered = read_mun_data(df_idhm_merged, test_municipalities, mun_col_name="ine_code")
        else:
            print("WARNING: Cannot map IDHM data to 5-digit INE codes. Equivalencias table might be missing 'mun_code_short_equiv' or 'ine_code', or not loaded.")
            df_idhm_filtered = pd.DataFrame() 
            
        if "year" in df_idhm_filtered.columns and "IDHM" in df_idhm_filtered.columns:
            df_idhm_2021 = df_idhm_filtered[df_idhm_filtered["year"] == 2021]
            descriptive_stats(df_idhm_2021, "IDHM")
        else:
            print("Required columns ('year' or 'IDHM') not found in IDHM data or data is empty after filtering/merging.")
    except Exception as e:
        print(f"Error loading IDHM data: {e}")

    # 4. Real Interest Rates (No municipal filtering needed for this national data)
    try:
        interest_path = os.path.join(NEW_ETL_ROOT, "interest_data_ETL/imputados/interest_real_imputado.csv")
        df_interest = read_data(interest_path, sep=";")
        df_interest_sample = df_interest.head(240)
        if "mortgage" in df_interest_sample.columns:
            descriptive_stats(df_interest_sample, "mortgage")
        else:
            print("Column 'mortgage' not found in interest data.")
    except Exception as e:
        print(f"Error loading real interest data: {e}")

    # 5. Firms Data (Municipal level)
    try:
        firms_path = os.path.join(NEW_ETL_ROOT, "empresas_municipio_actividad_principal/preprocesados/empresas_municipio_actividad_principal.csv")
        df_firms = read_data(firms_path, sep=",", dtype={'municipio_code': str})
        df_firms.loc[:, "municipio_code"] = df_firms["municipio_code"].astype(str).str.strip() # Ensure it's string and stripped

        if not df_equivalencias.empty and 'mun_code_short_equiv' in df_equivalencias.columns and 'ine_code' in df_equivalencias.columns:
            # Merge firms data with equivalencias table to get the 5-digit INE code ('ine_code')
            df_firms_merged = pd.merge(df_firms, df_equivalencias[['mun_code_short_equiv', 'ine_code']],
                                       left_on='municipio_code', right_on='mun_code_short_equiv', how='left')
            df_firms_filtered = read_mun_data(df_firms_merged, test_municipalities, mun_col_name="ine_code")
            print(f"Firms data merged with equivalencias. Filtered for test municipalities: {len(df_firms_filtered)} rows.")
        else:
            print("WARNING: Cannot map Firms data to 5-digit INE codes. Equivalencias table might be missing 'mun_code_short_equiv' or 'ine_code', or not loaded.")
            df_firms_filtered = pd.DataFrame() # Fallback to empty if merge not possible
        
        if "Periodo" in df_firms_filtered.columns and "Total" in df_firms_filtered.columns:
            df_firms_filtered.loc[:, "Periodo"] = pd.to_numeric(df_firms_filtered["Periodo"], errors='coerce')
            df_firms_2022 = df_firms_filtered[df_firms_filtered["Periodo"] == 2022]
            descriptive_stats(df_firms_2022, "Total")
        else:
            print("Required columns ('Periodo' or 'Total') not found in filtered firms data or data is empty after filtering/merging.")
        print("NOTE: Firms data is municipal. Original model used AP-level firms data. Model logic may need adaptation.")
    except Exception as e:
        print(f"Error loading firms data: {e}")

    # 6. GeoData (GeoJSON)
    try:
        geojson_path = os.path.join(NEW_ETL_ROOT, "GeoRef_Spain/georef-spain-municipio.geojson")
        gdf_municipalities = gpd.read_file(geojson_path)
        # Ensure CODIGO_INE is 5 digits for potential filtering
        if 'CODIGO_INE' in gdf_municipalities.columns:
            gdf_municipalities.loc[:, 'CODIGO_INE'] = gdf_municipalities['CODIGO_INE'].astype(str).str.strip().str.zfill(5)
        print(f"Loaded GeoJSON for Spanish municipalities: {len(gdf_municipalities)} features.")
        # Example of filtering GeoJSON if needed: 
        # gdf_municipalities_filtered = read_mun_data(gdf_municipalities, test_municipalities, mun_col_name="CODIGO_INE") 
    except Exception as e:
        print(f"Error loading GeoJSON data: {e}")

    # 7. Fertility Data (Provincial - no municipal filtering with test_municipalities)
    try:
        fertility_path = os.path.join(NEW_ETL_ROOT, "indicadores_fecundidad_municipio_provincias/df_total_interpolado_full_tasa_estandarizada.csv")
        df_fertility = read_data(fertility_path, sep=",")
        print(f"Loaded Spanish fertility data (provincial): {len(df_fertility)} rows.")
        if "tasa_estandarizada" in df_fertility.columns:
            descriptive_stats(df_fertility, "tasa_estandarizada")
        else:
            print("Column 'tasa_estandarizada' not found in fertility data.")
        print("NOTE: Spanish fertility data is provincial. Original model might expect different granularity/structure. Adaptation needed.")
    except Exception as e:
        print(f"Error loading fertility data: {e}")

    # 8. PIE (FPM equivalent)
    try:
        pie_path = os.path.join(NEW_ETL_ROOT, "PIE/data/raw/finanzas/liquidaciones/preprocess/pie_final_final.csv")
        df_pie = read_data(pie_path, sep=",", dtype=str)
        df_pie.loc[:, "codigo_provincia_fmt"] = df_pie["codigo_provincia"].str.split('.').str[0].str.zfill(2)
        df_pie.loc[:, "codigo_municipio_fmt"] = df_pie["codigo_municipio"].str.split('.').str[0].str.zfill(3)
        df_pie.loc[:, "mun_code_pie"] = df_pie["codigo_provincia_fmt"] + df_pie["codigo_municipio_fmt"]
        df_pie_filtered = read_mun_data(df_pie, test_municipalities, mun_col_name="mun_code_pie")
        if "año" in df_pie_filtered.columns and "total_participacion_variables" in df_pie_filtered.columns:
            df_pie_filtered.loc[:, "año"] = pd.to_numeric(df_pie_filtered["año"], errors='coerce')
            df_pie_filtered.loc[:, "total_participacion_variables"] = pd.to_numeric(df_pie_filtered["total_participacion_variables"], errors='coerce')
            df_pie_2022 = df_pie_filtered[df_pie_filtered["año"] == 2022]
            descriptive_stats(df_pie_2022, "total_participacion_variables")
            print(f"Loaded Spanish PIE data: {len(df_pie_2022)} rows for test municipalities for year 2022.")
        else:
            print("Required columns ('año' or 'total_participacion_variables') not found in filtered PIE data or data is empty after filtering.")
    except Exception as e:
        print(f"Error loading PIE data: {e}")

    print("--- Finished attempting to read Spanish data (Using Project ETL Folder - IDHM Direct INE Filter) ---")
