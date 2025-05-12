import pandas as pd
import os
import sys

def get_unique_codes_from_csv(file_path, column_name, sep=',', dtype_str=True, zfill_needed=True):
    """Helper function to get unique, formatted 5-digit codes from a CSV column."""
    dtype_options = {column_name: str} if dtype_str else None
    try:
        df = pd.read_csv(file_path, sep=sep, dtype=dtype_options, low_memory=False)
        
        if column_name not in df.columns:
            print(f"Error: Column '{column_name}' not found in {file_path}. Columns: {df.columns.tolist()}", file=sys.stderr)
            return set()

        unique_codes = df[column_name].dropna().unique()
        formatted_codes = set()
        for code in unique_codes:
            s_code = str(code).strip()
            if zfill_needed:
                s_code = s_code.zfill(5)
            
            if len(s_code) == 5 and s_code.isdigit():
                formatted_codes.add(s_code)
        return formatted_codes
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}", file=sys.stderr)
        return set()
    except Exception as e:
        print(f"An error occurred while processing {file_path} (column: {column_name}, sep: '{sep}'): {e}", file=sys.stderr)
        return set()

def find_common_municipalities():
    script_dir = os.path.dirname(os.path.realpath(__file__))
    project_root = os.path.join(script_dir, "..")

    # 1. Get municipalities from processed PIE data
    pie_csv_path = os.path.join(project_root, "ETL/PIE/data/raw/finanzas/liquidaciones/preprocess/pie_final_final.csv")
    common_codes_final = get_unique_codes_from_csv(pie_csv_path, 'mun_code')
    if not common_codes_final:
        print("Error: Could not extract municipality codes from PIE data. Aborting.", file=sys.stderr)
        return
    print(f"Found {len(common_codes_final)} unique municipalities in PIE data.", file=sys.stderr)

    # 2. Get municipalities from Population data (e.g., hombres_2014)
    pop_file_path = os.path.join(project_root, "ETL/cifras_poblacion_municipio/data_final/drive-download-20250506T180657Z-001/cifras_municipio_hombres_2014.csv")
    pop_mun_codes = get_unique_codes_from_csv(pop_file_path, 'municipio_code', sep=',')
    if not pop_mun_codes:
        print("Warning: Could not extract municipality codes from Population data. Proceeding without it for common list.", file=sys.stderr)
    else:
        print(f"Found {len(pop_mun_codes)} unique municipalities in Population data (hombres_2014).", file=sys.stderr)
        common_codes_final = common_codes_final.intersection(pop_mun_codes)
        print(f"Found {len(common_codes_final)} common municipalities after Population data.", file=sys.stderr)

    # 3. Get municipalities from IDHM data
    idhm_file_path = os.path.join(project_root, "ETL/idhm_indice_desarrollo_humano_municipal/IRPFmunicipios_final_IDHM.csv")
    idhm_mun_codes = get_unique_codes_from_csv(idhm_file_path, 'mun_code', sep=',')
    if not idhm_mun_codes: 
         idhm_mun_codes = get_unique_codes_from_csv(idhm_file_path, 'mun_code', sep=';')
    if not idhm_mun_codes:
        print("Warning: Could not extract municipality codes from IDHM data. Proceeding without it.", file=sys.stderr)
    else:
        print(f"Found {len(idhm_mun_codes)} unique municipalities in IDHM data.", file=sys.stderr)
        common_codes_final = common_codes_final.intersection(idhm_mun_codes)
        print(f"Found {len(common_codes_final)} common municipalities after IDHM data.", file=sys.stderr)

    # 4. Get municipalities from Proportion Urban data
    urban_file_path = os.path.join(project_root, "ETL/distribucion_urbana/data_final/distribucion_urbana_municipios_2003_to_2022.csv")
    # Based on previous script output, the column is 'municipio_code' and separator is ','
    urban_mun_codes = get_unique_codes_from_csv(urban_file_path, 'municipio_code', sep=',') 
    
    if not urban_mun_codes:
        print("Warning: Could not extract municipality codes from Proportion Urban data. Proceeding without it.", file=sys.stderr)
    else:
        print(f"Found {len(urban_mun_codes)} unique municipalities in Proportion Urban data.", file=sys.stderr)
        common_codes_final = common_codes_final.intersection(urban_mun_codes)
        print(f"Found {len(common_codes_final)} common municipalities after Proportion Urban data.", file=sys.stderr)

    # 5. Get municipalities from Firm data (requires mapping via equivalencias)
    firm_data_path = os.path.join(project_root, "ETL/empresas_municipio_actividad_principal/preprocesados/empresas_municipio_actividad_principal.csv")
    equivalencias_path = os.path.join(project_root, "ETL/tabla_equivalencias/data/df_equivalencias_municipio_CORRECTO.csv")
    
    firm_ine_codes = set()
    try:
        df_firms_raw = pd.read_csv(firm_data_path, sep=',', dtype={'municipio_code': str}) # Assuming 'municipio_code' and comma
        df_equivalencias = pd.read_csv(equivalencias_path, sep=",", dtype=str) # Assuming comma

        if 'mun_code' in df_equivalencias.columns: # This is the 5-digit INE
             df_equivalencias.rename(columns={'mun_code': 'ine_code'}, inplace=True)
        df_equivalencias['ine_code'] = df_equivalencias['ine_code'].str.zfill(5)
        
        # Create short code in equivalencias for merging (e.g. CPRO+CMUN)
        # Assuming CPRO and CMUN exist and are parts of the short code used in firms_raw
        if 'CPRO' in df_equivalencias.columns and 'CMUN' in df_equivalencias.columns:
            # Ensure CPRO is string, take first part if like "01.0", zfill(2)
            # Ensure CMUN is string, take first part if like "001.0", zfill(3)
            df_equivalencias['CPRO_clean'] = df_equivalencias['CPRO'].astype(str).str.split('.').str[0].str.zfill(2)
            df_equivalencias['CMUN_clean'] = df_equivalencias['CMUN'].astype(str).str.split('.').str[0].str.zfill(3)
            df_equivalencias['mun_code_short_equiv'] = df_equivalencias['CPRO_clean'] + df_equivalencias['CMUN_clean']
            
            # Merge firms data with equivalencias to get INE code
            # Assuming firms_raw has 'municipio_code' as the short code
            df_firms_merged = pd.merge(df_firms_raw, 
                                       df_equivalencias[['mun_code_short_equiv', 'ine_code']],
                                       left_on='municipio_code', # This is the short code in firms_raw
                                       right_on='mun_code_short_equiv', 
                                       how='left')
            df_firms_merged.dropna(subset=['ine_code'], inplace=True)
            firm_ine_codes = set(df_firms_merged['ine_code'].unique())
            print(f"Found {len(firm_ine_codes)} unique 5-digit INE municipalities with Firm data.", file=sys.stderr)
            common_codes_final = common_codes_final.intersection(firm_ine_codes)
            print(f"Found {len(common_codes_final)} common municipalities after Firm data.", file=sys.stderr)

        else:
            print("Warning: CPRO or CMUN missing in equivalencias for firm data mapping. Skipping firm data.", file=sys.stderr)
            
    except FileNotFoundError:
        print("Warning: Firm data or equivalencias file not found. Skipping firm data.", file=sys.stderr)
    except Exception as e:
        print(f"An error occurred processing firm data: {e}. Skipping firm data.", file=sys.stderr)


    output_file_path = os.path.join(project_root, "adapter_spain_info/common_municipalities_for_simulation.csv")
    pd.DataFrame(sorted(list(common_codes_final)), columns=['mun_code']).to_csv(output_file_path, index=False)
    print(f"Saved {len(common_codes_final)} common municipality codes to {output_file_path}", file=sys.stderr)
    
if __name__ == "__main__":
    find_common_municipalities()
