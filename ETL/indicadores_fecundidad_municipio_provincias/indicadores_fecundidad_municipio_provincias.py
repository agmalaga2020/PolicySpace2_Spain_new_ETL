# -*- coding: utf-8 -*-
"""
indicadores_fecundidad_municipio_provincias(original).py

Processes Spanish fertility data from INE, cleans it, interpolates rates
by individual age, standardizes units, and saves the results split by
province and autonomous community.

Adapted for local execution (Visual Studio Code, plain Python)
without Google Colab dependencies.
-------------------------------------------------------------------------
- Uses script-relative paths: All downloaded files, intermediate files,
  and final output folders/CSVs are created *next to this script file*,
  regardless of where the script is run from.
- Intermediate downloaded files (`tabla_*.csv`, `codigos_*.csv`) and
  intermediate processed files (`df_total_*.csv`) are saved directly
  in the script's directory.
- Final processed CSVs are saved in two subfolders within the script's directory:
  - `tasas_fertillidad_comunidades/` (one CSV per community)
  - `tasas_fertilidad_provincias/` (one CSV per province)
- Wraps execution logic in a `main()` function.
- Removes verbose output and plotting.

Run from anywhere:
    $ python path/to/indicadores_fecundidad_municipio_provincias(original).py
"""

import requests
import pandas as pd
import numpy as np
import os
import io
import re
import warnings
import pathlib # Import pathlib

# --- Configuration Constants ---
INE_TABLE_CODE = "29295"
INE_DATA_URL = f"https://servicios.ine.es/wstempus/csv/ES/DATOS_TABLA/{INE_TABLE_CODE}?nult=999"
GEO_CODES_URL = 'https://www.ine.es/daco/daco42/codmun/cod_ccaa_provincia.htm'

# --- Helper Functions ---

def get_script_directory() -> pathlib.Path:
    """Returns the absolute path to the directory containing this script."""
    return pathlib.Path(__file__).parent.resolve()

def download_file(url, save_path: pathlib.Path, is_csv=True, csv_sep='\t', encoding='utf-8'):
    """Downloads a file from a URL and optionally reads it as a CSV."""
    filename = save_path.name # Get just the filename for messages
    print(f"Attempting to download data from: {url}...")
    try:
        response = requests.get(url)
        response.raise_for_status()
        print(f"Successfully downloaded data for '{filename}'.")

        # Save the raw content using the full path
        with open(save_path, "w", encoding=encoding) as f:
            f.write(response.content.decode(encoding))
        print(f"Raw data saved to '{save_path}'.")

        if is_csv:
            # Read into DataFrame from the saved file using the full path
            df = pd.read_csv(save_path, sep=csv_sep, encoding=encoding)
            print(f"Data successfully read into DataFrame from '{filename}'.")
            return df
        else:
            return True

    except requests.exceptions.RequestException as e:
        print(f"❌ Error downloading {url}: {e}")
        return None
    except pd.errors.ParserError as e:
         print(f"❌ Error parsing CSV file '{save_path}': {e}")
         return None
    except Exception as e:
        print(f"❌ An unexpected error occurred during download/read of {filename}: {e}")
        return None

def download_html_table(url, save_path: pathlib.Path, encoding='ISO-8859-1'):
    """Downloads an HTML page, extracts the first table, and saves codes."""
    filename = save_path.name
    print(f"Attempting to download HTML table from: {url}...")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=FutureWarning)
            tablas = pd.read_html(url, encoding=encoding)

        if tablas:
            df_codigos = tablas[0]
            df_codigos.columns = ['CODAUTO', 'Comunidad Autónoma', 'CPRO', 'Provincia']
            print("HTML table obtained and columns renamed.")
            # Save using the full path
            df_codigos.to_csv(save_path, index=False, encoding='utf-8')
            print(f"Codes saved to '{save_path}'.")
            # Clean codes
            df_codigos = df_codigos[df_codigos['Comunidad Autónoma'] != 'Ciudades Autónomas']
            df_codigos = df_codigos.dropna(subset=['CPRO', 'CODAUTO', 'Comunidad Autónoma', 'Provincia'])
            return df_codigos
        else:
            print(f"❌ No tables found at {url}.")
            return None

    except ImportError:
        print("❌ Error: Libraries 'lxml' and 'html5lib' are required. Install with 'pip install lxml html5lib'")
        return None
    except Exception as e:
        print(f"❌ Error processing HTML table from {url}: {e}")
        return None

# (Keep clean_spain_data, merge_with_geo_codes, interpolate_data, standardize_rates functions as they were - they don't handle file paths directly)
def clean_spain_data(df):
    """Cleans the raw INE fertility data."""
    print("Cleaning raw Spanish fertility data...")
    df_clean = df.copy()
    df_clean.columns = df_clean.columns.str.lower()
    df_clean = df_clean[df_clean["provincias"] != "Total Nacional"]
    df_clean[["provincias_code", "provincias_name"]] = df_clean["provincias"].str.extract(r"^(\d+)\s+(.*)")

    df_clean["edad_inicio"] = pd.to_numeric(df_clean["grupos de edad"].str.extract(r"(\d+)", expand=False), errors='coerce')
    df_clean["edad_fin"] = np.where(
        df_clean["grupos de edad"].str.contains(" a ", case=False, na=False),
        pd.to_numeric(df_clean["grupos de edad"].str.extract(r"a\s*(\d+)", expand=False), errors='coerce'),
        df_clean["edad_inicio"] # End age is start age if not a range
    )
    df_clean.loc[df_clean["grupos de edad"].str.contains("Menores de", na=False), "edad_fin"] = 14

    df_clean["total"] = pd.to_numeric(df_clean["total"].astype(str).str.replace(",", "."), errors='coerce')
    df_clean['periodo'] = df_clean['periodo'].astype(int)

    initial_rows = len(df_clean)
    df_clean.dropna(subset=['edad_inicio', 'total', 'provincias_code', 'provincias_name'], inplace=True)
    if len(df_clean) < initial_rows:
         print(f"  Dropped {initial_rows - len(df_clean)} rows due to NaN values after cleaning.")

    df_clean["provincias_code"] = df_clean["provincias_code"].astype(str).str.zfill(2)

    print("Cleaning finished.")
    return df_clean

def merge_with_geo_codes(df_data, df_codigos):
    """Merges data with geographical codes."""
    if df_data is None or df_codigos is None:
        print("❌ Cannot merge, one of the DataFrames is missing.")
        return None
    print("Merging data with geographical codes...")
    df_codigos["CPRO"] = df_codigos["CPRO"].astype(int).astype(str).str.zfill(2)

    # Decide merge key based on columns available in df_data
    if "provincias_code" in df_data.columns:
        left_key = "provincias_code"
        right_key = "CPRO"
    elif "provincias_name" in df_data.columns:
         left_key = "provincias_name"
         right_key = "Provincia"
    else:
        print("❌ Cannot determine merge key ('provincias_code' or 'provincias_name' missing).")
        return None

    df_merged = df_data.merge(
        df_codigos,
        left_on=left_key,
        right_on=right_key,
        how="left"
    )

    # Clean up columns after merge if necessary
    cols_to_drop = [col for col in ["provincias", "grupos de edad", "CPRO", "Provincia"] if col in df_merged.columns]
    if "Provincia" in df_merged.columns and right_key == "Provincia": # Avoid dropping the key used if it was name
        pass # Don't drop 'Provincia' if it was the merge key from right side
    elif "Provincia" in df_merged.columns:
        # Check if 'provincias_name' exists before deciding to drop 'Provincia'
        if 'provincias_name' in df_merged.columns:
            cols_to_drop.append("Provincia")

    df_merged = df_merged.drop(columns=cols_to_drop, errors='ignore')


    nan_ccaa = df_merged['Comunidad Autónoma'].isnull().sum()
    if nan_ccaa > 0:
        print(f"⚠️ Warning: {nan_ccaa} rows could not be mapped to a Comunidad Autónoma after merge.")
    print("Merge finished.")
    return df_merged


def interpolate_data(df_clean_provincias):
    """Performs linear interpolation for each province and year."""
    if df_clean_provincias is None:
        print("❌ Cannot interpolate, input DataFrame is missing.")
        return None

    print("Starting data interpolation by age for all province-year groups...")
    interpolated_all = []
    try:
        # Use dropna=False to handle potential NaNs in grouping columns if any slipped through
        grouped = df_clean_provincias.groupby(["provincias_name", "periodo"], dropna=False)
        num_groups = grouped.ngroups
    except KeyError as e:
        print(f"❌ Interpolation failed: Missing column for grouping: {e}")
        return None

    processed_groups = 0

    for (provincia, periodo), grupo in grouped:
        # Check for NaN in grouping keys
        if pd.isna(provincia) or pd.isna(periodo):
            print(f"  Skipping interpolation for group with NaN key: Provincia='{provincia}', Periodo='{periodo}'")
            continue

        processed_groups += 1
        if processed_groups % 500 == 0: # Reduced frequency progress update
             print(f"  Interpolating group {processed_groups}/{num_groups}...")

        grupo_sorted = grupo.sort_values("edad_inicio").reset_index()
        # Ensure 'total' is numeric before using it
        grupo_sorted['total'] = pd.to_numeric(grupo_sorted['total'], errors='coerce')
        # Drop rows where 'total' became NaN as they can't be interpolated
        grupo_sorted.dropna(subset=['total'], inplace=True)

        edad_inicio_pts = grupo_sorted["edad_inicio"].astype(int).values
        total_inicio_pts = grupo_sorted["total"].values


        if len(edad_inicio_pts) < 2:
            if len(edad_inicio_pts) == 1: # Add single point if only one exists
                 interpolated_all.append({
                     "provincias_name": provincia, "periodo": periodo,
                     "edad": edad_inicio_pts[0], "total_interpolado": total_inicio_pts[0]
                 })
            continue # Skip if less than 2 points

        for i in range(len(edad_inicio_pts) - 1):
            e_start, e_end = edad_inicio_pts[i], edad_inicio_pts[i + 1]
            t_start, t_end = total_inicio_pts[i], total_inicio_pts[i + 1]

            # Skip if start or end total is NaN
            if pd.isna(t_start) or pd.isna(t_end):
                print(f"  Skipping segment for {provincia} ({periodo}) due to NaN totals between ages {e_start}-{e_end}.")
                continue

            edades = np.arange(e_start, e_end)
            num_points = len(edades)

            if num_points > 0:
                totales = np.linspace(t_start, t_end, num=num_points, endpoint=False)
                for edad, total in zip(edades, totales):
                    interpolated_all.append({
                        "provincias_name": provincia, "periodo": periodo,
                        "edad": edad, "total_interpolado": total
                    })

        # Add the last point explicitly, only if its total is not NaN
        if len(edad_inicio_pts) > 0 and pd.notna(total_inicio_pts[-1]):
             interpolated_all.append({
                 "provincias_name": provincia, "periodo": periodo,
                 "edad": edad_inicio_pts[-1], "total_interpolado": total_inicio_pts[-1]
             })

    df_total_interpolado = pd.DataFrame(interpolated_all)
    print(f"Interpolation finished. Generated {len(df_total_interpolado)} total rows.")
    return df_total_interpolado


def standardize_rates(df_interpolated_full):
    """Adds a standardized rate column (rate per woman)."""
    if df_interpolated_full is None:
        print("❌ Cannot standardize rates, input DataFrame is missing.")
        return None
    print("Standardizing rates (dividing by 1000)...")
    df_standardized = df_interpolated_full.copy()
    # Ensure the source column exists and is numeric
    if "total_interpolado" not in df_standardized.columns:
        print("❌ Cannot standardize: 'total_interpolado' column missing.")
        return None
    df_standardized['total_interpolado'] = pd.to_numeric(df_standardized['total_interpolado'], errors='coerce')
    # Perform calculation, NaNs will propagate if source was NaN
    df_standardized["tasa_estandarizada"] = df_standardized["total_interpolado"] / 1000
    print("Standardized rate column added.")
    return df_standardized

def aggregate_and_save_by_region(df_standardized, level_col, folder_path: pathlib.Path):
    """Aggregates data (if needed) and saves pivoted CSVs by region."""
    if df_standardized is None:
        print(f"❌ Cannot save by {level_col}, input DataFrame is missing.")
        return

    print(f"Processing and saving data by {level_col}...")
    # Use the full path for creating the directory
    folder_path.mkdir(parents=True, exist_ok=True)
    print(f"Ensured output folder exists: '{folder_path}'")

    data_to_process = df_standardized.copy()

    # Aggregate if level is Comunidad Autónoma
    if level_col == "Comunidad Autónoma":
        print("  Calculating mean rates per Comunidad Autónoma...")
        try:
             if "Comunidad Autónoma" not in data_to_process.columns:
                  print("  ❌ Aggregation failed: 'Comunidad Autónoma' column missing.")
                  return
             if "tasa_estandarizada" not in data_to_process.columns:
                  print("  ❌ Aggregation failed: 'tasa_estandarizada' column missing.")
                  return

             data_to_process = (
                 data_to_process
                 .groupby(["Comunidad Autónoma", "periodo", "edad"], observed=True, dropna=False)["tasa_estandarizada"] # Keep NaN groups if any
                 .mean()
                 .reset_index()
             )
             print("  Aggregation by Comunidad Autónoma finished.")
        except Exception as agg_err:
             print(f"  ❌ Error during aggregation by {level_col}: {agg_err}")
             return

    if level_col not in data_to_process.columns:
        print(f"❌ Cannot save: Grouping column '{level_col}' not found in data.")
        return

    regions = data_to_process[level_col].unique()
    saved_count = 0
    error_count = 0

    for region in regions:
        if pd.isna(region):
            print(f"  Skipping region with NaN name in column '{level_col}'.")
            continue

        df_region = data_to_process[data_to_process[level_col] == region]

        try:
            df_pivot = df_region.pivot(index="edad", columns="periodo", values="tasa_estandarizada")

            # Clean filename
            region_str = str(region) if pd.notna(region) else "NaN_Region"
            cleaned_name = re.sub(r"[^\w\-_.]", "_", region_str)
            # Construct the full save path using pathlib
            filename_path = folder_path / f"{cleaned_name}.csv"

            df_pivot.to_csv(filename_path, index=True, encoding='utf-8')
            saved_count += 1

        except ValueError as pivot_error:
            # Improved error message for duplicates
            if 'duplicate' in str(pivot_error).lower():
                 duplicates = df_region[df_region.duplicated(subset=['edad', 'periodo'], keep=False)]
                 print(f"  ❌ Error pivoting data for '{region}' in {level_col}: Duplicate entries for edad/periodo combination found. Skipping file.")
                 # Optionally print first few duplicates: print(duplicates.head())
            else:
                 print(f"  ❌ Error pivoting data for '{region}' in {level_col}: {pivot_error}. Skipping file.")
            error_count += 1
        except Exception as save_error:
            print(f"  ❌ Error saving file for '{region}' in {level_col}: {save_error}. Skipping file.")
            error_count += 1

    print(f"Finished saving by {level_col}. Successfully saved {saved_count} files, encountered {error_count} errors.")


# --- Main Execution Logic ---

def main():
    """Main function to orchestrate the data processing workflow."""
    print("--- Starting Fertility Data Processing Script ---")

    # --- Determine script-relative paths ---
    script_dir = get_script_directory()
    ine_file_path = script_dir / f"tabla_{INE_TABLE_CODE}.csv"
    geo_codes_file_path = script_dir / "codigos_ccaa_provincias.csv"
    interpolated_full_file_path = script_dir / "df_total_interpolado_full.csv"
    standardized_file_path = script_dir / "df_total_interpolado_full_tasa_estandarizada.csv"
    comunidades_folder_path = script_dir / "tasas_fertillidad_comunidades"
    provincias_folder_path = script_dir / "tasas_fertilidad_provincias"
    print(f"Script directory: {script_dir}")
    print(f"Output folders will be created inside script directory.")
    # --- End Path Definition ---

    # 1. Download Data
    # Pass the full path objects to the download functions
    df_ine_raw = download_file(INE_DATA_URL, ine_file_path, is_csv=True, csv_sep='\t')
    df_geo_codes = download_html_table(GEO_CODES_URL, geo_codes_file_path)

    if df_ine_raw is None or df_geo_codes is None:
        print("❌ Exiting script due to download failures.")
        return

    # 2. Clean Spanish Data
    df_cleaned = clean_spain_data(df_ine_raw)
    if df_cleaned is None or df_cleaned.empty:
        print("❌ Exiting script: Cleaning resulted in empty DataFrame.")
        return

    # 3. Interpolate Data by Age (Based on cleaned data before merge)
    df_interpolated = interpolate_data(df_cleaned)
    if df_interpolated is None or df_interpolated.empty:
        print("❌ Exiting script: Interpolation resulted in empty DataFrame.")
        return

    # 4. Merge Interpolated Data with Geo Codes (Now contains interpolated values and province names)
    df_interpolated_full = merge_with_geo_codes(df_interpolated, df_geo_codes)
    if df_interpolated_full is None or df_interpolated_full.empty:
        print("❌ Exiting script due to failure merging interpolated data or empty result.")
        return
    # Save intermediate full interpolated data
    try:
        # Use the full path object for saving
        df_interpolated_full.to_csv(interpolated_full_file_path, index=False, encoding='utf-8')
        print(f"Intermediate full interpolated data saved to '{interpolated_full_file_path}'.")
    except Exception as e:
        print(f"⚠️ Warning: Could not save intermediate file '{interpolated_full_file_path.name}': {e}")


    # 5. Standardize Rates
    df_standardized = standardize_rates(df_interpolated_full)
    if df_standardized is None or df_standardized.empty:
        print("❌ Exiting script due to failure standardizing rates or empty result.")
        return
    # Save standardized data
    try:
        # Use the full path object for saving
        df_standardized.to_csv(standardized_file_path, index=False, encoding='utf-8')
        print(f"Standardized interpolated data saved to '{standardized_file_path}'.")
    except Exception as e:
        print(f"⚠️ Warning: Could not save standardized file '{standardized_file_path.name}': {e}")

    # 6. Aggregate and Save Final Outputs
    # Pass the full path objects for the output folders
    aggregate_and_save_by_region(df_standardized, "Comunidad Autónoma", comunidades_folder_path)
    aggregate_and_save_by_region(df_standardized, "provincias_name", provincias_folder_path)

    print("--- Script finished successfully ---")

if __name__ == "__main__":
    # Ensure necessary libraries for pd.read_html are installed
    try:
        import lxml
        import html5lib
    except ImportError:
        print("--------------------------------------------------------------------")
        print("ERROR: Libraries 'lxml' and 'html5lib' are needed for this script.")
        print("Please install them using: pip install lxml html5lib")
        print("--------------------------------------------------------------------")
        exit() # Stop execution if libraries are missing

    main()