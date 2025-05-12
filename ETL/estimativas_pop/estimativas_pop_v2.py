# -*- coding: utf-8 -*-
"""
estimativas_pop_v2.py

Downloads, cleans, and processes Spanish municipal population data from INE
to create a consistent time series dataset. Includes outlier detection
and correction, and imputation of missing values.

Adapted for local execution (Visual Studio Code, plain Python)
without Google Colab dependencies.
-------------------------------------------------------------------------
- Uses script-relative paths.
- Raw downloaded tables (`tabla_*.csv`) are saved in `tablas_intermedias/` subfolder.
- All other intermediate and final processed files are saved in `preprocesados/` subfolder.
- Final output file: `cifras_poblacion_municipio.csv` (in `preprocesados/`).
- Wraps execution logic in functions and a `main()` function.
- Removes plotting code and verbose intermediate output.
- Requires installation of: pandas, requests, beautifulsoup4
  (pip install pandas requests beautifulsoup4)

Run from anywhere:
    $ python path/to/estimativas_pop_v2.py
"""

import requests
import pandas as pd
import numpy as np
import os
import io
import re
import glob
from pathlib import Path
from bs4 import BeautifulSoup
import warnings

# Suppress potential warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)


# --- Configuration ---
INE_BASE_URL = "https://www.ine.es"
INE_POP_PAGE_URL = "https://www.ine.es/dynt3/inebase/es/index.htm?padre=525"
# Define folder names
PROCESSED_SUBFOLDER = "preprocesados"
INTERMEDIATE_TABLES_SUBFOLDER = "tablas_intermedias" # New folder for raw tables

# --- Helper Functions ---

def get_script_directory() -> Path:
    """Returns the absolute path to the directory containing this script."""
    return Path(__file__).parent.resolve()

def create_output_folder(base_dir: Path, folder_name: str) -> Path:
    """Creates the output folder if it doesn't exist."""
    output_path = base_dir / folder_name
    try:
        output_path.mkdir(parents=True, exist_ok=True)
        print(f"Output folder ensured: '{output_path}'")
        return output_path
    except OSError as e:
        print(f"❌ Error creating output folder '{output_path}': {e}")
        return None

def download_and_extract_links(url: str) -> pd.DataFrame:
    """Fetches the INE population page and extracts links/table codes."""
    print(f"Fetching table links from: {url}...")
    try:
        response = requests.get(url)
        response.raise_for_status()
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')

        data = []
        for a in soup.find_all('a'):
            text = a.get_text(strip=True)
            if "Población por municipios y sexo" in text:
                nombre = text.split(":")[0].strip()
                enlace = a.get('href')
                table_code_match = re.search(r't=(\d+)', enlace) if enlace else None
                if enlace and table_code_match:
                    full_link = f"{INE_BASE_URL}{enlace}" if not enlace.startswith("http") else enlace
                    table_code = table_code_match.group(1)
                    data.append({"Municipio": nombre, "Enlace": full_link, "table_code": table_code})

        df_links = pd.DataFrame(data)
        if df_links.empty:
            print("⚠️ No links found matching the criteria.")
        else:
            print(f"Found {len(df_links)} table links.")
        return df_links

    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching links page: {e}")
        return pd.DataFrame() # Return empty DataFrame on error
    except Exception as e:
        print(f"❌ Error parsing links page: {e}")
        return pd.DataFrame()

# Modified to accept a specific directory for saving tables
def download_ine_tables(df_links: pd.DataFrame, tables_save_directory: Path):
    """Downloads individual INE CSV tables based on table codes into the specified directory."""
    if df_links.empty or not tables_save_directory.exists():
        print("❌ Cannot download tables: Missing links DataFrame or target save directory.")
        return False # Indicate failure

    print(f"Downloading {len(df_links)} individual INE tables into '{tables_save_directory.name}' folder...")
    success_count = 0
    error_count = 0
    for _, row in df_links.iterrows():
        code = row['table_code']
        url_csv = f"https://servicios.ine.es/wstempus/csv/ES/DATOS_TABLA/{code}?nult=999"
        # Construct path within the specific tables directory
        filename_path = tables_save_directory / f"tabla_{code}.csv"
        try:
            response = requests.get(url_csv, timeout=120)
            response.raise_for_status()
            # Save directly using utf-8 encoding
            with open(filename_path, "w", encoding="utf-8") as f:
                f.write(response.content.decode('utf-8'))
            success_count += 1
        except requests.exceptions.RequestException as e:
            print(f"  ❌ Error downloading table {code}: {e}")
            error_count += 1
        except Exception as e:
            print(f"  ❌ Error saving table {code} to '{filename_path}': {e}")
            error_count += 1

    print(f"Finished downloading tables: {success_count} successful, {error_count} errors.")
    return error_count == 0 # Return True if all downloads were successful


# Modified to read from the specific tables directory
def unify_ine_tables(tables_source_directory: Path) -> pd.DataFrame:
    """Unifies downloaded INE tables from the specified source directory."""
    print(f"Unifying downloaded tables from '{tables_source_directory}'...")
    # Use the specific source directory for glob
    archivos = list(tables_source_directory.glob("tabla_*.csv"))

    if not archivos:
        print("❌ No downloaded tables found in the specified directory to unify.")
        return pd.DataFrame()

    lista_df = []
    for archivo_path in archivos:
        try:
            table_code = archivo_path.stem.split('_')[1] # Extract code from filename stem
            df_temp = pd.read_csv(archivo_path, sep='\t', encoding='utf-8')
            df_temp['table_code'] = table_code
            lista_df.append(df_temp)
        except Exception as e:
            print(f"⚠️ Error reading or processing file '{archivo_path.name}': {e}. Skipping.")

    if not lista_df:
        print("❌ Failed to read any tables for unification.")
        return pd.DataFrame()

    df_unido = pd.concat(lista_df, ignore_index=True)
    print(f"Tables unified into a single DataFrame with {len(df_unido)} rows.")
    return df_unido

def preprocess_unified_data(df_unified: pd.DataFrame) -> pd.DataFrame:
    """Filters unified data for Sex='Total' and extracts mun_code/name."""
    if df_unified.empty:
        print("❌ Cannot preprocess: Input DataFrame is empty.")
        return pd.DataFrame()

    print("Preprocessing unified data (filtering Sex='Total', extracting codes)...")
    # Ensure 'Sexo' column exists
    if 'Sexo' not in df_unified.columns:
        print("❌ Cannot filter by Sex: 'Sexo' column not found.")
        return pd.DataFrame()

    df = df_unified[df_unified['Sexo'] == 'Total'].copy()

    # Identify the municipality column (handle variations)
    col_candidates = ["Municipios", "Código", "Municipio"] # Add more if needed
    muni_col = None
    for candidate in col_candidates:
        if candidate in df.columns:
            muni_col = candidate
            break
    if muni_col is None and len(df.columns) > 0:
         muni_col = df.columns[0] # Fallback to first column
         print(f"⚠️ Municipality column not explicitly found, using first column '{muni_col}'.")
    elif muni_col is None:
         print("❌ Cannot extract codes: No suitable municipality column found.")
         return pd.DataFrame()

    # Extract code and name, handle potential errors
    try:
        # Split only on the first space, handle cases with no space or only code
        split_data = df[muni_col].astype(str).str.split(" ", n=1, expand=True)
        df['mun_code'] = split_data[0]
        df['Municipios_name'] = split_data[1].fillna('') # Fill NaN names with empty string
        # Ensure mun_code is numeric where possible
        df['mun_code'] = pd.to_numeric(df['mun_code'], errors='coerce')
        # Optionally drop rows where mun_code could not be parsed if needed
        # df.dropna(subset=['mun_code'], inplace=True)
    except Exception as e:
        print(f"❌ Error extracting mun_code/name from column '{muni_col}': {e}")
        return pd.DataFrame() # Return empty on error

    # Optional: Clean up columns (remove original muni_col, Sexo, table_code if not needed)
    # df = df.drop(columns=[muni_col, 'Sexo', 'table_code'], errors='ignore')

    print("Preprocessing finished.")
    return df

def pivot_population_data(df_processed: pd.DataFrame) -> pd.DataFrame:
    """Pivots data to have years as columns and mun_code as index."""
    if df_processed.empty or 'mun_code' not in df_processed.columns or 'Periodo' not in df_processed.columns or 'Total' not in df_processed.columns:
        print("❌ Cannot pivot data: Missing required columns (mun_code, Periodo, Total) or empty DataFrame.")
        return pd.DataFrame()

    print("Pivoting data (mun_code vs Periodo)...")
    try:
        # Clean 'Total' before pivoting
        df_processed['Total'] = df_processed['Total'].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
        df_processed['Total'] = pd.to_numeric(df_processed['Total'], errors='coerce')

        df_pivot = df_processed.pivot_table(index='mun_code', columns='Periodo', values='Total', aggfunc='first') # Use aggfunc='first' or 'mean' if duplicates exist
        df_pivot = df_pivot.reset_index() # Make mun_code a column again
        df_pivot.columns.name = None # Remove the index name 'Periodo'
        print("Pivoting successful.")
        return df_pivot
    except Exception as e:
        print(f"❌ Error during pivoting: {e}")
        return pd.DataFrame()

def convert_pivot_to_numeric(df_pivot: pd.DataFrame) -> pd.DataFrame:
    """Converts pivoted population columns to numeric, keeping mun_code."""
    if df_pivot.empty:
        print("❌ Cannot convert to numeric: Input pivot DataFrame is empty.")
        return pd.DataFrame()

    print("Converting pivoted data to numeric...")
    df_numeric = df_pivot.copy()
    # Convert all columns except 'mun_code'
    year_cols = [col for col in df_numeric.columns if col != 'mun_code']
    for col in year_cols:
        # The cleaning should ideally happen before pivoting, but double-check here
        df_numeric[col] = pd.to_numeric(df_numeric[col], errors='coerce')

    # Verify dtypes (optional)
    # print(df_numeric.dtypes)
    print("Numeric conversion finished.")
    return df_numeric


def correct_outliers(df_numeric: pd.DataFrame, n_max_neighbors=5) -> pd.DataFrame:
    """Detects and corrects outliers using IQR and neighbor averaging."""
    if df_numeric.empty:
        print("❌ Cannot correct outliers: Input numeric DataFrame is empty.")
        return pd.DataFrame()

    print("Detecting and correcting outliers...")

    def detectar_outliers_fila(row_values):
        # Exclude non-numeric if any slipped through, though convert_pivot_to_numeric should handle this
        numeric_values = pd.to_numeric(row_values, errors='coerce').dropna()
        if len(numeric_values) < 4: return pd.Series(False, index=row_values.index) # Need enough points for IQR
        Q1 = numeric_values.quantile(0.25)
        Q3 = numeric_values.quantile(0.75)
        IQR = Q3 - Q1
        if IQR == 0: return pd.Series(False, index=row_values.index) # Avoid issues if all values are same
        lim_inf = Q1 - 1.5 * IQR
        lim_sup = Q3 + 1.5 * IQR
        # Ensure comparison is done with original numeric values
        return (row_values < lim_inf) | (row_values > lim_sup)

    def corregir_outliers_fila(row):
        codigo = row['mun_code']
        valores = row.drop('mun_code').copy()
        index = valores.index
        # Ensure the mask is calculated on the potentially non-numeric series before correction
        outlier_mask = detectar_outliers_fila(valores)
        outliers_idx = valores[outlier_mask].index

        if not outliers_idx.empty:
            # Create a working copy for modifications
            valores_corregidos = valores.copy()
            for idx_to_correct in outliers_idx:
                pos = index.get_loc(idx_to_correct)
                # Find nearest valid neighbors (not outliers themselves)
                vecinos_validos = pd.Series(dtype=float) # Initialize empty series for neighbors
                for n in range(1, n_max_neighbors + 1):
                     # Get potential neighbors (indices)
                     idx_left = index[max(0, pos - n)] if pos - n >= 0 else None
                     idx_right = index[pos + n] if pos + n < len(index) else None

                     # Check if left neighbor exists and is NOT an outlier
                     if idx_left is not None and not outlier_mask.get(idx_left, True): # Default to True if index not in mask
                          vecinos_validos = pd.concat([vecinos_validos, pd.Series({idx_left: valores[idx_left]})])

                     # Check if right neighbor exists and is NOT an outlier
                     if idx_right is not None and not outlier_mask.get(idx_right, True):
                           vecinos_validos = pd.concat([vecinos_validos, pd.Series({idx_right: valores[idx_right]})])

                     # If we have at least one valid neighbor, calculate mean and update the corrected value
                     # Ensure neighbors are numeric before calculating mean
                     numeric_neighbors = pd.to_numeric(vecinos_validos, errors='coerce').dropna()
                     if not numeric_neighbors.empty:
                          valores_corregidos[idx_to_correct] = numeric_neighbors.mean()
                          break # Stop searching for more neighbors once replacement is done
                     elif n == n_max_neighbors: # If max neighbors checked and none valid, keep original or set NaN? Keep original for now.
                         pass # Keep original outlier value if no valid neighbors found


            # Return the corrected series along with mun_code
            return pd.concat([pd.Series({'mun_code': codigo}), valores_corregidos])
        else:
            # Return original row if no outliers found
            return row

    # Apply the correction row by row
    df_corrected = df_numeric.apply(corregir_outliers_fila, axis=1)

    print("Outlier correction process finished.")
    return df_corrected

def impute_missing_values(df_corrected: pd.DataFrame, max_nan_threshold=6) -> pd.DataFrame:
    """Removes rows exceeding NaN threshold and imputes remaining NaNs."""
    if df_corrected.empty:
        print("❌ Cannot impute missing values: Input DataFrame is empty.")
        return pd.DataFrame()

    print("Imputing missing values...")
    df_impute = df_corrected.copy()

    # 1. Remove rows with too many NaNs
    year_cols = [col for col in df_impute.columns if col not in ['mun_code', 'num_outliers']] # Exclude helper cols
    nan_counts_per_row = df_impute[year_cols].isnull().sum(axis=1)
    rows_to_keep_mask = nan_counts_per_row <= max_nan_threshold
    initial_rows = len(df_impute)
    df_impute = df_impute[rows_to_keep_mask]
    removed_rows = initial_rows - len(df_impute)
    if removed_rows > 0:
        # Identify and save removed mun_codes *before* dropping them
        removed_mun_codes = df_corrected[~rows_to_keep_mask]['mun_code'].tolist()
        print(f"  Removed {removed_rows} rows exceeding the NaN threshold ({max_nan_threshold}).")
        # Optionally save these codes
        script_dir = get_script_directory()
        preproc_dir = script_dir / PROCESSED_SUBFOLDER
        removed_codes_path = preproc_dir / "municipios_borrados_por_nan.csv"
        pd.DataFrame({'mun_code_borrado': removed_mun_codes}).to_csv(removed_codes_path, index=False)
        print(f"  List of removed mun_codes saved to '{removed_codes_path.name}'")


    # 2. Interpolate horizontally (across years)
    # Ensure columns are numeric before interpolation
    for col in year_cols:
        df_impute[col] = pd.to_numeric(df_impute[col], errors='coerce')
    df_impute[year_cols] = df_impute[year_cols].interpolate(axis=1, limit_direction='both', limit_area='inside') # limit_area='inside' prevents extending NaNs at edges


    # 3. Apply ffill and bfill horizontally to catch edges that interpolate didn't fill
    df_impute[year_cols] = df_impute[year_cols].ffill(axis=1).bfill(axis=1)

    # Final check for NaNs
    nan_restantes = df_impute[year_cols].isnull().sum().sum()
    if nan_restantes > 0:
        print(f"⚠️ Warning: {nan_restantes} NaNs remain after final imputation step. Rows with persistent NaNs might need manual review or removal.")
        # Optionally identify and drop rows that still have NaNs if absolutely required
        # df_impute.dropna(subset=year_cols, inplace=True)
    else:
        print("Imputation finished. No remaining NaNs in data columns.")

    # Drop helper column if it exists
    if 'num_outliers' in df_impute.columns:
        df_impute = df_impute.drop(columns=['num_outliers'])

    return df_impute


# --- Main Execution Logic ---

def main():
    """Main function to orchestrate the data processing workflow."""
    print("--- Starting Population Estimation Processing Script ---")
    script_dir = get_script_directory()
    # Create both output folders
    preproc_dir = create_output_folder(script_dir, PROCESSED_SUBFOLDER)
    intermediate_tables_dir = create_output_folder(script_dir, INTERMEDIATE_TABLES_SUBFOLDER)

    if preproc_dir is None or intermediate_tables_dir is None:
        print("❌ Exiting: Could not create required output folders.")
        return

    # --- Define file paths using the correct directories ---
    path_df_unido = preproc_dir / "df_unido.csv"
    path_df_unido_preproc = preproc_dir / "df_unido_preprocessed.csv"
    path_df_pivot = preproc_dir / "df_pivot.csv"
    path_df_pivot_numeric = preproc_dir / "df_pivot_numeric.csv"
    path_df_corrected = preproc_dir / "df_outliers_corrected.csv"
    path_df_final = preproc_dir / "cifras_poblacion_municipio.csv"
    # ---

    # 1. Download Links
    df_links = download_and_extract_links(INE_POP_PAGE_URL)
    if df_links.empty:
        print("❌ Exiting: Failed to retrieve table links.")
        return

    # 2. Download Individual Tables into 'tablas_intermedias'
    download_success = download_ine_tables(df_links, intermediate_tables_dir)
    # Proceed even if some downloads failed, unify what was downloaded

    # 3. Unify Tables from 'tablas_intermedias'
    df_unido = unify_ine_tables(intermediate_tables_dir)
    if df_unido.empty:
        print("❌ Exiting: Failed to unify downloaded tables.")
        return
    # Save unified table into 'preprocesados'
    df_unido.to_csv(path_df_unido, index=False, encoding='utf-8')
    print(f"Unified table saved to '{path_df_unido.relative_to(script_dir)}'")

    # 4. Preprocess Unified Data
    df_unido_preproc = preprocess_unified_data(df_unido)
    if df_unido_preproc.empty:
        print("❌ Exiting: Preprocessing failed.")
        return
    df_unido_preproc.to_csv(path_df_unido_preproc, index=False, encoding='utf-8')
    print(f"Preprocessed data saved to '{path_df_unido_preproc.relative_to(script_dir)}'")

    # 5. Pivot Data
    df_pivot = pivot_population_data(df_unido_preproc)
    if df_pivot.empty:
        print("❌ Exiting: Pivoting failed.")
        return
    df_pivot.to_csv(path_df_pivot, index=False, encoding='utf-8')
    print(f"Pivoted data saved to '{path_df_pivot.relative_to(script_dir)}'")

    # 6. Convert Pivot to Numeric
    df_pivot_numeric = convert_pivot_to_numeric(df_pivot)
    if df_pivot_numeric.empty:
        print("❌ Exiting: Numeric conversion failed.")
        return
    df_pivot_numeric.to_csv(path_df_pivot_numeric, index=False, encoding='utf-8')
    print(f"Numeric pivoted data saved to '{path_df_pivot_numeric.relative_to(script_dir)}'")

    # 7. Correct Outliers
    df_corrected = correct_outliers(df_pivot_numeric)
    if df_corrected.empty:
        print("❌ Exiting: Outlier correction failed.")
        return
    df_corrected.to_csv(path_df_corrected, index=False, encoding='utf-8')
    print(f"Outlier-corrected data saved to '{path_df_corrected.relative_to(script_dir)}'")

    # 8. Impute Missing Values
    df_final = impute_missing_values(df_corrected)
    if df_final.empty:
        print("❌ Exiting: Final imputation failed.")
        return
    df_final.to_csv(path_df_final, index=False, encoding='utf-8')
    print(f"✅ Final imputed data saved to '{path_df_final.relative_to(script_dir)}'")


    print("\n--- Population Estimation Script Finished Successfully ---")


if __name__ == "__main__":
     # Ensure necessary libraries are installed
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        print("--------------------------------------------------------------------")
        print("ERROR: Library 'beautifulsoup4' is needed for this script.")
        print("Please install it using: pip install beautifulsoup4")
        print("--------------------------------------------------------------------")
        exit()

    main()
