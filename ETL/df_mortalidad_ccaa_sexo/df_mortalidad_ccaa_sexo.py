# -*- coding: utf-8 -*-
"""
df_mortalidad_ccaa_sexo.py

Downloads, cleans, processes, and imputes Spanish mortality data from INE
to generate files suitable for PolicySpace2 (or similar models).
The data covers mortality rates by CCAA, sex, age, and year.

Adapted for local execution (Visual Studio Code, plain Python)
without Google Colab dependencies.
-------------------------------------------------------------------------
- Uses script-relative paths for all file operations.
- Initial downloaded INE table (`tabla_*.csv`) and intermediate processed
  file (`df_mortalidad_final.csv`) are saved in the script's directory.
- Final pivoted mortality files (e.g., `mortality_men_AC.csv`) are saved
  in a subfolder `mortalidad_policyspace_es/` created within the
  script's directory.
- Wraps execution logic in functions and a `main()` function.
- Removes plotting code and verbose intermediate output.
- Requires installation of: pandas, requests
  (pip install pandas requests)

Run from anywhere:
    $ python path/to/df_mortalidad_ccaa_sexo.py
"""

import requests
import pandas as pd
import numpy as np
import os
from pathlib import Path
import io
import warnings

# Suppress potential warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# --- Configuration ---
INE_TABLE_CODE = "27154"
INE_DATA_URL = f"https://servicios.ine.es/wstempus/csv/ES/DATOS_TABLA/{INE_TABLE_CODE}?nult=999"
FINAL_OUTPUT_SUBFOLDER = "mortalidad_policyspace_es"

# --- Helper Functions ---

def get_script_directory() -> Path:
    """Returns the absolute path to the directory containing this script."""
    return Path(__file__).parent.resolve()

def create_output_folder(base_dir: Path, folder_name: str) -> Path | None:
    """Creates the output folder if it doesn't exist."""
    output_path = base_dir / folder_name
    try:
        output_path.mkdir(parents=True, exist_ok=True)
        print(f"Output subfolder ensured: '{output_path}'")
        return output_path
    except OSError as e:
        print(f"❌ Error creating output folder '{output_path}': {e}")
        return None

def download_ine_mortality_data(url: str, save_path: Path) -> pd.DataFrame | None:
    """Downloads INE mortality data, saves it, and reads it into a DataFrame."""
    print(f"Attempting to download INE mortality data from: {url}...")
    try:
        response = requests.get(url, timeout=120)
        response.raise_for_status()
        csv_data = response.content.decode('utf-8')

        with open(save_path, "w", encoding="utf-8") as f:
            f.write(csv_data)
        print(f"Raw INE mortality data saved to '{save_path.name}'.")

        df = pd.read_csv(save_path, sep='\t', encoding='utf-8')
        print(f"Data successfully read into DataFrame from '{save_path.name}'.")
        return df
    except requests.exceptions.RequestException as e:
        print(f"❌ Error downloading INE mortality data: {e}")
        return None
    except Exception as e:
        print(f"❌ Error processing downloaded INE mortality data: {e}")
        return None

def clean_mortality_data(df_raw: pd.DataFrame) -> pd.DataFrame | None:
    """Cleans the raw mortality data: filters, converts types, extracts codes, handles duplicates."""
    if df_raw is None or df_raw.empty:
        print("❌ Cannot clean data: Input DataFrame is missing or empty.")
        return None
    print("Cleaning raw mortality data...")

    # Filter for 'Tasa de mortalidad' and exclude 'Ambos sexos'
    df = df_raw[df_raw['Funciones'] == 'Tasa de mortalidad'].copy()
    df = df[df['Sexo'] != 'Ambos sexos'].copy()

    # Convert 'Total' to numeric (rate per 1000)
    df['Total'] = pd.to_numeric(df['Total'].astype(str).str.replace(',', '.', regex=False), errors='coerce')

    # Clean 'Edad' column, extract numeric age
    df['Edad'] = pd.to_numeric(df['Edad'].astype(str).str.extract(r'(\d+)')[0], errors='coerce').astype('Int64')
    df.dropna(subset=['Edad'], inplace=True) # Drop if age extraction failed

    # Extract CCAA code and name
    if 'Comunidades y Ciudades Autónomas' in df.columns:
        extracted_ccaa = df['Comunidades y Ciudades Autónomas'].astype(str).str.extract(r'^(\d+)\s+(.*)')
        df['ccaa_code'] = extracted_ccaa[0].str.zfill(2)
        df['ccaa_name'] = extracted_ccaa[1].str.strip()
    else:
        print("❌ Error: 'Comunidades y Ciudades Autónomas' column not found.")
        return None

    # Handle duplicates: keep row with non-NaN 'Total' if one exists, otherwise first
    key_cols = ['ccaa_code', 'Sexo', 'Edad', 'Periodo']
    df = df.sort_values('Total', na_position='last') # Prefer non-NaNs
    df = df.drop_duplicates(subset=key_cols, keep='first')

    print("Mortality data cleaning finished.")
    return df

def impute_ceuta_melilla_age95(df_cleaned: pd.DataFrame) -> pd.DataFrame | None:
    """Imputes missing 'Total' for Ceuta/Melilla at age 95 using national average."""
    if df_cleaned is None or df_cleaned.empty: return None
    print("Imputing missing data for Ceuta/Melilla (age 95)...")
    df_imputed = df_cleaned.copy()

    # Calculate national average for age 95, excluding Ceuta/Melilla
    media_nacional_edad_95 = (
        df_imputed[
            (df_imputed['Edad'] == 95) &
            (~df_imputed['ccaa_name'].isin(['Ceuta', 'Melilla'])) &
            (df_imputed['Total'].notna())
        ]
        .groupby(['Periodo', 'Sexo'])['Total']
        .mean()
        .reset_index(name='media_nacional_val') # Renamed to avoid conflict
    )

    if media_nacional_edad_95.empty:
        print("⚠️ Warning: Could not calculate national average for imputation. Skipping imputation.")
        return df_imputed # Return as is if no average can be calculated

    # Merge national average back to the main DataFrame
    df_imputed = df_imputed.merge(media_nacional_edad_95, on=['Periodo', 'Sexo'], how='left')

    # Impute only where needed
    mask_impute = (
        (df_imputed['Edad'] == 95) &
        (df_imputed['ccaa_name'].isin(['Ceuta', 'Melilla'])) &
        (df_imputed['Total'].isna()) &
        (df_imputed['media_nacional_val'].notna()) # Ensure there's a value to impute
    )
    df_imputed.loc[mask_impute, 'Total'] = df_imputed.loc[mask_impute, 'media_nacional_val']

    df_imputed.drop(columns=['media_nacional_val'], inplace=True, errors='ignore')

    # Check if imputation was successful for target rows
    still_na_after_impute = df_imputed[
        (df_imputed['Edad'] == 95) &
        (df_imputed['ccaa_name'].isin(['Ceuta', 'Melilla'])) &
        (df_imputed['Total'].isna())
    ].shape[0]

    if still_na_after_impute > 0:
        print(f"⚠️ Warning: {still_na_after_impute} NaNs remain for Ceuta/Melilla age 95 after imputation attempt.")
    else:
        print("Imputation for Ceuta/Melilla (age 95) complete.")

    return df_imputed


def finalize_and_convert_to_probability(df_imputed: pd.DataFrame) -> pd.DataFrame | None:
    """Selects final columns and converts mortality rate to probability."""
    if df_imputed is None or df_imputed.empty: return None
    print("Finalizing data and converting rates to probabilities...")

    # Select relevant columns
    cols_to_keep = ['ccaa_code', 'ccaa_name', 'Edad', 'Periodo', 'Total', 'Sexo']
    if not all(col in df_imputed.columns for col in ['ccaa_code', 'Edad', 'Periodo', 'Total', 'Sexo']):
        print("❌ Error: Missing one or more required columns for final selection.")
        return None
    df_final_selection = df_imputed[cols_to_keep].copy()

    # Convert rate (per 1000) to probability (0-1)
    # Ensure 'Total' is numeric first
    df_final_selection['Total'] = pd.to_numeric(df_final_selection['Total'], errors='coerce')
    df_final_selection['prob_mortalidad'] = df_final_selection['Total'] / 1000

    # Drop original 'Total' (rate per 1000) and rename 'prob_mortalidad' to 'Total' to match original final structure.
    # Or, if the final files need 'prob_mortalidad', then keep that name.
    # The original notebook saves 'Total' which is the probability.
    df_final_selection.drop(columns=['Total'], inplace=True)
    df_final_selection.rename(columns={'prob_mortalidad': 'Total'}, inplace=True)


    # Handle any remaining NaNs in 'Total' (probability column) if critical, e.g., fill with a default or drop.
    # For now, we assume previous steps handled most critical NaNs.
    if df_final_selection['Total'].isna().any():
        print(f"⚠️ Warning: {df_final_selection['Total'].isna().sum()} NaNs present in final 'Total' (probability) column. Consider further imputation if problematic.")
        # Example: df_final_selection['Total'].fillna(df_final_selection['Total'].median(), inplace=True) # Or 0, or drop

    print("Data finalized. 'Total' column now represents probability of mortality.")
    return df_final_selection


def create_and_save_pivoted_files(df_final_probs: pd.DataFrame, output_dir: Path):
    """Creates pivoted files by CCAA and Sex, for years 2010-2020."""
    if df_final_probs is None or df_final_probs.empty or not output_dir.exists():
        print("❌ Cannot create pivoted files: Input data or output directory missing/invalid.")
        return

    print(f"Creating and saving pivoted mortality files to '{output_dir.name}' folder...")
    # Filter for years 2010-2020
    df_filtered_years = df_final_probs[
        pd.to_numeric(df_final_probs['Periodo'], errors='coerce').between(2010, 2020)
    ].copy()
    df_filtered_years['Periodo'] = df_filtered_years['Periodo'].astype(int) # Ensure Periodo is int for column names

    if df_filtered_years.empty:
        print("⚠️ No data found for the period 2010-2020. No files will be generated.")
        return

    saved_count = 0
    for ccaa_code in df_filtered_years['ccaa_code'].unique():
        if pd.isna(ccaa_code): continue # Skip if ccaa_code is NaN
        for sexo_val in ['Hombres', 'Mujeres']:
            df_temp = df_filtered_years[
                (df_filtered_years['ccaa_code'] == ccaa_code) &
                (df_filtered_years['Sexo'] == sexo_val)
            ]
            if df_temp.empty: continue

            try:
                df_pivot = df_temp.pivot_table(index='Edad', columns='Periodo', values='Total', aggfunc='first').sort_index()
                df_pivot.reset_index(inplace=True)
                df_pivot.columns.name = None  # Remove index name from columns

                sex_label = 'men' if sexo_val == 'Hombres' else 'women'
                filename = f"mortality_{sex_label}_{ccaa_code}.csv"
                filepath = output_dir / filename
                df_pivot.to_csv(filepath, sep=';', index=False, encoding='utf-8')
                saved_count += 1
            except Exception as e:
                print(f"  ❌ Error creating/saving pivoted file for CCAA {ccaa_code}, Sex {sexo_val}: {e}")

    print(f"Pivoted files generation complete. {saved_count} files saved.")


# --- Main Execution Logic ---

def main():
    """Main function to orchestrate the mortality data processing."""
    print("--- Starting Mortality Data Processing Script ---")
    script_dir = get_script_directory()

    # Define file paths (intermediate files saved in script's root directory for simplicity)
    path_raw_ine_data = script_dir / f"tabla_{INE_TABLE_CODE}.csv"
    path_df_mortalidad_final_csv = script_dir / "df_mortalidad_final.csv" # Intermediate, before pivoting
    final_pivoted_output_dir = create_output_folder(script_dir, FINAL_OUTPUT_SUBFOLDER)
    if final_pivoted_output_dir is None: return
    # ---

    # 1. Download INE Mortality Data
    df_raw = download_ine_mortality_data(INE_DATA_URL, path_raw_ine_data)
    if df_raw is None:
        print("❌ Exiting: Failed to download or read INE mortality data.")
        return

    # 2. Clean Raw Data
    df_cleaned = clean_mortality_data(df_raw)
    if df_cleaned is None or df_cleaned.empty:
        print("❌ Exiting: Data cleaning failed or resulted in empty DataFrame.")
        return

    # 3. Impute for Ceuta/Melilla age 95
    df_imputed = impute_ceuta_melilla_age95(df_cleaned)
    if df_imputed is None or df_imputed.empty:
        print("❌ Exiting: Imputation step failed.")
        return

    # 4. Finalize (select cols, convert to probability)
    df_final_probs_long = finalize_and_convert_to_probability(df_imputed)
    if df_final_probs_long is None or df_final_probs_long.empty:
        print("❌ Exiting: Final data preparation failed.")
        return
    # Save this intermediate long-format file
    df_final_probs_long.to_csv(path_df_mortalidad_final_csv, index=False, encoding='utf-8')
    print(f"Intermediate processed mortality data (long format) saved to '{path_df_mortalidad_final_csv.name}'.")

    # 5. Create and Save Pivoted Files for PolicySpace2 format
    create_and_save_pivoted_files(df_final_probs_long, final_pivoted_output_dir)

    print("\n--- Mortality Data Processing Script Finished Successfully ---")


if __name__ == "__main__":
    main()
