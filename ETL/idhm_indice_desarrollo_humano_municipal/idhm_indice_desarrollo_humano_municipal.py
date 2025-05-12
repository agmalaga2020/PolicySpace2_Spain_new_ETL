# -*- coding: utf-8 -*-
"""
idhm_indice_desarrollo_humano_municipal.py

Calculates a Municipal Human Development Index (IDHM) for Spain using
data primarily from the Spanish Tax Agency (AEAT) and INE.

Adapted for local execution (Visual Studio Code, plain Python)
without Google Colab dependencies.
-------------------------------------------------------------------------
- Uses script-relative paths: All downloaded files, intermediate files,
  and final output folders/CSVs are created *next to this script file*,
  regardless of where the script is run from.
- Intermediate files (PDFs, mappings, processed/imputed data) are saved
  directly in the script's directory.
- Final output files:
  - `IRPFmunicipios_final_IDHM.csv` (full data used for calculation)
  - `idhm_2013_2022.csv` (simplified format for modeling: year;cod_mun;idhm)
- Wraps execution logic in functions and a `main()` function.
- Removes plotting code and verbose intermediate output.

Run from anywhere:
    $ python path/to/idhm_indice_desarrollo_humano_municipal.py
"""

import requests
import pandas as pd
import numpy as np
import os
import io
import re
import warnings
import pdfplumber
import logging
from pathlib import Path

# --- Configuration ---
# Suppress PDFMiner logging noise
logging.getLogger("pdfminer").setLevel(logging.ERROR)

# URLs
AEAT_HELP_PDF_URL = (
    "https://sede.agenciatributaria.gob.es/static_files/Sede/Tema/"
    "Estadisticas/Anuario_estadistico/Exportacion/"
    "AyudaCSV_AnuarioMunicipal.pdf"
)
AEAT_IRPF_CSV_URL = (
    "https://sede.agenciatributaria.gob.es/static_files/Sede/Tema/"
    "Estadisticas/Anuario_estadistico/Exportacion/IRPFmunicipios.csv"
)
INE_MUNI_CODES_URL = "https://www.ine.es/daco/daco42/codmun/diccionario25.xlsx"
INE_MORTALITY_TABLE_CODE = "27154"
INE_MORTALITY_URL = f"https://servicios.ine.es/wstempus/csv/ES/DATOS_TABLA/{INE_MORTALITY_TABLE_CODE}?nult=999"
INE_EDUCATION_TABLE_CODE = "65289"
INE_EDUCATION_URL = f"https://servicios.ine.es/wstempus/csv/ES/DATOS_TABLA/{INE_EDUCATION_TABLE_CODE}?nult=999"


# --- Helper Functions ---

def get_script_directory() -> Path:
    """Returns the absolute path to the directory containing this script."""
    return Path(__file__).parent.resolve()

def download_pdf_content(url, timeout=120):
    """Downloads PDF content from a URL."""
    print(f"Attempting to download PDF from: {url}...")
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        print("Successfully downloaded PDF content.")
        return io.BytesIO(response.content)
    except requests.exceptions.RequestException as e:
        print(f"❌ Error downloading PDF from {url}: {e}")
        return None

def download_csv_to_dataframe(url, save_path: Path, sep=";", decimal=",", encoding="latin-1", timeout=120, dtype=None):
    """Downloads a CSV from a URL, saves it, and reads it into a DataFrame."""
    print(f"Attempting to download CSV from: {url}...")
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        print(f"Successfully downloaded CSV content for '{save_path.name}'.")

        # Save the raw content
        with open(save_path, "wb") as f: # Use 'wb' for binary content
            f.write(response.content)
        print(f"Raw data saved to '{save_path}'.")

        # Read into DataFrame
        df = pd.read_csv(save_path, sep=sep, decimal=decimal, encoding=encoding, dtype=dtype)
        print(f"Data successfully read into DataFrame from '{save_path.name}'.")
        return df

    except requests.exceptions.RequestException as e:
        print(f"❌ Error downloading CSV from {url}: {e}")
        return None
    except pd.errors.ParserError as e:
         print(f"❌ Error parsing CSV file '{save_path}': {e}")
         return None
    except Exception as e:
        print(f"❌ An unexpected error occurred during download/read of {save_path.name}: {e}")
        return None

def download_excel_to_dataframe(url, save_path: Path, skiprows=None, timeout=120):
    """Downloads an Excel file from a URL, saves it, and reads it into a DataFrame."""
    print(f"Attempting to download Excel from: {url}...")
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        print(f"Successfully downloaded Excel content for '{save_path.name}'.")

        # Save the raw content
        with open(save_path, "wb") as f:
            f.write(response.content)
        print(f"Raw data saved to '{save_path}'.")

        # Read into DataFrame
        df = pd.read_excel(save_path, skiprows=skiprows)
        print(f"Data successfully read into DataFrame from '{save_path.name}'.")
        return df

    except requests.exceptions.RequestException as e:
        print(f"❌ Error downloading Excel from {url}: {e}")
        return None
    except Exception as e:
        print(f"❌ An unexpected error occurred during download/read of {save_path.name}: {e}")
        return None

def extract_muni_variable_mapping(pdf_io):
    """Extracts MUNI_XXX variable mappings from the AEAT help PDF."""
    if pdf_io is None: return None
    print("Extracting AEAT variable mappings from PDF...")
    pattern = re.compile(r"^(MUNI_\d{1,3})\s+(.*)$")
    records = []
    try:
        with pdfplumber.open(pdf_io) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text: continue
                for line in text.splitlines():
                    match = pattern.match(line.strip())
                    if match:
                        variable = match.group(1)
                        literal = re.sub(r"\s{2,}", " ", match.group(2)).strip()
                        records.append((variable, literal))
        df = (pd.DataFrame(records, columns=["Variable", "Literal"])
                .assign(order=lambda d: d["Variable"].str.extract(r"_(\d+)").astype(int))
                .sort_values("order")
                .drop(columns="order")
                .reset_index(drop=True))
        print("Variable mapping extracted successfully.")
        return df
    except Exception as e:
        print(f"❌ Error extracting variable mappings from PDF: {e}")
        return None

def process_aeat_irpf_data(df_raw):
    """Selects, renames, cleans, and calculates per capita income from raw AEAT data."""
    if df_raw is None: return None
    print("Processing raw AEAT IRPF data...")
    col_map = {
        "EJER": "year", "MUNI_DEF": "codigo_aeat", "MUNI_4": "population",
        "MUNI_23": "renta_bruta_total", "MUNI_28": "renta_disponible_total",
    }
    if not all(col in df_raw.columns for col in col_map.keys()):
        print("❌ Error: Raw AEAT DataFrame is missing required columns.")
        return None

    df = df_raw[list(col_map)].rename(columns=col_map)

    numeric_cols = ["population", "renta_bruta_total", "renta_disponible_total"]
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")

    # Handle division by zero or NaN population gracefully
    df["renta_disponible_per_capita"] = np.where(
        (df["population"] > 0) & (df["population"].notna()),
        df["renta_disponible_total"] / df["population"],
        np.nan # Set to NaN if population is zero, negative, or NaN
    )

    df = df[[ "year", "codigo_aeat", "population", "renta_bruta_total",
              "renta_disponible_total", "renta_disponible_per_capita"]]
    print("AEAT IRPF data processed.")
    return df

def impute_and_clean_irpf_data(df_processed):
    """Imputes missing values and removes rows with insufficient data."""
    if df_processed is None: return None
    print("Imputing and cleaning processed IRPF data...")
    df = df_processed.sort_values(["codigo_aeat", "year"]).copy()

    # Impute temporally within each municipality
    impute_cols = ["population", "renta_bruta_total", "renta_disponible_total"]
    for col in impute_cols:
        # Use transform with lambda for imputation
        df[col] = df.groupby("codigo_aeat")[col].transform(lambda s: s.ffill().bfill())

    # Recalculate per capita income after imputation
    df["renta_disponible_per_capita"] = np.where(
        (df["population"] > 0) & (df["population"].notna()),
        df["renta_disponible_total"] / df["population"],
        np.nan
    )

    # Identify rows/municipalities to remove
    # a) No population AND no total disposable income after imputation
    mask_both_missing = df["population"].isna() & df["renta_disponible_total"].isna()

    # b) Population is still NaN for ALL years of a municipality
    # Calculate size and count of NaNs per group
    pop_stats = df.groupby("codigo_aeat")["population"].agg(['size', lambda x: x.isna().sum()])
    pop_stats.columns = ['total_years', 'nan_years']
    # Identify municipalities where all years have NaN population
    munis_all_pop_na = pop_stats[pop_stats['nan_years'] == pop_stats['total_years']].index
    mask_pop_always_na = df['codigo_aeat'].isin(munis_all_pop_na)

    mask_remove = mask_both_missing | mask_pop_always_na
    removed_count = mask_remove.sum()
    removed_codes = sorted(df.loc[mask_remove, "codigo_aeat"].unique())

    df_final = df[~mask_remove].copy()

    if removed_count > 0:
        print(f"  Removed {removed_count} rows due to irreparable missing data.")
        print(f"  Affected AEAT codes: {removed_codes}")
    else:
        print("  No rows removed during imputation/cleaning.")

    # Final check for NaNs
    if df_final[impute_cols + ["renta_disponible_per_capita"]].isna().any().any():
         print("⚠️ Warning: NaNs remain after imputation. Check logic.")

    print("Imputation and cleaning finished.")
    return df_final

def filter_full_series(df_imputed):
    """Filters the data to keep only municipalities with a full time series."""
    if df_imputed is None: return None
    print("Filtering for municipalities with full time series...")
    expected_years = df_imputed['year'].nunique()
    year_counts = df_imputed.groupby("codigo_aeat")["year"].nunique()
    full_series_codes = year_counts[year_counts == expected_years].index
    df_full = df_imputed[df_imputed["codigo_aeat"].isin(full_series_codes)].copy()
    print(f"Filtered down to {len(full_series_codes)} municipalities with full {expected_years}-year series.")
    return df_full

def extract_aeat_ine_equivalencies(pdf_io):
    """Extracts AEAT to INE code equivalencies from the AEAT help PDF."""
    if pdf_io is None: return None
    print("Extracting AEAT-INE equivalency table from PDF...")
    filas_acumuladas = []
    encabezado_ref = None
    try:
        with pdfplumber.open(pdf_io) as pdf:
            for page in pdf.pages:
                # Adjust settings for better table extraction if needed
                tables = page.extract_tables(table_settings={"vertical_strategy": "lines", "horizontal_strategy": "lines"})
                for table in tables:
                    if table and table[0] and table[0][0] == "MUNI_DEF":
                        if encabezado_ref is None:
                            encabezado_ref = table[0]
                        filas_acumuladas.extend(row for row in table[1:] if row and row[0] != "MUNI_DEF")

        if not filas_acumuladas or encabezado_ref is None:
            print("❌ No table with header 'MUNI_DEF' found in PDF.")
            return None

        df = pd.DataFrame(filas_acumuladas, columns=encabezado_ref)
        df = df.dropna(how="all").drop_duplicates().reset_index(drop=True)
        print("Equivalency table extracted.")
        return df
    except Exception as e:
        print(f"❌ Error extracting equivalency table from PDF: {e}")
        return None

def clean_equivalency_table(df_equiv_raw):
    """Cleans the raw equivalency table."""
    if df_equiv_raw is None: return None
    print("Cleaning AEAT-INE equivalency table...")
    df = df_equiv_raw.copy()
    # Remove summary rows
    mask = df["MUNICIPIO"].str.contains(r"Resto acumulado|Agrupación municipios pequeños", case=False, na=False)
    df = df[~mask]

    # Fix Ceuta and Melilla (assuming MUNI_DEF 9151 is Ceuta, 9152 is Melilla based on typical AEAT codes)
    # Verify these MUNI_DEF codes if possible from the source or other contexts.
    # Use .loc for setting values
    df.loc[df["MUNI_DEF"] == '9151', ["CCAA", "PROVINCIA", "MUNICIPIO"]] = ["Ceuta", "Ceuta", "Ceuta-51001"]
    df.loc[df["MUNI_DEF"] == '9152', ["CCAA", "PROVINCIA", "MUNICIPIO"]] = ["Melilla", "Melilla", "Melilla-52001"]

    # Extract 5-digit INE code
    df["mun_code"] = df["MUNICIPIO"].str.extract(r"(\d{5})$")[0]
    df["mun_code"] = pd.to_numeric(df["mun_code"], errors='coerce').astype("Int64")

    # Clean MUNI_DEF to numeric
    df["MUNI_DEF"] = pd.to_numeric(df["MUNI_DEF"], errors='coerce').astype("Int64")


    # Remove rows where mun_code or MUNI_DEF extraction failed
    initial_rows = len(df)
    df = df.dropna(subset=["mun_code", "MUNI_DEF"]).copy()
    if len(df) < initial_rows:
         print(f"  Removed {initial_rows - len(df)} rows with missing mun_code or MUNI_DEF.")

    # Check for duplicate mun_codes or MUNI_DEF
    dup_mun_code = df["mun_code"].duplicated().sum()
    dup_muni_def = df["MUNI_DEF"].duplicated().sum()
    if dup_mun_code > 0: print(f"⚠️ Warning: {dup_mun_code} duplicate mun_code values found.")
    if dup_muni_def > 0: print(f"⚠️ Warning: {dup_muni_def} duplicate MUNI_DEF values found.")

    print("Equivalency table cleaned.")
    return df

def process_ine_municipality_codes(df_ine_raw):
    """Processes the raw INE municipality dictionary."""
    if df_ine_raw is None: return None
    print("Processing INE municipality codes dictionary...")
    df = df_ine_raw.copy()
    # Ensure codes are strings with leading zeros
    df['CPRO'] = df['CPRO'].astype(int).astype(str).str.zfill(2)
    df['CMUN'] = df['CMUN'].astype(int).astype(str).str.zfill(3)
    df['mun_code'] = df['CPRO'] + df['CMUN']
    df['mun_code'] = pd.to_numeric(df['mun_code'], errors='coerce').astype("Int64")
    # Select relevant columns
    df_out = df[['mun_code', 'NOMBRE', 'CODAUTO']].copy() # Added CODAUTO
    df_out['CODAUTO'] = df_out['CODAUTO'].astype(int).astype(str).str.zfill(2) # Format CODAUTO
    print("INE codes dictionary processed.")
    return df_out


def map_codes_and_names(df_renta, df_equiv_clean, df_ine_codes):
    """Maps INE codes and names onto the rent data."""
    if df_renta is None or df_equiv_clean is None or df_ine_codes is None:
        print("❌ Cannot map codes/names, input DataFrames missing.")
        return None
    print("Mapping INE codes and names to rent data...")

    # 1. Map AEAT code -> mun_code (INE 5-digit)
    df_eq_subset = df_equiv_clean[["MUNI_DEF", "mun_code"]].rename(columns={"MUNI_DEF": "codigo_aeat"})
    df_mapped = df_renta.merge(df_eq_subset, on="codigo_aeat", how="left")

    # 2. Map mun_code -> NOMBRE and CODAUTO (from INE dictionary)
    df_ine_subset = df_ine_codes[["mun_code", "NOMBRE", "CODAUTO"]] # Include CODAUTO
    df_mapped = df_mapped.merge(df_ine_subset, on="mun_code", how="left")

    # 3. Handle potential mapping issues (e.g., code 440 mentioned in original)
    initial_rows = len(df_mapped)
    # Example: remove rows where mapping failed or for specific problematic codes
    # df_mapped = df_mapped[df_mapped["mun_code"] != 440] # If code 440 is problematic
    df_mapped = df_mapped.dropna(subset=["mun_code", "NOMBRE", "CODAUTO"]) # Remove rows where mapping failed
    if len(df_mapped) < initial_rows:
         print(f"  Removed {initial_rows - len(df_mapped)} rows due to mapping issues or specific filters.")

    # Final check for NaNs in key mapping columns
    if df_mapped[["mun_code", "NOMBRE", "CODAUTO"]].isna().any().any():
        print("⚠️ Warning: NaNs remain in mun_code, NOMBRE, or CODAUTO after mapping.")

    print("Mapping finished.")
    return df_mapped

def process_ine_mortality_data(df_raw):
    """Cleans and prepares INE mortality data."""
    if df_raw is None: return None
    print("Processing INE mortality data...")
    df = df_raw[df_raw["Funciones"] == "Tasa de mortalidad"].query("Sexo != 'Ambos sexos'").copy()

    df["Total"] = pd.to_numeric(df["Total"].str.replace(",", ".", regex=False), errors='coerce')
    df["Edad"] = pd.to_numeric(df["Edad"].str.extract(r"(\d+)")[0], errors='coerce').astype(int)
    df[["ccaa_code", "ccaa_name"]] = df["Comunidades y Ciudades Autónomas"].str.extract(r"^(\d+)\s+(.*)")
    df["ccaa_code"] = df["ccaa_code"].str.zfill(2)

    # Handle duplicates, preferring non-NaN 'Total'
    df = df.sort_values('Total', na_position='last')
    df = df.drop_duplicates(subset=["ccaa_code", "Sexo", "Edad", "Periodo"], keep='first')


    # Impute NaNs for Ceuta/Melilla at age 95 using national average (excluding C/M)
    media_nac = (
        df[(df["Edad"] == 95) & (~df["ccaa_name"].isin(["Ceuta", "Melilla"])) & (df["Total"].notna())]
        .groupby(["Periodo", "Sexo"])["Total"]
        .mean()
        .reset_index(name="media_nacional")
    )
    df = df.merge(media_nac, on=["Periodo", "Sexo"], how="left")
    mask_impute = (df["Edad"].eq(95) & df["ccaa_name"].isin(["Ceuta", "Melilla"]) & df["Total"].isna())
    df.loc[mask_impute, "Total"] = df.loc[mask_impute, "media_nacional"]
    df.drop(columns="media_nacional", inplace=True)

    # Convert rate (per 1000) to probability
    df["prob_mortalidad"] = df["Total"] / 1000

    # Final selection and check for remaining NaNs in prob_mortalidad
    df_final = df[["ccaa_code", "ccaa_name", "Edad", "Periodo", "Sexo", "prob_mortalidad"]].copy()
    if df_final["prob_mortalidad"].isna().any():
         print("⚠️ Warning: NaNs remain in 'prob_mortalidad' after processing.")
         # Optional: Drop rows with NaN probability if they cannot be used
         # df_final.dropna(subset=["prob_mortalidad"], inplace=True)

    print("Mortality data processed.")
    return df_final

def calculate_health_index(df_mortality):
    """Calculates life expectancy (EV0) and health index (I_salud) per CCAA/Year."""
    if df_mortality is None: return None
    print("Calculating Life Expectancy (EV0) and Health Index (I_salud)...")

    def ev0_from_m(m_series):
        # Life table calculation using m(x) rates
        ages = list(m_series.index)
        m_x = m_series.values
        l, T = 100_000.0, 0.0
        for i, age in enumerate(ages):
            m = m_x[i]
            if pd.isna(m): continue # Skip if m(x) is NaN
            # Define n (interval width) and a (average years lived in interval by those dying)
            if age == 0: n, a = 1, 0.3
            elif age == 1: n, a = 4, 1.5
            elif age < 85: n, a = 5, 2.5
            else: # Final open interval (85+)
                if m > 0: T += l / m # Estimate T_85
                l = 0 # Everyone dies eventually
                break
            # Calculate q(x) from m(x)
            q = (n * m) / (1 + (n - a) * m) if (1 + (n - a) * m) != 0 else 1.0 # Avoid division by zero
            q = min(q, 1.0) # Probability cannot exceed 1
            d = l * q
            Lx = n * l - d * (n - a) # Person-years lived in interval
            T += Lx
            l -= d # Survivors to next age
            if l <= 0: break # Stop if no survivors
        return round(T / 100_000.0, 2) if T > 0 else 0 # EV0 = T_0 / l_0

    rows = []
    # Ensure Periodo is integer for grouping
    df_mortality['Periodo'] = pd.to_numeric(df_mortality['Periodo'], errors='coerce')
    df_mortality.dropna(subset=['Periodo'], inplace=True)
    df_mortality['Periodo'] = df_mortality['Periodo'].astype(int)

    for (ccaa, year), grp in df_mortality.groupby(["ccaa_code", "Periodo"]):
        # Pivot and handle missing sex data by averaging
        piv = grp.pivot(index="Edad", columns="Sexo", values="prob_mortalidad")
        if "Hombres" not in piv.columns and "Mujeres" in piv.columns: piv["Hombres"] = piv["Mujeres"]
        if "Mujeres" not in piv.columns and "Hombres" in piv.columns: piv["Mujeres"] = piv["Hombres"]
        if "Hombres" not in piv.columns or "Mujeres" not in piv.columns: continue # Skip if no sex data

        m_mean = piv.mean(axis=1).sort_index() # Average mortality rate m(x)
        ev0 = ev0_from_m(m_mean)
        rows.append({"CODAUTO": ccaa, "year": year, "EV0": ev0})

    ev = pd.DataFrame(rows)
    ev["I_salud"] = ((ev["EV0"] - 20) / 65).clip(0, 1) # Normalize and clip
    print("EV0 and I_salud calculated.")
    return ev

def process_ine_education_data(df_raw):
    """Cleans and prepares INE education level data."""
    if df_raw is None: return None
    print("Processing INE education data...")

    # Dynamically find column names (handle potential variations)
    cols = df_raw.columns.tolist()
    try:
        sex_col     = next(c for c in cols if 'sexo' in c.lower())
        region_col  = next(c for c in cols if 'comunidades' in c.lower() or 'ciudades' in c.lower())
        nivel_col   = next(c for c in cols if 'nivel' in c.lower())
        periodo_col = next(c for c in cols if 'periodo' in c.lower())
        total_col   = next(c for c in cols if c.lower() == 'total')
    except StopIteration:
        print("❌ Error: Could not find expected columns in education data.")
        return None

    df = df_raw[df_raw[region_col] != "Total Nacional"].copy()
    df[["ccaa_code", "ccaa_name"]] = df[region_col].str.extract(r"^(\d+)\s+(.*)$", expand=True)
    df["ccaa_code"] = df["ccaa_code"].str.zfill(2)

    # Clean 'Total' column carefully
    df["total"] = df[total_col].astype(str).str.replace(r'[^\d,]', '', regex=True) # Keep only digits and comma
    df["total"] = pd.to_numeric(df["total"].str.replace(",", ".", regex=False), errors='coerce')


    df = df.rename(columns={sex_col: "sexo", nivel_col: "nivel_formacion", periodo_col: "periodo"})
    df = df[df["sexo"].str.lower() == "ambos sexos"]
    df = df[~df["nivel_formacion"].str.lower().eq("total")]

    df["year"] = pd.to_numeric(df["periodo"].str.extract(r"(\d{4})")[0], errors='coerce').astype('Int64')
    df.dropna(subset=['year'], inplace=True) # Drop if year extraction failed

    # Fix potential encoding issues in level names
    try:
        df["nivel_formacion"] = df["nivel_formacion"].str.encode("latin-1", errors="ignore").str.decode("utf-8", errors="ignore")
    except Exception as e:
         print(f"⚠️ Warning: Encoding fix for nivel_formacion failed: {e}")

    # Map levels to numeric codes
    codigo_niveles = {
        'analfabetos': 1, 'estudios primarios incompletos': 2, 'educación primaria': 3,
        'primera etapa de educación secundaria y similar': 4,
        'segunda etapa de educación secundaria, con orientación general': 5,
        'segunda etapa de educación secundaria con orientación profesional (incluye educación postsecundaria no superior)': 6,
        'educación superior': 7
    }
    df["nivel_code"] = df["nivel_formacion"].str.lower().map(codigo_niveles)
    df.dropna(subset=['nivel_code'], inplace=True) # Drop levels not in map
    df["nivel_code"] = df["nivel_code"].astype(int)

    # Aggregate average 'total' per level
    df_med = df.groupby(["ccaa_code", "year", "nivel_code"], as_index=False)["total"].mean()

    # Pivot to wide format
    df_pivot = df_med.pivot_table(index=["ccaa_code", "year"], columns="nivel_code", values="total").reset_index()
    df_pivot.columns.name = None # Remove name from columns index

    # Ensure all level columns 1-7 exist, fill missing with 0 or NaN
    expected_cols = list(range(1, 8))
    for col in expected_cols:
        if col not in df_pivot.columns:
            df_pivot[col] = 0 # Or np.nan if preferred

    df_pivot = df_pivot[["ccaa_code", "year"] + expected_cols]
    print("Education data processed.")
    return df_pivot


def calculate_education_index(df_education_pivot):
    """Calculates the education index (I_educ) per CCAA/Year."""
    if df_education_pivot is None: return None
    print("Calculating Education Index (I_educ)...")
    df = df_education_pivot.copy()
    level_cols = [col for col in df.columns if isinstance(col, int) and 1 <= col <= 7]

    # Ensure level columns are numeric, fill NaNs with 0 for calculation
    df[level_cols] = df[level_cols].apply(pd.to_numeric, errors='coerce').fillna(0)

    # Calculate total population and weighted sum for the index
    df["total_pop"] = df[level_cols].sum(axis=1)
    weighted_sum = sum(level * df[level] for level in level_cols)

    # Calculate I_educ, handle division by zero
    df["I_educ"] = np.where(
        df["total_pop"] > 0,
        (weighted_sum / df["total_pop"]) / 7, # Divide average level by max level (7)
        0 # Assign 0 if total_pop is 0
    ).clip(0, 1) # Ensure index is between 0 and 1

    df_out = df[["ccaa_code", "year", "I_educ"]].rename(columns={"ccaa_code": "CODAUTO"})
    df_out["CODAUTO"] = df_out["CODAUTO"].str.zfill(2)
    print("I_educ calculated.")
    return df_out


def calculate_income_index(df_panel):
    """Calculates the income index (I_ingresos) using global min/max normalization."""
    if df_panel is None or "renta_disponible_per_capita" not in df_panel.columns:
        print("❌ Cannot calculate income index, DataFrame or required column missing.")
        return None
    print("Calculating Income Index (I_ingresos)...")
    df = df_panel.copy()
    # Ensure income is numeric
    df["renta_disponible_per_capita"] = pd.to_numeric(df["renta_disponible_per_capita"], errors='coerce')
    df.dropna(subset=["renta_disponible_per_capita"], inplace=True) # Drop rows where income is NaN

    rpc = df["renta_disponible_per_capita"]
    min_rpc, max_rpc = rpc.min(), rpc.max()

    if min_rpc == max_rpc: # Handle case where all values are the same
        df["I_ingresos"] = 0.5 # Or 0 or 1, depending on desired behavior
        print("  Warning: All income values are identical, setting I_ingresos to 0.5.")
    else:
        df["I_ingresos"] = ((rpc - min_rpc) / (max_rpc - min_rpc)).clip(0, 1)

    print("I_ingresos calculated.")
    return df


def calculate_idhm(df_final_panel):
    """Calculates the final IDHM using the three sub-indices."""
    if df_final_panel is None:
        print("❌ Cannot calculate IDHM, input DataFrame missing.")
        return None
    required_cols = ["I_ingresos", "I_salud", "I_educ"]
    if not all(col in df_final_panel.columns for col in required_cols):
        print(f"❌ Cannot calculate IDHM, missing one or more required columns: {required_cols}")
        return None

    print("Calculating final IDHM...")
    df = df_final_panel.copy()

    # Ensure indices are numeric and non-negative
    for col in required_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).clip(lower=0)

    # Calculate geometric mean, handle potential zero values gracefully
    # If any index is 0, IDHM will be 0. Use small epsilon if strict >0 is needed.
    df["IDHM"] = (df["I_ingresos"] * df["I_salud"] * df["I_educ"]) ** (1/3)

    print("IDHM calculated.")
    return df


# --- Main Execution Logic ---

def main():
    """Main function to orchestrate the IDHM calculation workflow."""
    print("--- Starting Municipal Human Development Index (IDHM) Calculation ---")
    script_dir = get_script_directory()
    print(f"Using script directory: {script_dir}")

    # --- Define file paths ---
    path_aeat_help_pdf = script_dir / "AEAT_AyudaCSV_AnuarioMunicipal.pdf" # Optional saving
    path_muni_var_map = script_dir / "EDM_variable_reference_full.csv"
    path_aeat_irpf_csv = script_dir / "IRPFmunicipios.csv"
    path_irpf_processed = script_dir / "IRPFmunicipios_processed.csv"
    path_irpf_imputed = script_dir / "IRPFmunicipios_imputado.csv"
    path_irpf_full_series = script_dir / "IRPFmunicipios_full_series.csv"
    path_aeat_ine_equiv_raw = script_dir / "tabla_equivalencias_aeat_ine_raw.csv" # Extracted from PDF
    path_aeat_ine_equiv_clean = script_dir / "tabla_equivalencias_aeat_ine_clean_muncode.csv" # Cleaned
    path_ine_muni_codes_excel = script_dir / "diccionario25.xlsx"
    path_ine_muni_codes_csv = script_dir / "df_equivalencias_municipio_CORRECTO.csv" # Processed
    path_irpf_mapped = script_dir / "IRPFmunicipios_full_series_mapped.csv"
    path_ine_mortality_csv = script_dir / f"ine_mortality_{INE_MORTALITY_TABLE_CODE}.csv"
    path_mortality_processed = script_dir / "df_mortalidad_final.csv"
    path_health_index = script_dir / "df_health_index_ccaa.csv" # Calculated EV0/I_salud
    path_panel_with_health = script_dir / "IRPFmunicipios_with_salud.csv"
    path_ine_education_csv = script_dir / f"ine_education_{INE_EDUCATION_TABLE_CODE}.csv"
    path_education_processed = script_dir / "df_educacion_processed_pivot.csv"
    path_education_index = script_dir / "df_education_index_ccaa.csv" # Calculated I_educ
    path_panel_with_education = script_dir / "IRPFmunicipios_with_educacion.csv"
    path_panel_with_income = script_dir / "IRPFmunicipios_with_income.csv" # After I_ingresos calc
    path_final_idhm = script_dir / "IRPFmunicipios_final_IDHM.csv"
    path_final_idhm_simplified = script_dir / "idhm_2013_2022.csv"
    # ---

    # === Part 1: AEAT Income Data Processing ===
    print("\n--- Part 1: Processing AEAT Income Data ---")
    # Optional: Download and extract AEAT variable mapping
    # pdf_content_help = download_pdf_content(AEAT_HELP_PDF_URL)
    # df_var_map = extract_muni_variable_mapping(pdf_content_help)
    # if df_var_map is not None: df_var_map.to_csv(path_muni_var_map, index=False, encoding='utf-8')

    # Download and process IRPF data
    df_aeat_raw = download_csv_to_dataframe(
        AEAT_IRPF_CSV_URL, path_aeat_irpf_csv,
        sep=";", decimal=",", encoding="latin-1",
        dtype={"MUNI_DEF": "int32", "EJER": "int16"} # Specify dtypes for faster read
    )
    df_irpf_processed = process_aeat_irpf_data(df_aeat_raw)
    if df_irpf_processed is not None: df_irpf_processed.to_csv(path_irpf_processed, index=False, encoding='utf-8')

    df_irpf_imputed = impute_and_clean_irpf_data(df_irpf_processed)
    if df_irpf_imputed is not None: df_irpf_imputed.to_csv(path_irpf_imputed, index=False, encoding='utf-8')

    df_irpf_full_series = filter_full_series(df_irpf_imputed)
    if df_irpf_full_series is not None: df_irpf_full_series.to_csv(path_irpf_full_series, index=False, encoding='utf-8')
    else:
        print("❌ Exiting: Failed to create full series income data.")
        return # Stop if base income data failed

    # === Part 2: Code Mapping (AEAT -> INE) ===
    print("\n--- Part 2: Mapping AEAT to INE Codes ---")
    # Download AEAT Help PDF again for equivalency table if not done yet
    pdf_content_help_equiv = download_pdf_content(AEAT_HELP_PDF_URL)
    df_equiv_raw = extract_aeat_ine_equivalencies(pdf_content_help_equiv)
    if df_equiv_raw is not None: df_equiv_raw.to_csv(path_aeat_ine_equiv_raw, index=False, encoding='utf-8')

    df_equiv_clean = clean_equivalency_table(df_equiv_raw)
    if df_equiv_clean is not None: df_equiv_clean.to_csv(path_aeat_ine_equiv_clean, index=False, encoding='utf-8')

    # Download and process INE codes dictionary
    df_ine_raw_codes = download_excel_to_dataframe(INE_MUNI_CODES_URL, path_ine_muni_codes_excel, skiprows=1)
    df_ine_codes = process_ine_municipality_codes(df_ine_raw_codes)
    if df_ine_codes is not None: df_ine_codes.to_csv(path_ine_muni_codes_csv, index=False, encoding='utf-8')

    # Perform the mapping
    df_irpf_mapped = map_codes_and_names(df_irpf_full_series, df_equiv_clean, df_ine_codes)
    if df_irpf_mapped is not None: df_irpf_mapped.to_csv(path_irpf_mapped, index=False, encoding='utf-8')
    else:
        print("❌ Exiting: Failed to map INE codes to income data.")
        return

    # === Part 3: Health Dimension (Mortality -> EV0 -> I_salud) ===
    print("\n--- Part 3: Processing Health Dimension ---")
    df_mort_raw = download_csv_to_dataframe(
        INE_MORTALITY_URL, path_ine_mortality_csv,
        sep="\t", decimal=",", encoding="utf-8" # Note: INE uses TAB separator here
    )
    df_mort_processed = process_ine_mortality_data(df_mort_raw)
    if df_mort_processed is not None: df_mort_processed.to_csv(path_mortality_processed, index=False, encoding='utf-8')

    df_health = calculate_health_index(df_mort_processed)
    if df_health is not None: df_health.to_csv(path_health_index, index=False, encoding='utf-8')
    else:
        print("❌ Exiting: Failed to calculate health index.")
        return

    # Merge health index into the main panel
    panel_with_health = df_irpf_mapped.merge(df_health, on=["CODAUTO", "year"], how="left")
    # Check for merge issues (NaNs in health columns)
    if panel_with_health[['EV0', 'I_salud']].isna().any().any():
         print("⚠️ Warning: NaNs introduced when merging health index. Check CODAUTO/year matching.")
         # Optional: Impute missing health data (e.g., with national avg or ffill/bfill by CODAUTO)
         panel_with_health['I_salud'] = panel_with_health.groupby('CODAUTO')['I_salud'].transform(lambda s: s.ffill().bfill())
         panel_with_health['EV0'] = panel_with_health.groupby('CODAUTO')['EV0'].transform(lambda s: s.ffill().bfill())
         panel_with_health.dropna(subset=['I_salud'], inplace=True) # Drop if still NaN after imputation

    if panel_with_health is not None: panel_with_health.to_csv(path_panel_with_health, index=False, encoding='utf-8')


    # === Part 4: Education Dimension (Levels -> I_educ) ===
    print("\n--- Part 4: Processing Education Dimension ---")
    df_edu_raw = download_csv_to_dataframe(
        INE_EDUCATION_URL, path_ine_education_csv,
        sep="\t", decimal=",", encoding="utf-8" # Note: INE uses TAB separator
    )
    df_edu_processed = process_ine_education_data(df_edu_raw)
    if df_edu_processed is not None: df_edu_processed.to_csv(path_education_processed, index=False, encoding='utf-8')

    df_education = calculate_education_index(df_edu_processed)
    if df_education is not None: df_education.to_csv(path_education_index, index=False, encoding='utf-8')
    else:
        print("❌ Exiting: Failed to calculate education index.")
        return

    # Merge education index into the panel (which already has health)
    panel_with_education = panel_with_health.merge(df_education, on=["CODAUTO", "year"], how="left")
     # Impute missing education data if necessary (e.g. if years don't align perfectly)
    if panel_with_education['I_educ'].isna().any().any():
        print("⚠️ Warning: NaNs found for I_educ after merge. Imputing by CODAUTO...")
        panel_with_education = panel_with_education.sort_values(["CODAUTO", "year"])
        panel_with_education["I_educ"] = panel_with_education.groupby("CODAUTO")["I_educ"].transform(lambda s: s.ffill().bfill())
        # If NaNs remain (e.g., a CODAUTO has no education data at all), consider dropping or alternative imputation
        panel_with_education.dropna(subset=['I_educ'], inplace=True)

    if panel_with_education is not None: panel_with_education.to_csv(path_panel_with_education, index=False, encoding='utf-8')


    # === Part 5: Income Index and Final IDHM Calculation ===
    print("\n--- Part 5: Calculating Income Index and Final IDHM ---")
    panel_with_income = calculate_income_index(panel_with_education)
    if panel_with_income is not None: panel_with_income.to_csv(path_panel_with_income, index=False, encoding='utf-8')
    else:
        print("❌ Exiting: Failed to calculate income index.")
        return

    df_final_idhm = calculate_idhm(panel_with_income)

    if df_final_idhm is not None:
        # Save the full final dataset
        df_final_idhm.to_csv(path_final_idhm, index=False, encoding='utf-8')
        print(f"✅ Full final dataset with IDHM saved to: '{path_final_idhm}'")

        # Create and save the simplified version for the model
        df_simplified = df_final_idhm[['year', 'mun_code', 'IDHM']].copy()
        df_simplified = df_simplified.rename(columns={'mun_code': 'cod_mun', 'IDHM': 'idhm'})
        df_simplified['idhm'] = df_simplified['idhm'].round(3)
        # Convert mun_code back to string zfill(5) if needed by model
        df_simplified['cod_mun'] = df_simplified['cod_mun'].astype(int).astype(str).str.zfill(5)


        df_simplified.to_csv(path_final_idhm_simplified, sep=';', index=False, encoding='utf-8')
        print(f"✅ Simplified dataset for model saved to: '{path_final_idhm_simplified}'")
    else:
        print("❌ Exiting: Failed to calculate final IDHM.")
        return

    print("\n--- IDHM Calculation Script Finished Successfully ---")


if __name__ == "__main__":
    # Ensure necessary libraries are installed
    try:
        import lxml # For pd.read_html used indirectly by download_excel maybe? Check pdfplumber reqs
        import openpyxl # For pd.read_excel
        import pdfplumber
    except ImportError as e:
        print("--------------------------------------------------------------------")
        print(f"ERROR: Missing required library: {e.name}")
        print("Please install required libraries:")
        print("pip install requests pandas numpy pdfplumber openpyxl")
        # Optionally add lxml if needed by excel reading or pdfplumber internally
        # print("pip install lxml")
        print("--------------------------------------------------------------------")
        exit()

    main()