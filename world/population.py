import math
import os
import logging

import numpy as np
import pandas as pd
import statsmodels.api as sm

logger_pop = logging.getLogger(__name__)

# Define base paths consistently
SCRIPT_DIR_POP = os.path.dirname(os.path.realpath(__file__)) # world/
PROJECT_ROOT_POP = os.path.join(SCRIPT_DIR_POP, "..") # Navigate up to project root
INPUT_DATA_PATH = os.path.join(PROJECT_ROOT_POP, "input")
ETL_DATA_PATH = os.path.join(PROJECT_ROOT_POP, "ETL")


def simplify_pops(pops, params):
    """Simplify population"""
    list_new_age_groups = [0] + params['LIST_NEW_AGE_GROUPS']
    pops_ = {}

    # Define a mapping from canonical age groups (like '0--4') to a representative single age (e.g., lower bound)
    # This is needed if input columns to simplify_pops are '0--4', '5--9', etc.
    # The function expects numeric column names for its current logic.
    # This part requires careful adaptation if `pops` DataFrames have 'X--Y' style columns.
    
    # For now, assume that if this function is called, `load_pops` has already prepared
    # `pops` such that its columns are the *output* of a previous simplification,
    # i.e., columns are named after params['LIST_NEW_AGE_GROUPS'] upper bounds.
    # This is circular. The original `simplify_pops` took single-year columns.
    # The new `load_pops` will produce '0--4', '5--9', etc.
    # If SIMPLIFY_POP_EVOLUTION is True, these are passed to this function.
    # This function MUST convert '0--4', '5--9' into the new groups defined by LIST_NEW_AGE_GROUPS.

    # Example: Input `pop` has columns '0--4', '5--9', '10--14', ...
    # `list_new_age_groups` is [0, 6, 12, 17, 25, 35, 45, 65, 100]
    # Output columns should be '6', '12', '17', ... (representing ages 0-6, 7-12, etc. or <=6, <=12)
    # The original code's output columns were the upper bounds.

    for gender, pop_df_orig in pops.items():
        pop_df = pop_df_orig.copy()
        if 'code' not in pop_df.columns: # If 'code' is index
            pop_df.reset_index(inplace=True)

        temp_pop_fmt = pop_df[['code']].copy()

        for i in range(len(list_new_age_groups) - 1):
            lower_bound_new_group = list_new_age_groups[i]
            upper_bound_new_group = list_new_age_groups[i+1]
            new_col_name = str(upper_bound_new_group) # Name new columns by upper bound
            
            current_group_sum = pd.Series(0, index=pop_df.index)

            # Iterate through original age group columns (e.g., '0--4', '5--9')
            for orig_col_name in pop_df.columns:
                if orig_col_name == 'code':
                    continue
                
                try:
                    # Try to parse original column name like 'X--Y' or 'X+'
                    if '--' in orig_col_name:
                        low_orig, high_orig = map(int, orig_col_name.split('--'))
                    elif '+' in orig_col_name:
                        low_orig = int(orig_col_name.replace('+', ''))
                        high_orig = 200 # A large number for open-ended groups like 85+
                    else: # Assume single year if not range (should not happen with current load_pops)
                        low_orig = high_orig = int(orig_col_name)
                    
                    # Check for overlap between original group [low_orig, high_orig]
                    # and new target group (lower_bound_new_group, upper_bound_new_group]
                    # This logic needs to be precise for how much of pop_df[orig_col_name] to add.
                    # For simplicity, if any part of [low_orig, high_orig] falls into the new bin,
                    # we might sum it. This is an oversimplification if original groups are wider than new groups.
                    # A more accurate way would be to disaggregate to single years first.
                    
                    # Simplified: if the midpoint of original group falls into new group interval (exclusive lower, inclusive upper)
                    mid_point_orig = (low_orig + high_orig) / 2.0
                    if lower_bound_new_group < mid_point_orig <= upper_bound_new_group:
                         current_group_sum += pop_df[orig_col_name]

                except ValueError: # If column name is not like 'X--Y' or 'X+' or numeric
                    logger_pop.warning(f"Could not parse age group column '{orig_col_name}' in simplify_pops. Skipping.")
                    continue
            
            temp_pop_fmt[new_col_name] = current_group_sum
        pops_[gender] = temp_pop_fmt
    return pops_


def format_pops(pops):
    """Rename the columns names to be compatible as the pop simplification modification"""
    # This function assumes input `pops` has single-year age columns (0-100)
    # and renames them to integers.
    # If `load_pops` produces '0--4' etc., this function is not directly usable without adaptation.
    logger_pop.warning("format_pops is designed for single-year age columns. Current data may be incompatible.")
    for gender_key in pops:
        pop_df = pops[gender_key].copy()
        if 'code' not in pop_df.columns:
            pop_df.reset_index(inplace=True)
        
        new_columns = ['code']
        for col in pop_df.columns:
            if col == 'code':
                continue
            try: # Try to convert to int, assuming it's a single year like '0', '1', ... '100'
                new_columns.append(int(col))
            except ValueError: # If it's '0--4', keep as is or handle error
                new_columns.append(col) # Keep original name if not convertible
        pop_df.columns = new_columns
        pops[gender_key] = pop_df
    return pops


def pop_age_data(pop, code, age, percent_pop):
    """Select and return the proportion value of population
    for a given municipality, gender and age"""
    
    region_pop_data = pop[pop['code'] == str(code)]
    
    if region_pop_data.empty:
        return 0 
        
    # `age` here is an upper bound from LIST_NEW_AGE_GROUPS (e.g. 6, 12, 17)
    # The columns of `pop` (output of simplify_pops) should match these.
    # Columns in `pop` are now strings like '6', '12', etc.
    age_col_str = str(age) 
    if age_col_str not in region_pop_data.columns:
        logger_pop.warning(f"Age column '{age_col_str}' not found for code {code}. Available: {region_pop_data.columns.tolist()}")
        return 0 
        
    value_series = region_pop_data[age_col_str]
    
    if value_series.empty: 
        return 0
        
    n_pop = value_series.iloc[0] * percent_pop 
    rounded = int(round(n_pop))

    if rounded == 0 and math.ceil(n_pop) == 1:
        return 1
    return rounded


def load_pops(mun_codes_sim, params, sim_year_param):
    logger_pop.info(f"Starting Spanish population data load from ETL for target year {sim_year_param}.")
    pops = {'male': pd.DataFrame(), 'female': pd.DataFrame()}
    
    ETL_POP_SUBDIR_PATH = os.path.join(ETL_DATA_PATH, "cifras_poblacion_municipio/data_final/drive-download-20250506T180657Z-001/")
    sex_filename_map = {'men': 'hombres', 'women': 'mujeres'}
    available_years_param = params.get('POPULATION_AVAILABLE_YEARS', [2014, 2013, 2011, 2010, 2009, 2008, 2007, 2006, 2003])
    
    year_data_loaded_from_gender = {}

    age_bins = [-1, 4, 9, 14, 19, 24, 29, 34, 39, 44, 49, 54, 59, 64, 69, 74, 79, 84, 200] 
    canonical_age_cols = ['0--4', '5--9', '10--14', '15--19', '20--24', '25--29', 
                          '30--34', '35--39', '40--44', '45--49', '50--54', '55--59', 
                          '60--64', '65--69', '70--74', '75--79', '80--84', '85+']

    for name_csv_key, gender_key in [('men', 'male'), ('women', 'female')]:
        pop_df_raw = None
        actual_year_loaded = None
        sex_file_part = sex_filename_map[name_csv_key]
        
        target_file_path = os.path.join(ETL_POP_SUBDIR_PATH, f'cifras_municipio_{sex_file_part}_{sim_year_param}.csv')

        if os.path.exists(target_file_path):
            try:
                pop_df_raw = pd.read_csv(target_file_path, sep=',') 
                logger_pop.info(f"Successfully loaded population data for {gender_key} for year {sim_year_param} from {target_file_path}")
                actual_year_loaded = sim_year_param
            except Exception as e:
                logger_pop.error(f"Error reading existing file {target_file_path}: {e}. Will attempt fallback.")
                pop_df_raw = None
        else:
            logger_pop.warning(f"Population data file not found for {gender_key} for year {sim_year_param} ({target_file_path}).")

        if pop_df_raw is None: 
            logger_pop.info(f"Attempting fallback for {gender_key} population data. Available fallback years: {available_years_param}")
            for fallback_year in available_years_param:
                fallback_file_path = os.path.join(ETL_POP_SUBDIR_PATH, f'cifras_municipio_{sex_file_part}_{fallback_year}.csv')
                if os.path.exists(fallback_file_path):
                    try:
                        pop_df_raw = pd.read_csv(fallback_file_path, sep=',')
                        logger_pop.info(f"Using fallback population data for {gender_key} from year {fallback_year} ({fallback_file_path})")
                        actual_year_loaded = fallback_year
                        break
                    except Exception as e:
                        logger_pop.error(f"Error reading fallback file {fallback_file_path}: {e}. Trying next fallback.")
                        pop_df_raw = None
                else:
                    logger_pop.warning(f"Fallback population data file not found: {fallback_file_path}")
            
            if pop_df_raw is None:
                logger_pop.error(f"CRITICAL: No population data found for {gender_key} for year {sim_year_param} or any fallback years.")
                raise FileNotFoundError(f"No population data for {gender_key} found for {sim_year_param} or fallbacks.")

        year_data_loaded_from_gender[gender_key] = actual_year_loaded
        
        required_cols = ['municipio_code', 'edad', 'total'] 
        if not all(col in pop_df_raw.columns for col in required_cols):
            current_file_for_error = target_file_path if os.path.exists(target_file_path) else fallback_file_path
            logger_pop.error(f"Population file {current_file_for_error} is missing one or more required columns: {required_cols}. Found: {pop_df_raw.columns.tolist()}")
            raise ValueError("Missing required columns in population file.")

        pop_df_processed = pop_df_raw.copy()
        pop_df_processed['municipio_code'] = pop_df_processed['municipio_code'].astype(str).str.zfill(5)
        
        mun_codes_sim_str = [str(mc).zfill(5) for mc in mun_codes_sim]
        pop_df_processed = pop_df_processed[pop_df_processed['municipio_code'].isin(mun_codes_sim_str)]
        
        if pop_df_processed.empty:
            logger_pop.warning(f"No population data rows for {gender_key}, year {actual_year_loaded} after filtering for simulated municipalities: {mun_codes_sim_str}.")
            empty_df_cols = ['code'] + canonical_age_cols
            pops[gender_key] = pd.DataFrame(columns=empty_df_cols).set_index('code') # Set index for consistency
            continue

        pop_df_processed['edad'] = pd.to_numeric(pop_df_processed['edad'], errors='coerce')
        pop_df_processed['total'] = pd.to_numeric(pop_df_processed['total'], errors='coerce')
        pop_df_processed.dropna(subset=['edad', 'total'], inplace=True)

        pop_df_processed['age_group'] = pd.cut(pop_df_processed['edad'], bins=age_bins, labels=canonical_age_cols, right=True, include_lowest=True)
        
        pop_df_grouped = pop_df_processed.groupby(['municipio_code', 'age_group'], observed=False)['total'].sum()
        pop_df_pivoted = pop_df_grouped.unstack(level='age_group', fill_value=0)
        
        for col in canonical_age_cols:
            if col not in pop_df_pivoted.columns:
                pop_df_pivoted[col] = 0
        
        pop_df_final = pop_df_pivoted[canonical_age_cols].reset_index() 
        pop_df_final.rename(columns={'municipio_code': 'code'}, inplace=True)
        pops[gender_key] = pop_df_final

    logger_pop.info("INFO: AP (Área de Ponderação) specific population data loading is BYPASSED when using new ETL population files.") # Changed from WARNING to INFO

    total_pop = 0
    if not pops['male'].empty and not pops['female'].empty:
        # Ensure 'code' is not included in sum if it's not index
        numeric_cols_male = [col for col in pops['male'].columns if col != 'code']
        numeric_cols_female = [col for col in pops['female'].columns if col != 'code']
        pop_male_sum = pops['male'][numeric_cols_male].sum().sum() if numeric_cols_male else 0
        pop_female_sum = pops['female'][numeric_cols_female].sum().sum() if numeric_cols_female else 0
        total_pop = round((pop_male_sum + pop_female_sum) * params['PERCENTAGE_ACTUAL_POP'])
    
    if params.get('SIMPLIFY_POP_EVOLUTION', True):
        logger_pop.info("Calling simplify_pops. Input columns to simplify_pops will be '0--4', '5--9', etc.")
        # The current simplify_pops expects numeric column names (single ages or upper bounds).
        # Passing '0--4' style columns will likely cause errors within simplify_pops.
        # This interaction needs to be resolved: either adapt simplify_pops or ensure load_pops
        # produces data in the format simplify_pops expects (e.g. single year ages before simplification).
        # For now, the call is made, and errors within simplify_pops might occur.
        pops = simplify_pops(pops, params) 
    else:
        logger_pop.warning("SIMPLIFY_POP_EVOLUTION is False. format_pops() might be needed but is not called due to potential column name incompatibilities with current age group format.")

    logger_pop.info(f"Finished loading and processing population data. Total scaled population: {total_pop}")
    return pops, total_pop


class PopulationEstimates:
    def __init__(self, fname_etl):
        self.linear_models = {}
        self.data = {} # Store data as {mun_code_str: {year_str: value}}
        
        try:
            df = pd.read_csv(fname_etl, sep=',')
            logger_pop.info(f"PopulationEstimates: Successfully read {fname_etl}")

            # Assuming the first column is 'mun_code' and needs formatting
            # and subsequent columns are years with population data.
            mun_code_col_name = df.columns[0] # e.g., 'mun_code'
            
            # Process mun_code to be 5-digit string
            df['mun_code_str'] = df[mun_code_col_name].apply(lambda x: str(int(float(str(x)))).zfill(5) if pd.notna(x) else None)
            df.dropna(subset=['mun_code_str'], inplace=True)
            df.set_index('mun_code_str', inplace=True)
            df.drop(columns=[mun_code_col_name], inplace=True) # Drop original mun_code column

            # Ensure year columns are strings for .astype('int') later if needed, and for dict keys
            df.columns = df.columns.astype(str)

            for mun_code_str, pops_series in df.iterrows():
                # Filter out NaN values from population series for regression
                pops_series_cleaned = pops_series.dropna()
                if len(pops_series_cleaned) < 2: # Need at least 2 points for regression
                    # logger_pop.warning(f"PopulationEstimates: Not enough data for mun_code {mun_code_str} to build model. Min 2 required, got {len(pops_series_cleaned)}.")
                    continue

                x = pops_series_cleaned.index.values.astype('int') # Years as integers
                y = pops_series_cleaned.values
                
                try:
                    # Add constant for intercept if not already present (sm.OLS behavior)
                    X_const = sm.add_constant(x, prepend=True)
                    self.linear_models[mun_code_str] = sm.OLS(y, X_const).fit()
                except Exception as e_model:
                    logger_pop.error(f"PopulationEstimates: Error building model for mun_code {mun_code_str}: {e_model}")
            
            # Store data for direct lookup (mun_code_str -> year_str -> value)
            # df.T.to_dict() would create {year_str: {mun_code_str: value}}, we need the other way
            for mun_code_str_idx in df.index:
                self.data[mun_code_str_idx] = df.loc[mun_code_str_idx].dropna().astype(float).to_dict()
                # Ensure keys in inner dict are strings (years)
                self.data[mun_code_str_idx] = {str(k): v for k, v in self.data[mun_code_str_idx].items()}

            logger_pop.info(f"PopulationEstimates initialized from ETL file: {fname_etl}. Models built: {len(self.linear_models)}")

        except FileNotFoundError:
            logger_pop.error(f"PopulationEstimates: ETL File not found {fname_etl}. Population estimation will not work.")
        except Exception as e:
            logger_pop.error(f"PopulationEstimates: Error initializing from ETL file {fname_etl}: {e}")


    def estimate_for_year(self, mun_code_str, year_int): # mun_code_str is 5-digit string, year_int is int
        year_str = str(year_int)
        try:
            # Try direct lookup first
            if mun_code_str in self.data and year_str in self.data[mun_code_str]:
                estimate = self.data[mun_code_str][year_str]
                if pd.notna(estimate):
                    return estimate
            
            # Fallback to linear model if direct data not found or if it was NaN
            if mun_code_str in self.linear_models:
                # Predict requires a constant term if model was fit with one
                prediction = self.linear_models[mun_code_str].predict([1, year_int])[0] # [1, year] for constant and year
                return round(max(0, prediction)) # Ensure non-negative population
            else:
                # logger_pop.warning(f"PopulationEstimates: No model or data for mun_code {mun_code_str}. Returning 0.")
                return 0 
        except Exception as e:
            # logger_pop.error(f"Error in PopulationEstimates.estimate_for_year for {mun_code_str}, {year_int}: {e}")
            return 0


class MarriageData:
    def __init__(self):
        self.data = {'male': {}, 'female': {}}
        logger_pop.info("MarriageData initialized. Data loading is disabled as per user instruction; marriage probabilities will be 0.")
        # Original file loading logic is commented out / removed.
        # try:
        #     for gender, key_suffix in [('male', 'men'), ('female', 'women')]:
        #         marriage_file_path = os.path.join(INPUT_DATA_PATH, f'marriage_age_{key_suffix}.csv')
        #         if os.path.exists(marriage_file_path):
        #             df_marriage = pd.read_csv(marriage_file_path, sep=',') 
        #             expected_cols = ['low', 'high', 'percentage']
        #             if not all(col in df_marriage.columns for col in expected_cols):
        #                 logger_pop.error(f"Marriage data file {marriage_file_path} has incorrect columns. Expected: {expected_cols}, Found: {df_marriage.columns.tolist()}")
        #                 continue
        #             for row in df_marriage.itertuples(index=False):
        #                 if hasattr(row, 'low') and hasattr(row, 'high') and hasattr(row, 'percentage'):
        #                     for age_val in range(int(row.low), int(row.high) + 1):
        #                         self.data[gender][age_val] = float(row.percentage)
        #                 else:
        #                     logger_pop.error(f"Row in {marriage_file_path} does not have expected attributes. Row: {row}")
        #         else:
        #             logger_pop.warning(f"Marriage data file not found: {marriage_file_path}. Marriage probabilities for {gender} will be 0.")
        # except Exception as e:
        #     logger_pop.error(f"Error loading or processing marriage data: {e}. Marriage probabilities may be incorrect.")

    def p_marriage(self, agent):
        # Since self.data is empty, this will always return 0.
        return self.data[agent.gender.lower()].get(agent.age, 0)


# Initialize PopulationEstimates with the new ETL file path
ETL_ESTIMATIVAS_PATH = os.path.join(ETL_DATA_PATH, "estimativas_pop/preprocesados/cifras_poblacion_municipio.csv")
pop_estimates = PopulationEstimates(ETL_ESTIMATIVAS_PATH)
marriage_data = MarriageData()


def immigration(sim):
    """Adjust population for immigration"""
    year = sim.clock.year

    for mun_code_str, pop_count in sim.mun_pops.items(): # mun_pops keys are strings
        estimated_pop = pop_estimates.estimate_for_year(mun_code_str, year) # Pass string mun_code
        estimated_pop *= sim.PARAMS['PERCENTAGE_ACTUAL_POP']
        n_immigration = max(estimated_pop - pop_count, 0)
        n_immigration *= 1/12
        n_migrants = math.ceil(n_immigration)
        if not n_migrants:
            continue

        new_agents = sim.generator.create_random_agents(n_migrants)
        if not new_agents: continue

        # Determine members_per_family for this municipality's CCAA
        current_members_per_family = sim.PARAMS['MEMBERS_PER_FAMILY'] # Default
        ccaa_code = sim.generator.df_equivalencias_map_ine_to_ccaa.get(mun_code_str)
        current_year = sim.clock.year

        if ccaa_code and not sim.generator.avg_household_size_data.empty:
            try:
                avg_size = sim.generator.avg_household_size_data.get((ccaa_code, current_year))
                if pd.notna(avg_size) and avg_size > 0:
                    current_members_per_family = avg_size
                    # logger_pop.info(f"Immigration: Using CCAA {ccaa_code} specific household size for year {current_year}: {avg_size:.2f} for mun {mun_code_str}")
                # else:
                    # logger_pop.warning(f"Immigration: Avg household size for CCAA {ccaa_code}, year {current_year} not found or invalid. Using default: {current_members_per_family}")
            except KeyError:
                # logger_pop.warning(f"Immigration: Avg household size for CCAA {ccaa_code}, year {current_year} not found in index. Using default: {current_members_per_family}")
                pass # Use default if lookup fails
        # else:
            # if not ccaa_code:
                # logger_pop.warning(f"Immigration: CCAA code for mun {mun_code_str} not found. Using default household size: {current_members_per_family}")
        
        if current_members_per_family <= 0: # Safeguard
            current_members_per_family = sim.PARAMS['MEMBERS_PER_FAMILY']

        n_families = 0
        if len(new_agents) > 0: # Avoid division by zero if no new agents
            n_families = math.ceil(len(new_agents) / current_members_per_family)
        
        if n_families == 0 and len(new_agents) > 0: # Ensure at least one family if there are agents
            n_families = 1
            # logger_pop.info(f"Immigration: Adjusted n_families to 1 for mun {mun_code_str} as num_agents ({len(new_agents)}) > 0 but calculated n_families was 0 with household size {current_members_per_family:.2f}")

        if n_families == 0: continue
        new_families_dict = sim.generator.create_families(n_families)

        sim.generator.allocate_to_family(new_agents, new_families_dict)

        families_to_process = []
        for f_id, f_obj in new_families_dict.items():
            if not f_obj.members:
                del sim.families[f_id] # Should not happen if allocate_to_family ensures members
                continue
            f_obj.savings = sum(m.grab_money() for m in f_obj.members.values())
            # Assign a temporary region_id to the family based on one of its members,
            # before housing market, so they are considered for the correct municipality.
            # This assumes create_random_agents assigns a region_id to agents.
            # If create_random_agents doesn't set region_id, this needs to be handled.
            # For now, assume agents created by create_random_agents are not yet placed in a region.
            # The rental market will place them.
            # However, the original code for immigration didn't explicitly set family region_id before rental.
            # Let's assume the rental market handles families without a pre-set region_id by placing them
            # in one of the simulated municipalities.
            families_to_process.append(f_obj)

        if not families_to_process: continue

        sim.housing.rental.rental_market(families_to_process, sim)

        for f_obj in families_to_process:
            if f_obj.house is not None: # Only add families that found housing
                sim.families[f_obj.id] = f_obj
                for agent_id, agent_obj in f_obj.members.items():
                    if agent_id not in sim.agents: # If agent was newly created and not yet in sim.agents
                        sim.agents[agent_id] = agent_obj
                        # Agent's region_id is set by family.move_in(house)
                        sim.update_pop(None, agent_obj.region_id) # Update pop for new agent in new region
            # else: family remains homeless and is not added to sim.families


def marriage(sim):
    """Adjust families for marriages"""
    to_marry = []
    for agent in sim.agents.values():
        if sim.seed.random() < sim.PARAMS['MARRIAGE_CHECK_PROBABILITY']:
            if sim.seed.random() < agent.p_marriage:
                to_marry.append(agent)

    sim.seed.shuffle(to_marry)
    
    # Iterate over pairs
    i = 0
    while i < len(to_marry) - 1:
        a = to_marry[i]
        b = to_marry[i+1]
        i += 2 # Move to next potential pair

        if a.family and b.family and a.family.id != b.family.id: # Ensure both are in families and different ones
            a_to_move_out = len([m for m in a.family.members.values() if m.age >= 21]) >= 2
            b_to_move_out = len([m for m in b.family.members.values() if m.age >= 21]) >= 2
            
            family_a_original_region = a.family.house.region_id if a.family.house else None
            family_b_original_region = b.family.house.region_id if b.family.house else None

            if a_to_move_out and b_to_move_out:
                new_family_dict = sim.generator.create_families(1)
                new_family = list(new_family_dict.values())[0]
                
                old_family_a = a.family
                old_family_b = b.family

                old_family_a.remove_agent(a)
                old_family_b.remove_agent(b)
                
                new_family.add_agent(a)
                new_family.add_agent(b)
                new_family.relatives.add(a.id)
                new_family.relatives.add(b.id)
                
                sim.housing.rental.rental_market([new_family], sim)

                if new_family.house is None: # Marriage failed (no house)
                    old_family_a.add_agent(a) # Revert
                    old_family_b.add_agent(b)
                else:
                    sim.families[new_family.id] = new_family
                    if family_a_original_region:
                         sim.update_pop(family_a_original_region, a.region_id) # a.region_id is new house region
                    if family_b_original_region:
                         sim.update_pop(family_b_original_region, b.region_id) # b.region_id is new house region
            
            elif b_to_move_out and a.family: # b moves to a's family
                b.family.remove_agent(b)
                a.family.add_agent(b)
                if family_b_original_region:
                    sim.update_pop(family_b_original_region, b.region_id) # b's region is now a's family's house region

            elif a_to_move_out and b.family: # a moves to b's family
                a.family.remove_agent(a)
                b.family.add_agent(a)
                if family_a_original_region:
                    sim.update_pop(family_a_original_region, a.region_id) # a's region is now b's family's house region
            
            else: # Merge families: b's family merges into a's family
                if a.family and b.family: # Both must exist
                    family_a = a.family
                    family_b = b.family
                    id_family_b = family_b.id

                    # Transfer assets from family_b to family_a
                    for house_b in list(family_b.owned_houses): # Iterate over a copy
                        family_b.owned_houses.remove(house_b)
                        family_a.owned_houses.append(house_b)
                        house_b.owner_id = family_a.id
                    
                    savings_b = family_b.grab_savings(sim.central, sim.clock.year, sim.clock.months)
                    family_a.update_balance(savings_b)

                    if id_family_b in sim.central.loans:
                        loans_b = sim.central.loans.pop(id_family_b)
                        sim.central.loans[family_a.id] = loans_b # This might overwrite existing loans of family_a

                    # Move members from family_b to family_a
                    for member_b_id, member_b_obj in list(family_b.members.items()): # Iterate over a copy
                        family_b.remove_agent(member_b_obj) # This sets agent.family = None
                        family_a.add_agent(member_b_obj) # This sets agent.family = family_a and agent.region_id
                        if family_b_original_region and member_b_obj.region_id: # member_b_obj.region_id is now family_a's house region
                             sim.update_pop(family_b_original_region, member_b_obj.region_id)


                    # Vacate family_b's house if it was rented
                    if family_b.house and not family_b.is_owner(family_b.house.id):
                        family_b.house.empty() # family_id = None, rent_data = None
                    
                    if id_family_b in sim.families:
                        del sim.families[id_family_b]
