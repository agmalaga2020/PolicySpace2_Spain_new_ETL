import pandas as pd
import os
import sys

def explore_data():
    """
    Loads the Spanish population estimates data from ETL and prints its structure.
    """
    script_dir = os.path.dirname(os.path.realpath(__file__))
    project_root = os.path.join(script_dir, "..")
    
    file_path = os.path.join(
        project_root,
        "ETL/estimativas_pop/preprocesados/cifras_poblacion_municipio.csv"
    )

    try:
        # Load a small sample first to infer structure, then load full if needed or parts
        print(f"Attempting to read file: {file_path}", file=sys.stderr)
        df_sample = pd.read_csv(file_path, sep=',', nrows=10) # Assuming comma separator
        
        print("\nColumns found:")
        print(df_sample.columns.tolist())

        print("\nFirst 5 rows of data (sample):")
        # For full head, load the whole df, but be mindful of memory for very large files
        # For exploration, a sample head is often enough.
        df_head = pd.read_csv(file_path, sep=',', nrows=5)
        print(df_head)

        # Identify potential year and municipality code columns based on common names
        # This part might need adjustment after seeing the actual column names
        potential_year_cols = ['Periodo', 'año', 'year', 'ANO']
        potential_mun_code_cols = ['municipio_code', 'mun_code', 'COD_MUN', 'INE_MUN']
        
        year_col = None
        for col in potential_year_cols:
            if col in df_sample.columns:
                year_col = col
                break
        
        mun_code_col = None
        for col in potential_mun_code_cols:
            if col in df_sample.columns:
                mun_code_col = col
                break

        # Load full data for unique values if columns are identified
        if year_col:
            print(f"\nUnique values in '{year_col}' column (sample of first 100k rows for performance):")
            df_partial_for_year = pd.read_csv(file_path, sep=',', usecols=[year_col], nrows=100000)
            unique_years = sorted(df_partial_for_year[year_col].dropna().unique())
            print(unique_years)
        else:
            print("\nCould not identify a year column from common names.", file=sys.stderr)

        if mun_code_col:
            print(f"\nUnique values in '{mun_code_col}' column (sample of first 100k rows for performance):")
            df_partial_for_mun = pd.read_csv(file_path, sep=',', usecols=[mun_code_col], nrows=100000)
            unique_mun_codes = df_partial_for_mun[mun_code_col].dropna().unique()
            print(f"Found {len(unique_mun_codes)} unique municipality codes in sample.")
            # print(list(unique_mun_codes)[:20]) # Print a few examples
        else:
            print("\nCould not identify a municipality code column from common names.", file=sys.stderr)


    except FileNotFoundError:
        print(f"Error: File not found at {file_path}", file=sys.stderr)
    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)

if __name__ == "__main__":
    explore_data()
