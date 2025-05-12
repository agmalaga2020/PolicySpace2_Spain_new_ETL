import datetime
from collections import defaultdict

import pandas as pd
import numpy as np
import os # Added import os

from markets.housing import HousingMarket
from .geography import STATES_CODES, state_string # Assuming these are adapted for Spain (e.g., CPRO/CCAA)

# Define base paths consistently
SCRIPT_DIR_FUNDS = os.path.dirname(os.path.realpath(__file__)) # world/
PROJECT_ROOT_FUNDS = os.path.join(SCRIPT_DIR_FUNDS, "..") # Navigate up to project root
ETL_DATA_PATH_FUNDS = os.path.join(PROJECT_ROOT_FUNDS, "ETL") 


class Funds:
    def __init__(self, sim):
        self.sim = sim
        self.families_subsided = 0
        self.money_applied_policy = 0
        self.pie_data = None # Initialize pie_data attribute

        # Use PIE_DISTRIBUTION if defined, otherwise fallback to FPM_DISTRIBUTION for compatibility
        pie_param_key = 'PIE_DISTRIBUTION' if 'PIE_DISTRIBUTION' in sim.PARAMS else 'FPM_DISTRIBUTION'

        if sim.PARAMS.get(pie_param_key, False): # Check if the parameter exists and is True
            try:
                pie_path = os.path.join(ETL_DATA_PATH_FUNDS, "PIE/data/raw/finanzas/liquidaciones/preprocess/pie_final_final.csv")
                self.pie_data = pd.read_csv(pie_path, sep=',', dtype={'codigo_provincia': str, 'codigo_municipio': str, 'año': str, 'mun_code': str})
                
                # mun_code is now expected to be in pie_final_final.csv directly from ETL/PIE/procesar_pie.py
                # So, the manual creation of mun_code_pie can be removed.
                # Ensure 'mun_code' column exists, if not, log error or fallback (though it should exist now)
                if 'mun_code' not in self.pie_data.columns:
                    print(f"ERROR: 'mun_code' column not found in PIE data file: {pie_path}. PIE distribution might fail or be incorrect.")
                    # As a fallback, try to create it, but this indicates an issue with procesar_pie.py not running or failing.
                    if 'codigo_provincia' in self.pie_data.columns and 'codigo_municipio' in self.pie_data.columns:
                        print("Attempting to create 'mun_code' on the fly as a fallback...")
                        self.pie_data['codigo_provincia'] = self.pie_data['codigo_provincia'].astype(str)
                        self.pie_data['codigo_municipio'] = self.pie_data['codigo_municipio'].astype(str)
                        self.pie_data['codigo_provincia_fmt'] = self.pie_data['codigo_provincia'].str.split('.').str[0].str.zfill(2)
                        self.pie_data['codigo_municipio_fmt'] = self.pie_data['codigo_municipio'].str.split('.').str[0].str.zfill(3)
                        self.pie_data['mun_code'] = self.pie_data['codigo_provincia_fmt'] + self.pie_data['codigo_municipio_fmt']
                        print("Fallback 'mun_code' created. Please ensure ETL/PIE/procesar_pie.py ran correctly.")
                    else:
                        # Cannot create mun_code, PIE will likely fail.
                        pass # Let it proceed, errors will occur downstream if mun_code is essential and missing.
                else:
                    # Ensure mun_code is string and padded correctly if loaded from CSV, though procesar_pie.py should handle this.
                    self.pie_data['mun_code'] = self.pie_data['mun_code'].astype(str).str.zfill(5)


                # Convert 'año' to int and 'total_participacion_variables' to float
                self.pie_data['año'] = pd.to_numeric(self.pie_data['año'], errors='coerce')
                self.pie_data['total_participacion_variables'] = pd.to_numeric(self.pie_data['total_participacion_variables'], errors='coerce')
                
                # Set index for easier lookup if needed later, though distribute_pie might not need it if filtering directly
                # self.pie_data.set_index(['mun_code_pie', 'año'], inplace=True)
                print(f"Successfully loaded and processed Spanish PIE data from {pie_path}")
            except FileNotFoundError:
                print(f"ERROR: Spanish PIE data file not found at {pie_path}. PIE distribution will not work.")
                self.pie_data = pd.DataFrame() # Empty DataFrame
            except Exception as e:
                print(f"ERROR: Could not load or process Spanish PIE data: {e}")
                self.pie_data = pd.DataFrame()
        
        if sim.PARAMS['POLICY_COEFFICIENT']:
            # Gather the money by municipality. Later gather the families and act upon policy!
            self.policy_money = defaultdict(float)
            self.policy_families = defaultdict(list)
            self.temporary_houses = defaultdict(list)

    def update_policy_families(self):
        # Entering the list this month
        incomes = [f.get_permanent_income() for f in self.sim.families.values()]
        quantile = np.quantile(incomes, self.sim.PARAMS['POLICY_QUANTILE'])
        for region in self.sim.regions.values():
            # Unemployed, Default on rent from the region
            self.sim.regions[region.id].registry[self.sim.clock.days] += [f for f in self.sim.families.values()
                                                                          if f.get_permanent_income() < quantile
                                                                          and f.house.region_id == region.id]
        if self.sim.clock.days < self.sim.PARAMS['STARTING_DAY'] + datetime.timedelta(360):
            return
        # Entering the policy list. Includes families for past months as well
        for region in self.sim.regions.values():
            for keys in region.registry:
                if keys > self.sim.clock.days - datetime.timedelta(self.sim.PARAMS['POLICY_DAYS']):
                    self.policy_families[region.id[:7]] += region.registry[keys]
        for mun in self.policy_families.keys():
            # Make sure families on the list are still valid families, residing at the municipality
            self.policy_families[mun] = [f for f in self.policy_families[mun]
                                         if f.id in self.sim.families.keys() and f.house.region_id[:7] == mun]
            self.policy_families[mun] = list(set(f for f in self.policy_families[mun]))
            self.policy_families[mun] = sorted(self.policy_families[mun], key=lambda f: f.get_permanent_income())

    def apply_policies(self):
        if self.sim.PARAMS['POLICIES'] not in ['buy', 'rent', 'wage']:
            # Baseline scenario. Do nothing!
            return
        # Reset indicator every month to reflect subside in a given month, not cumulatively
        self.families_subsided = 0
        self.update_policy_families()
        # Implement policies only after first year of simulation run
        if self.sim.clock.days < self.sim.PARAMS['STARTING_DAY'] + datetime.timedelta(360):
            return
        if self.sim.PARAMS['POLICIES'] == 'buy':
            self.buy_houses_give_to_families()
        elif self.sim.PARAMS['POLICIES'] == 'rent':
            self.pay_families_rent()
        else:
            self.distribute_funds_to_families()
        # Resetting lists for next month
        self.policy_families = defaultdict(list)
        self.temporary_houses = defaultdict(list)

    def pay_families_rent(self):
        for mun in self.policy_money.keys():
            self.policy_families[mun] = [f for f in self.policy_families[mun] if not f.owned_houses]
            for family in self.policy_families[mun]:
                if family.house.rent_data:
                    if self.policy_money[mun] > 0 and family.house.rent_data[0] * 24 < self.policy_money[mun]:
                        if not family.rent_voucher:
                            # Paying rent for a given number of months, independent of rent value.
                            family.rent_voucher = 24
                            self.policy_money[mun] -= family.house.rent_data[0] * 24
                            self.money_applied_policy += family.house.rent_data[0] * 24
                            self.families_subsided += 1

    def distribute_funds_to_families(self):
        for mun in self.policy_money.keys():
            if self.policy_families[mun] and self.policy_money[mun] > 0:
                # Registering subsidies
                self.money_applied_policy += self.policy_money[mun]
                self.families_subsided += len(self.policy_families[mun])
                # Amount is proportional to available funding and families
                amount = self.policy_money[mun] / len(self.policy_families[mun])
                [f.update_balance(amount) for f in self.policy_families[mun]]
                # Reset fund because it has been totally expended.
                self.policy_money[mun] = 0

    def buy_houses_give_to_families(self):
        # Families are sorted in self.policy_families. Buy and give as much as money allows
        for mun in self.policy_money.keys():
            for firm in self.sim.firms.values():
                if firm.type == 'CONSTRUCTION':
                    # Get the list of the houses for sale within the municipality
                    self.temporary_houses[mun] += [h for h in firm.houses_for_sale if h.region_id[:7] == mun]
            # Sort houses and families by cheapest, poorest.
            # Considering # houses is limited, help as many as possible earlier.
            # Although families in sucession gets better and better houses. Then nothing.
            self.temporary_houses[mun] = sorted(self.temporary_houses[mun], key=lambda h: h.price)
            # Exclude families who own any house. Exclusively for renters
            self.policy_families[mun] = [f for f in self.policy_families[mun] if not f.owned_houses]
            if self.policy_families[mun]:
                for house in self.temporary_houses[mun]:
                    # While money is good.
                    if self.policy_money[mun] > 0 and self.policy_families[mun] \
                            and house.price < self.policy_money[mun]:
                        # Getting poorest family first, given permanent income
                        family = self.policy_families[mun].pop(0)
                        # Transaction taxes help reduce the price of the bulk buying by the municipality
                        taxes = house.price * self.sim.PARAMS['TAX_ESTATE_TRANSACTION']
                        self.sim.regions[house.region_id].collect_taxes(taxes, 'transaction')
                        # Register subsidies
                        self.money_applied_policy += house.price
                        self.families_subsided += 1
                        # Pay construction company
                        self.sim.firms[house.owner_id].update_balance(house.price - taxes,
                                                                      self.sim.PARAMS['CONSTRUCTION_ACC_CASH_FLOW'],
                                                                      self.sim.clock.days)
                        # Deduce from municipality fund
                        self.policy_money[mun] -= house.price
                        # Transfer ownership
                        self.sim.firms[house.owner_id].houses_for_sale.remove(house)
                        # Finish notarial procedures
                        house.owner_id = family.id
                        house.family_owner = True
                        family.owned_houses.append(house)
                        house.on_market = 0
                        # Move out. Move in
                        HousingMarket.make_move(family, house, self.sim)
                    else:
                        break

        # Clean up list for next month
        self.temporary_houses = defaultdict(list)

    def distribute_pie(self, value_to_distribute, regions, pop_t, pop_mun_t, year_int): # Renamed from distribute_fpm
        """Distribute PIE funds to municipalities.
        Value is the total value of PIE to distribute based on collected labor and firm taxes."""
        
        if self.pie_data is None or self.pie_data.empty:
            print("WARNING: PIE data not loaded. Cannot distribute PIE funds.")
            return

        # Filter PIE data for the given year
        # Ensure year_int is an integer for comparison
        current_year_pie_data = self.pie_data[self.pie_data['año'] == year_int]

        if current_year_pie_data.empty:
            print(f"WARNING: No PIE data available for year {year_int}. Cannot distribute PIE funds for this year.")
            # Fallback: could try to use data from the closest available year or a default distribution.
            # For now, we just return if no data for the specific year.
            # As a simple fallback, try the latest year available in PIE data if current year is not found
            if not self.pie_data.empty:
                latest_year_in_pie = self.pie_data['año'].max()
                if pd.notna(latest_year_in_pie):
                    print(f"INFO: Using PIE data from latest available year: {latest_year_in_pie} as fallback for year {year_int}.")
                    current_year_pie_data = self.pie_data[self.pie_data['año'] == latest_year_in_pie]
                else: # Should not happen if pie_data is not empty and 'año' is numeric
                    return 
            else: # pie_data is completely empty
                return


        # Calculate the sum of PIE for all relevant municipalities in the simulation for that year
        # This sum will be used to calculate proportions.
        # We only consider municipalities that are part of the current simulation (in self.sim.regions.keys())
        sim_mun_codes_ine5 = list(regions.keys()) # These are 5-digit INE codes
        
        # Filter PIE data for municipalities in the simulation using the new 'mun_code' column
        if 'mun_code' not in current_year_pie_data.columns:
            print(f"ERROR: 'mun_code' column is missing from PIE data for year {year_int}. Cannot filter for simulation municipalities.")
            relevant_pie_data = pd.DataFrame() # Empty DataFrame
        else:
            relevant_pie_data = current_year_pie_data[current_year_pie_data['mun_code'].isin(sim_mun_codes_ine5)]
        
        total_pie_for_sim_municipalities = relevant_pie_data['total_participacion_variables'].sum()

        if total_pie_for_sim_municipalities == 0:
            print(f"WARNING: Total PIE for simulated municipalities in year {year_int} (or fallback) is 0. Cannot distribute proportionally.")
            # Fallback: distribute 'value_to_distribute' equally among municipalities based on population?
            # Or simply do not distribute if no base PIE data. For now, do not distribute.
            return

        for region_id_ine5, region in regions.items(): # region_id_ine5 is the 5-digit INE code
            # Find the PIE value for this specific municipality and year using 'mun_code'
            pie_entry = pd.DataFrame() # Default to empty
            if 'mun_code' in relevant_pie_data.columns:
                pie_entry = relevant_pie_data[relevant_pie_data['mun_code'] == region_id_ine5]
            
            if not pie_entry.empty:
                actual_pie_for_municipality = pie_entry['total_participacion_variables'].iloc[0]
                
                # Calculate proportion of this municipality's PIE relative to total PIE of simulated municipalities
                proportion_of_total_pie = actual_pie_for_municipality / total_pie_for_sim_municipalities
                
                # Distribute the 'value_to_distribute' (collected taxes) based on this proportion
                # The original logic also had a population adjustment: * pop_t[id] / pop_mun_t[mun_code]
                # If region_id_ine5 is the municipal level, pop_t[region_id_ine5] is municipal pop,
                # and pop_mun_t[region_id_ine5] (assuming mun_code key is region_id_ine5) is also municipal pop.
                # So pop_t[id] / pop_mun_t[mun_code] would be 1.
                # This implies the 'value_to_distribute' is already at a level that needs to be shared among regions
                # based on their PIE share.
                
                regional_pie_share = proportion_of_total_pie * value_to_distribute
            else:
                # If a municipality in the simulation has no PIE data for the year (even after fallback)
                # assign it a zero share or a small default based on population?
                # For now, assign zero. This means it won't receive funds from this pot.
                regional_pie_share = 0
                print(f"WARNING: No PIE data for municipality {region_id_ine5} in year {year_int} (or fallback). It will receive 0 from this distribution.")

            # Separating money for policy
            if self.sim.PARAMS['POLICY_COEFFICIENT']: # This is a global param
                policy_allocation = regional_pie_share * self.sim.PARAMS['POLICY_COEFFICIENT']
                # policy_money key should be consistent (e.g. 5-digit INE, or first 2 for province, or first N for CCAA)
                # Original used region.id[:7]. For Spain, if region.id is 5-digit INE, this is still 5-digit INE.
                self.policy_money[region.id] += policy_allocation 
                regional_pie_share -= policy_allocation

            # Actually investing the PIE funds
            # The key for applied_taxes was 'fpm', changing to 'pie'
            region.update_index(regional_pie_share * self.sim.PARAMS['MUNICIPAL_EFFICIENCY_MANAGEMENT'])
            region.update_applied_taxes(regional_pie_share, 'pie') # Changed from 'fpm'

    def locally(self, value, regions, mun_code, pop_t, pop_mun_t):
        for mun in mun_code.keys():
            for id in mun_code[mun]:
                amount = 0.0  # Default to 0 if municipal population is zero
                if pop_mun_t[mun] != 0:
                    amount = value[mun] * pop_t[id] / pop_mun_t[mun]

                # Separating money for policy
                if self.sim.PARAMS['POLICY_COEFFICIENT']:
                    self.policy_money[mun] += amount * self.sim.PARAMS['POLICY_COEFFICIENT']
                    amount *= 1 - self.sim.PARAMS['POLICY_COEFFICIENT']

                regions[id].update_index(amount * self.sim.PARAMS['MUNICIPAL_EFFICIENCY_MANAGEMENT'])
                regions[id].update_applied_taxes(amount, 'locally')

    def equally(self, value, regions, pop_t, pop_total):
        for id, region in regions.items():
            amount = 0.0  # Default to 0 if total population is zero
            if pop_total != 0:
                amount = value * pop_t[id] / pop_total
            # Separating money for policy
            if self.sim.PARAMS['POLICY_COEFFICIENT']:
                self.policy_money[id[:7]] += amount * self.sim.PARAMS['POLICY_COEFFICIENT']
                amount *= 1 - self.sim.PARAMS['POLICY_COEFFICIENT']
            region.update_index(amount * self.sim.PARAMS['MUNICIPAL_EFFICIENCY_MANAGEMENT'])
            region.update_applied_taxes(amount, 'equally')

    def invest_taxes(self, year, bank_taxes):
        if self.sim.PARAMS['POLICIES'] not in ['buy', 'rent', 'wage']:
            self.sim.PARAMS['POLICY_COEFFICIENT'] = 0
        # Collect and UPDATE pop_t-1 and pop_t
        regions = self.sim.regions
        pop_t_minus_1, pop_t = {}, {}
        pop_mun_minus = defaultdict(int)
        pop_mun_t = defaultdict(int)
        treasure = defaultdict(dict)
        for id, region in regions.items():
            pop_t_minus_1[id] = region.pop
            pop_mun_minus[id[:7]] += region.pop
            # Update
            region.pop = self.sim.reg_pops.get(id, 0.0) # Use .get() to provide a default if key is missing
            pop_t[id] = region.pop
            pop_mun_t[id[:7]] += region.pop

            # BRING treasure from regions to municipalities
            treasure[id] = region.transfer_treasure()

        # Update proportion of index coming from population variation
        for id, region in regions.items():
            m_id = id[:7]
            factor = 1.0  # Default to no change if current municipal population is zero
            if pop_mun_t[m_id] != 0:
                factor = pop_mun_minus[m_id] / pop_mun_t[m_id]
            region.update_index_pop(factor)

        v_local = defaultdict(int)
        v_equal = 0
        if self.sim.PARAMS['ALTERNATIVE0']:
            # Dividing proortion of consumption into equal and local (state, municipality)
            # And adding local part of consumption plus transaction and property to local
            v_equal += sum([treasure[key]['consumption'] for key in treasure.keys()]) * \
                      self.sim.PARAMS['TAXES_STRUCTURE']['consumption_equal']
            mun_code = self.sim.mun_to_regions
            for mun in mun_code.keys():
                v_local[mun] += sum(treasure[r]['consumption'] for r in mun_code[mun]) * \
                                (1 - self.sim.PARAMS['TAXES_STRUCTURE']['consumption_equal'])
                v_local[mun] += sum(treasure[r]['transaction'] for r in mun_code[mun])
                v_local[mun] += sum(treasure[r]['property'] for r in mun_code[mun])
            # The only case in which local funds are distributed
            self.locally(v_local, regions, mun_code, pop_t, pop_mun_t)
        else:
            for each in ['consumption', 'property', 'transaction']:
                v_equal += sum([treasure[key][each] for key in treasure.keys()])

        # Use PIE_DISTRIBUTION if defined, otherwise fallback to FPM_DISTRIBUTION for compatibility
        pie_param_key = 'PIE_DISTRIBUTION' if 'PIE_DISTRIBUTION' in self.sim.PARAMS else 'FPM_DISTRIBUTION'
        tax_structure_key = 'pie' if 'pie' in self.sim.PARAMS['TAXES_STRUCTURE'] else 'fpm'


        if self.sim.PARAMS.get(pie_param_key, False):
            v_pie_base = (sum([treasure[key]['labor'] for key in treasure.keys()]) +
                          sum([treasure[key]['firm'] for key in treasure.keys()]))
            
            pie_share_for_distribution = v_pie_base * self.sim.PARAMS['TAXES_STRUCTURE'].get(tax_structure_key, 0)
            self.distribute_pie(pie_share_for_distribution, regions, pop_t, pop_mun_t, year) # Changed fpm to pie
            
            v_equal += v_pie_base * (1 - self.sim.PARAMS['TAXES_STRUCTURE'].get(tax_structure_key, 0))
        else:
            v_equal += (sum([treasure[key]['labor'] for key in treasure.keys()]) +
                        sum([treasure[key]['firm'] for key in treasure.keys()]))
        # Taxes charged from interests paid by the bank are equally distributed
        v_equal += bank_taxes
        self.equally(v_equal, regions, pop_t, sum(pop_mun_t.values()))
