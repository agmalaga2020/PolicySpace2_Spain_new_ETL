import pandas as pd
import os
import sys

def explore_periods():
    """
    Loads the processed firm data and prints unique values and value counts for the 'Periodo' column.
    """
    script_dir = os.path.dirname(os.path.realpath(__file__))
    project_root = os.path.join(script_dir, "..")
    
    file_path = os.path.join(
        project_root,
        "ETL/empresas_municipio_actividad_principal/preprocesados/empresas_municipio_actividad_principal.csv"
    )

    try:
        df = pd.read_csv(file_path, sep=',') # Assuming comma separator
        
        if 'Periodo' not in df.columns:
            print(f"Error: Column 'Periodo' not found in {file_path}. Columns found: {df.columns.tolist()}", file=sys.stderr)
            return

        print("Unique values in 'Periodo' column:")
        unique_periods = sorted(df['Periodo'].dropna().unique())
        for period in unique_periods:
            print(period)
        
        print("\nValue counts for 'Periodo' column:")
        print(df['Periodo'].value_counts().sort_index())

    except FileNotFoundError:
        print(f"Error: File not found at {file_path}", file=sys.stderr)
    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)

if __name__ == "__main__":
    explore_periods()
