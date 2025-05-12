# -*- coding: utf-8 -*-
"""
empresas_municipio_actividad_principal.py

Processes data on the number of businesses per municipality and main activity
in Spain, sourced from INE. The script cleans, transforms, and imputes
missing data to generate a robust dataset for analysis.

Adapted for local execution (Visual Studio Code, plain Python)
without Google Colab dependencies.
-------------------------------------------------------------------------
- Uses script-relative paths for all file operations.
- Input file `cifras_poblacion_municipio.csv` is expected in the script's directory.
- Raw downloaded INE table is saved in `tablas_intermedias/` subfolder.
- All other intermediate and final processed files are saved in `preprocesados/` subfolder.
- Final output file: `empresas_municipio_actividad_principal.csv` (in `preprocesados/`).
- Wraps execution logic in functions and a `main()` function.
- Removes plotting code and verbose intermediate output.
- Requires installation of: pandas, requests
  (pip install pandas requests)

Run from anywhere:
    $ python path/to/empresas_municipio_actividad_principal.py
"""

import requests
import pandas as pd
import numpy as np
import os
import io
from pathlib import Path
import warnings

# Suppress potential warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)


# --- Configuration ---
INE_TABLE_CODE = "4721"
INE_DATA_URL = f"https://servicios.ine.es/wstempus/csv/ES/DATOS_TABLA/{INE_TABLE_CODE}?nult=999"

# Folder names
PROCESSED_SUBFOLDER = "preprocesados"
INTERMEDIATE_TABLES_SUBFOLDER = "tablas_intermedias"
INPUT_POPULATION_FILENAME = "cifras_poblacion_municipio.csv" # Expected in script's dir

# --- Helper Functions ---

def get_script_directory() -> Path:
    """Returns the absolute path to the directory containing this script."""
    return Path(__file__).parent.resolve()

def create_output_folder(base_dir: Path, folder_name: str) -> Path:
    """Creates the output folder if it doesn't exist."""
    output_path = base_dir / folder_name
    try:
        output_path.mkdir(parents=True, exist_ok=True)
        print(f"Output subfolder ensured: '{output_path}'")
        return output_path
    except OSError as e:
        print(f"❌ Error creating output folder '{output_path}': {e}")
        return None

def download_ine_data(url: str, save_path: Path) -> pd.DataFrame | None:
    """Downloads INE data, saves it, and reads it into a DataFrame."""
    print(f"Attempting to download INE data from: {url}...")
    try:
        response = requests.get(url, timeout=120)
        response.raise_for_status()
        csv_data = response.content.decode('utf-8')

        # Save the raw downloaded file
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(csv_data)
        print(f"Raw INE data saved to '{save_path.name}' in '{save_path.parent.name}'.")

        # Read into DataFrame
        df = pd.read_csv(save_path, sep='\t', encoding='utf-8')
        print(f"Data successfully read into DataFrame from '{save_path.name}'.")
        return df
    except requests.exceptions.RequestException as e:
        print(f"❌ Error downloading INE data: {e}")
        return None
    except Exception as e:
        print(f"❌ Error processing downloaded INE data: {e}")
        return None

def initial_clean_and_filter(df_raw: pd.DataFrame) -> pd.DataFrame | None:
    """Performs initial cleaning: drops NaNs in 'Municipios', filters by 'Total' CNAE, extracts codes."""
    if df_raw is None or df_raw.empty:
        print("❌ Cannot perform initial clean: Input DataFrame is missing or empty.")
        return None
    print("Performing initial data cleaning and filtering...")

    # Drop rows where 'Municipios' is NaN
    df_cleaned = df_raw.dropna(subset=['Municipios']).copy() # Use .copy()
    initial_rows = len(df_raw)
    if len(df_cleaned) < initial_rows:
        print(f"  Removed {initial_rows - len(df_cleaned)} rows with NaN in 'Municipios'.")

    # Filter for 'Total' in 'Grupos CNAE'
    if 'Grupos CNAE' not in df_cleaned.columns:
        print("❌ Error: 'Grupos CNAE' column not found for filtering.")
        return None
    df_total_cnae = df_cleaned[df_cleaned['Grupos CNAE'] == 'Total'].copy() # Use .copy()
    if df_total_cnae.empty:
        print("⚠️ Warning: No rows found for 'Total' in 'Grupos CNAE'.")
        return pd.DataFrame() # Return empty if no 'Total' rows

    # Extract municipio_code and municipio_name
    if 'Municipios' not in df_total_cnae.columns:
        print("❌ Error: 'Municipios' column not found for code extraction.")
        return None
    try:
        # Ensure the regex captures numeric code and the rest as name
        extracted_codes = df_total_cnae['Municipios'].str.extract(r'^(\d+)\s+(.+)$', expand=True)
        df_total_cnae['municipio_code'] = pd.to_numeric(extracted_codes[0], errors='coerce') # Convert code to numeric
        df_total_cnae['municipio_name'] = extracted_codes[1].str.strip()

        # Drop rows where municipio_code could not be extracted
        initial_rows_total = len(df_total_cnae)
        df_total_cnae.dropna(subset=['municipio_code'], inplace=True)
        if len(df_total_cnae) < initial_rows_total:
             print(f"  Removed {initial_rows_total - len(df_total_cnae)} rows with invalid 'municipio_code' after extraction.")

    except Exception as e:
        print(f"❌ Error extracting municipio codes/names: {e}")
        return None

    print("Initial cleaning and filtering finished.")
    return df_total_cnae

def select_and_prepare_base_df(df_total_cnae: pd.DataFrame) -> pd.DataFrame | None:
    """Selects key columns and prepares 'Total' column as numeric."""
    if df_total_cnae is None or df_total_cnae.empty:
        print("❌ Cannot prepare base DataFrame: Input is missing or empty.")
        return None
    print("Preparing base DataFrame with selected columns...")

    required_cols = ['municipio_code', 'municipio_name', 'Periodo', 'Total']
    if not all(col in df_total_cnae.columns for col in required_cols):
        print(f"❌ Error: Missing one or more required columns: {required_cols}")
        return None

    df_base = df_total_cnae[required_cols].copy() # Use .copy()
    # Convert 'Total' to numeric, coercing errors to NaN
    df_base['Total'] = pd.to_numeric(df_base['Total'], errors='coerce')
    print("Base DataFrame prepared.")
    return df_base

def identify_problematic_municipalities(df_base: pd.DataFrame, population_df_path: Path) -> tuple[list, pd.DataFrame | None]:
    """Identifies municipalities with many NaNs and cross-references with population data."""
    if df_base is None or df_base.empty:
        print("❌ Cannot identify problematic municipalities: Input DataFrame missing or empty.")
        return [], None
    print("Identifying problematic municipalities based on NaN counts and population...")

    # 1. Find municipios with > 12 NaNs in 'Total'
    nan_counts_by_code = df_base[df_base['Total'].isna()].groupby('municipio_code').size()
    municipios_many_nans = nan_counts_by_code[nan_counts_by_code > 12].index.tolist()

    # 2. Load population data
    try:
        df_poblacion = pd.read_csv(population_df_path)
        df_poblacion.columns = df_poblacion.columns.str.strip() # Clean column names
        if 'mun_code' not in df_poblacion.columns:
            print(f"❌ Population file '{population_df_path.name}' missing 'mun_code' column.")
            return municipios_many_nans, None # Return codes found so far, but no population data
        df_poblacion['mun_code'] = pd.to_numeric(df_poblacion['mun_code'], errors='coerce').astype('Int64')
    except FileNotFoundError:
        print(f"❌ Population file not found: '{population_df_path.name}'. Cannot cross-reference.")
        return municipios_many_nans, None # Return codes found so far
    except Exception as e:
        print(f"❌ Error loading population file '{population_df_path.name}': {e}")
        return municipios_many_nans, None

    # 3. Cross-reference
    df_many_nans_info = pd.DataFrame({'municipio_code': municipios_many_nans})
    df_many_nans_info['municipio_code'] = pd.to_numeric(df_many_nans_info['municipio_code'], errors='coerce').astype('Int64')

    df_merged_pop = df_many_nans_info.merge(
        df_poblacion, left_on='municipio_code', right_on='mun_code', how='left'
    )

    # Identify codes that did not merge (no population data) or have very low recent pop
    # Example: Check population in the latest available year (e.g., '2024')
    latest_pop_year = '2024' # Adjust if population data has different year columns
    if latest_pop_year not in df_merged_pop.columns:
         # Find the latest year column dynamically if '2024' doesn't exist
         year_cols_pop = [col for col in df_merged_pop.columns if col.isdigit() and len(col)==4]
         if year_cols_pop:
             latest_pop_year = max(year_cols_pop)
         else:
             latest_pop_year = None # No year columns found
             print("⚠️ No suitable year column found in population data for recent population check.")


    codes_to_consider_removing = []
    if latest_pop_year:
        codes_no_recent_pop_data = df_merged_pop[
            df_merged_pop[latest_pop_year].isna() | (df_merged_pop[latest_pop_year] < 100) # Example threshold
        ]['municipio_code'].tolist()
        codes_to_consider_removing.extend(codes_no_recent_pop_data)
    else: # If no year column, take all that didn't merge well
        codes_to_consider_removing.extend(df_merged_pop[df_merged_pop['mun_code'].isna()]['municipio_code'].tolist())


    # Add the predefined list of municipalities to always remove
    predefined_to_remove = [10905, 18915, 29903, 29904, 12066, 17122]
    final_codes_to_remove = sorted(list(set(codes_to_consider_removing + predefined_to_remove)))

    print(f"Identified {len(final_codes_to_remove)} municipalities for potential removal or zero-filling based on high NaN count and population data.")
    return final_codes_to_remove, df_merged_pop # Return df_merged_pop for potential further analysis

def filter_and_impute_stage1(df_base: pd.DataFrame, codes_to_remove: list, df_many_nans_pop_info: pd.DataFrame | None) -> pd.DataFrame | None:
    """Removes specified municipalities and fills NaNs with 0 for others with many NaNs (likely low activity)."""
    if df_base is None or df_base.empty: return None
    print("Performing Stage 1 filtering and imputation (removal and zero-filling)...")
    df_filtered = df_base.copy()

    # 1. Remove the identified codes
    initial_rows = len(df_filtered)
    df_filtered = df_filtered[~df_filtered['municipio_code'].isin(codes_to_remove)]
    print(f"  Removed {initial_rows - len(df_filtered)} rows corresponding to {len(codes_to_remove)} specified municipalities.")

    # 2. Identify remaining municipalities that had >12 NaNs originally (from df_many_nans_pop_info)
    #    and fill their 'Total' NaNs with 0.
    if df_many_nans_pop_info is not None and 'municipio_code' in df_many_nans_pop_info.columns:
        # Get codes that had many NaNs but were NOT in codes_to_remove
        codes_for_zero_fill = df_many_nans_pop_info[
            ~df_many_nans_pop_info['municipio_code'].isin(codes_to_remove)
        ]['municipio_code'].unique()

        mask_zero_fill = df_filtered['municipio_code'].isin(codes_for_zero_fill)
        df_filtered.loc[mask_zero_fill, 'Total'] = df_filtered.loc[mask_zero_fill, 'Total'].fillna(0)
        print(f"  Filled NaNs with 0 for {mask_zero_fill.sum()} entries in municipalities with historically high NaNs (low activity).")
    else:
        print("  Skipping zero-filling for high-NaN municipalities as population info was not available or incomplete.")

    print("Stage 1 filtering and imputation finished.")
    return df_filtered


def filter_and_impute_stage2(df_stage1_filtered: pd.DataFrame) -> pd.DataFrame | None:
    """Identifies municipalities with 11-12 NaNs, checks their business volume, and imputes with 0 if low."""
    if df_stage1_filtered is None or df_stage1_filtered.empty: return None
    print("Performing Stage 2 filtering and imputation (for 11-12 NaNs based on business volume)...")
    df_filtered_s2 = df_stage1_filtered.copy()

    # 1. Identify codes with 11-12 NaNs *in the current DataFrame*
    nan_counts_s2 = df_filtered_s2[df_filtered_s2['Total'].isna()].groupby('municipio_code').size()
    codes_11_12_nans = nan_counts_s2[(nan_counts_s2 == 11) | (nan_counts_s2 == 12)].index.tolist()

    if not codes_11_12_nans:
        print("  No municipalities found with 11-12 NaNs in the current dataset. Skipping Stage 2 zero-filling.")
        return df_filtered_s2

    # 2. For these codes, check the sum of 'Total' where it's not NaN.
    #    If sum is very low (e.g., < 10, implying only 1-2 businesses registered in the few non-NaN years),
    #    then fill their NaNs with 0.
    imputed_count_s2 = 0
    for code in codes_11_12_nans:
        current_totals = df_filtered_s2.loc[
            (df_filtered_s2['municipio_code'] == code) & (df_filtered_s2['Total'].notna()),
            'Total'
        ]
        sum_existing_businesses = current_totals.sum()
        # Define a threshold for "very low activity"
        # If sum is low (e.g. less than 10, or average per non-NaN year is < 2)
        # and count of non-NaN years is small (e.g., 1 or 2 years of data out of 13)
        if sum_existing_businesses < 10 and len(current_totals) <= 2: # Heuristic threshold
            mask_s2_zero_fill = (df_filtered_s2['municipio_code'] == code)
            df_filtered_s2.loc[mask_s2_zero_fill, 'Total'] = df_filtered_s2.loc[mask_s2_zero_fill, 'Total'].fillna(0)
            imputed_count_s2 += df_filtered_s2.loc[mask_s2_zero_fill, 'Total'].isnull().sum() # Count how many NaNs were actually filled

    if imputed_count_s2 > 0:
        print(f"  Filled {imputed_count_s2} NaNs with 0 for municipalities with 11-12 NaNs and very low business activity.")
    else:
        print("  No further NaNs filled with 0 in Stage 2 (municipalities with 11-12 NaNs either had higher activity or no NaNs left for them).")


    print("Stage 2 imputation finished.")
    return df_filtered_s2


def final_impute_by_mean(df_stage2_filtered: pd.DataFrame) -> pd.DataFrame | None:
    """Imputes remaining NaNs in 'Total' using the mean for each municipality."""
    if df_stage2_filtered is None or df_stage2_filtered.empty: return None
    print("Performing final imputation of remaining NaNs using municipal mean...")
    df_final_imputed = df_stage2_filtered.copy()

    # Impute remaining NaNs in 'Total' using the mean of 'Total' for that 'municipio_code'
    # Ensure 'Total' is numeric before mean calculation
    df_final_imputed['Total'] = pd.to_numeric(df_final_imputed['Total'], errors='coerce')

    # Calculate mean per group, then use transform to broadcast and fillna
    df_final_imputed['Total'] = df_final_imputed.groupby('municipio_code')['Total']\
                                     .transform(lambda x: x.fillna(x.mean()))

    # If a municipality had ALL NaNs for 'Total', its mean would be NaN.
    # In this case, after transform, 'Total' would still be NaN. Fill these with 0.
    # (Though previous steps should have handled most complete NaN cases by removal or zero-fill)
    remaining_nans_after_mean = df_final_imputed['Total'].isna().sum()
    if remaining_nans_after_mean > 0:
        print(f"  {remaining_nans_after_mean} NaNs still present after mean imputation (likely all-NaN groups). Filling with 0.")
        df_final_imputed['Total'].fillna(0, inplace=True)

    # Final check
    if df_final_imputed['Total'].isna().any():
        print("⚠️ Warning: NaNs still remain in 'Total' after all imputation steps.")
    else:
        print("Final mean imputation complete. No NaNs remain in 'Total'.")

    return df_final_imputed


# --- Main Execution Logic ---

def main():
    """Main function to orchestrate the data processing workflow."""
    print("--- Starting Business Data Processing Script ---")
    script_dir = get_script_directory()
    # Create output folders
    intermediate_dir = create_output_folder(script_dir, INTERMEDIATE_TABLES_SUBFOLDER)
    processed_dir = create_output_folder(script_dir, PROCESSED_SUBFOLDER)
    if intermediate_dir is None or processed_dir is None: return

    # --- Define file paths ---
    path_raw_ine_data = intermediate_dir / "empresas_por_municipio_y_actividad.csv"
    path_df_total_cnae = processed_dir / "df_total_cnae_extracted.csv" # After initial clean
    path_df_base = processed_dir / "df_base_selected.csv"      # After selection and 'Total' numeric
    path_population_data = script_dir / INPUT_POPULATION_FILENAME # Expect in script's root
    path_df_s1_filtered = processed_dir / "df_filtered_stage1.csv"
    path_df_s2_filtered = processed_dir / "df_filtered_stage2.csv"
    path_final_output = processed_dir / "empresas_municipio_actividad_principal.csv"
    # ---

    # 1. Download INE Data
    df_raw = download_ine_data(INE_DATA_URL, path_raw_ine_data)
    if df_raw is None:
        print("❌ Exiting: Failed to download or read INE data.")
        return

    # 2. Initial Cleaning and Filtering
    df_total_cnae = initial_clean_and_filter(df_raw)
    if df_total_cnae is None or df_total_cnae.empty:
        print("❌ Exiting: Initial cleaning failed or resulted in empty DataFrame.")
        return
    df_total_cnae.to_csv(path_df_total_cnae, index=False, encoding='utf-8')
    print(f"Cleaned data (Total CNAE) saved to '{path_df_total_cnae.relative_to(script_dir)}'")

    # 3. Prepare Base DataFrame
    df_base = select_and_prepare_base_df(df_total_cnae)
    if df_base is None or df_base.empty:
        print("❌ Exiting: Base DataFrame preparation failed.")
        return
    df_base.to_csv(path_df_base, index=False, encoding='utf-8')
    print(f"Base DataFrame saved to '{path_df_base.relative_to(script_dir)}'")

    # 4. Identify Problematic Municipalities
    codes_to_remove, df_many_nans_pop_info = identify_problematic_municipalities(df_base, path_population_data)
    # df_many_nans_pop_info can be saved if detailed review is needed, e.g.:
    # if df_many_nans_pop_info is not None:
    # df_many_nans_pop_info.to_csv(processed_dir / "debug_high_nan_pop_info.csv", index=False)

    # 5. Stage 1 Filtering and Imputation (Removal and Zero-filling)
    df_s1_filtered = filter_and_impute_stage1(df_base, codes_to_remove, df_many_nans_pop_info)
    if df_s1_filtered is None or df_s1_filtered.empty:
        print("❌ Exiting: Stage 1 filtering/imputation failed.")
        return
    df_s1_filtered.to_csv(path_df_s1_filtered, index=False, encoding='utf-8')
    print(f"Stage 1 filtered data saved to '{path_df_s1_filtered.relative_to(script_dir)}'")

    # 6. Stage 2 Filtering and Imputation (for 11-12 NaNs with low activity)
    df_s2_filtered = filter_and_impute_stage2(df_s1_filtered)
    if df_s2_filtered is None or df_s2_filtered.empty:
        print("❌ Exiting: Stage 2 filtering/imputation failed.")
        return
    df_s2_filtered.to_csv(path_df_s2_filtered, index=False, encoding='utf-8')
    print(f"Stage 2 filtered data saved to '{path_df_s2_filtered.relative_to(script_dir)}'")


    # 7. Final Imputation by Municipal Mean
    df_final = final_impute_by_mean(df_s2_filtered)
    if df_final is None or df_final.empty:
        print("❌ Exiting: Final mean imputation failed.")
        return
    df_final.to_csv(path_final_output, index=False, encoding='utf-8')
    print(f"✅ Final imputed business data saved to '{path_final_output.relative_to(script_dir)}'")

    print("\n--- Business Data Processing Script Finished Successfully ---")


if __name__ == "__main__":
    main()