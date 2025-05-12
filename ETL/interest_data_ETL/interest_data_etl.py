#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
interest_data_etl.py

Pipeline ETL + imputación de tasas de interés para PolicySpace2, listo para ejecución local
(VS Code u otro entorno). Mantiene la lógica del cuaderno original pero sin dependencias de
Google Colab ni rutas absolutas.
"""
from __future__ import annotations

import os
from pathlib import Path
from io import StringIO

import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# --------------------------------------------------------------------------------------
# Configuración de rutas (todas relativas al directorio del script)
# --------------------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
IMPUTADOS_DIR = BASE_DIR / "imputados"
VIS_DIR = BASE_DIR / "visualizaciones"

for d in (DATA_DIR, IMPUTADOS_DIR, VIS_DIR):
    d.mkdir(exist_ok=True)

DATE_FMT_MONTH = "%Y-%m"

# --------------------------------------------------------------------------------------
# 1. DESCARGA DE DATOS
# --------------------------------------------------------------------------------------

def _download_csv(url: str, **params) -> pd.DataFrame:
    """Descarga un CSV desde SDW/Eurostat y lo devuelve como DataFrame."""
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return pd.read_csv(StringIO(r.text))


def fetch_ecb_interest_rates(start: str = "2000-01-01", end: str = "2025-04-30") -> pd.DataFrame:
    """Tasa de facilidad marginal (FM.D.U2.EUR.4F.KR.MRR_FR.LEV)."""
    flow, key = "FM", "D.U2.EUR.4F.KR.MRR_FR.LEV"
    base = "https://sdw-wsrest.ecb.europa.eu/service/data"
    df = _download_csv(f"{base}/{flow}/{key}", startPeriod=start, endPeriod=end, format="csvdata")

    df = (
        df.rename(columns={"TIME_PERIOD": "date", "OBS_VALUE": "interest"})
        .assign(date=lambda d: pd.to_datetime(d["date"]).dt.strftime(DATE_FMT_MONTH))
    )

    # ▶️ Colapsar posibles múltiples observaciones por mes (media) para mantener UNA fila/mes
    df = df.groupby("date", as_index=False)["interest"].mean()

    # Normalizar a proporción si llega en %
    if df["interest"].max() > 1:
        df["interest"] /= 100

    df.to_csv(DATA_DIR / "ecb_interest_monthly.csv", sep=";", index=False)
    return df


def fetch_bde_mortgage_rates(start: str = "2000-01", end: str = "2025-04") -> pd.DataFrame:
    """TEDR hipotecario (MIR.M.ES.B.A2C.A.R.A.2250.EUR.N)."""
    flow, key = "MIR", "M.ES.B.A2C.A.R.A.2250.EUR.N"
    base = "https://sdw-wsrest.ecb.europa.eu/service/data"
    df = _download_csv(f"{base}/{flow}/{key}", startPeriod=start, endPeriod=end, format="csvdata")

    df = (
        df.rename(columns={"TIME_PERIOD": "date", "OBS_VALUE": "mortgage"})
        .assign(date=lambda d: pd.to_datetime(d["date"]).dt.strftime(DATE_FMT_MONTH))
    )

    # ▶️ Agrupar duplicados mensuales
    df = df.groupby("date", as_index=False)["mortgage"].mean()

    if df["mortgage"].max() > 1:
        df["mortgage"] /= 100

    df.to_csv(DATA_DIR / "bde_mortgage_monthly.csv", sep=";", index=False)
    return df


def fetch_eurostat_hicp(start: str = "2000-01", end: str = "2025-04") -> pd.DataFrame:
    """HICP EA-19, índice 2015 = 100, mensual."""
    dataset = "prc_hicp_midx"
    base = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
    params = {
        "format": "JSON",
        "lang": "EN",
        "coicop": "CP00",
        "geo": "EA",
        "unit": "I15",
        "startPeriod": start,
        "endPeriod": end,
    }
    r = requests.get(f"{base}/{dataset}", params=params, timeout=30)
    r.raise_for_status()
    js = r.json()

    values = js.get("value", {})
    time_idx = js["dimension"]["time"]["category"]["index"]
    rows = [
        {"date": t, "hicp_index": values[str(i)]}
        for t, i in time_idx.items()
        if str(i) in values
    ]
    df = pd.DataFrame(rows).sort_values("date")
    df["hicp_rate"] = df["hicp_index"].pct_change()
    df.to_csv(DATA_DIR / "eurostat_hicp_monthly.csv", sep=";", index=False)
    return df

# --------------------------------------------------------------------------------------
# 2. CREACIÓN DE CSVs
# --------------------------------------------------------------------------------------

def create_interest_fixed() -> pd.DataFrame:
    dates = pd.date_range("2000-01", "2025-04", freq="MS").strftime(DATE_FMT_MONTH)
    df = pd.DataFrame({"date": dates, "interest": 0.004167, "mortgage": 0.004167})
    df.to_csv(DATA_DIR / "interest_fixed.csv", sep=";", index=False)
    return df


def create_interest_nominal(df_ecb: pd.DataFrame, df_bde: pd.DataFrame) -> pd.DataFrame:
    df = pd.merge(df_ecb, df_bde, on="date", how="outer")
    # ▶️ Asegurar UNA fila/mes tras el merge
    df = df.groupby("date", as_index=False)[["interest", "mortgage"]].mean()
    df = df.sort_values("date")
    df.to_csv("interest_nominal.csv", sep=";", index=False)
    return df


def create_interest_real(df_nominal: pd.DataFrame, df_hicp: pd.DataFrame) -> pd.DataFrame:
    df = pd.merge(df_nominal, df_hicp[["date", "hicp_rate"]], on="date", how="outer")
    df[["interest", "mortgage"]] = df[["interest", "mortgage"]].sub(df["hicp_rate"], axis=0)
    df = (
        df[["date", "interest", "mortgage"]]
        .groupby("date", as_index=False)
        .mean()
        .sort_values("date")
    )
    df.to_csv("interest_real.csv", sep=";", index=False)
    return df

# --------------------------------------------------------------------------------------
# 3. IMPUTACIÓN
# --------------------------------------------------------------------------------------

def _ffill(series: pd.Series) -> pd.Series:
    return series.ffill()


def impute_datasets():
    df_fixed = pd.read_csv(DATA_DIR / "interest_fixed.csv", sep=";")
    df_nominal = pd.read_csv("interest_nominal.csv", sep=";")
    df_real = pd.read_csv("interest_real.csv", sep=";")

    for df in (df_nominal, df_real):
        df["interest"] = _ffill(df["interest"])
        df["mortgage"] = _ffill(df["mortgage"])

    df_fixed.to_csv(IMPUTADOS_DIR / "interest_fixed_imputado.csv", sep=";", index=False)
    df_nominal.to_csv(IMPUTADOS_DIR / "interest_nominal_imputado.csv", sep=";", index=False)
    df_real.to_csv(IMPUTADOS_DIR / "interest_real_imputado.csv", sep=";", index=False)

    return df_fixed, df_nominal, df_real

# --------------------------------------------------------------------------------------
# 4. VISUALIZACIONES
# --------------------------------------------------------------------------------------

def _plot(df_orig: pd.DataFrame, df_imp: pd.DataFrame, col: str, title: str, fname: str):
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(pd.to_datetime(df_orig["date"], format=DATE_FMT_MONTH), df_orig[col], label="Original")
    ax.plot(pd.to_datetime(df_imp["date"], format=DATE_FMT_MONTH), df_imp[col], "--", label="Imputado")
    ax.set(title=title, xlabel="Fecha", ylabel=col.capitalize())
    ax.grid(True)
    ax.legend()
    fig.tight_layout()
    fig.savefig(VIS_DIR / fname)
    plt.close(fig)


def generate_visualizations(df_nominal: pd.DataFrame, df_nom_imp: pd.DataFrame,
                            df_real: pd.DataFrame, df_real_imp: pd.DataFrame):
    _plot(df_nominal, df_nom_imp, "interest", "Interest Nominal", "interest_nominal.png")
    _plot(df_nominal, df_nom_imp, "mortgage", "Mortgage Nominal", "mortgage_nominal.png")
    _plot(df_real, df_real_imp, "interest", "Interest Real", "interest_real.png")
    _plot(df_real, df_real_imp, "mortgage", "Mortgage Real", "mortgage_real.png")

# --------------------------------------------------------------------------------------
# 5. MAIN
# --------------------------------------------------------------------------------------

def main():
    print("\n>> Descargando datos…")
    df_ecb = fetch_ecb_interest_rates()
    df_bde = fetch_bde_mortgage_rates()
    df_hicp = fetch_eurostat_hicp()

    print(">> Generando CSVs base…")
    create_interest_fixed()
    df_nominal = create_interest_nominal(df_ecb, df_bde)
    create_interest_real(df_nominal, df_hicp)

    print(">> Imputando valores faltantes…")
    df_fixed, df_nom_imp, df_real_imp = impute_datasets()

    print(">> Creando visualizaciones…")
    generate_visualizations(df_nominal, df_nom_imp,
                            pd.read_csv("interest_real.csv", sep=";"), df_real_imp)

    print(
        "\nProceso ETL completado.\n"
        f"- Datos: {DATA_DIR.absolute()}\n"
        f"- Imputados: {IMPUTADOS_DIR.absolute()}\n"
        f"- Gráficos: {VIS_DIR.absolute()}"
    )


if __name__ == "__main__":
    main()