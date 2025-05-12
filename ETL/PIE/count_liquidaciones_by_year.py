import os
import re
from collections import Counter
from urllib.parse import unquote



folder = "./ETL/PIE/data/raw/finanzas/liquidaciones/por_municipios_regimen_general/"
files = os.listdir(folder)

years = []
for fname in files:
    fname_decoded = unquote(fname)
    found = re.findall(r'(?:19|20)\d{2}', fname_decoded)
    if found:
        year = found[-1]
    else:
        year = "SIN_AÑO"
    print(f"{fname_decoded}: {year}")
    years.append(year)

conteo = Counter(years)
print("\nResumen:")
for year, count in sorted(conteo.items()):
    print(f"{year}: {count}")
