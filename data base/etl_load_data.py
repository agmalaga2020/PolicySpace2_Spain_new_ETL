import os
import pandas as pd
from sqlalchemy import create_engine
from datetime import datetime
import numpy as np

# Configuración de paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "datawarehouse.db")
LOG_PATH = os.path.join(BASE_DIR, "etl_load_log.txt")

def log(msg):
    print(msg)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"{msg}\n")

# Limpiar log anterior
with open(LOG_PATH, "w", encoding="utf-8") as f:
    f.write(f"LOG ETL LOAD DATA - {datetime.now()}\n\n")

# Crear motor de base de datos (SQLite)
engine = create_engine(f"sqlite:///{DB_PATH}")

try:
    # 1. Tabla de equivalencias (municipios)
    df_eq = pd.read_csv(
        os.path.join(BASE_DIR, '../ETL/tabla_equivalencias/data/df_equivalencias_municipio_CORRECTO.csv'),
        dtype=str
    )
    df_eq.to_sql('tabla_equivalencias', engine, if_exists='replace', index=False)
    log(f"[tabla_equivalencias] OK: {df_eq.shape[0]} filas, {df_eq.shape[1]} columnas")
    
    # Cargar códigos de provincias (para el merge de fecundidad)
    df_prov = pd.read_csv(
        os.path.join(BASE_DIR, '../ETL/indicadores_fecundidad_municipio_provincias/codigos_ccaa_provincias.csv'),
        dtype=str
    )
    # Renombrar columna de provincia para el merge
    df_prov = df_prov.rename(columns={'Provincia': 'provincia_name'})
    log(f"\n[codigos_ccaa_provincias] Cargado: {df_prov.shape[0]} filas, {df_prov.shape[1]} columnas")
    log(f"Columnas: {', '.join(df_prov.columns)}")
    log(df_prov.head().to_string())

    # 2. Cifras población municipio
    df_cif_pob = pd.read_csv(
        os.path.join(BASE_DIR, '../ETL/cifras_poblacion_municipio/cifras_poblacion_municipio.csv'),
        dtype={'mun_code': str}
    )
    df_cif_pob.to_sql('cifras_poblacion_municipio', engine, if_exists='replace', index=False)
    log(f"\n[cifras_poblacion_municipio] OK: {df_cif_pob.shape[0]} filas, {df_cif_pob.shape[1]} columnas")

    # 3. Mortalidad CCAA por sexo
    df_mort = pd.read_csv(
        os.path.join(BASE_DIR, '../ETL/df_mortalidad_ccaa_sexo/df_mortalidad_final.csv'),
        dtype={'ccaa_code': str}
    )
    df_mort = df_mort.rename(
        columns={
            'ccaa_code': 'ccaa_code',
            'Sexo': 'sex',
            'Periodo': 'year',
            'Total': 'total_muertes'
        }
    )
    df_mort.to_sql('df_mortalidad_ccaa_sexo', engine, if_exists='replace', index=False)
    log(f"\n[df_mortalidad_ccaa_sexo] OK: {df_mort.shape[0]} filas, {df_mort.shape[1]} columnas")

    # 4. Distribución urbana (2003-2022)
    df_urb = pd.read_csv(
        os.path.join(BASE_DIR, '../ETL/distribucion_urbana/data_final/distribucion_urbana_municipios_2003_to_2022.csv'),
        dtype={'municipio_code': str}
    )
    years = [c for c in df_urb.columns if c.isdigit()]
    df_urb_long = df_urb.melt(
        id_vars=['municipio_code'],
        value_vars=years,
        var_name='year',
        value_name='proporcion_urbana'
    )
    df_urb_long = df_urb_long.rename(columns={'municipio_code': 'mun_code'})
    df_urb_long.to_sql('distribucion_urbana', engine, if_exists='replace', index=False)
    log(f"\n[distribucion_urbana] OK: {df_urb_long.shape[0]} filas, {df_urb_long.shape[1]} columnas")

    # 5. Empresas Municipio
    df_emp = pd.read_csv(
        os.path.join(BASE_DIR, '../ETL/empresas_municipio_actividad_principal/preprocesados/empresas_municipio_actividad_principal.csv'),
        dtype={'municipio_code': str}
    )
    df_emp = df_emp.rename(
        columns={
            'municipio_code': 'mun_code',
            'Periodo': 'year',
            'Total': 'total_empresas'
        }
    )
    df_emp.to_sql('empresas_municipio_actividad_principal', engine, if_exists='replace', index=False)
    log(f"\n[empresas_municipio_actividad_principal] OK: {df_emp.shape[0]} filas, {df_emp.shape[1]} columnas")

    # 6. Estimativas población
    df_estpop = pd.read_csv(
        os.path.join(BASE_DIR, '../ETL/estimativas_pop/preprocesados/cifras_poblacion_municipio.csv'),
        dtype={'mun_code': str}
    )
    df_estpop.to_sql('estimativas_pop', engine, if_exists='replace', index=False)
    log(f"\n[estimativas_pop] OK: {df_estpop.shape[0]} filas, {df_estpop.shape[1]} columnas")

    # 7. IDHM municipal
    df_idhm = pd.read_csv(
        os.path.join(BASE_DIR, '../ETL/idhm_indice_desarrollo_humano_municipal/IRPFmunicipios_final_IDHM.csv'),
        dtype={'mun_code': str}
    )
    df_idhm.to_sql('idhm_indice_desarrollo_humano_municipal', engine, if_exists='replace', index=False)
    log(f"\n[idhm_indice_desarrollo_humano_municipal] OK: {df_idhm.shape[0]} filas, {df_idhm.shape[1]} columnas")

    # 8. Indicadores fecundidad provincias
    df_fert = pd.read_csv(
        os.path.join(BASE_DIR, '../ETL/indicadores_fecundidad_municipio_provincias/df_total_interpolado_full_tasa_estandarizada.csv'),
        dtype=str
    )
    
    log("\n[indicadores_fecundidad] Provincias en datos:")
    prov_list = df_fert['provincias_name'].unique().tolist()
    log(str(sorted(prov_list)[:10]))
    
    # Normalizar nombres de provincia para el merge
    df_fert['provincias_name_clean'] = df_fert['provincias_name'].str.normalize('NFKD').str.encode('ASCII', errors='ignore').str.decode('ASCII').str.upper()
    df_prov['provincia_name_clean'] = df_prov['provincia_name'].str.normalize('NFKD').str.encode('ASCII', errors='ignore').str.decode('ASCII').str.upper()
    
    # Intentar merge con códigos de provincias usando el archivo correcto
    df_fert_merged = df_fert.merge(
        df_prov[['CPRO', 'provincia_name_clean']], 
        left_on='provincias_name_clean', 
        right_on='provincia_name_clean', 
        how='left'
    )
    
    n_missing = df_fert_merged['CPRO'].isna().sum()
    if n_missing > 0:
        log(f"\n[indicadores_fecundidad] ADVERTENCIA: {n_missing} filas sin correspondencia de provincia")
        log("Provincias sin match:")
        missing_prov = df_fert_merged[df_fert_merged['CPRO'].isna()]['provincias_name'].unique()
        log(str(sorted(missing_prov.tolist())))
    
    df_fert_merged = df_fert_merged.drop(['provincias_name_clean', 'provincia_name_clean'], axis=1)
    df_fert_merged = df_fert_merged.rename(columns={
        'tasa_estandarizada': 'tasa_fert_prov', 
        'periodo': 'year',
        'CPRO': 'cpro'
    })
    
    df_fert_merged.to_sql('indicadores_fecundidad_municipio_provincias', engine, if_exists='replace', index=False)
    log(f"\n[indicadores_fecundidad_municipio_provincias] OK: {df_fert_merged.shape[0]} filas, {df_fert_merged.shape[1]} columnas")

    # 9. Interest data (nacional)
    df_fixed = pd.read_csv(
        os.path.join(BASE_DIR, '../ETL/interest_data_ETL/imputados/interest_fixed_imputado.csv'),
        sep=';', parse_dates=['date']
    )
    df_nom = pd.read_csv(
        os.path.join(BASE_DIR, '../ETL/interest_data_ETL/imputados/interest_nominal_imputado.csv'),
        sep=';', parse_dates=['date']
    )
    df_real = pd.read_csv(
        os.path.join(BASE_DIR, '../ETL/interest_data_ETL/imputados/interest_real_imputado.csv'),
        sep=';', parse_dates=['date']
    )
    df_int = df_fixed.merge(df_nom, on='date').merge(df_real, on='date')
    df_int = df_int.rename(
        columns={
            'interest_x': 'interest_fixed',
            'interest_y': 'interest_nominal',
            'interest': 'interest_real'
        }
    )
    df_int.to_sql('interest_data_ETL', engine, if_exists='replace', index=False)
    log(f"\n[interest_data_ETL] OK: {df_int.shape[0]} filas, {df_int.shape[1]} columnas")

    # 10. Nivel educativo CCAA
    df_edu = pd.read_csv(
        os.path.join(BASE_DIR, '../ETL/nivel_educativo_comunidades/data_final/nivel_educativo_comunidades_completo.csv'),
        dtype={'ccaa_code': str}
    )
    df_edu.to_sql('nivel_educativo_comunidades', engine, if_exists='replace', index=False)
    log(f"\n[nivel_educativo_comunidades] OK: {df_edu.shape[0]} filas, {df_edu.shape[1]} columnas")

    # 11. PIE
    df_pie = pd.read_csv(
        os.path.join(BASE_DIR, '../ETL/PIE/data/raw/finanzas/liquidaciones/preprocess/pie_final_final.csv'),
        dtype={'codigo_municipio': str}
    )
    df_pie = df_pie.rename(columns={'codigo_municipio': 'mun_code', 'año': 'year'})
    df_pie.to_sql('PIE', engine, if_exists='replace', index=False)
    log(f"\n[PIE] OK: {df_pie.shape[0]} filas, {df_pie.shape[1]} columnas")

except Exception as e:
    log(f"\nERROR GENERAL: {str(e)}")

log("\nCarga completa de todas las tablas seleccionadas.")
print("\nCarga completa. Revisa el log en data base/etl_load_log.txt")
