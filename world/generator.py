"""
This is the module that uses input data to generate the artificial entities (instances)
used in the model. First, regions - the actual municipalities - are created using
shapefile input of real limits and real urban/rural areas.
Then, Agents are created and bundled into families, given population measures.
Then, houses and firms are created and families are allocated to their first houses.
"""
import os # Added import os
import logging
import math
import uuid

import pandas as pd
import numpy as np # Added import
import shapely
from shapely.ops import triangulate # Added for new sampling method
# import random # No longer needed as self.seed is used

from agents import Agent, Family, Firm, ConstructionFirm, Region, House, Central
from .firms import FirmData
from .population import pop_age_data
from .shapes import prepare_shapes

logger = logging.getLogger('generator')

# Define base paths consistently
SCRIPT_DIR_GENERATOR = os.path.dirname(os.path.realpath(__file__)) # world/
PROJECT_ROOT_GENERATOR = os.path.join(SCRIPT_DIR_GENERATOR, "..") # Navigate up to project root
INPUT_DATA_PATH = os.path.join(PROJECT_ROOT_GENERATOR, "input") # Original input path
ETL_DATA_PATH = os.path.join(PROJECT_ROOT_GENERATOR, "ETL") # Spanish ETL data path

# Necessary input Data - Adapted for Spanish data
try:
    prop_urban_path = os.path.join(ETL_DATA_PATH, "distribucion_urbana/data_final/distribucion_urbana_municipios_2003_to_2022.csv")
    prop_urban_full_wide = pd.read_csv(prop_urban_path, sep=',', dtype={'municipio_code': str})
    
    # Melt the DataFrame from wide to long format
    # 'municipio_code' is the identifier, year columns are variables to unpivot
    year_columns = [col for col in prop_urban_full_wide.columns if col.isdigit() and len(col) == 4] # e.g., '2003', '2004', ...
    
    prop_urban = pd.melt(prop_urban_full_wide, 
                         id_vars=['municipio_code'], 
                         value_vars=year_columns, 
                         var_name='year', 
                         value_name='prop_urban')
    
    # Rename 'municipio_code' to 'cod_mun' and ensure correct types
    prop_urban.rename(columns={'municipio_code': 'cod_mun'}, inplace=True)
    prop_urban['cod_mun'] = prop_urban['cod_mun'].astype(str).str.zfill(5)
    prop_urban['year'] = prop_urban['year'].astype(int)
    prop_urban['prop_urban'] = pd.to_numeric(prop_urban['prop_urban'], errors='coerce') # Ensure numeric, handle potential errors

    logger.info(f"Loaded and transformed Spanish prop_urban data from {prop_urban_path}")
except FileNotFoundError:
    logger.error(f"prop_urban file not found at {prop_urban_path}. Using placeholder or original if available.")
    # Fallback or error handling if Spanish data is not found
    prop_urban = pd.read_csv(os.path.join(INPUT_DATA_PATH, 'prop_urban_2000_2010.csv'), sep=';')


class Generator:
    def __init__(self, sim):
        self.sim = sim
        self.seed = sim.seed
        self.urban, self.shapes = prepare_shapes(sim.geo) # self.urban should be populated correctly by prepare_shapes
        self.firm_data = FirmData(self.sim.geo.year)
        self.central = Central('central')
        # single_ap_muns logic is deprecated for Spanish adaptation as APs are not used.
        # self.prob_urban now directly uses the Spanish prop_urban data.
        # single_ap_muns = pd.read_csv(os.path.join(INPUT_DATA_PATH, f'single_aps_{self.sim.geo.year}.csv')) # Original path
        # self.single_ap_muns = single_ap_muns['mun_code'].tolist()
        self.single_ap_muns = [] # Set to empty list as it's not used by the adapted prob_urban
        # Store years_study parameters for easier access in self.qual
        self.years_study_parameters = {
            '1': ['1', '2'], '2': ['4', '6', '8'], '3': ['9', '10', '11'],
            '4': ['12', '13', '14', '15'], '5': ['1', '2', '4', '6', '8', '9']
        }
        self.df_equivalencias = pd.DataFrame() # Initialize, will be populated in create_regions
        self.df_equivalencias_map_ine_to_ccaa = {} # Initialize map
        
        # Load predicted average household size data
        self.avg_household_size_data = pd.DataFrame() # Initialize as empty
        try:
            household_size_path = os.path.join(ETL_DATA_PATH, "tamaño_medio_hogares_ccaa/datos_prediccion/predicted_household_sizes_by_ccaa.csv")
            df_hh_size = pd.read_csv(household_size_path)
            df_hh_size['ccaa_code'] = df_hh_size['ccaa_code'].astype(str).str.zfill(2)
            df_hh_size['year'] = df_hh_size['year'].astype(int)
            # Store as a Series with MultiIndex for easy lookup
            self.avg_household_size_data = df_hh_size.set_index(['ccaa_code', 'year'])['avg_household_size']
            logger.info(f"Successfully loaded predicted average household size data from {household_size_path}")
        except FileNotFoundError:
            logger.error(f"Predicted household size data file not found at {household_size_path}. Will use default MEMBERS_PER_FAMILY.")
        except Exception as e:
            logger.error(f"Error loading predicted household size data: {e}. Will use default MEMBERS_PER_FAMILY.")

        self.quali = self.load_quali() # Ensure this is called after df_equivalencias might be needed by household size lookup if map is built here

    def years_study(self, loc):
        # Qualification 2010 degrees of instruction transformation into years of study
        # Now uses self.years_study_parameters which is initialized in __init__
        # The choice is made when the parameter is accessed, so keep self.seed.choice here
        return self.seed.choice(self.years_study_parameters[loc])

    def gen_id(self):
        """Generate a random id that should
        avoid collisions"""
        return str(uuid.uuid4())[:12]

    def create_regions(self):
        """Create regions"""
        # Load Spanish IDHM data
        # Original columns: ['cod_mun', 'year', 'idhm']
        # Spanish: ['mun_code' (short), 'year', 'IDHM']
        try:
            idhm_path = os.path.join(ETL_DATA_PATH, "idhm_indice_desarrollo_humano_municipal/IRPFmunicipios_final_IDHM.csv")
            idhm_spanish = pd.read_csv(idhm_path, sep=',', dtype={'mun_code': str})
            idhm_spanish.rename(columns={'mun_code': 'mun_code_short', 'IDHM': 'idhm'}, inplace=True) # Use 'idhm' for value
            idhm_spanish = idhm_spanish.loc[idhm_spanish['year'] == self.sim.geo.year]
            logger.info(f"Loaded Spanish IDHM data from {idhm_path} for year {self.sim.geo.year}")

            # Load equivalencias to map INE 5-digit (from shapes) to short mun_code for IDHM lookup
            equivalencias_path = os.path.join(ETL_DATA_PATH, "tabla_equivalencias/data/df_equivalencias_municipio_CORRECTO.csv")
            df_equivalencias = pd.read_csv(equivalencias_path, sep=",", dtype=str)
            if 'mun_code' in df_equivalencias.columns: # This is the 5-digit INE
                 df_equivalencias.rename(columns={'mun_code': 'ine_code'}, inplace=True)
            df_equivalencias['ine_code'] = df_equivalencias['ine_code'].str.zfill(5)
            if 'CPRO' in df_equivalencias.columns and 'CMUN' in df_equivalencias.columns:
                df_equivalencias['mun_code_short_equiv'] = df_equivalencias['CPRO'].astype(int).astype(str) + \
                                                           df_equivalencias['CMUN'].astype(str).str.zfill(3)
            else:
                raise ValueError("CPRO or CMUN missing in equivalencias for mun_code_short_equiv creation.")
            
            idhm_map = pd.merge(df_equivalencias[['ine_code', 'mun_code_short_equiv']],
                                idhm_spanish[['mun_code_short', 'idhm', 'year']],
                                left_on='mun_code_short_equiv', right_on='mun_code_short', how='left')
            idhm_map = idhm_map.set_index('ine_code')
            
            self.df_equivalencias = df_equivalencias # Store for use in self.qual

        except Exception as e:
            logger.error(f"Error loading or processing Spanish IDHM/Equivalencias data: {e}. Using default index=1 for regions.")
            idhm_map = pd.DataFrame(columns=['idhm']) # Empty df to avoid errors, regions will get default index

        regions = {}
        for item in self.shapes: # self.shapes should come from prepare_shapes, items should have .id as 5-digit INE
            # Assuming 'item' has 'id' as 5-digit INE code and 'geometry'
            # Also, Region class expects 'NAME' or 'NOMBRE' if available in 'item'
            region_ine_code = str(item.id).zfill(5)
            
            initial_index = 1 # Default QLI
            if region_ine_code in idhm_map.index:
                idhm_selected = idhm_map.loc[region_ine_code, 'idhm']
                if isinstance(idhm_selected, pd.Series):
                    # If multiple matches (e.g. due to merge issues, though unlikely for a specific year)
                    idhm_val = idhm_selected.iloc[0] 
                else: # Scalar value
                    idhm_val = idhm_selected
                
                if pd.notna(idhm_val):
                    initial_index = float(idhm_val)
            
            # Pass the 'item' itself to Region constructor, which expects geometry and id, and optionally NAME/NOMBRE
            r = Region(item, index=initial_index) 
            regions[r.id] = r # r.id should be the 5-digit INE from item.id
        return regions

    def create_all(self, regions):
        """Based on regions and population data,
        create agents, families, houses, and firms"""
        my_agents = {}
        my_families = {}
        my_houses = {}
        my_firms = {}

        # Load Spanish average number of family members (this is CCAA level)
        # Original: input/average_num_members_families_2010.csv (AREAP based)
        # Spanish: ETL/tamaño_medio_hogares_ccaa/data_final/tamaño_medio_hogares_ccaa.csv
        # This needs careful handling as Spanish data is CCAA, not municipal/AP.
        # For now, we might use a national average or a default from params.
        # Or, map region_id (municipal) to CCAA to get specific avg_num_fam.
        
        # Placeholder for avg_num_fam logic:
        # For simplicity in this step, we'll rely on MEMBERS_PER_FAMILY from params.
        # A more detailed implementation would load CCAA data and map mun_code to CCAA.
        # avg_num_fam_path = os.path.join(ETL_DATA_PATH, "tamaño_medio_hogares_ccaa/data_final/tamaño_medio_hogares_ccaa.csv")
        # df_avg_fam_ccaa = pd.read_csv(avg_num_fam_path) # Needs processing for the current year and mapping

        for region_id, region in regions.items(): # region_id is 5-digit INE
            logger.info('Generating region {}'.format(region_id))

            regional_agents = self.create_agents(region) # region.id is 5-digit INE
            for agent in regional_agents.keys():
                my_agents[agent] = regional_agents[agent]

            num_agents = len(regional_agents)
            
            current_members_per_family = self.sim.PARAMS['MEMBERS_PER_FAMILY'] # Default
            region_id_str = str(region.id).zfill(5)
            ccaa_code = self.df_equivalencias_map_ine_to_ccaa.get(region_id_str) # Map is ine_code -> CODAUTO_cleaned (2-digit CCAA)
            current_year = self.sim.clock.year

            if ccaa_code and not self.avg_household_size_data.empty:
                try:
                    avg_size = self.avg_household_size_data.get((ccaa_code, current_year))
                    if pd.notna(avg_size) and avg_size > 0:
                        current_members_per_family = avg_size
                        logger.info(f"Using CCAA {ccaa_code} specific household size for year {current_year}: {avg_size:.2f} for region {region_id_str}")
                    else:
                        logger.warning(f"Avg household size for CCAA {ccaa_code}, year {current_year} not found or invalid in predicted data. Using default: {current_members_per_family}")
                except KeyError: # If (ccaa_code, current_year) tuple not in MultiIndex
                    logger.warning(f"Avg household size for CCAA {ccaa_code}, year {current_year} not found in predicted data index. Using default: {current_members_per_family}")
            else:
                if not ccaa_code:
                    logger.warning(f"CCAA code for region {region_id_str} not found in equivalencias map. Using default household size: {current_members_per_family}")
                # If self.avg_household_size_data is empty, already logged in __init__

            if current_members_per_family <= 0: # Safeguard against zero or negative
                logger.error(f"Invalid current_members_per_family ({current_members_per_family}) for region {region_id_str}. Using default: {self.sim.PARAMS['MEMBERS_PER_FAMILY']}")
                current_members_per_family = self.sim.PARAMS['MEMBERS_PER_FAMILY']
                
            num_families = 0
            if num_agents > 0 : # Avoid division by zero if no agents
                 num_families = int(num_agents / current_members_per_family)
            
            if num_families == 0 and num_agents > 0 : # Ensure at least one family if there are agents
                num_families = 1
                logger.info(f"Adjusted num_families to 1 for region {region_id_str} as num_agents ({num_agents}) > 0 but calculated num_families was 0 with household size {current_members_per_family:.2f}")


            num_houses = int(num_families * (1 + self.sim.PARAMS['HOUSE_VACANCY']))
            
            # Firm data needs to be adapted to use municipal codes
            # self.firm_data.num_emp_t0 is indexed by AP in original. Needs to be indexed by mun_code.
            # Assuming self.firm_data is adapted to handle 5-digit INE codes.
            try:
                num_firms_for_region = self.firm_data.num_emp_t0.get(int(region.id), 0) # Use .get for safety
            except AttributeError: # If firm_data or num_emp_t0 is not set up as expected
                 logger.warning(f"FirmData or num_emp_t0 not properly initialized. Defaulting num_firms to 0 for region {region.id}")
                 num_firms_for_region = 0

            num_firms = int(num_firms_for_region * self.sim.PARAMS['PERCENTAGE_ACTUAL_POP'])


            regional_families = self.create_families(num_families)
            regional_houses = self.create_houses(num_houses, region)
            regional_firms = self.create_firms(num_firms, region)

            regional_agents, regional_families = self.allocate_to_family(regional_agents, regional_families)

            # Allocating only percentage of houses to ownership.
            owners_size = int((1 - self.sim.PARAMS['RENTAL_SHARE']) * len(regional_houses))

            # Do not allocate all houses to families. Some families (parameter) will have to rent
            regional_families.update(self.allocate_to_households(dict(list(regional_families.items())[:owners_size]),
                                                                 dict(list(regional_houses.items())[:owners_size])))

            # Set ownership of remaining houses for random families
            self.randomly_assign_houses(regional_houses.values(), regional_families.values())

            # Check families that still do not rent house.
            # Run the first Rental Market
            renting = [f for f in regional_families.values() if f.house is None]
            to_rent = [h for h in regional_houses.values() if h.family_id is None]
            self.sim.housing.rental.rental_market(renting, self.sim, to_rent)

            # Saving on almighty dictionary of families
            for family in regional_families.keys():
                my_families[family] = regional_families[family]

            for house in regional_houses.keys():
                my_houses[house] = regional_houses[house]

            for firm in regional_firms.keys():
                my_firms[firm] = regional_firms[firm]

            try:
                assert len([h for h in regional_houses.values() if h.owner_id is None]) == 0
            except AssertionError:
                print('Houses without ownership')

        return my_agents, my_houses, my_families, my_firms

    def create_agents(self, region):
        agents = {}
        pops = self.sim.pops # This is the output of simplify_pops if SIMPLIFY_POP_EVOLUTION is True
        # Its columns are 'code', '6', '12', '17', ... (strings, upper bounds of new age groups)
        
        pop_cols_str = list(list(pops.values())[0].columns) # e.g. ['code', '6', '12', ...]
        
        # These are the upper bounds of the simplified age groups, converted to int for calculations
        simplified_age_group_uppers_int = [int(c) for c in pop_cols_str if c != 'code']
        
        # list_of_possible_ages for randint needs to be [0, 6, 12, 17, ...] (integers)
        list_of_possible_ages_int = [0] + sorted(simplified_age_group_uppers_int)

        # loop_age_control iterates through the upper bounds (as integers) of the simplified groups
        loop_age_control_int = sorted(simplified_age_group_uppers_int)


        for age_upper_bound_int in loop_age_control_int: # age_upper_bound_int is e.g. 6, 12, 17 (int)
            # Determine the lower bound for randint (exclusive for 0, inclusive otherwise)
            idx = list_of_possible_ages_int.index(age_upper_bound_int)
            lower_bound_for_randint_exclusive = list_of_possible_ages_int[idx - 1]
            
            start_age_for_rand = lower_bound_for_randint_exclusive + 1
            if lower_bound_for_randint_exclusive == 0: # Special handling for the first group (e.g. 0-6)
                 start_age_for_rand = 0


            for gender in ['male', 'female']:
                code = region.id # 5-digit INE string
                # When calling pop_age_data, the 'age' parameter must match a column name in pops[gender]
                # Columns are strings: '6', '12', etc.
                age_col_name_for_pop_data = str(age_upper_bound_int)
                
                pop = pop_age_data(pops[gender], code, age_col_name_for_pop_data, self.sim.PARAMS['PERCENTAGE_ACTUAL_POP'])
                if pop > 0: # Add logging for significant agent creation loops
                    logger.debug(f"Region {code}, Gender {gender}, AgeGroupCol {age_col_name_for_pop_data}: Creating {pop} agents.")
                for individual in range(pop):
                    qualification = self.qual(code)
                    # Generate random age within the [start_age_for_rand, age_upper_bound_int] bucket
                    r_age = self.seed.randint(start_age_for_rand, age_upper_bound_int)
                    money = self.seed.randrange(1, 34)
                    month = self.seed.randrange(1, 13, 1)
                    agent_id = self.gen_id()
                    a = Agent(agent_id, gender, r_age, qualification, money, month)
                    agents[agent_id] = a
        logger.info(f"Finished creating {len(agents)} agents for region {region.id}.")
        return agents

    def create_random_agents(self, n_agents):
        """Create random agents by sampling the existing
        agent population and creating clones of the sampled agents"""
        new_agents = {}
        sample = self.seed.sample(list(self.sim.agents.values()), n_agents)
        for a in sample:
            agent_id = self.gen_id()
            money = self.seed.randrange(1, 34)
            new_agent = Agent(agent_id, a.gender, a.age, a.qualification, money, a.month)
            new_agents[agent_id] = new_agent
        return new_agents

    def create_families(self, num_families):
        community = {}
        for _ in range(num_families):
            family_id = self.gen_id()
            community[family_id] = Family(family_id)
        return community

    def allocate_to_family(self, agents, families):
        """Allocate agents to families"""
        agents = list(agents.values())
        self.seed.shuffle(agents)
        fams = list(families.values())
        # Separate adults to make sure all families have at least one adult
        adults = [a for a in agents if a.age > 21]
        chd = [a for a in agents if a not in adults]
        # Assume there are more adults than families
        # First, distribute adults as equally as possible
        for i in range(len(adults)):
            if not adults[i].belongs_to_family:
                fams[i % len(fams)].add_agent(adults[i])

        # Allocate children into random families
        for agent in chd:
            family = self.seed.choice(fams)
            if not agent.belongs_to_family:
                family.add_agent(agent)
        return agents, families

    # Address within the region
    # Additional details so that address fall in urban areas, given percentage
    def get_random_point_in_polygon(self, region, urban=True):
        logger.debug(f"Attempting get_random_point_in_polygon for region {region.id}, urban={urban} using triangulate method.")
        
        target_geom = None
        geom_type_used = "unknown"

        if urban:
            mun_code = str(region.id).zfill(5) # region.id is 5-digit INE
            if mun_code in self.urban and self.urban[mun_code] is not None and not self.urban[mun_code].is_empty:
                target_geom = self.urban[mun_code]
                geom_type_used = "urban"
                # logger.debug(f"  Using urban geometry for region {mun_code}. Area: {target_geom.area:.6f}") # Less verbose
            else:
                logger.warning(f"Urban geometry for mun_code {mun_code} (region {region.id}) not found or empty. Falling back to full region polygon for address.")
                target_geom = region.addresses
                geom_type_used = "full_region (urban fallback)"
        else: # Rural
            target_geom = region.addresses
            geom_type_used = "full_region (rural)"

        if target_geom is None or target_geom.is_empty:
            logger.error(f"Target geometry for region {region.id} (urban={urban}, type={geom_type_used}) is None or empty. Cannot place point. Returning region centroid.")
            return region.addresses.centroid
        
        # Ensure the geometry is valid for triangulation
        if not target_geom.is_valid:
            logger.warning(f"Target geometry for region {region.id} (type={geom_type_used}) is invalid. Attempting to buffer by 0 to fix.")
            target_geom = target_geom.buffer(0)
            if not target_geom.is_valid or target_geom.is_empty:
                logger.error(f"Failed to fix invalid geometry for region {region.id} after buffer(0). Returning centroid.")
                return target_geom.centroid if not target_geom.is_empty else region.addresses.centroid


        try:
            logger.debug(f"Antes de triangulate para region {region.id} (type={geom_type_used}).")
            tris = triangulate(target_geom)
            logger.debug(f"Después de triangulate: {len(tris)} triángulos generados para region {region.id} (type={geom_type_used}).")
            if not tris:
                logger.warning(f"Triangulation of target_geom for region {region.id} (type={geom_type_used}) resulted in no triangles. Area: {target_geom.area:.6f}. Geom type: {target_geom.geom_type}. Returning centroid.")
                return target_geom.centroid

            areas = [t.area for t in tris]
            logger.debug(f"Áreas de triángulos calculadas para region {region.id}: {areas[:10]}... (total {len(areas)})")

            valid_tris_areas = [(t, a) for t, a in zip(tris, areas) if a > 0]
            logger.debug(f"Triángulos con área positiva: {len(valid_tris_areas)} para region {region.id}.")

            if not valid_tris_areas:
                logger.warning(f"No triangles with positive area after triangulation for region {region.id} (type={geom_type_used}). Returning centroid.")
                return target_geom.centroid

            tris, areas = zip(*valid_tris_areas)
            cum_areas = np.cumsum(areas)
            logger.debug(f"Cumulative areas: {cum_areas[:10]}... (total {len(cum_areas)}) para region {region.id}.")

            if cum_areas[-1] == 0:
                logger.warning(f"Total area of triangulated parts is zero for region {region.id} (type={geom_type_used}). Returning centroid.")
                return target_geom.centroid

            r = self.seed.random() * cum_areas[-1]
            logger.debug(f"Valor aleatorio para muestreo: {r} de {cum_areas[-1]} para region {region.id}.")

            for idx, (t, ca) in enumerate(zip(tris, cum_areas)):
                if r <= ca:
                    logger.debug(f"Seleccionado triángulo {idx} para region {region.id}.")
                    if len(t.exterior.coords) < 3:
                        logger.warning(f"Triangle has less than 3 coordinates for region {region.id}. Coords: {list(t.exterior.coords)}. Skipping this triangle.")
                        continue
                    a, b, c = t.exterior.coords[:3]
                    r1, r2 = self.seed.random(), self.seed.random()
                    sqrt_r1 = math.sqrt(r1)
                    x = (1 - sqrt_r1) * a[0] + sqrt_r1 * (1 - r2) * b[0] + sqrt_r1 * r2 * c[0]
                    y = (1 - sqrt_r1) * a[1] + sqrt_r1 * (1 - r2) * b[1] + sqrt_r1 * r2 * c[1]
                    logger.debug(f"Punto generado en triángulo {idx} para region {region.id}: ({x}, {y})")
                    return shapely.geometry.Point(x, y)

            logger.warning(f"Triangulation sampling loop completed without returning a point for region {region.id} (type={geom_type_used}). This is unexpected. Returning centroid.")
            return target_geom.centroid

        except Exception as e:
            logger.error(f"Error during triangulation or point generation for region {region.id} (type={geom_type_used}): {e}. Returning centroid.")
            return target_geom.centroid

    def create_houses(self, num_houses, region):
        """Create houses for a region"""
        neighborhood = {}
        probability_urban = self.prob_urban(region)
        logger.info(f"Creating {num_houses} houses for region {region.id} (Prob Urban: {probability_urban:.2f}).")
        for i in range(num_houses):
            # Log progress for large numbers and each house creation
            if i % 100 == 0 and i > 0:
                logger.debug(f"  Created {i}/{num_houses} houses for region {region.id}...")
            logger.debug(f"    Creating house {i+1}/{num_houses} for region {region.id}...")
            address = self.random_address(region, probability_urban)
            size = self.seed.randrange(20, 120)
            # Price is given by 4 quality levels
            quality = self.seed.choice([1, 2, 3, 4])
            price = size * quality * region.index
            house_id = self.gen_id()
            h = House(house_id, address, size, price, region.id, quality)
            neighborhood[house_id] = h
        return neighborhood

    def prob_urban(self, region):
        # Adapted for Spanish data: prop_urban is now indexed by 5-digit INE 'cod_mun' (string)
        # The single_ap_muns logic is removed as APs are not used.
        # We directly use the prop_urban for the given municipality.
        mun_code_str = str(region.id).zfill(5) # region.id is 5-digit INE
        year_str = str(self.sim.geo.year)
        
        try:
            # Filter prop_urban for the specific municipality and year
            # Ensure prop_urban['cod_mun'] is string for matching
            
            # Check if year_str is a column in prop_urban, if not, find closest or default
            # For simplicity, this example assumes year_str matches a column in the Spanish prop_urban data
            # The Spanish prop_urban was loaded with 'year' as a column, not years as columns.
            # So, we need to filter by year column.
            
            # The global prop_urban was reshaped to have 'cod_mun', 'year', 'prop_urban'
            # prop_urban['cod_mun'] is already string zfilled
            
            # Ensure year is int for comparison with 'year' column in prop_urban
            current_year_int = int(self.sim.geo.year)

            # Filter for the municipality and year
            # prop_urban_region_year = prop_urban[
            #     (prop_urban['cod_mun'] == mun_code_str) & (prop_urban['year'] == current_year_int)
            # ]
            # Temporary fix: prop_urban has years as columns in original, Spanish data has 'year' column.
            # The loaded prop_urban has 'cod_mun', 'year', 'prop_urban'
            # The original logic was: prop_urban[prop_urban['cod_mun'] == int(mun_code)][str(self.sim.geo.year)].iloc[0]
            # This implies prop_urban was indexed by cod_mun and had years as columns.
            # Our new prop_urban is a long format.
            
            # Let's assume the global `prop_urban` is now correctly formatted with 'cod_mun', 'year', 'prop_urban'
            # And 'cod_mun' is string, 'year' is int.
            
            # Find the row for the current municipality and year
            # Convert self.sim.geo.year to int for matching if 'year' column in prop_urban is int
            year_to_match = int(self.sim.geo.year)
            
            # Ensure 'cod_mun' in prop_urban is string and padded
            # prop_urban['cod_mun'] = prop_urban['cod_mun'].astype(str).str.zfill(5) # Done at load time
            prop_urban['year'] = prop_urban['year'].astype(int)


            specific_prop = prop_urban[
                (prop_urban['cod_mun'] == mun_code_str) & (prop_urban['year'] == year_to_match)
            ]

            if not specific_prop.empty:
                probability = specific_prop['prop_urban'].iloc[0]
                # Ensure probability is between 0 and 1 (it might be percentage)
                if probability > 1: # Assuming it might be 0-100 scale
                    probability = probability / 100.0
                return probability
            else:
                # Fallback if no specific data for that mun_code and year
                logger.warning(f"No prop_urban data for mun_code {mun_code_str} and year {year_to_match}. Defaulting to 0.5.")
                return 0.5 # Default or average probability
        except KeyError:
            logger.warning(f"KeyError for prop_urban for mun_code {mun_code_str}, year {year_str}. Defaulting to 0.5.")
            return 0.5 # Default if year column not found or other key error
        except Exception as e:
            logger.error(f"Error in prob_urban for {mun_code_str}, {year_str}: {e}. Defaulting to 0.5.")
            return 0.5

    def random_address(self, region, prob_urban):
        urban = self.seed.random() < prob_urban
        return self.get_random_point_in_polygon(region, urban=urban)

    def allocate_to_households(self, families, households):
        """Allocate houses to families"""
        unclaimed = list(households)
        self.seed.shuffle(unclaimed)
        house_id = None
        while unclaimed:
            for family in families.values():
                if house_id is None:
                    try:
                        house_id = unclaimed.pop(0)
                    except IndexError:
                        break
                house = households[house_id]
                if not house.is_occupied:
                    family.move_in(house)
                    house.owner_id = family.id
                    family.owned_houses.append(house)
                    house_id = None
        assert len(unclaimed) == 0
        return families

    def randomly_assign_houses(self, houses, families):
        families = list(families)
        houses = [h for h in houses if h.owner_id is None]
        for house in houses:
            family = self.seed.choice(families)
            house.owner_id = family.id
            family.owned_houses.append(house)

    def create_firms(self, num_firms, region):
        sector = {}
        num_construction_firms = math.ceil(num_firms * self.sim.PARAMS['PERCENT_CONSTRUCTION_FIRMS'])
        logger.info(f"Creating {num_firms} firms for region {region.id} ({num_construction_firms} construction).")
        for i in range(num_firms):
            # Log progress for large numbers and each firm creation
            if i % 50 == 0 and i > 0:
                logger.debug(f"  Created {i}/{num_firms} firms for region {region.id}...")
            logger.debug(f"    Creating firm {i+1}/{num_firms} for region {region.id}...")
            address = self.get_random_point_in_polygon(region)
            total_balance = self.seed.betavariate(1.5, 10) * 10000
            firm_id = self.gen_id()
            if i < num_construction_firms:
                f = ConstructionFirm(firm_id, address, total_balance, region.id)
            else:
                f = Firm(firm_id, address, total_balance, region.id)
            sector[f.id] = f
        return sector

    def load_quali(self):
        logger.info("Starting Spanish qualification data loading process...")
        sim_year = self.sim.geo.year # e.g., 2010
        base_path = os.path.join(ETL_DATA_PATH, "nivel_educativo_comunidades/data_final")
        
        target_filename = f"nivel_educativo_comunidades_{sim_year}.csv"
        quali_path = os.path.join(base_path, target_filename)
        
        file_to_load_path = None
        actual_year_loaded = None

        if os.path.exists(quali_path):
            file_to_load_path = quali_path
            actual_year_loaded = sim_year
            logger.info(f"Found qualification data for simulation year {sim_year}: {quali_path}")
        else:
            logger.warning(f"Qualification data for simulation year {sim_year} not found at {quali_path}. Attempting fallback.")
            try:
                available_files = [f for f in os.listdir(base_path) if f.startswith("nivel_educativo_comunidades_") and f.endswith(".csv")]
                available_years = []
                for f_name in available_files:
                    try:
                        year_str = f_name.replace("nivel_educativo_comunidades_", "").replace(".csv", "")
                        if year_str.isdigit():
                            available_years.append(int(year_str))
                    except:
                        continue 

                if not available_years:
                    logger.error("No qualification data files found in directory for fallback.")
                    return pd.DataFrame()

                prior_years = sorted([yr for yr in available_years if yr <= sim_year], reverse=True)
                future_years = sorted([yr for yr in available_years if yr > sim_year])

                if prior_years:
                    actual_year_loaded = prior_years[0]
                elif future_years: # If no prior year, use earliest future year as last resort
                    actual_year_loaded = future_years[0]
                
                if actual_year_loaded:
                    fallback_filename = f"nivel_educativo_comunidades_{actual_year_loaded}.csv"
                    file_to_load_path = os.path.join(base_path, fallback_filename)
                    logger.info(f"Using fallback qualification data from year {actual_year_loaded}: {file_to_load_path}")
                else:
                    logger.error("No suitable fallback qualification data file found.")
                    return pd.DataFrame()
            except Exception as e_fallback:
                 logger.error(f"Error during fallback search for qualification data: {e_fallback}")
                 return pd.DataFrame()

        try:
            df_quali_raw = pd.read_csv(file_to_load_path, dtype={'ccaa_code': str})
            # Ensure ccaa_code is string and padded if necessary, e.g. '1' -> '01'
            df_quali_raw['ccaa_code'] = df_quali_raw['ccaa_code'].astype(str).str.zfill(2)
            df_quali_raw.set_index('ccaa_code', inplace=True)
            
            # Rename columns like '1.0' to '1', etc.
            rename_map = {col: str(col).split('.')[0] for col in df_quali_raw.columns}
            df_quali_renamed = df_quali_raw.rename(columns=rename_map)
            
            # Expected levels based on file structure '1', '2', '3', '5', '6', '7' (level '4' is missing)
            # These are the column names after renaming.
            level_cols_present = [col for col in ['1','2','3','5','6','7'] if col in df_quali_renamed.columns]
            df_quali_levels = df_quali_renamed[level_cols_present]

            # Convert to proportions (divide by 100, assuming values are percentages)
            df_proportions = df_quali_levels / 100.0
            
            # Calculate cumulative proportions
            # Sort columns by their numeric interpretation for correct cumulative sum.
            sorted_level_cols = sorted(df_proportions.columns, key=lambda x: int(x))
            df_cumulative_proportions = df_proportions[sorted_level_cols].cumsum(axis=1)
            
            # Ensure the last column of cumulative probabilities is 1.0 or very close.
            # If not, it might indicate issues with source data (percentages not summing to 100).
            # For robustness, can cap last column at 1.0 if slightly off due to float precision.
            if not df_cumulative_proportions.empty:
                 last_col_name = df_cumulative_proportions.columns[-1]
                 # Cap at 1.0, also handle cases where sum might be slightly > 1.0 due to rounding
                 # df_cumulative_proportions[last_col_name] = df_cumulative_proportions[last_col_name].clip(upper=1.0)
                 # Ensure it's exactly 1.0 for the last valid level.
                 df_cumulative_proportions[last_col_name] = 1.0


            logger.info(f"Successfully loaded and processed qualification data from year {actual_year_loaded}.")
            return df_cumulative_proportions
            
        except Exception as e:
            logger.error(f"Error processing qualification data file {file_to_load_path}: {e}. Qualification will be default.")
            return pd.DataFrame()

    def qual(self, region_id_ine5): # region_id_ine5 is the 5-digit INE code
        if self.quali.empty:
            logger.warning(f"Qualification data (self.quali) is empty. Returning default qualification 3.")
            return 3

        # Create INE to CCAA mapping if not already created
        if not self.df_equivalencias_map_ine_to_ccaa:
            if hasattr(self, 'df_equivalencias') and not self.df_equivalencias.empty and \
               'ine_code' in self.df_equivalencias.columns and 'CODAUTO' in self.df_equivalencias.columns:
                
                # Ensure CODAUTO is cleaned (e.g. '01', '02', ... '19')
                # The CCAA codes in nivel_educativo files are '01', '02', etc.
                self.df_equivalencias['CODAUTO_cleaned'] = self.df_equivalencias['CODAUTO'].astype(str).str.split('.').str[0].str.zfill(2)
                temp_map_df = self.df_equivalencias.drop_duplicates(subset=['ine_code'])
                self.df_equivalencias_map_ine_to_ccaa = temp_map_df.set_index('ine_code')['CODAUTO_cleaned'].to_dict()
            else:
                logger.error("Equivalencias data for INE to CCAA mapping not available or incomplete in Generator. Cannot determine CCAA for qualification. Defaulting to 3.")
                return 3
        
        ccaa_code_str = self.df_equivalencias_map_ine_to_ccaa.get(str(region_id_ine5).zfill(5))

        if not ccaa_code_str:
            logger.warning(f"CCAA code not found for region {region_id_ine5} in equivalencias map. Returning default qualification 3.")
            return 3
        
        if ccaa_code_str not in self.quali.index:
            logger.warning(f"CCAA code {ccaa_code_str} (from region {region_id_ine5}) not found in self.quali index. Available CCAA codes in quali data: {self.quali.index.tolist()}. Returning default 3.")
            return 3

        try:
            # self.quali contains cumulative probabilities, columns are '1', '2', '3', '5', '6', '7'
            # Generate a random number for selection
            random_draw = self.seed.random()
            cumulative_probs_series = self.quali.loc[ccaa_code_str]
            
            chosen_level_str = None
            # Iterate through sorted columns ('1', '2', '3', '5', '6', '7')
            for level_str in cumulative_probs_series.index: 
                if random_draw <= cumulative_probs_series[level_str]:
                    chosen_level_str = level_str
                    break
            
            if chosen_level_str is None: # Should not happen if last cum_prob is 1.0
                logger.warning(f"Could not determine qualification level for CCAA {ccaa_code_str}, random draw {random_draw}. Probs: {cumulative_probs_series.to_dict()}. Defaulting to lowest level '1'.")
                chosen_level_str = cumulative_probs_series.index[0] # Default to the lowest available level

            # Map chosen_level_str ('1', '2', '3', '5', '6', '7') to what years_study expects ('1'-'5')
            level_for_years_study = chosen_level_str
            if chosen_level_str in ['5', '6', '7']: # Higher education levels
                level_for_years_study = '5' # Map to highest category in years_study
            elif chosen_level_str == '4': # Level '4' is missing in data, but present in years_study
                 logger.warning(f"Level '4' chosen but missing in data, mapping to '3' for years_study for CCAA {ccaa_code_str}")
                 level_for_years_study = '3' # Or '5', depending on interpretation
            elif chosen_level_str not in self.years_study_parameters:
                 logger.warning(f"Chosen qualification level '{chosen_level_str}' not in years_study mapping for CCAA {ccaa_code_str}. Defaulting to level '3' for years_study.")
                 level_for_years_study = '3' 

            return int(self.years_study(level_for_years_study))
            
        except Exception as e:
            logger.error(f"Error in self.qual for CCAA {ccaa_code_str} (region {region_id_ine5}): {e}. Returning default 3.")
            return 3
