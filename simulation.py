import datetime
import json
import math
import os
import pickle
import random
import sys
from collections import defaultdict
import logging # Added logging

# Define module-level logger
script_logger = logging.getLogger(__name__)

import numpy as np
import pandas as pd

import analysis
import conf
import markets
from world import Generator, demographics, clock, population
from world.firms import firm_growth
from world.funds import Funds
from world.geography import Geography, STATES_CODES, state_string


class Simulation:
    def __init__(self, params, output_path):
        self.PARAMS = params
        self.geo = Geography(params, self.PARAMS['STARTING_DAY'].year)
        self.funds = Funds(self)
        self.clock = clock.Clock(self.PARAMS['STARTING_DAY'])
        self.output = analysis.Output(self, output_path)
        self.stats = analysis.Statistics()
        self.logger = analysis.Logger(hex(id(self))[-5:])
        self._seed = random.randrange(sys.maxsize) if conf.RUN['KEEP_RANDOM_SEED'] else conf.RUN.get('SEED', 0)
        self.seed = random.Random(self._seed)
        self.generator = Generator(self)

        # Define base paths consistently relative to this script's location
        SCRIPT_DIR_SIMULATION = os.path.dirname(os.path.realpath(__file__))
        PROJECT_ROOT_SIMULATION = SCRIPT_DIR_SIMULATION # simulation.py is in the root
        ETL_DATA_PATH_SIMULATION = os.path.join(PROJECT_ROOT_SIMULATION, "ETL")
        INPUT_DATA_PATH_SIMULATION = os.path.join(PROJECT_ROOT_SIMULATION, "input")
        # script_logger = logging.getLogger(__name__) # Logger for this script <- Moved to module level

        # --- Adapted Mortality Data Loading for Spain ---
        self.mortality = {
            'male': defaultdict(lambda: pd.DataFrame(columns=['age', 'rate']).groupby('age')),
            'female': defaultdict(lambda: pd.DataFrame(columns=['age', 'rate']).groupby('age'))
        }
        try:
            script_logger.info("Starting Spanish mortality data loading process...")
            # Load CPRO to CCAA mapping (CODAUTO is CCAA code)
            codigos_provincias_path = os.path.join(ETL_DATA_PATH_SIMULATION, "indicadores_fecundidad_municipio_provincias/codigos_ccaa_provincias.csv")
            df_codigos_provincias = pd.read_csv(codigos_provincias_path, dtype={'CPRO': str, 'CODAUTO': str})
            df_codigos_provincias['CPRO_cleaned'] = df_codigos_provincias['CPRO'].astype(str).str.split('.').str[0].str.zfill(2)
            df_codigos_provincias['CODAUTO_cleaned'] = df_codigos_provincias['CODAUTO'].astype(str).str.split('.').str[0].str.zfill(2)
            cpro_to_ccaa_map = df_codigos_provincias.set_index('CPRO_cleaned')['CODAUTO_cleaned'].to_dict()

            current_sim_year_str = str(self.geo.year) # e.g., '2010'
            base_mortality_data_path = os.path.join(ETL_DATA_PATH_SIMULATION, "df_mortalidad_ccaa_sexo/mortalidad_policyspace_es")

            for sex_label_loop, sex_filename_part in [('male', 'men'), ('female', 'women')]:
                for cpro_code in self.geo.states_on_process: # cpro_code is like '01', '28'
                    ccaa_code = cpro_to_ccaa_map.get(cpro_code)
                    
                    if not ccaa_code:
                        script_logger.warning(f"Mortality: CCAA code not found for CPRO {cpro_code}. Assigning default empty mortality data for {sex_label_loop}.")
                        self.mortality[sex_label_loop][cpro_code] = pd.DataFrame(columns=['age','rate']).groupby('age')
                        continue
                    
                    mortality_filename = f"mortality_{sex_filename_part}_{ccaa_code}.csv"
                    mortality_filepath = os.path.join(base_mortality_data_path, mortality_filename)

                    try:
                        df_mortality_ccaa_raw = pd.read_csv(mortality_filepath, sep=';')
                        # The first column is 'Edad', subsequent columns are years.
                        age_col_name = df_mortality_ccaa_raw.columns[0] # Should be 'Edad'
                        
                        year_to_load = None
                        if current_sim_year_str in df_mortality_ccaa_raw.columns:
                            year_to_load = current_sim_year_str
                        else: # Fallback to latest available year <= sim_year
                            year_columns = [col for col in df_mortality_ccaa_raw.columns if col.isdigit() and len(col) == 4]
                            available_fallback_years = sorted([yr for yr in year_columns if yr <= current_sim_year_str], reverse=True)
                            if available_fallback_years:
                                year_to_load = available_fallback_years[0]
                                script_logger.info(f"Mortality data for CPRO {cpro_code} (CCAA {ccaa_code}), Sex {sex_label_loop}: Year {current_sim_year_str} not found. Using fallback year: {year_to_load}.")
                        
                        if year_to_load and age_col_name == 'Edad':
                            df_mortality_processed = df_mortality_ccaa_raw[[age_col_name, year_to_load]].copy()
                            df_mortality_processed.rename(columns={age_col_name: 'age', year_to_load: 'rate'}, inplace=True)
                            
                            df_mortality_processed['age'] = pd.to_numeric(df_mortality_processed['age'], errors='coerce')
                            df_mortality_processed['rate'] = pd.to_numeric(df_mortality_processed['rate'], errors='coerce')
                            df_mortality_processed.dropna(subset=['age', 'rate'], inplace=True)
                            
                            if not df_mortality_processed.empty:
                                self.mortality[sex_label_loop][cpro_code] = df_mortality_processed.groupby('age')
                                script_logger.info(f"Successfully loaded mortality data for CPRO {cpro_code} (CCAA {ccaa_code}), Sex {sex_label_loop}, Year {year_to_load}.")
                            else:
                                script_logger.warning(f"No valid mortality data rows after processing for CPRO {cpro_code} (CCAA {ccaa_code}), Sex {sex_label_loop}, Year {year_to_load}. Assigning default.")
                                self.mortality[sex_label_loop][cpro_code] = pd.DataFrame(columns=['age','rate']).groupby('age')
                        else:
                            script_logger.warning(f"Mortality data for CPRO {cpro_code} (CCAA {ccaa_code}), Sex {sex_label_loop}: File {mortality_filepath} loaded, but 'Edad' or suitable year column (target: {current_sim_year_str}) not found. Assigning default.")
                            self.mortality[sex_label_loop][cpro_code] = pd.DataFrame(columns=['age','rate']).groupby('age')
                            
                    except FileNotFoundError:
                        script_logger.warning(f"Mortality data file not found: {mortality_filepath} (for CPRO {cpro_code}, CCAA {ccaa_code}, Sex {sex_label_loop}). Assigning default.")
                        self.mortality[sex_label_loop][cpro_code] = pd.DataFrame(columns=['age','rate']).groupby('age')
                    except Exception as e_prov_sex:
                        script_logger.error(f"Error processing mortality file {mortality_filepath} for CPRO {cpro_code}, Sex {sex_label_loop}: {e_prov_sex}. Assigning default.")
                        self.mortality[sex_label_loop][cpro_code] = pd.DataFrame(columns=['age','rate']).groupby('age')
            
            script_logger.info("Finished processing Spanish mortality data based on individual CCAA/sex files.")

        except Exception as e:
            script_logger.error(f"CRITICAL ERROR in main mortality data loading block: {e}. Mortality data might be incomplete/incorrect.")

        # --- Adapted Fertility Data Loading for Spain ---
        self.fertility = defaultdict(lambda: pd.DataFrame(columns=['age','rate']).groupby('age'))
        try:
            script_logger.info("Starting Spanish fertility data loading process...")
            # Load CPRO to Province Name mapping
            codigos_provincias_path = os.path.join(ETL_DATA_PATH_SIMULATION, "indicadores_fecundidad_municipio_provincias/codigos_ccaa_provincias.csv")
            df_codigos_provincias = pd.read_csv(codigos_provincias_path, dtype={'CPRO': str, 'Provincia': str})
            
            # Clean CPRO codes in mapping: remove '.0' and zfill to 2 digits
            df_codigos_provincias['CPRO_cleaned'] = df_codigos_provincias['CPRO'].astype(str).str.split('.').str[0].str.zfill(2)
            cpro_to_name_map = df_codigos_provincias.set_index('CPRO_cleaned')['Provincia'].to_dict()

            current_sim_year_str = str(self.geo.year) # e.g., '2022'
            base_fertility_data_path = os.path.join(ETL_DATA_PATH_SIMULATION, "indicadores_fecundidad_municipio_provincias/tasas_fertilidad_provincias")

            for state_cpro_code in self.geo.states_on_process: # state_cpro_code is like '02', '28'
                province_name_original = cpro_to_name_map.get(state_cpro_code)
                
                if not province_name_original:
                    script_logger.warning(f"Fertility: Province name not found for CPRO {state_cpro_code}. Assigning default empty fertility data.")
                    self.fertility[state_cpro_code] = pd.DataFrame(columns=['age','rate']).groupby('age')
                    continue

                # Transform province name to match filename convention
                filename_province_name = province_name_original.replace('/', '_').replace(', ', '__').replace(' ', '_')
                
                fertility_province_path = os.path.join(base_fertility_data_path, f"{filename_province_name}.csv")
                
                try:
                    df_province_fert_raw = pd.read_csv(fertility_province_path)
                    if 'edad' in df_province_fert_raw.columns and current_sim_year_str in df_province_fert_raw.columns:
                        df_province_fert_year = df_province_fert_raw[['edad', current_sim_year_str]].copy()
                        df_province_fert_year.rename(columns={'edad': 'age', current_sim_year_str: 'rate'}, inplace=True)
                        
                        df_province_fert_year['age'] = pd.to_numeric(df_province_fert_year['age'], errors='coerce')
                        df_province_fert_year['rate'] = pd.to_numeric(df_province_fert_year['rate'], errors='coerce')
                        df_province_fert_year.dropna(subset=['age', 'rate'], inplace=True) # Remove rows where age or rate couldn't be parsed
                        
                        if not df_province_fert_year.empty:
                            self.fertility[state_cpro_code] = df_province_fert_year.groupby('age')
                            script_logger.info(f"Successfully loaded fertility data for CPRO {state_cpro_code} ({province_name_original}) for year {current_sim_year_str}.")
                        else:
                            script_logger.warning(f"No valid fertility data rows after processing for CPRO {state_cpro_code} ({province_name_original}), year {current_sim_year_str} in {fertility_province_path}. Assigning default.")
                            self.fertility[state_cpro_code] = pd.DataFrame(columns=['age','rate']).groupby('age')
                    else:
                        # Try to find the latest available year if current_sim_year_str is not present
                        year_columns = [col for col in df_province_fert_raw.columns if col.isdigit() and len(col) == 4]
                        if not year_columns:
                            script_logger.warning(f"Fertility data for CPRO {state_cpro_code} ({province_name_original}): File {fertility_province_path} loaded, but no year columns found or 'edad' column missing. Assigning default.")
                            self.fertility[state_cpro_code] = pd.DataFrame(columns=['age','rate']).groupby('age')
                            continue

                        # Find years <= current_sim_year_str
                        available_fallback_years = sorted([yr for yr in year_columns if yr <= current_sim_year_str], reverse=True)
                        
                        selected_fallback_year = None
                        if available_fallback_years:
                            selected_fallback_year = available_fallback_years[0]
                            script_logger.info(f"Fertility data for CPRO {state_cpro_code}: Year {current_sim_year_str} not found in {fertility_province_path}. Using latest available fallback year: {selected_fallback_year}.")
                        else: # No fallback year found (all years are in the future, or no numeric year columns)
                            script_logger.warning(f"Fertility data for CPRO {state_cpro_code}: Year {current_sim_year_str} not found in {fertility_province_path}, and no suitable fallback year available. Assigning default.")
                            self.fertility[state_cpro_code] = pd.DataFrame(columns=['age','rate']).groupby('age')
                            continue
                        
                        # Process with selected_fallback_year
                        df_province_fert_year = df_province_fert_raw[['edad', selected_fallback_year]].copy()
                        df_province_fert_year.rename(columns={'edad': 'age', selected_fallback_year: 'rate'}, inplace=True)
                        df_province_fert_year['age'] = pd.to_numeric(df_province_fert_year['age'], errors='coerce')
                        df_province_fert_year['rate'] = pd.to_numeric(df_province_fert_year['rate'], errors='coerce')
                        df_province_fert_year.dropna(subset=['age', 'rate'], inplace=True)

                        if not df_province_fert_year.empty:
                            self.fertility[state_cpro_code] = df_province_fert_year.groupby('age')
                            script_logger.info(f"Successfully loaded fallback fertility data for CPRO {state_cpro_code} ({province_name_original}) for year {selected_fallback_year}.")
                        else:
                            script_logger.warning(f"No valid fertility data rows after processing fallback for CPRO {state_cpro_code}, year {selected_fallback_year} in {fertility_province_path}. Assigning default.")
                            self.fertility[state_cpro_code] = pd.DataFrame(columns=['age','rate']).groupby('age')

                except FileNotFoundError:
                    script_logger.warning(f"Fertility data file not found for CPRO {state_cpro_code} (Name: {province_name_original}, Attempted filename: {filename_province_name}.csv). Path: {fertility_province_path}. Assigning default.")
                    self.fertility[state_cpro_code] = pd.DataFrame(columns=['age','rate']).groupby('age')
                except Exception as e_prov:
                    script_logger.error(f"Error processing fertility file {fertility_province_path} for CPRO {state_cpro_code} ({province_name_original}): {e_prov}. Assigning default.")
                    self.fertility[state_cpro_code] = pd.DataFrame(columns=['age','rate']).groupby('age')
            
            script_logger.info("Finished processing Spanish fertility data based on individual province files.")

        except Exception as e:
            script_logger.error(f"CRITICAL ERROR in main fertility data loading block: {e}. Fertility data might be incomplete/incorrect.")
        
        self.pops = {} 

        self.marriage_probs = {'male': pd.DataFrame(), 'female': pd.DataFrame()}
        try:
            self.marriage_probs['male'] = pd.read_csv(os.path.join(INPUT_DATA_PATH_SIMULATION, 'marriage_age_men.csv'), sep=';')
            self.marriage_probs['female'] = pd.read_csv(os.path.join(INPUT_DATA_PATH_SIMULATION, 'marriage_age_women.csv'), sep=';')
            script_logger.info("Loaded original marriage probability data.")
        except FileNotFoundError:
            script_logger.warning("Original marriage probability files not found. Marriage logic might fail or use defaults if active.")
        except Exception as e:
            script_logger.error(f"Error loading marriage probability data: {e}")

        # --- Interest Data Loading (Adapted for Spain) ---
        self.interest = pd.DataFrame().set_index(pd.to_datetime([])) 
        try:
            interest_param_val = self.PARAMS.get('INTEREST', 'real') 
            interest_filename_adapted = f"interest_{interest_param_val}_imputado.csv"
            interest_path_adapted = os.path.join(ETL_DATA_PATH_SIMULATION, "interest_data_ETL/imputados", interest_filename_adapted)
            
            interest_df = None
            if os.path.exists(interest_path_adapted):
                interest_df = pd.read_csv(interest_path_adapted, sep=';')
                script_logger.info(f"Successfully loaded interest data from ETL: {interest_path_adapted}")
            else: 
                script_logger.warning(f"Adapted interest file not found at {interest_path_adapted}. Trying original input folder.")
                interest_filename_original = f"interest_{interest_param_val}.csv"
                interest_path_original = os.path.join(INPUT_DATA_PATH_SIMULATION, interest_filename_original) 
                if os.path.exists(interest_path_original):
                    interest_df = pd.read_csv(interest_path_original, sep=';')
                    script_logger.info(f"Successfully loaded interest data from original input: {interest_path_original}")
                else:
                    script_logger.error(f"CRITICAL ERROR: Interest data file not found in ETL or input for type '{interest_param_val}'. Model may fail.")
            
            if interest_df is not None:
                interest_df.date = pd.to_datetime(interest_df.date)
                self.interest = interest_df.set_index('date')
        except Exception as e:
            script_logger.error(f"CRITICAL ERROR loading interest data: {e}. Model may fail.")

    def update_pop(self, old_region_id, new_region_id):
        if old_region_id is not None:
            self.mun_pops[old_region_id[:7]] += 1
            self.reg_pops[old_region_id] += 1
        if new_region_id is not None:
            self.mun_pops[new_region_id[:7]] += 1
            self.reg_pops[new_region_id] += 1

    def generate(self):
        """Spawn or load regions, agents, houses, families, and firms"""
        save_file = '{}.agents'.format(self.output.save_name)
        if not os.path.isfile(save_file) or conf.RUN['FORCE_NEW_POPULATION']:
            self.logger.logger.info('Creating new agents')
            regions = self.generator.create_regions()
            agents, houses, families, firms = self.generator.create_all(regions)
            agents = {a: agents[a] for a in agents.keys() if agents[a].address is not None}
            with open(save_file, 'wb') as f:
                pickle.dump([agents, houses, families, firms, regions], f)
        else:
            self.logger.logger.info('Loading existing agents')
            with open(save_file, 'rb') as f:
                 agents, houses, families, firms, regions = pickle.load(f)

        # Count populations for each municipality and region
        self.mun_pops = {}
        self.reg_pops = {}
        for agent in agents.values():
            r_id = agent.region_id
            mun_code = r_id[:7]
            if r_id not in self.reg_pops:
                self.reg_pops[r_id] = 0
            if mun_code not in self.mun_pops:
                self.mun_pops[mun_code] = 0
            self.mun_pops[mun_code] += 1
            self.reg_pops[r_id] += 1

        return regions, agents, houses, families, firms, self.generator.central

    def run(self):
        """Runs the simulation"""
        self.logger.logger.info('Starting run.')
        self.logger.logger.info('Output: {}'.format(self.output.path))
        self.logger.logger.info('Params: {}'.format(json.dumps(self.PARAMS, default=str)))
        self.logger.logger.info('Seed: {}'.format(self._seed))

        self.logger.logger.info('Running...')
        while self.clock.days < self.PARAMS['STARTING_DAY'] + datetime.timedelta(days=self.PARAMS['TOTAL_DAYS']):
            self.daily()
            if self.clock.months == 1 and conf.RUN['SAVE_TRANSIT_DATA']:
                self.output.save_transit_data(self, 'start')
            if self.clock.new_month:
                self.monthly()
            if self.clock.new_quarter:
                self.quarterly()
            if self.clock.new_year:
                self.yearly()
            self.clock.days += datetime.timedelta(days=1)

        if conf.RUN['PRINT_FINAL_STATISTICS_ABOUT_AGENTS']:
            self.logger.log_outcomes(self)

        if conf.RUN['SAVE_TRANSIT_DATA']:
            self.output.save_transit_data(self, 'end')
        self.logger.logger.info('Simulation completed.')

    def initialize(self):
        """Initiating simulation"""
        self.logger.logger.info('Initializing...')
        self.grave = []

        self.labor_market = markets.LaborMarket(self.seed)
        self.housing = markets.HousingMarket()
        self.pops, self.total_pop = population.load_pops(self.geo.mun_codes, self.PARAMS, self.geo.year)
        self.regions, self.agents, self.houses, self.families, self.firms, self.central = self.generate()
        self.construction_firms = {f.id: f for f in self.firms.values() if f.type == 'CONSTRUCTION'}
        self.consumer_firms = {f.id: f for f in self.firms.values() if f.type == 'CONSUMER'}

        # Group regions into their municipalities
        self.mun_to_regions = defaultdict(set)
        for region_id in self.regions.keys():
            mun_code = region_id[:7]
            self.mun_to_regions[mun_code].add(region_id)
        for mun_code, regions in self.mun_to_regions.items():
            self.mun_to_regions[mun_code] = list(regions)

        # Beginning of simulation, generate a product
        for firm in self.firms.values():
            firm.create_product()

        # First jobs allocated
        # Create an existing job market
        # Leave only 5% residual unemployment as of simulation starts
        self.labor_market.look_for_jobs(self.agents)
        total = actual = self.labor_market.num_candidates
        actual_unemployment = self.stats.global_unemployment_rate / 100
        # Simple average of 6 Metropolitan regions Brazil January 2000
        while total > 0 and actual / total > .086: # This threshold might need adjustment for Spain
            self.labor_market.hire_fire(self.firms, self.PARAMS['LABOR_MARKET'])
            self.labor_market.assign_post(actual_unemployment, None, self.PARAMS)
            self.labor_market.look_for_jobs(self.agents)
            actual = self.labor_market.num_candidates
            if total == 0: # Re-check total in case all candidates got jobs
                 break
        self.labor_market.reset()

        # Update initial pop
        for region in self.regions.values():
            region.pop = self.reg_pops.get(region.id, 0.0) # Use .get() to provide a default if key is missing

    def daily(self):
        pass

    def monthly(self):
        # Set interest rates
        i = self.interest[self.interest.index.date == self.clock.days]['interest'].iloc[0]
        m = self.interest[self.interest.index.date == self.clock.days]['mortgage'].iloc[0]
        self.central.set_interest(i, m)

        current_unemployment = self.stats.global_unemployment_rate / 100

        # Create new land licenses
        for region in self.regions.values():
            if self.PARAMS['T_LICENSES_PER_REGION'] == 'random':
                region.licenses += self.seed.choice([True, False])
            else:
                region.licenses += self.PARAMS['T_LICENSES_PER_REGION']

        # Create new firms according to average historical growth
        firm_growth(self)

        # Update firm products
        for firm in self.firms.values():
            firm.update_product_quantity(self.PARAMS['PRODUCTIVITY_EXPONENT'],
                                         self.PARAMS['PRODUCTIVITY_MAGNITUDE_DIVISOR'])

        # Call demographics
        # Update agent life cycles
        for state in self.geo.states_on_process: # state is cpro_code
            mortality_men = self.mortality['male'][state]
            mortality_women = self.mortality['female'][state]
            fertility = self.fertility[state] # self.f was replaced by self.fertility

            state_str = state # 'state' is already the CPRO string, e.g., '28'

            birthdays = defaultdict(list)
            for agent in self.agents.values():
                if self.clock.months == agent.month and agent.region_id[:2] == state_str:
                    birthdays[agent.age].append(agent)

            demographics.check_demographics(self, birthdays, self.clock.year,
                                            mortality_men, mortality_women, fertility)

        # Adjust population for immigration
        population.immigration(self)

        # Adjust families for marriages
        # population.marriage(self) # Disabled as per user instruction (no marriage data)
        script_logger.info("Marriage logic skipped as per configuration/data availability.")

        # Firms initialization
        for firm in self.firms.values():
            firm.present = self.clock
            firm.amount_sold = 0
            if firm.type is not 'CONSTRUCTION':
                firm.revenue = 0

        # FAMILIES CONSUMPTION -- using payment received from previous month
        # Equalize money within family members
        # Tax consumption when doing sales are realized
        markets.goods.consume(self)

        # Collect loan repayments
        self.central.collect_loan_payments(self)

        # FIRMS
        for firm in self.firms.values():
            # Tax workers when paying salaries
            firm.make_payment(self.regions, current_unemployment,
                              self.PARAMS['PRODUCTIVITY_EXPONENT'],
                              self.PARAMS['TAX_LABOR'],
                              self.PARAMS['WAGE_IGNORE_UNEMPLOYMENT'])
            # Tax firms before profits: (revenue - salaries paid)
            firm.pay_taxes(self.regions, self.PARAMS['TAX_FIRM'])
            # Profits are after taxes
            firm.calculate_profit()
            # Check whether it is necessary to update prices
            firm.update_prices(self.PARAMS['STICKY_PRICES'], self.PARAMS['MARKUP'], self.seed)

        # Construction firms
        vacancy = self.stats.calculate_house_vacancy(self.houses, False)
        vacancy_value = None
        # Probability depends on size of market
        if self.PARAMS['OFFER_SIZE_ON_PRICE']:
            vacancy_value = 1 - (vacancy * self.PARAMS['OFFER_SIZE_ON_PRICE'])
            if vacancy_value < self.PARAMS['MAX_OFFER_DISCOUNT']:
                vacancy_value = self.PARAMS['MAX_OFFER_DISCOUNT']
        for firm in self.construction_firms.values():
            # See if firm can build a house
            firm.plan_house(self.regions.values(), self.houses.values(), self.PARAMS, self.seed, vacancy_value)
            # See whether a house has been completed. If so, register. Else, continue
            house = firm.build_house(self.regions, self.generator)
            if house is not None:
                self.houses[house.id] = house

        # Initiating Labor Market
        # AGENTS
        self.labor_market.look_for_jobs(self.agents)

        # FIRMS
        # Check if new employee needed (functions below)
        # Check if firing is necessary
        self.labor_market.hire_fire(self.firms, self.PARAMS['LABOR_MARKET'])

        # Job Matching
        # Sample used only to calculate wage deciles
        sample_size = math.floor(len(self.agents) * 0.5)
        agent_keys_list = list(self.agents.keys())
        # Ensure sample_size is not greater than the population size
        if sample_size > len(agent_keys_list):
            sample_size = len(agent_keys_list)
            
        last_wages = [self.agents[a].last_wage
                      for a in self.seed.sample(agent_keys_list, sample_size)
                      if self.agents[a].last_wage is not None]
        
        # Handle case where last_wages might be empty (e.g., if no agents have last_wage)
        if last_wages:
            wage_deciles = np.percentile(last_wages, np.arange(0, 100, 10))
        else:
            # Default wage_deciles if no wage data available, e.g. array of zeros or a typical range
            # This depends on how downstream code handles empty/default wage_deciles
            wage_deciles = np.zeros(10) # Example: 10 deciles, all zero
            script_logger.warning("No last_wage data available to calculate wage_deciles. Using default.")

        self.labor_market.assign_post(current_unemployment, wage_deciles, self.PARAMS)

        # Initiating Real Estate Market
        self.logger.logger.info(f'Available licenses: {sum([r.licenses for r in self.regions.values()]):,.0f}')
        # Tax transaction taxes (ITBI) when selling house
        # Property tax (IPTU) collected. One twelfth per month
        # self.central.calculate_monthly_mortgage_rate()
        self.housing.housing_market(self)
        self.housing.process_monthly_rent(self)
        for house in self.houses.values():
            house.pay_property_tax(self)

        # Family investments
        for fam in self.families.values():
            fam.invest(self.central.interest, self.central, self.clock.year, self.clock.months)

        # Using all collected taxes to improve public services
        bank_taxes = self.central.collect_taxes()

        # Separate funds for region index update and separate for the policy case
        self.funds.invest_taxes(self.clock.year, bank_taxes)

        # Apply policies if percentage is different than 0
        if self.PARAMS['POLICY_COEFFICIENT']:
            self.funds.apply_policies()

        # Pass monthly information to be stored in Statistics
        self.output.save_stats_report(self, bank_taxes)

        # Getting regional GDP
        self.output.save_regional_report(self)

        if conf.RUN['SAVE_AGENTS_DATA'] == 'MONTHLY':
            self.output.save_data(self)

        if conf.RUN['PRINT_STATISTICS_AND_RESULTS_DURING_PROCESS']:
            self.logger.info(self.clock.days)

    def quarterly(self):
        if conf.RUN['SAVE_AGENTS_DATA'] == 'QUARTERLY':
            self.output.save_data(self)

    def yearly(self):
        if conf.RUN['SAVE_AGENTS_DATA'] == 'ANNUALLY':
            self.output.save_data(self)
