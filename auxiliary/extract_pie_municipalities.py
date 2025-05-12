import pandas as pd
import os
import sys

def extract_codes_from_processed_pie():
    """
    Reads the processed PIE data CSV ('pie_final_final.csv'),
    extracts unique municipality codes from the 'mun_code' column,
    and prints them to standard output.
    """
    script_dir = os.path.dirname(os.path.realpath(__file__))
    project_root = os.path.join(script_dir, "..")
    
    # Path to the processed PIE CSV file
    file_path = os.path.join(
        project_root,
        "ETL/PIE/data/raw/finanzas/liquidaciones/preprocess/pie_final_final.csv"
    )

    code_column = 'mun_code' # This column is known to exist and be 5-digit INE

    try:
        df = pd.read_csv(file_path, dtype={code_column: str})
        print(f"Successfully read processed PIE CSV file: {file_path}", file=sys.stderr)
        
        if code_column not in df.columns:
            print(f"Error: Expected municipality code column '{code_column}' not found in {file_path}. Columns found: {df.columns.tolist()}", file=sys.stderr)
            return

        unique_codes = df[code_column].dropna().unique()
        
        formatted_codes = set()
        for code in unique_codes:
            s_code = str(code).zfill(5)
            if len(s_code) == 5 and s_code.isdigit():
                formatted_codes.add(s_code)
            else:
                print(f"Warning: Code '{code}' from {file_path} formatted to '{s_code}' is not a 5-digit number. Skipping.", file=sys.stderr)
        
        if not formatted_codes:
            print(f"Warning: No valid 5-digit codes were extracted from '{code_column}' in {file_path}.", file=sys.stderr)
            return

        for f_code in sorted(list(formatted_codes)):
            print(f_code)

    except FileNotFoundError:
        print(f"Error: Processed PIE CSV file not found at {file_path}", file=sys.stderr)
    except Exception as e:
        print(f"An error occurred while processing {file_path}: {e}", file=sys.stderr)

if __name__ == "__main__":
    extract_codes_from_processed_pie()
