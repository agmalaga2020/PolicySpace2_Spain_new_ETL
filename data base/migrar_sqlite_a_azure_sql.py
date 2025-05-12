\
import sqlite3
import pyodbc
import re

print("--- Script top level: Imports loaded ---", flush=True)

# --- CONFIGURATION ---
# Azure SQL Database connection details (FILL THESE IN)
AZURE_DB_SERVER   = 'servidor-tfg.database.windows.net'
AZURE_DB_NAME     = 'tfg-database'
AZURE_DB_USER = 'agmalaga2020'
AZURE_DB_PASSWORD = 'sJc!Ld5R.k6kT9r'
# Common drivers: 'ODBC Driver 17 for SQL Server', 'ODBC Driver 18 for SQL Server'
# Ensure this driver is installed on your system
AZURE_DB_DRIVER = '{ODBC Driver 17 for SQL Server}'

# SQLite database file path
SQLITE_DB_PATH = '/home/agmalaga/Documentos/GitHub/PolicySpace2_Spanish_data/data base/datawarehouse.db'

print(f"--- Script top level: SQLITE_DB_PATH = {SQLITE_DB_PATH} ---", flush=True)

# --- HELPER FUNCTIONS ---

def clean_name(name):
    """Cleans table and column names to be SQL-friendly."""
    name = str(name)
    # If name is purely numeric (like "1996"), prefix it
    if re.match(r'^\d+$', name):
        return f'Anio_{name}'
    
    # Replace spaces and special characters with underscores
    name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    
    # Remove leading/trailing underscores that might result from replacements
    name = name.strip('_')
    
    # Avoid names starting with a number if not already handled (e.g. after stripping underscores)
    if name and name[0].isdigit():
        name = f'_{name}' # Generic prefix if it still starts with a digit

    # Ensure name is not empty after cleaning
    if not name:
        return '_unnamed_column'
        
    return name

def map_sqlite_type_to_azure(sqlite_type):
    """Maps SQLite data types to Azure SQL data types."""
    sqlite_type_upper = sqlite_type.upper() if sqlite_type else ''
    
    if 'INT' in sqlite_type_upper: # INTEGER, BIGINT
        return 'BIGINT'
    elif 'TEXT' in sqlite_type_upper or 'CHAR' in sqlite_type_upper or 'CLOB' in sqlite_type_upper:
        return 'NVARCHAR(MAX)'
    elif 'REAL' in sqlite_type_upper or 'FLOAT' in sqlite_type_upper or 'DOUBLE' in sqlite_type_upper:
        return 'FLOAT'
    elif 'BLOB' in sqlite_type_upper:
        return 'VARBINARY(MAX)'
    elif 'NUMERIC' in sqlite_type_upper:
        return 'DECIMAL(38, 10)' # Adjust precision and scale as needed
    elif 'DATE' in sqlite_type_upper or 'TIME' in sqlite_type_upper: # DATETIME
        return 'DATETIME2'
    else:
        return 'NVARCHAR(MAX)' # Default fallback

# --- MAIN MIGRATION LOGIC ---

def migrate_data():
    print("--- Starting migrate_data() function ---", flush=True)

    # Connect to SQLite
    print(f"Attempting to connect to SQLite database: {SQLITE_DB_PATH}", flush=True)
    try:
        sqlite_conn = sqlite3.connect(SQLITE_DB_PATH)
        sqlite_cursor = sqlite_conn.cursor()
        print("Successfully connected to SQLite.", flush=True)
    except Exception as e_sqlite:
        print(f"!!! Critical error connecting to SQLite: {e_sqlite} !!!", flush=True)
        return

    # Connect to Azure SQL
    print(f"Attempting to connect to Azure SQL database: Server={AZURE_DB_SERVER}, DB={AZURE_DB_NAME}, User={AZURE_DB_USER}", flush=True)
    
    # --- Enhanced Placeholder Check ---
    placeholder_server = 'your_server_name.database.windows.net'
    placeholder_user = 'your_username'
    placeholder_password = 'your_password'

    print(f"--- DEBUG: Checking placeholders ---", flush=True)
    print(f"--- DEBUG: AZURE_DB_SERVER   = '{AZURE_DB_SERVER}' (Type: {type(AZURE_DB_SERVER)})", flush=True)
    print(f"--- DEBUG: placeholder_server = '{placeholder_server}' (Type: {type(placeholder_server)})", flush=True)
    print(f"--- DEBUG: Comparison 1 (Server): {AZURE_DB_SERVER == placeholder_server}", flush=True)

    print(f"--- DEBUG: AZURE_DB_USER     = '{AZURE_DB_USER}' (Type: {type(AZURE_DB_USER)})", flush=True)
    print(f"--- DEBUG: placeholder_user   = '{placeholder_user}' (Type: {type(placeholder_user)})", flush=True)
    print(f"--- DEBUG: Comparison 2 (User): {AZURE_DB_USER == placeholder_user}", flush=True)

    print(f"--- DEBUG: AZURE_DB_PASSWORD  = '{AZURE_DB_PASSWORD}' (Type: {type(AZURE_DB_PASSWORD)})", flush=True)
    print(f"--- DEBUG: placeholder_password= '{placeholder_password}' (Type: {type(placeholder_password)})", flush=True)
    print(f"--- DEBUG: Comparison 3 (Password): {AZURE_DB_PASSWORD == placeholder_password}", flush=True)
    
    is_placeholder_server = AZURE_DB_SERVER == placeholder_server
    is_placeholder_user = AZURE_DB_USER == placeholder_user
    is_placeholder_password = AZURE_DB_PASSWORD == placeholder_password

    if is_placeholder_server or is_placeholder_user or is_placeholder_password:
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!", flush=True)
        print("!!! ERROR: Azure SQL credentials are still placeholders. Please fill them in. !!!", flush=True)
        print(f"--- DEBUG: Triggered by: Server={is_placeholder_server}, User={is_placeholder_user}, Password={is_placeholder_password} ---", flush=True)
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!", flush=True)
        sqlite_conn.close()
        print("SQLite connection closed due to placeholder credentials.", flush=True)
        return

    azure_conn_str = (
        f'DRIVER={AZURE_DB_DRIVER};'
        f'SERVER={AZURE_DB_SERVER};'
        f'DATABASE={AZURE_DB_NAME};'
        f'UID={AZURE_DB_USER};'
        f'PWD={AZURE_DB_PASSWORD};'
        f'Encrypt=yes;'
        f'TrustServerCertificate=no;'
        f'Connection Timeout=30;'
    )
    print(f"Using Azure connection string (password redacted): DRIVER={AZURE_DB_DRIVER};SERVER={AZURE_DB_SERVER};DATABASE={AZURE_DB_NAME};UID={AZURE_DB_USER};PWD=********;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;", flush=True)

    try:
        azure_conn = pyodbc.connect(azure_conn_str)
        azure_cursor = azure_conn.cursor()
        print("Successfully connected to Azure SQL.", flush=True)
    except pyodbc.Error as ex:
        sqlstate = ex.args[0] if ex.args and len(ex.args) > 0 else "Unknown SQL state"
        detailed_error_message = str(ex)
        print(f"!!! pyodbc.Error connecting to Azure SQL. SQLSTATE: {sqlstate} !!!", flush=True)
        print(f"Full pyodbc error details: {detailed_error_message}", flush=True)
        sqlite_conn.close()
        print("SQLite connection closed due to Azure connection error.", flush=True)
        return
    except Exception as e_generic_azure:
        print(f"!!! A non-pyodbc error occurred while trying to connect to Azure SQL: {e_generic_azure} !!!", flush=True)
        sqlite_conn.close()
        print("SQLite connection closed due to Azure connection error.", flush=True)
        return

    # Get list of tables from SQLite (excluding sqlite internal tables)
    print("Fetching list of tables from SQLite...", flush=True)
    sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tables = [row[0] for row in sqlite_cursor.fetchall()]
    print(f"Found tables: {tables}", flush=True)


    for table_name in tables:
        print(f"\nProcessing table: {table_name}", flush=True)
        azure_table_name = clean_name(table_name)
        
        # Get SQLite table schema
        sqlite_cursor.execute(f"PRAGMA table_info('{table_name}');")
        columns_info = sqlite_cursor.fetchall()
        
        if not columns_info:
            print(f"Could not get schema for table {table_name}. Skipping.", flush=True)
            continue

        # Create Azure SQL table
        azure_columns_defs = []
        column_names_sqlite = []
        column_names_azure = []

        for col_info in columns_info:
            # col_info: (cid, name, type, notnull, dflt_value, pk)
            col_name_sqlite = col_info[1]
            col_type_sqlite = col_info[2]
            
            col_name_azure = clean_name(col_name_sqlite)
            col_type_azure = map_sqlite_type_to_azure(col_type_sqlite)
            
            azure_columns_defs.append(f"[{col_name_azure}] {col_type_azure}")
            column_names_sqlite.append(col_name_sqlite)
            column_names_azure.append(f"[{col_name_azure}]")


        # Check if table exists in Azure SQL
        check_table_exists_sql = f"""
        IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[{azure_table_name}]') AND type in (N'U'))
        BEGIN
            CREATE TABLE [dbo].[{azure_table_name}] ({', '.join(azure_columns_defs)});
        END
        """
        
        try:
            print(f"Ensuring table [{azure_table_name}] exists in Azure SQL...", flush=True)
            # For CREATE TABLE, it's better to execute without parameters and commit immediately if needed.
            # Or ensure autocommit is on (default for DDL usually).
            azure_conn.autocommit = True 
            azure_cursor.execute(check_table_exists_sql)
            azure_conn.autocommit = False # Turn off autocommit for data insertion
            print(f"Table [{azure_table_name}] ensured.", flush=True)
        except pyodbc.Error as ex:
            print(f"Error creating/checking table [{azure_table_name}] in Azure SQL: {ex}", flush=True)
            # Consider if you want to skip or halt on error
            continue 

        # Fetch data from SQLite
        print(f"Fetching data from SQLite table: {table_name}...", flush=True)
        sqlite_cursor.execute(f"SELECT {', '.join([f'\\"{c}\\"' for c in column_names_sqlite])} FROM \"{table_name}\";")
        
        # Insert data into Azure SQL
        insert_sql = f"INSERT INTO [dbo].[{azure_table_name}] ({', '.join(column_names_azure)}) VALUES ({', '.join(['?'] * len(column_names_azure))});"
        
        batch_size = 1000
        rows_inserted = 0
        
        while True:
            rows = sqlite_cursor.fetchmany(batch_size)
            if not rows:
                break
            
            try:
                azure_cursor.fast_executemany = True # Enable for potentially faster inserts
                azure_cursor.executemany(insert_sql, rows)
                azure_conn.commit()
                rows_inserted += len(rows)
                print(f"Inserted {rows_inserted} rows into [{azure_table_name}] (batch of {len(rows)})...", flush=True)
            except pyodbc.Error as ex:
                print(f"Error inserting data into [{azure_table_name}]: {ex}", flush=True)
                azure_conn.rollback() # Rollback batch on error
                # Decide if you want to skip this batch or halt
                break # Halting for this example
        print(f"Finished inserting data for table [{azure_table_name}]. Total rows: {rows_inserted}", flush=True)

    # Recreate the view
    print("\nRecreating view: vista_equivalencias_unicas", flush=True)
    azure_view_name = clean_name("vista_equivalencias_unicas")
    # Original SQLite view: CREATE VIEW vista_equivalencias_unicas AS SELECT CMUN, MIN(NOMBRE) AS NOMBRE, MIN(CPRO) AS CPRO FROM tabla_equivalencias GROUP BY CMUN
    # Cleaned names for Azure SQL:
    # CMUN -> CMUN (assuming it's already clean)
    # NOMBRE -> NOMBRE
    # CPRO -> CPRO
    # tabla_equivalencias -> tabla_equivalencias (assuming it's already clean or cleaned by clean_name)
    
    # We need to use the cleaned names of the table and columns in the view definition
    cleaned_source_table_name = clean_name("tabla_equivalencias")
    cleaned_cmun_col = clean_name("CMUN")
    cleaned_nombre_col = clean_name("NOMBRE")
    cleaned_cpro_col = clean_name("CPRO")

    create_view_sql = f"""
    IF OBJECT_ID(N'[dbo].[{azure_view_name}]', 'V') IS NOT NULL
        DROP VIEW [dbo].[{azure_view_name}];
    EXEC('CREATE VIEW [dbo].[{azure_view_name}] AS 
        SELECT 
            [{cleaned_cmun_col}], 
            MIN([{cleaned_nombre_col}]) AS [{cleaned_nombre_col}], 
            MIN([{cleaned_cpro_col}]) AS [{cleaned_cpro_col}] 
        FROM 
            [dbo].[{cleaned_source_table_name}] 
        GROUP BY 
            [{cleaned_cmun_col}]
    ');
    """
    try:
        azure_conn.autocommit = True
        azure_cursor.execute(create_view_sql)
        azure_conn.autocommit = False
        print(f"View [{azure_view_name}] recreated successfully.", flush=True)
    except pyodbc.Error as ex:
        print(f"Error recreating view [{azure_view_name}]: {ex}", flush=True)


    # Close connections
    print("\nMigration process finished.", flush=True)
    sqlite_conn.close()
    azure_conn.close()
    print("Connections closed.", flush=True)

if __name__ == '__main__':
    print("--- Script execution started (__main__ block) ---", flush=True)
    migrate_data()
    print("--- Script execution finished (__main__ block) ---", flush=True)
