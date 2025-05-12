"""
Adapted Geography class for PolicySpace2 using Spanish municipal data.
This version removes ACP (Area de Concentracao de Populacao) dependencies and works directly with Spanish municipal codes.
"""
import os
import pandas as pd

# Define base paths for the Spanish data
# Corrected to be relative to the project root
SCRIPT_DIR_GEOGRAPHY = os.path.dirname(os.path.realpath(__file__)) # world/
PROJECT_ROOT_GEOGRAPHY = os.path.join(SCRIPT_DIR_GEOGRAPHY, "..") # Navigate up to project root
SPANISH_ETL_PATH = os.path.join(PROJECT_ROOT_GEOGRAPHY, "ETL")

# Path to the Spanish municipal codes and names
# This file should contain at least 'mun_code' (as 5-digit INE) and 'NOMBRE'
SPANISH_MUNICIPALITIES_INFO_PATH = os.path.join(SPANISH_ETL_PATH, "tabla_equivalencias/data/df_equivalencias_municipio_CORRECTO.csv")

class Geography:
    """Manages which Spanish municipalities are used for the simulation."""
    def __init__(self, params, year):
        """
        Initializes the geography based on Spanish municipal data.
        `params` should contain a key like 'SPANISH_MUNICIPALITIES_TO_PROCESS' which can be:
        - A list of 'mun_code' strings to process.
        - The string 'ALL' to process all municipalities found in the equivalencias table.
        - Potentially, in the future, codes for provinces or CCAAs to filter municipalities.
        """
        self.year = year
        self.params = params

        try:
            self.municipal_equivalencias = pd.read_csv(SPANISH_MUNICIPALITIES_INFO_PATH, dtype={'mun_code': str, 'CPRO': str, 'CMUN': str})
            # Ensure 'mun_code' is the primary municipal identifier from this table
            if 'mun_code' not in self.municipal_equivalencias.columns:
                raise ValueError("'mun_code' column not found in Spanish municipalities info file.")
            if 'NOMBRE' not in self.municipal_equivalencias.columns:
                print("Warning: 'NOMBRE' column for municipality name not found, names might be missing.")
        except Exception as e:
            print(f"CRITICAL ERROR: Could not load Spanish municipalities info from {SPANISH_MUNICIPALITIES_INFO_PATH}. Error: {e}")
            self.municipal_equivalencias = pd.DataFrame(columns=['mun_code', 'NOMBRE'])
            self.mun_codes = []
            self.LIST_NAMES_MUN = pd.DataFrame(columns=['cod_name', 'cod_mun', 'state'])
            return

        # Determine which municipalities to process
        processing_directive = params.get('SPANISH_MUNICIPALITIES_TO_PROCESS', 'ALL') # Default to all

        if isinstance(processing_directive, list):
            # Filter equivalencias table for the specified mun_codes
            self.selected_municipalities_info = self.municipal_equivalencias[
                self.municipal_equivalencias['mun_code'].isin(processing_directive)
            ].copy()
            self.mun_codes = self.selected_municipalities_info['mun_code'].unique().tolist()
            if len(self.mun_codes) != len(processing_directive):
                print(f"Warning: Some specified mun_codes in SPANISH_MUNICIPALITIES_TO_PROCESS were not found in the equivalencias table.")
        elif isinstance(processing_directive, str) and processing_directive.upper() == 'ALL':
            self.selected_municipalities_info = self.municipal_equivalencias.copy()
            self.mun_codes = self.selected_municipalities_info['mun_code'].unique().tolist()
        else:
            # Future: Add logic for province codes or CCAA codes if needed
            print(f"Warning: SPANISH_MUNICIPALITIES_TO_PROCESS directive '{processing_directive}' not recognized or not a list. Defaulting to ALL municipalities.")
            self.selected_municipalities_info = self.municipal_equivalencias.copy()
            self.mun_codes = self.selected_municipalities_info['mun_code'].unique().tolist()

        if not self.mun_codes:
            print("Warning: No municipalities selected for processing based on current parameters.")

        # Creating a list of municipalities and their names (and potentially state/province if available)
        # The original LIST_NAMES_MUN had columns: 'cod_name', 'cod_mun', 'state'
        # We adapt this using the Spanish data structure.
        self.LIST_NAMES_MUN = pd.DataFrame()
        if 'NOMBRE' in self.selected_municipalities_info.columns and 'mun_code' in self.selected_municipalities_info.columns:
            self.LIST_NAMES_MUN['cod_name'] = self.selected_municipalities_info['NOMBRE']
            self.LIST_NAMES_MUN['cod_mun'] = self.selected_municipalities_info['mun_code']
            # Add 'state' or 'province' if available in equivalencias table, e.g., from 'CPRO' or a CCAA name column
            if 'CPRO' in self.selected_municipalities_info.columns: # Example: using CPRO as state/province identifier
                self.LIST_NAMES_MUN['state'] = self.selected_municipalities_info['CPRO']
            else:
                self.LIST_NAMES_MUN['state'] = 'N/A' # Placeholder if no province/state info
        else:
             self.LIST_NAMES_MUN = pd.DataFrame(columns=['cod_name', 'cod_mun', 'state'])
        
        if 'state' in self.LIST_NAMES_MUN.columns:
            self.states_on_process = set(self.LIST_NAMES_MUN['state'].unique())
        else:
            self.states_on_process = set()
        
        print(f"Geography initialized for {len(self.mun_codes)} Spanish municipalities, covering {len(self.states_on_process)} states/provinces.")

# Placeholder for STATES_CODES and state_string, adapt as needed for Spanish context (e.g., CCAA codes)
# These might be loaded from a file (e.g. containing CCAA codes and names)
# Example: CODAUTO from equivalencias could be used.
# For now, providing simple placeholders to allow imports.
STATES_CODES = { # Example: Mapping CCAA code (str) to a numerical ID (int) if needed by original logic
    '01': 1, '02': 2, '03': 3, '04': 4, '05': 5, '06': 6, '07': 7, '08': 8, '09': 9,
    '10': 10, '11': 11, '12': 12, '13': 13, '14': 14, '15': 15, '16': 16, '17': 17,
    '18': 18, '19': 19 # Ceuta and Melilla
}

def state_string(cod_mun_ine5):
    """
    Placeholder function to get a state/CCAA identifier from a municipal code.
    Actual implementation would look up CPRO or CODAUTO from ine_code.
    """
    if isinstance(cod_mun_ine5, str) and len(cod_mun_ine5) >= 2:
        return cod_mun_ine5[:2] # Example: using first 2 digits (province code) as 'state' identifier
    return "UNKNOWN_STATE"


# Example of how params.py might be updated:
# Add to params.py:
# SPANISH_MUNICIPALITIES_TO_PROCESS = ['28079', '08019'] # Example: Madrid and Barcelona mun_codes
# or
# SPANISH_MUNICIPALITIES_TO_PROCESS = 'ALL'

if __name__ == '__main__':
    # Example Usage (requires params.py to be adapted or a mock params dict)
    mock_params_all = {
        'SPANISH_MUNICIPALITIES_TO_PROCESS': 'ALL',
        # ... other params if needed by other parts of the model ...
    }
    mock_params_specific = {
        'SPANISH_MUNICIPALITIES_TO_PROCESS': ['28079', '08019'], # Madrid and Barcelona
    }

    print("--- Testing Geography with 'ALL' municipalities ---")
    geo_all = Geography(params=mock_params_all, year=2022)
    print(f"Number of mun_codes loaded: {len(geo_all.mun_codes)}")
    if geo_all.mun_codes:
        print(f"First 5 mun_codes: {geo_all.mun_codes[:5]}")
        print("LIST_NAMES_MUN sample:")
        print(geo_all.LIST_NAMES_MUN.head())

    print("\n--- Testing Geography with specific municipalities ---")
    geo_specific = Geography(params=mock_params_specific, year=2022)
    print(f"Number of mun_codes loaded: {len(geo_specific.mun_codes)}")
    if geo_specific.mun_codes:
        print(f"Mun_codes: {geo_specific.mun_codes}")
        print("LIST_NAMES_MUN sample:")
        print(geo_specific.LIST_NAMES_MUN)

    # To integrate this, the main simulation script (e.g., simulation.py or main.py)
    # would instantiate this Geography class and pass it to other modules that need geographic info.
    # Calls to the original ACP-based functions/attributes would need to be refactored.
