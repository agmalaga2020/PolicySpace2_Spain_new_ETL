#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
procesar_pie.py

Script para procesar el archivo pie_final.csv y generar un nuevo archivo pie_final_final.csv
que excluya registros donde el año sea 2005.

También identifica y reporta valores NaN o problemas en el dataset.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import os
import sys

# --- Configuración de rutas relativas ---
# Obtener el directorio donde se encuentra este script
SCRIPT_DIR = Path(__file__).resolve().parent

# Archivo de entrada (ruta relativa)
INPUT_FILE = SCRIPT_DIR / "data/raw/finanzas/liquidaciones/preprocess/pie_final.csv"
# Archivo de salida (en el mismo directorio que el de entrada)
OUTPUT_FILE = SCRIPT_DIR / "data/raw/finanzas/liquidaciones/preprocess/pie_final_final.csv"

# Verificar si el archivo existe
if not os.path.exists(INPUT_FILE):
    print(f"Error: El archivo {INPUT_FILE} no existe.")
    sys.exit(1)
    
print(f"Verificado: El archivo de entrada existe: {INPUT_FILE}")

def main():
    try:
        print(f"Procesando archivo: {INPUT_FILE}")
        
        # Cargar el dataset
        df = pd.read_csv(INPUT_FILE, encoding='utf-8')
        
        # Mostrar información del dataset cargado
        print(f"\nDimensiones originales: {df.shape}")
        print(f"Columnas: {', '.join(df.columns)}")
        
        # Verificar si hay valores NaN
        nan_counts = df.isna().sum()
        print("\nValores NaN por columna:")
        for col, count in nan_counts.items():
            print(f"  {col}: {count}")
        
        # Verificar años presentes en el dataset
        years = df['año'].unique()
        years.sort()
        print(f"\nAños presentes en el dataset: {years}")
        
        # Contar registros por año
        print("\nRegistros por año:")
        year_counts = df['año'].value_counts().sort_index()
        for year, count in year_counts.items():
            print(f"  {year}: {count}")
        
        # Filtrar registros donde el año no sea 2005
        print("\nExcluyendo registros del año 2005...")
        df_filtered = df[df['año'] != 2005]
        print(f"Registros después del filtrado: {df_filtered.shape[0]} (eliminados: {df.shape[0] - df_filtered.shape[0]})")

        # --- Crear columna mun_code ---
        print("\nCreando columna 'mun_code'...")
        # Asegurar que las columnas son string para poder usar .str y .split
        # Es importante manejar el caso de que ya sean strings o sean numéricos (float/int)
        df_filtered['codigo_provincia'] = df_filtered['codigo_provincia'].astype(str)
        df_filtered['codigo_municipio'] = df_filtered['codigo_municipio'].astype(str)

        df_filtered['codigo_provincia_fmt'] = df_filtered['codigo_provincia'].apply(lambda x: x.split('.')[0]).str.zfill(2)
        df_filtered['codigo_municipio_fmt'] = df_filtered['codigo_municipio'].apply(lambda x: x.split('.')[0]).str.zfill(3)
        df_filtered['mun_code'] = df_filtered['codigo_provincia_fmt'] + df_filtered['codigo_municipio_fmt']
        
        print("Columna 'mun_code' creada.")
        # Mostrar una muestra para verificar, si el dataframe no es muy grande o seleccionar unas pocas columnas
        if not df_filtered.empty:
            print(f"Muestra de columnas relevantes con mun_code:\n{df_filtered[['codigo_provincia', 'codigo_municipio', 'mun_code', 'año']].head()}")
        else:
            print("DataFrame filtrado está vacío, no se puede mostrar muestra de mun_code.")
        
        # Guardar el dataset procesado
        df_filtered.to_csv(OUTPUT_FILE, index=False, encoding='utf-8')
        print(f"\nArchivo guardado exitosamente en: {OUTPUT_FILE}")
        
    except Exception as e:
        print(f"Error en la función main: {e}")

if __name__ == "__main__":
    print("Iniciando procesamiento de pie_final.csv")
    try:
        main()
        print("Procesamiento completado exitosamente.")
    except Exception as e:
        print(f"Error general: {e}")
