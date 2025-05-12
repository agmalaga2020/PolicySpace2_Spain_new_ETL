import pandas as pd
from pathlib import Path

# --- Carga de datos ---
url_mun = "https://www.ine.es/daco/daco42/codmun/diccionario25.xlsx"
df_municipios = pd.read_excel(url_mun, skiprows=1)

# --- Asegurar padding ---
df_municipios['CPRO'] = df_municipios['CPRO'].astype(int).astype(str).str.zfill(2)
df_municipios['CMUN'] = df_municipios['CMUN'].astype(int).astype(str).str.zfill(3)

# --- Formar mun_code ---
df_municipios['mun_code'] = df_municipios['CPRO'] + df_municipios['CMUN']

df_equivalencias_municipio_CORRECTO = df_municipios.copy()

# --- Ruta basada en la ubicación del script ---
base_dir = Path(__file__).parent         # carpeta donde está este .py
output_dir = base_dir / 'data'           # subcarpeta 'data' junto al script
output_dir.mkdir(parents=True, exist_ok=True)

output_path = output_dir / 'df_equivalencias_municipio_CORRECTO.csv'
df_equivalencias_municipio_CORRECTO.to_csv(output_path, index=False)

print(f"CSV guardado en: {output_path}")
