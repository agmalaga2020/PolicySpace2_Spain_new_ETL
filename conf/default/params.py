import datetime

# MODEL PARAMETERS
# FIRMS
PRODUCTIVITY_EXPONENT = .6
PRODUCTIVITY_MAGNITUDE_DIVISOR = 12
MUNICIPAL_EFFICIENCY_MANAGEMENT = .0001
INTEREST = 'real'
MARKUP = 0.15
STICKY_PRICES = .5
SIZE_MARKET = 10
LABOR_MARKET = 0.75
PCT_DISTANCE_HIRING = .3
WAGE_IGNORE_UNEMPLOYMENT = False
HIRING_SAMPLE_SIZE = 20

# TAXES - IMPORTANT: These values are likely from the Brazilian context and NEED CALIBRATION for Spain.
TAX_CONSUMPTION = .3 # Spanish IVA is variable (e.g., 4%, 10%, 21%). Needs representative value or more complex logic.
TAX_LABOR = .15 # Spanish IRPF withholdings and Social Security are complex. Needs representative value.
TAX_ESTATE_TRANSACTION = .005 # Spanish ITP/AJD varies by CCAA and value. Needs representative value.
TAX_FIRM = .15 # Spanish Corporate Tax (Impuesto de Sociedades) is typically 25%. Needs review.
TAX_PROPERTY = .005 # Spanish IBI varies by municipality. Needs representative value.

# GOVERNMENT
ALTERNATIVE0 = True
FPM_DISTRIBUTION = True # This will need to be re-evaluated for Spanish PIE data. The logic using this param might need to change.

# POVERTY POLICIES
POLICY_COEFFICIENT = 0.2
POLICIES = 'no_policy'
POLICY_DAYS = 360
POLICY_QUANTILE = .2

# HOUSING AND REAL ESTATE MARKET
MAX_LOAN_AGE = 75
LOAN_PAYMENT_TO_PERMANENT_INCOME = .6
MAX_LOAN_TO_VALUE = .6
MAX_LOAN_BANK_PERCENT = .7
CAPPED_TOP_VALUE = 1.3
CAPPED_LOW_VALUE = .7
OFFER_SIZE_ON_PRICE = 2
ON_MARKET_DECAY_FACTOR = -.01
MAX_OFFER_DISCOUNT = .6
PERCENTAGE_ENTERING_ESTATE_MARKET = 0.0045
NEIGHBORHOOD_EFFECT = 3 # This might need recalibration based on Spanish geography definition

# RENTAL
RENTAL_SHARE = 0.3
INITIAL_RENTAL_PRICE = .0028

# CONSTRUCTION
T_LICENSES_PER_REGION = 'random' # 'Region' here will now refer to municipality
PERCENT_CONSTRUCTION_FIRMS = 0.03
CONSTRUCTION_ACC_CASH_FLOW = 24
LOT_COST = .15

MEMBERS_PER_FAMILY = 2.5 # Spanish average household size was around 2.48 in 2022 (INE). This is a reasonable default but could be refined with ETL/tamaño_medio_hogares_ccaa data.
HOUSE_VACANCY = .1

SIMPLIFY_POP_EVOLUTION = True
LIST_NEW_AGE_GROUPS = [6, 12, 17, 25, 35, 45, 65, 100]
MARRIAGE_CHECK_PROBABILITY = .034 # User indicated marriage data might not be used. If marriage logic is removed, this param is irrelevant.

# TAXES_STRUCTURE might need re-evaluation for Spanish fiscal system
# The original model might use this to distribute collected taxes back to regions/municipalities.
# The Spanish PIE system is complex. This structure needs significant review.
TAXES_STRUCTURE = {'consumption_equal': .1875, 'pie': .235} # Changed 'fpm' to 'pie'. Value for 'pie' needs calibration.

WAGE_TO_CAR_OWNERSHIP_QUANTILES = [ # These are likely Brazil-specific. Need review/calibration for Spain.
    0.1174, 0.1429, 0.2303, 0.2883, 0.3395, 0.4667, 0.5554, 0.6508, 0.7779, 0.9135,
]
PRIVATE_TRANSIT_COST = 0.25
PUBLIC_TRANSIT_COST = 0.05

# --- Parameters for Spanish Adaptation ---
# Define which Spanish municipalities to process.
# Can be a list of 'mun_code' strings, or 'ALL'.
# Example: Madrid (28079) and Barcelona (08019)
SPANISH_MUNICIPALITIES_TO_PROCESS = ['01001', '01008'] # Changed to test municipalities as per user request
# SPANISH_MUNICIPALITIES_TO_PROCESS = 'ALL' # Uncomment to process all available

# Data paths (could be centralized here or handled by data loading scripts)
# SPANISH_DATA_ROOT = '/home/ubuntu/PolicySpace2_Spanish_github/' 
# SPANISH_ETL_PATH = os.path.join(SPANISH_DATA_ROOT, 'ETL')
# SPANISH_MUNICIPALITIES_INFO_PATH = os.path.join(SPANISH_ETL_PATH, "tabla_equivalencias/data/df_equivalencias_municipio_CORRECTO.csv")

# Percentage of actual population to run the simulation
PERCENTAGE_ACTUAL_POP = 0.1 # Adjusted from 0.01 to 0.1 for a more representative scale

# Available years for population data (e.g., pop_men_YEAR.csv, pop_women_YEAR.csv)
# The simulation will try the STARTING_DAY.year first, then these fallbacks.
# Updated based on files in ETL/cifras_poblacion_municipio/data_final/drive-download-20250506T180657Z-001/
POPULATION_AVAILABLE_YEARS = [2014, 2013, 2011, 2010, 2009, 2008, 2007, 2006, 2003] 

# Selecting the starting year to build the Agents
# This should align with the availability of Spanish data
STARTING_DAY = datetime.date(2014, 1, 1) # Changed to 2014 as per user request

# Maximum running time (restrained by official data)
# Adjust based on the time range of your Spanish data
TOTAL_DAYS = 365 # Simulating for 1 year from the new STARTING_DAY

# Original ACP-related parameters - these are now DEPRECATED for the Spanish version
# PROCESSING_ACPS = ['BRASILIA'] # DEPRECATED

print(f"PARAMS: Spanish adaptation - Processing municipalities: {SPANISH_MUNICIPALITIES_TO_PROCESS}")
print(f"PARAMS: Starting simulation on {STARTING_DAY} for {TOTAL_DAYS} days.")
