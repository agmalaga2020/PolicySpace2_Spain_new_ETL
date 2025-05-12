from collections import defaultdict

import numpy as np
import pandas as pd


import os # Added import os
import logging # Added logging

logger_firms = logging.getLogger(__name__)

# Define base paths consistently relative to this script's location (world/)
SCRIPT_DIR_FIRMS = os.path.dirname(os.path.realpath(__file__))
PROJECT_ROOT_FIRMS = os.path.join(SCRIPT_DIR_FIRMS, "..")
ETL_DATA_PATH_FIRMS = os.path.join(PROJECT_ROOT_FIRMS, "ETL")


class FirmData:
    """ Firm growth is estimated from a monthly value of growth. Adapted for Spanish data. """
    def __init__(self, sim_year): # sim_year is the starting year of the simulation
        self.num_emp_t0 = defaultdict(int)
        self.num_emp_t1 = defaultdict(int)
        self.deltas = defaultdict(int)
        self.avg_monthly_deltas = defaultdict(float)

        try:
            # Define t0 and t1 years for growth calculation.
            # For simulation year 2014, using t0=2014 and t1=2019 (5-year span for growth).
            t0_year = 2014
            t1_year = 2019 
            
            # num_years_for_delta will be calculated after confirming actual t1 year used.
            # num_months will also be calculated then.

            firms_data_path = os.path.join(ETL_DATA_PATH_FIRMS, "empresas_municipio_actividad_principal/preprocesados/empresas_municipio_actividad_principal.csv")
            df_firms_raw = pd.read_csv(firms_data_path, sep=',', dtype={'municipio_code': str, 'Periodo': str})
            df_firms_raw['Periodo'] = pd.to_numeric(df_firms_raw['Periodo'], errors='coerce')
            df_firms_raw['Total'] = pd.to_numeric(df_firms_raw['Total'], errors='coerce').fillna(0)

            # Load equivalencias to map 'municipio_code' (short) to 5-digit INE (numeric for dict key)
            equivalencias_path = os.path.join(ETL_DATA_PATH_FIRMS, "tabla_equivalencias/data/df_equivalencias_municipio_CORRECTO.csv")
            df_equivalencias = pd.read_csv(equivalencias_path, sep=",", dtype=str)
            if 'mun_code' in df_equivalencias.columns: # This is the 5-digit INE
                 df_equivalencias.rename(columns={'mun_code': 'ine_code'}, inplace=True)
            df_equivalencias['ine_code'] = df_equivalencias['ine_code'].str.zfill(5)
            if 'CPRO' in df_equivalencias.columns and 'CMUN' in df_equivalencias.columns:
                df_equivalencias['mun_code_short_equiv'] = df_equivalencias['CPRO'].astype(int).astype(str) + \
                                                           df_equivalencias['CMUN'].astype(str).str.zfill(3)
            else:
                raise ValueError("CPRO or CMUN missing in equivalencias for mun_code_short_equiv creation.")

            # Merge firms data with equivalencias to get INE code
            df_firms_merged = pd.merge(df_firms_raw, 
                                       df_equivalencias[['mun_code_short_equiv', 'ine_code']],
                                       left_on='municipio_code', 
                                       right_on='mun_code_short_equiv', 
                                       how='left')
            
            df_firms_merged.dropna(subset=['ine_code'], inplace=True) # Drop firms not in equivalencias
            df_firms_merged['ine_code_numeric'] = df_firms_merged['ine_code'].astype(int)

            # Populate num_emp_t0
            df_t0 = df_firms_merged[df_firms_merged['Periodo'] == t0_year]
            for _, row in df_t0.iterrows():
                self.num_emp_t0[row['ine_code_numeric']] += row['Total']
            
            # Populate num_emp_t1
            df_t1 = df_firms_merged[df_firms_merged['Periodo'] == t1_year]
            actual_t1_year_for_calc = t1_year # Assume we use the target t1_year

            if df_t1.empty:
                logger_firms.warning(f"FirmData: No data for specified t1_year {t1_year}. Attempting fallback.")
                # Fallback: use latest available year <= t1_year from the dataset
                available_t1_options = df_firms_merged[df_firms_merged['Periodo'] <= t1_year]['Periodo']
                if not available_t1_options.empty:
                    actual_t1_year_for_calc = available_t1_options.max()
                    if actual_t1_year_for_calc < t0_year: # If latest available is before t0, this is problematic
                        logger_firms.error(f"FirmData: Latest available year for t1 ({actual_t1_year_for_calc}) is before t0_year ({t0_year}). Cannot calculate growth.")
                        # Set num_months to a state that results in zero growth, or raise error
                        num_months = -1 # Indicates error or no growth calculable
                    else:
                        df_t1 = df_firms_merged[df_firms_merged['Periodo'] == actual_t1_year_for_calc]
                        logger_firms.warning(f"Using fallback t1 data from year: {actual_t1_year_for_calc}")
                else:
                    logger_firms.error(f"No data found at or before specified t1_year {t1_year}. Cannot calculate growth.")
                    num_months = -1 # Indicates error
            
            if 'num_months' not in locals() or num_months != -1: # If not already set to error state
                num_years_for_delta = actual_t1_year_for_calc - t0_year
                if num_years_for_delta <= 0:
                    logger_firms.warning(f"t1_year_for_calc ({actual_t1_year_for_calc}) must be greater than t0_year ({t0_year}). Setting growth to 0.")
                    num_months = 0 # Results in zero growth if delta is non-zero, or NaN if delta is 0 (handled below)
                else:
                    num_months = num_years_for_delta * 12
            
            for _, row in df_t1.iterrows(): # df_t1 might be empty if no suitable t1 data found
                self.num_emp_t1[row['ine_code_numeric']] += row['Total']

            all_mun_codes_numeric = set(self.num_emp_t0.keys()) | set(self.num_emp_t1.keys())

            for code_num in all_mun_codes_numeric:
                n_t0 = self.num_emp_t0.get(code_num, 0)
                n_t1 = self.num_emp_t1.get(code_num, 0)
                delta = n_t1 - n_t0
                self.deltas[code_num] = delta
                if num_months > 0:
                    self.avg_monthly_deltas[code_num] = delta / num_months
                else: 
                    self.avg_monthly_deltas[code_num] = 0 # No growth if period is invalid or zero
            
            logger_firms.info(f"FirmData initialized. t0_year={t0_year}, Target t1_year={t1_year}, Actual t1_year_used={actual_t1_year_for_calc if num_months > -1 else 'N/A (error)'}.")
            logger_firms.info(f"Calculated avg_monthly_deltas for {len(self.avg_monthly_deltas)} municipalities.")

        except FileNotFoundError as e:
            logger_firms.error(f"Error initializing FirmData: Required file not found. {e}")
        except Exception as e:
            logger_firms.error(f"Error initializing FirmData: {e}")
            # Fallback: initialize with empty dicts to prevent crashes, but growth will be 0
            self.num_emp_t0 = defaultdict(int)
            self.num_emp_t1 = defaultdict(int)
            self.deltas = defaultdict(int)
            self.avg_monthly_deltas = defaultdict(float)


def firm_growth(sim):
    """ Create new firms according to average historical growth
        Location within the municipality is more likely on regions with growth of profit and employees
        """

    # Group firms by region
    firms_by_region = defaultdict(list)
    for firm in sim.firms.values():
        firms_by_region[firm.region_id].append(firm)

    # For each municipality
    for mun_code, regions in sim.mun_to_regions.items():
        # Get growth based on historical data
        growth = sim.generator.firm_data.avg_monthly_deltas[int(mun_code)] * sim.PARAMS['PERCENTAGE_ACTUAL_POP']
        growth = int(round(growth))

        # Ignoring shrinkage for now
        if growth <= 0:
            continue

        # Calculate average profit and number of employees for firms in each region
        avg_profit, avg_n_emp = {}, {}
        for region_id in regions:
            firms = firms_by_region[region_id]
            if firms:
                # keep non-negative for probabilities
                avg_profit[region_id] = max(0, sum(f.profit for f in firms)/len(firms))
                avg_n_emp[region_id] = max(0, sum(f.num_employees for f in firms)/len(firms))
            else:
                avg_profit[region_id] = 0
                avg_n_emp[region_id] = 0

        # Compute probabilities that a firm starts in a region, based on that regions' average
        # profit and number of employees
        region_ps = []
        sum_profit = sum(avg_profit.values())
        sum_n_emp = sum(avg_n_emp.values())
        for region_id in regions:
            if sum_profit == 0 and sum_n_emp == 0:
                # Small non-zero probability
                region_ps.append(0.0001)
            else:
                # Equally weight probability from profit and number of employees
                p_profit = avg_profit[region_id]/sum_profit if sum_profit != 0 else 0
                p_n_emp = avg_n_emp[region_id]/sum_n_emp if sum_n_emp != 0 else 0
                region_ps.append((p_profit + p_n_emp)/2)

        # Normalize probabilities
        region_ps = region_ps/np.sum(region_ps)

        # For each new firm, randomly select its region based on the probabilities we computed
        # and then create the new firm
        for _ in range(growth):
            region_id = sim.seed.choices(regions, weights=region_ps)
            region = sim.regions[region_id[0]]
            firm = list(sim.generator.create_firms(1, region).values())[0]
            firm.create_product()
            sim.firms[firm.id] = firm
