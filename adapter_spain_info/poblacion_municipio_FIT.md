# Adaptación de Datos: Población Municipal desde ETL

**Ruta Relativa de los Datos Fuente:** `ETL/cifras_poblacion_municipio/data_final/drive-download-20250506T180657Z-001/`
**Ejemplos de Nombres de Archivo:** `cifras_municipio_hombres_{YYYY}.csv`, `cifras_municipio_mujeres_{YYYY}.csv`

Este documento describe los pasos que realicé para adaptar y verificar el uso de los datos de población municipal españoles procesados por ETL para la simulación de PolicySpace2.

## Problema Inicial Identificado
La simulación originalmente cargaba datos de población desde la carpeta `input/` (ej. `input/pop_men_2010.csv`). Estos archivos no correspondían a las fuentes de datos españolas procesadas y disponibles en la carpeta `ETL/`. Era necesario modificar la lógica de carga para utilizar los archivos ETL correctos, que además presentaban un formato diferente (largo, con edad simple) al esperado por la función original (ancho, con grupos de edad).

## Pasos de Adaptación y Verificación

1.  **Identificación de la Fuente de Datos Correcta:**
    *   El usuario me indicó que los datos de población procesados por ETL se encuentran en `ETL/cifras_poblacion_municipio/data_final/drive-download-20250506T180657Z-001/`.
    *   Los archivos en esta carpeta siguen el patrón `cifras_municipio_{sexo}_{año}.csv` (ej. `cifras_municipio_hombres_2014.csv`).
    *   El usuario proporcionó una fila de ejemplo: `sexo,municipio_code,municipio_name,edad,periodo,total` con valores como `Hombres,44001,Ababuj,0,2004,0.0`. Esto confirmó que los archivos son CSV delimitados por comas y están en formato largo, con una fila por cada edad simple.

2.  **Modificación de la Lógica de Carga en `world/population.py` (función `load_pops`):**
    *   **Ruta y Nombres de Archivo:** Actualicé la función para construir las rutas a los archivos correctos en el subdirectorio ETL mencionado, usando los nombres `cifras_municipio_hombres_{año}.csv` y `cifras_municipio_mujeres_{año}.csv`.
    *   **Lectura de CSV:** Se utiliza `pd.read_csv(filepath, sep=',')`.
    *   **Fallback de Año:** Se mantiene la lógica de fallback para el año, utilizando la lista `POPULATION_AVAILABLE_YEARS` (actualizada en `conf/default/params.py` para reflejar los años disponibles en la nueva ruta ETL).
    *   **Procesamiento de Datos (Formato Largo a Ancho):**
        1.  Para cada archivo de sexo/año cargado (`pop_df_raw`):
        2.  Se validan las columnas esperadas (`municipio_code`, `edad`, `total`).
        3.  La columna `municipio_code` se convierte a string de 5 dígitos y se filtra por los municipios de la simulación (`mun_codes_sim`).
        4.  Las columnas `edad` y `total` se convierten a tipo numérico.
        5.  Se crean grupos de edad estándar (ej. '0--4', '5--9', ..., '85+') usando `pd.cut` sobre la columna `edad`.
        6.  Los datos se agrupan por `municipio_code` y el nuevo `age_group`, sumando la columna `total`.
        7.  La tabla agrupada se pivota (unstack) para que los `age_group` se conviertan en columnas.
        8.  Se asegura que todas las columnas de grupos de edad canónicos estén presentes, rellenando con 0 las faltantes.
        9.  La columna `municipio_code` se renombra a `code`.
        10. El DataFrame procesado se almacena en `pops[gender_key]`.
    *   **Datos AP:** La carga y procesamiento de datos específicos de "Áreas de Ponderación" (AP) se omite, ya que no tienen un equivalente directo en los nuevos archivos ETL municipales y no son críticos si `SIMPLIFY_POP_EVOLUTION` es `True`. Se registra una advertencia.
    *   **Llamada a `simplify_pops`:** Si `SIMPLIFY_POP_EVOLUTION` es `True` (por defecto), se llama a `simplify_pops` con los DataFrames procesados (que ahora tienen columnas '0--4', '5--9', etc.). Se adaptó `simplify_pops` para intentar manejar estas columnas de rango de edad.

3.  **Resultado de la Verificación (Simulación para 2014):**
    *   Tras aplicar los cambios, ejecuté la simulación (`python main.py run`) para el año 2014.
    *   Los logs confirmaron la carga exitosa de los datos de población para hombres y mujeres desde los nuevos archivos ETL:
        ```
        INFO:world.population:Starting Spanish population data load from ETL for target year 2014.
        INFO:world.population:Successfully loaded population data for male for year 2014 from .../ETL/cifras_poblacion_municipio/data_final/drive-download-20250506T180657Z-001/cifras_municipio_hombres_2014.csv
        INFO:world.population:Successfully loaded population data for female for year 2014 from .../ETL/cifras_poblacion_municipio/data_final/drive-download-20250506T180657Z-001/cifras_municipio_mujeres_2014.csv
        INFO:world.population:Calling simplify_pops. Input columns to simplify_pops will be '0--4', '5--9', etc.
        INFO:world.population:Finished loading and processing population data. Total scaled population: 39190
        ```
    *   La simulación se completó exitosamente, indicando que los datos de población fueron procesados y utilizados correctamente por el resto del modelo.

## Estado Actual del Procesamiento de Datos de Población
La lógica para cargar y procesar los datos de población ha sido adaptada exitosamente para utilizar los archivos ETL españoles. Los datos se cargan para el año de simulación especificado (con fallback si es necesario) y se transforman al formato ancho con grupos de edad que el modelo requiere.
