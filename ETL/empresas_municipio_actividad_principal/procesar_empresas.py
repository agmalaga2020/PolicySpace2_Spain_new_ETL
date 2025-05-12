#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
procesar_empresas.py

Script para procesar el archivo empresas_municipio_actividad_principal.csv
y generar un nuevo archivo pie_final_final.csv que excluya registros donde el año sea 2005.

También identifica y reporta valores NaN o valores potencialmente problemáticos.
"""

import pandas as pd
import numpy as np
import os
from pathlib import Path

# --- Configuración de rutas ---
# Directorio del script
BASE_DIR = Path(__file__).resolve().parent
# Archivo de entrada
INPUT_FILE = BASE_DIR / "preprocesados" / "empresas_municipio_actividad_principal.csv"
# Archivo de salida
OUTPUT_FILE = BASE_DIR / "pie_final_final.csv"

def main():
    print(f"Procesando archivo: {INPUT_FILE}")
    
    # Cargar el dataset
    df = pd.read_csv(INPUT_FILE)
    
    # Mostrar información del dataset cargado
    print(f"\nDimensiones originales: {df.shape}")
    print(f"Columnas: {', '.join(df.columns)}")
    
    # Verificar si hay valores NaN
    nan_counts = df.isna().sum()
    print("\nValores NaN por columna:")
    for col, count in nan_counts.items():
        print(f"  {col}: {count}")
    
    # Verificar años presentes en el dataset
    years = df['Periodo'].unique()
    years.sort()
    print(f"\nAños presentes en el dataset: {years}")
    
    # Filtrar registros donde el año no sea 2005
    if 2005 in years:
        print("\nExcluyendo registros del año 2005...")
        df_filtered = df[df['Periodo'] != 2005]
        print(f"Registros después del filtrado: {df_filtered.shape[0]} (eliminados: {df.shape[0] - df_filtered.shape[0]})")
    else:
        print("\nNo se encontraron registros del año 2005. No se realizó filtrado.")
        df_filtered = df
    
    # Buscar valores potencialmente problemáticos (como números muy grandes o muy pequeños)
    if 'Total' in df.columns:
        print("\nEstadísticas de la columna 'Total':")
        print(f"  Min: {df_filtered['Total'].min()}")
        print(f"  Max: {df_filtered['Total'].max()}")
        print(f"  Media: {df_filtered['Total'].mean():.2f}")
        print(f"  Mediana: {df_filtered['Total'].median()}")
        
        # Identificar valores atípicos usando IQR
        Q1 = df_filtered['Total'].quantile(0.25)
        Q3 = df_filtered['Total'].quantile(0.75)
        IQR = Q3 - Q1
        outliers = df_filtered[(df_filtered['Total'] < (Q1 - 1.5 * IQR)) | 
                              (df_filtered['Total'] > (Q3 + 1.5 * IQR))]
        if not outliers.empty:
            print(f"\nEncontrados {len(outliers)} valores atípicos en la columna 'Total'")
            print("Ejemplo de valores atípicos:")
            print(outliers.head(5) if len(outliers) > 5 else outliers)
    
    # Guardar el dataset procesado
    df_filtered.to_csv(OUTPUT_FILE, index=False)
    print(f"\nArchivo guardado exitosamente en: {OUTPUT_FILE}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
