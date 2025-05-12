#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script mejorado para extraer datos específicos de los archivos de liquidación de la PIE
utilizando un enfoque más directo para manejar las estructuras complejas de los archivos Excel.
"""

import os
import json
import pandas as pd
import numpy as np
import warnings
from datetime import datetime

# Ignorar advertencias específicas para facilitar la lectura de la salida
warnings.filterwarnings('ignore', category=pd.errors.DtypeWarning)
warnings.filterwarnings('ignore', category=UserWarning)

def cargar_configuracion(ruta_config):
    """
    Carga la configuración para el script de extracción.
    
    Args:
        ruta_config: Ruta al archivo de configuración JSON
    
    Returns:
        Diccionario con la configuración
    """
    with open(ruta_config, 'r') as f:
        config = json.load(f)
    
    return config

def procesar_archivo_directo(archivo, config_archivo, directorio_entrada):
    """
    Procesa un archivo específico según su configuración con un enfoque más directo.
    
    Args:
        archivo: Nombre del archivo a procesar
        config_archivo: Configuración específica para este archivo
        directorio_entrada: Directorio donde se encuentra el archivo
    
    Returns:
        DataFrame con los datos extraídos
    """
    año = config_archivo['año']
    hoja_variables = config_archivo['hoja_variables']
    fila_encabezado = config_archivo['fila_encabezado']
    
    print(f"Procesando archivo: {archivo} (Año: {año})")
    
    # Si no hay hoja de variables definida, intentar usar hoja de liquidación
    if pd.isna(hoja_variables):
        if not pd.isna(config_archivo['hoja_liquidacion']):
            hoja_variables = config_archivo['hoja_liquidacion']
            print(f"  Usando hoja de liquidación: {hoja_variables}")
        else:
            print(f"  No se encontró hoja adecuada para procesar.")
            return pd.DataFrame()
    
    ruta_archivo = os.path.join(directorio_entrada, archivo)
    
    try:
        # Leer el archivo con la configuración específica
        df = pd.read_excel(ruta_archivo, sheet_name=hoja_variables, header=None)
        
        # Identificar la fila de encabezado
        if fila_encabezado >= 0 and fila_encabezado < len(df):
            # Usar la fila específica como encabezado
            headers = df.iloc[fila_encabezado].values
            df_data = df.iloc[fila_encabezado+1:].copy()
            df_data.columns = headers
            
            # Crear un nuevo DataFrame con las columnas identificadas
            result_df = pd.DataFrame()
            
            # Buscar columnas específicas por nombre
            for col in df_data.columns:
                col_str = str(col).lower()
                
                # Identificadores de municipio
                if 'prov' in col_str:
                    result_df['codigo_provincia'] = df_data[col]
                elif 'corp' in col_str:
                    result_df['codigo_municipio'] = df_data[col]
                elif col_str == 'nombre':
                    result_df['nombre_municipio'] = df_data[col]
                
                # Variables demográficas
                elif 'población' in col_str:
                    result_df['poblacion'] = df_data[col]
                
                # Variables fiscales
                elif 'esfuerzo' in col_str and 'fiscal' in col_str:
                    result_df['esfuerzo_fiscal'] = df_data[col]
                elif 'inverso' in col_str and 'capacidad' in col_str:
                    result_df['inverso_capacidad_tributaria'] = df_data[col]
                
                # Variables de distribución
                elif 'participación' in col_str and 'población' in col_str:
                    result_df['participacion_poblacion'] = df_data[col]
                elif 'participación' in col_str and 'esfuerzo' in col_str:
                    result_df['participacion_esfuerzo_fiscal'] = df_data[col]
                elif 'participación' in col_str and 'inverso' in col_str:
                    result_df['participacion_inverso_capacidad'] = df_data[col]
                elif 'total' in col_str and 'participación' in col_str and 'variables' in col_str:
                    result_df['total_participacion_variables'] = df_data[col]
            
            # Añadir columna de año
            result_df['año'] = año
            
            # Verificar si tenemos suficientes columnas
            if len(result_df.columns) < 4:  # Al menos necesitamos algunos identificadores y variables
                print(f"  No se identificaron suficientes columnas clave. Columnas identificadas: {list(result_df.columns)}")
                return pd.DataFrame()
            
            # Limpiar y convertir tipos de datos
            if 'codigo_provincia' in result_df.columns:
                result_df['codigo_provincia'] = result_df['codigo_provincia'].astype(str)
            
            if 'codigo_municipio' in result_df.columns:
                result_df['codigo_municipio'] = result_df['codigo_municipio'].astype(str)
            
            # Convertir columnas numéricas
            numeric_cols = ['poblacion', 'esfuerzo_fiscal', 'inverso_capacidad_tributaria', 
                           'participacion_poblacion', 'participacion_esfuerzo_fiscal', 
                           'participacion_inverso_capacidad', 'total_participacion_variables']
            
            for col in numeric_cols:
                if col in result_df.columns:
                    result_df[col] = pd.to_numeric(result_df[col], errors='coerce')
            
            # Filtrar filas con valores nulos en columnas clave
            if 'codigo_provincia' in result_df.columns and 'codigo_municipio' in result_df.columns:
                result_df = result_df[result_df['codigo_provincia'].notna() & result_df['codigo_municipio'].notna()]
            
            # Eliminar filas duplicadas
            result_df = result_df.drop_duplicates()
            
            print(f"  Procesado correctamente. Filas obtenidas: {len(result_df)}")
            print(f"  Columnas extraídas: {list(result_df.columns)}")
            
            return result_df
        else:
            print(f"  Índice de fila de encabezado fuera de rango: {fila_encabezado}")
            return pd.DataFrame()
    
    except Exception as e:
        print(f"  Error al procesar el archivo: {e}")
        return pd.DataFrame()

def procesar_archivos(config):
    """
    Procesa todos los archivos según la configuración.
    
    Args:
        config: Configuración para el script de extracción
    
    Returns:
        DataFrame con todos los datos extraídos
    """
    directorio_entrada = config['directorio_entrada']
    directorio_salida = config['directorio_salida']
    mapeo = config['mapeo']
    
    # Crear directorio de salida si no existe
    os.makedirs(directorio_salida, exist_ok=True)
    
    # Inicializar DataFrame para almacenar resultados
    df_final = pd.DataFrame()
    
    # Procesar cada archivo
    for config_archivo in mapeo:
        archivo = config_archivo['archivo']
        df_archivo = procesar_archivo_directo(archivo, config_archivo, directorio_entrada)
        
        # Si se obtuvieron datos, añadir al DataFrame final
        if not df_archivo.empty:
            df_final = pd.concat([df_final, df_archivo], ignore_index=True)
    
    return df_final

def guardar_resultados(df, directorio_salida):
    """
    Guarda los resultados en diferentes formatos.
    
    Args:
        df: DataFrame con los datos extraídos
        directorio_salida: Directorio donde guardar los resultados
    """
    if df.empty:
        print("No se obtuvieron datos para guardar.")
        return
    
    # Guardar CSV completo
    ruta_csv = os.path.join(directorio_salida, 'pie_final.csv')
    df.to_csv(ruta_csv, index=False)
    print(f"Datos guardados en CSV: {ruta_csv}")
    
    # Guardar Excel (por años para evitar problemas de memoria)
    try:
        ruta_excel = os.path.join(directorio_salida, 'pie_final.xlsx')
        with pd.ExcelWriter(ruta_excel) as writer:
            # Hoja con todos los datos
            df.to_excel(writer, sheet_name='Todos_los_años', index=False)
            
            # Una hoja por año
            for año, grupo in df.groupby('año'):
                grupo.to_excel(writer, sheet_name=f'Año_{año}', index=False)
        
        print(f"Datos guardados en Excel: {ruta_excel}")
    except Exception as e:
        print(f"Error al guardar Excel: {e}")
        print("Se guardó solo el archivo CSV.")
    
    # Guardar estadísticas
    try:
        stats = []
        for año, grupo in df.groupby('año'):
            stats_año = {
                'año': año,
                'num_municipios': len(grupo),
                'poblacion_total': grupo['poblacion'].sum() if 'poblacion' in grupo.columns else None,
                'poblacion_media': grupo['poblacion'].mean() if 'poblacion' in grupo.columns else None,
                'participacion_total': grupo['total_participacion_variables'].sum() if 'total_participacion_variables' in grupo.columns else None,
                'participacion_media': grupo['total_participacion_variables'].mean() if 'total_participacion_variables' in grupo.columns else None
            }
            stats.append(stats_año)
        
        df_stats = pd.DataFrame(stats)
        ruta_stats = os.path.join(directorio_salida, 'pie_estadisticas.xlsx')
        df_stats.to_excel(ruta_stats, index=False)
        print(f"Estadísticas guardadas en: {ruta_stats}")
    except Exception as e:
        print(f"Error al guardar estadísticas: {e}")

def main():
    """
    Función principal que ejecuta la extracción de datos.
    """
    # Cargar configuración
    ruta_config = '/home/agmalaga/Documentos/GitHub/JUST-TESTING/src/PIE/config_extraccion.json'
    config = cargar_configuracion(ruta_config)
    
    print(f"Configuración cargada desde: {ruta_config}")
    print(f"Directorio de entrada: {config['directorio_entrada']}")
    print(f"Directorio de salida: {config['directorio_salida']}")
    print(f"Variables clave a extraer: {config['variables_clave']}")
    print(f"Número de archivos a procesar: {len(config['mapeo'])}")
    print()
    
    # Procesar archivos
    df_final = procesar_archivos(config)
    
    # Guardar resultados
    guardar_resultados(df_final, config['directorio_salida'])
    
    # Mostrar resumen
    if not df_final.empty:
        print("\nResumen del dataset final:")
        print(f"Total de registros: {len(df_final)}")
        print(f"Años incluidos: {sorted(df_final['año'].unique())}")
        print(f"Columnas incluidas: {list(df_final.columns)}")
        
        # Verificar cobertura anual
        años_presentes = sorted(df_final['año'].unique())
        años_esperados = list(range(2003, 2023))
        años_faltantes = [año for año in años_esperados if año not in años_presentes]
        
        if años_faltantes:
            print("\nAños faltantes en el dataset:")
            for año in años_faltantes:
                print(f"  - {año}")
        else:
            print("\nEl dataset incluye datos para todos los años esperados (2003-2022).")
    else:
        print("\nNo se pudieron extraer datos de ningún archivo.")

if __name__ == "__main__":
    main()
