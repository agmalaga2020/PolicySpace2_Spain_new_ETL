import os
import re
import shutil
from urllib.parse import unquote
import pandas as pd

SRC_DIR = "./ETL/PIE/data/raw/finanzas/liquidaciones"
DST_DIR = "./ETL/PIE/data/raw/finanzas/liquidaciones/por_municipios_regimen_general/"
os.makedirs(DST_DIR, exist_ok=True)

files = os.listdir(SRC_DIR)
files = [f for f in files if not f.startswith(".~lock") and not f.startswith(".")]

selected = {}
for fname in files:
    fname_decoded = unquote(fname)
    found = re.findall(r'(?:19|20)\d{2}', fname_decoded)
    if found:
        year = found[-1]
        if year not in selected:
            if (("LiquidacionVariable" in fname_decoded and year in fname_decoded) or
                (year == "2017" and "Variables2017" in fname_decoded)):
                selected[year] = fname
        if year not in selected:
            selected[year] = fname

if "2014" in selected and "LiquidacionVariable2014.xls" in files:
    selected["2014"] = "LiquidacionVariable2014.xls"
if "2017" in selected and "LiquidacionVariables2017.xls" in files:
    selected["2017"] = "LiquidacionVariables2017.xls"

for year, fname in sorted(selected.items()):
    src_path = os.path.join(SRC_DIR, fname)
    ext = os.path.splitext(fname)[1].lower()
    dst_name = f"liquidacion_{year}.xlsx"
    dst_path = os.path.join(DST_DIR, dst_name)
    if ext == ".xls":
        try:
            xls = pd.ExcelFile(src_path, engine="xlrd")
            with pd.ExcelWriter(dst_path, engine="openpyxl") as writer:
                for sheet in xls.sheet_names:
                    df = pd.read_excel(xls, sheet_name=sheet)
                    df.to_excel(writer, sheet_name=sheet, index=False)
            print(f"{year}: {fname} convertido y guardado como {dst_path}")
        except Exception as e:
            print(f"Error convirtiendo {fname}: {e}")
    else:
        shutil.copy2(src_path, dst_path)
        print(f"{year}: {fname} copiado como {dst_path}")

print("\nArchivos seleccionados, convertidos a .xlsx y renombrados a 'liquidacion_AÑO.xlsx' en 'por_municipios_regimen_general'.")
