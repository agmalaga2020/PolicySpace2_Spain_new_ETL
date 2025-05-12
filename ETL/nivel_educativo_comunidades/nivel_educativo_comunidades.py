# -*- coding: utf-8 -*-
"""
nivel_educativo_comunidades.py

Adapted for **local execution** (VS Code / plain Python) – Colab‑free version
==========================================================================
- ✅ Eliminados restos de `/content/` y cualquier dependencia de Google Colab.
- ✅ Todas las salidas (CSV) se guardan en una carpeta **data_final/** junto al
  script, independientemente del `cwd` desde donde lo lances.
- ✅ Añadida la función `ensure_output_dir()` basada en `Path(__file__).parent`.
- ✅ Reorganizado en una función `main()`; el módulo se puede importar sin
  ejecutar la ETL automáticamente.

Ejemplo de uso
--------------
```
$ python nivel_educativo_comunidades.py
```

Se generarán uno o más CSV dentro de `data_final/` (véase el log al final).
"""

from __future__ import annotations
import io
import sys
from pathlib import Path
import warnings
import requests
import pandas as pd
import matplotlib.pyplot as plt

###############################################################################
# 0. Utilidades comunes                                                       #
###############################################################################

def ensure_output_dir(path: str = "data_final") -> Path:
    """Return (and create if needed) a directory **next to this script**."""
    script_dir = Path(__file__).resolve().parent
    out_dir = (script_dir / path).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


###############################################################################
# 1. Descarga – Dataset de referencia de Brasil                               #
###############################################################################

BRAZIL_URL = (
    "https://raw.githubusercontent.com/BAFurtado/PolicySpace2/refs/heads/master/"
    "input/qualification_APs_2000.csv"
)

def load_brazil_reference(url: str = BRAZIL_URL) -> pd.DataFrame:
    """Descarga el CSV brasileño y lo devuelve como DataFrame."""
    print("\n📥 Descargando referencia de Brasil …", end=" ")
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    print("ok")
    return pd.read_csv(io.StringIO(resp.content.decode("utf-8")))


###############################################################################
# 2. Descarga – Tabla INE (nivel educativo por CCAA)                          #
###############################################################################

def download_ine_csv(table_code: str = "65289") -> Path:
    """Descarga la tabla TEM‑PUS del INE en formato CSV dentro de *data_final*."""
    out_dir = ensure_output_dir()
    url = f"https://servicios.ine.es/wstempus/csv/ES/DATOS_TABLA/{table_code}?nult=999"
    print(f"📥 Descargando tabla INE {table_code} …", end=" ")
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    csv_path = out_dir / f"tabla_{table_code}.csv"
    csv_path.write_text(resp.content.decode("utf-8"), encoding="utf-8")
    print("guardada →", csv_path.relative_to(csv_path.parent.parent))
    return csv_path


###############################################################################
# 3. Limpieza y transformación                                                #
###############################################################################

# Mappings – Nivel formativo → código 1‑7
CODIGO_NIVELES = {
    "Analfabetos": 1,
    "Estudios primarios incompletos": 2,
    "Educación primaria": 3,
    "Primera etapa de educación secundaria y similar": 4,
    "Segunda etapa de educación secundaria, con orientación general": 5,
    "Segunda etapa de educación secundaria con orientación profesional (incluye educación postsecundaria no superior)": 6,
    "Educación superior": 7,
}


def clean_ine_df(path_csv: Path) -> pd.DataFrame:
    """Carga la tabla INE y la transforma según el plan de limpieza del notebook."""

    df = pd.read_csv(path_csv, sep="\t", encoding="utf-8")

    # Filtrado y columnas básicas
    df = df[df["Comunidades y Ciudades Autónomas"] != "Total Nacional"].copy()
    df[["ccaa_code", "ccaa_name"]] = df["Comunidades y Ciudades Autónomas"].str.extract(r"(\d+)\s+(.*)")

    # Total como float - manejo más robusto de valores no numéricos
    df["Total_clean"] = df["Total"].str.replace(",", ".", regex=False)
    df["Total_clean"] = df["Total_clean"].replace("..", None)
    # Convertir a float solo los valores válidos
    df["total"] = pd.to_numeric(df["Total_clean"], errors="coerce")
    # Eliminar filas con valores nulos en 'total'
    df = df.dropna(subset=["total"])
    # Eliminar columna temporal
    df = df.drop(columns=["Total_clean"])

    # Rename columns
    df = df.rename(
        columns={
            "Sexo": "sexo",
            "Nivel de formación alcanzado": "nivel_formacion",
            "Periodo": "periodo",
        }
    )

    # Drop original redundant columns
    df = df.drop(columns=["Comunidades y Ciudades Autónomas", "Total"], errors="ignore")

    # Lowercase comparables
    df["nivel_formacion"] = df["nivel_formacion"].str.strip()
    df = df[df["nivel_formacion"].str.lower() != "total"]

    # Extract año y trimestre
    df["año"] = df["periodo"].str.extract(r"(\d{4})").astype(int)

    # Keep ambos sexos only
    df = df[df["sexo"].str.lower() == "ambos sexos"].copy()

    # Aggregate mean per ccaa‑año‑nivel
    df_media = (
        df.groupby(["ccaa_code", "ccaa_name", "año", "nivel_formacion"], as_index=False)
        ["total"].mean()
        .rename(columns={"total": "media_total"})
    )

    # Map códigos 1‑7
    df_media["nivel_formacion_code"] = df_media["nivel_formacion"].map(CODIGO_NIVELES)

    # Pivot a formato final 1‑7 como columnas
    df_final = df_media.pivot_table(
        index=["ccaa_code", "año"],
        columns="nivel_formacion_code",
        values="media_total",
    ).reset_index()
    df_final.columns.name = None
    df_final.columns = [
        "ccaa_code",
        "año",
        *[str(c) for c in df_final.columns[2:]],
    ]

    return df_media, df_final


###############################################################################
# 4. Salida de archivos                                                       #
###############################################################################

def save_outputs(df_media: pd.DataFrame, df_final: pd.DataFrame) -> None:
    out_dir = ensure_output_dir()

    # Consolidado completo
    df_media.to_csv(out_dir / "nivel_educativo_comunidades_completo.csv", index=False)
    df_final.to_csv(out_dir / "nivel_educativo_comunidades_pivot.csv", index=False)

    # División anual (sin columna año)
    for año, df_anual in df_final.groupby("año"):
        df_anual.drop(columns="año").to_csv(
            out_dir / f"nivel_educativo_comunidades_{año}.csv", index=False
        )

    print("\n📁 Archivos generados en", out_dir.relative_to(out_dir.parent))
    for p in sorted(out_dir.glob("nivel_educativo_comunidades*.csv")):
        print("   ", p.name)


###############################################################################
# 5. Plot rápido (opcional)                                                   #
###############################################################################

def plot_national_evolution(df_media: pd.DataFrame) -> None:
    """Grafica la evolución nacional media de cada nivel educativo."""
    df_national = (
        df_media.groupby(["nivel_formacion", "año"], as_index=False)["media_total"].mean()
    )
    plt.figure(figsize=(11, 8))
    for nivel, grupo in df_national.groupby("nivel_formacion"):
        plt.plot(grupo["año"], grupo["media_total"], marker="o", label=nivel)
    plt.title("Evolución nacional del nivel de formación (2000‑2024)")
    plt.xlabel("Año")
    plt.ylabel("Media total (%)")
    plt.grid(True)
    plt.legend(bbox_to_anchor=(1.04, 1), loc="upper left")
    plt.tight_layout()
    plt.show()


###############################################################################
# 6. Main                                                                     #
###############################################################################

def main() -> None:
    warnings.filterwarnings("ignore")

    print("\n═══════════════════════════════════════════════════════════════════════")
    print(" Nivel educativo comunidades  –  ETL pipeline (local)")
    print("═══════════════════════════════════════════════════════════════════════")

    # Paso 1: referencia Brasil (no se guarda, solo info)
    df_bra = load_brazil_reference()
    print("→ Brasil rows:", df_bra.shape[0])

    # Paso 2: descarga tabla INE
    table_code = "65289"
    csv_path = download_ine_csv(table_code)

    # Paso 3: limpieza
    df_media, df_final = clean_ine_df(csv_path)

    # Paso 4: guardado
    save_outputs(df_media, df_final)

    # Paso 5: gráfico rápido 
    plot_national_evolution(df_media)

    print("\n✅ Pipeline finalizado con éxito.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("❌ Error:", exc, file=sys.stderr)
        sys.exit(1)
