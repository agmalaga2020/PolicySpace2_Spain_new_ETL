# -*- coding: utf-8 -*-
"""
tamaño_medio_hogares_ccaa.py

Adapted for local execution (Visual Studio Code, plain Python) without Google Colab dependencies.
-------------------------------------------------------------------------
- Eliminates all `google.colab`‐specific imports and `files.download()` calls.
- Replaces hard‑coded Colab paths ("/content/…") with **script‑relative** paths.
- All generated CSVs (including `df_original.csv`) now live in a single
  subfolder `data_final/` next to this script, regardless of where you run it.
- Adds network‑error handling and wraps everything in a `main()` so the module
  can be imported without side effects.

Run from anywhere:
    $ python tamaño_medio_hogares_ccaa.py

"""

from __future__ import annotations
import io
import sys
import warnings
from pathlib import Path

import pandas as pd
import requests

###############################################################################
# 1. Load original PolicySpace2 data (Brazil) – kept for reference            #
###############################################################################

def load_original_brazil_dataset(url: str) -> pd.DataFrame:
    """Download and load the PolicySpace2 average household size CSV."""
    print("\n📥 Downloading Brazilian baseline data …", end=" ")
    response = requests.get(url, timeout=60)
    if response.status_code != 200:
        raise RuntimeError(f"Failed with HTTP {response.status_code} → {url}")
    print("done.")
    return pd.read_csv(io.StringIO(response.content.decode("utf-8")), sep=";")

###############################################################################
# 2. Download INE table on Spanish household size (monthly)                   #
###############################################################################

def download_ine_table(table_code: str) -> pd.DataFrame:
    """Return raw INE table as DataFrame (tab‑separated)."""
    url = (
        f"https://servicios.ine.es/wstempus/csv/ES/DATOS_TABLA/{table_code}?nult=999"
    )
    print(f"📥 Downloading INE table {table_code} …", end=" ")
    response = requests.get(url, timeout=60)
    if response.status_code != 200:
        raise RuntimeError(
            f"Failed to download INE table {table_code} – HTTP {response.status_code}")
    print("done.")
    return pd.read_csv(io.StringIO(response.content.decode("utf-8")), sep="\t")

###############################################################################
# 3. Download mapping Comunidad Autónoma ↔ code                               #
###############################################################################

def download_ccaa_mapping() -> pd.DataFrame:
    url = "https://www.ine.es/daco/daco42/codmun/cod_ccaa_provincia.htm"
    print("📥 Downloading CCAA mapping …", end=" ")
    tables = pd.read_html(url, encoding="ISO-8859-1")
    print("done.")
    df_temp = tables[0]
    df_temp.columns = ["CODAUTO", "Comunidad Autónoma", "CPRO", "Provincia"]
    df_temp = df_temp[df_temp["Comunidad Autónoma"] != "Ciudades Autónomas"]
    df_temp["CODAUTO"] = pd.to_numeric(df_temp["CODAUTO"], errors="coerce")
    df_temp = df_temp.dropna(subset=["CODAUTO"])
    mapping = (
        df_temp[["CODAUTO", "Comunidad Autónoma"]]
        .drop_duplicates("CODAUTO")
        .rename(columns={"CODAUTO": "comunidad_code"})
    )
    return mapping

###############################################################################
# 4. Transform INE monthly series into cleaned annual averages                #
###############################################################################

MES_MAP = {
    "enero": "01",
    "febrero": "02",
    "marzo": "03",
    "abril": "04",
    "mayo": "05",
    "junio": "06",
    "julio": "07",
    "agosto": "08",
    "septiembre": "09",
    "octubre": "10",
    "noviembre": "11",
    "diciembre": "12",
}


def clean_ine_df(df_raw: pd.DataFrame, mapping: pd.DataFrame) -> pd.DataFrame:
    warnings.filterwarnings("ignore")

    df = df_raw.copy()
    df = df.rename(columns={"Comunidades y ciudades autónomas": "comunidad_name"})

    # Extract year and month
    df["mes"] = df["Periodo"].str.extract(r"de (\w+) de")[0].str.lower().map(MES_MAP)
    df["año"] = df["Periodo"].str.extract(r"de (\d{4})")[0].astype(int)

    # Convert Total → float (comma decimal)
    df["total"] = df["Total"].str.replace(",", ".").astype(float)

    # Merge with CCAA codes
    df = df.merge(mapping, left_on="comunidad_name", right_on="Comunidad Autónoma", how="left")

    # Drop unused cols
    df = df.drop(columns=["Periodo", "Total", "Comunidad Autónoma"], errors="ignore")

    # Remove national aggregate
    df = df[df["comunidad_name"] != "Total Nacional"]

    # Fix Castilla‑La Mancha missing code (CODAUTO 8)
    mask = (df["comunidad_name"] == "Castilla-La Mancha") & df["comunidad_code"].isna()
    df.loc[mask, "comunidad_code"] = 8

    # Annual mean by CCAA
    return df.groupby(["comunidad_code", "año"], as_index=False)["total"].mean()

###############################################################################
# 5. Persistence helpers                                                     #
###############################################################################

def ensure_output_dir(path: str = "data_final") -> Path:
    """Create (if needed) & return a folder **next to this script**."""
    script_dir = Path(__file__).resolve().parent
    out_dir = (script_dir / path).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def save_outputs(df_media_anual: pd.DataFrame, out_dir: Path) -> None:
    """Write consolidated & per‑year CSVs inside *out_dir*."""
    consolidated = out_dir / "tamaño_medio_hogares_ccaa_completo.csv"
    df_media_anual.to_csv(consolidated, index=False)

    for year, df_year in df_media_anual.groupby("año"):
        (out_dir / f"tamaño_medio_hogares_ccaa_{year}.csv").write_text(
            df_year.drop(columns=["año"]).to_csv(index=False))

    print("\n📁 Generated files:")
    for path in sorted(out_dir.glob("*.csv")):
        print("   ", path.name)

###############################################################################
# 6. Main execution                                                          #
###############################################################################

def main() -> None:
    print("\n═══════════════════════════════════════════════════════════════════════")
    print("  Tamaño medio de los hogares por CCAA  –  ETL pipeline (local)")
    print("═══════════════════════════════════════════════════════════════════════")

    # Ensure output directory first so it can be reused everywhere
    out_dir = ensure_output_dir()

    # Brazilian baseline (optional)
    brazil_url = (
        "https://raw.githubusercontent.com/BAFurtado/PolicySpace2/refs/heads/master/input/"
        "average_num_members_families_2010.csv"
    )
    df_original = load_original_brazil_dataset(brazil_url)
    df_original.to_csv(out_dir / "df_original.csv", encoding="utf-8-sig", index=False)

    # Spain – INE household size
    df_raw = download_ine_table("60132")
    mapping = download_ccaa_mapping()
    df_media_anual = clean_ine_df(df_raw, mapping)

    save_outputs(df_media_anual, out_dir)

    print("\n✅ Pipeline finished successfully.")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("❌ Error:", exc, file=sys.stderr)
        sys.exit(1)
