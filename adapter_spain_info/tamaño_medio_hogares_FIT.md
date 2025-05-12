# Adaptación de Datos: Modelo Predictivo para Tamaño Medio de Hogares por CCAA

**Datos Fuente Originales:** `ETL/tamaño_medio_hogares_ccaa/data_final/tamaño_medio_hogares_ccaa_completo.csv` (con datos para 2021-2025)
**Script de Predicción:** `ETL/tamaño_medio_hogares_ccaa/predict_household_size.py`
**Datos Generados:** `ETL/tamaño_medio_hogares_ccaa/datos_prediccion/predicted_household_sizes_by_ccaa.csv`
**Plots Generados:** `ETL/tamaño_medio_hogares_ccaa/datos_prediccion/plots/household_size_ccaa_{ccaa_code}.png`

Este documento describe los pasos que realicé para crear un modelo predictivo para el tamaño medio de los hogares por Comunidad Autónoma (CCAA) y para integrar estos datos en la simulación de PolicySpace2.

## Problema Inicial Identificado
Originalmente, la simulación utilizaba un parámetro global `MEMBERS_PER_FAMILY` definido en `conf/default/params.py` para determinar el tamaño de las familias creadas. Esto no reflejaba las variaciones regionales (por CCAA) ni temporales en el tamaño medio de los hogares. Se disponía de datos ETL para el tamaño medio de los hogares por CCAA para los años 2021-2025, pero la simulación se ejecuta para el año 2014.

## Pasos de Adaptación y Verificación

1.  **Creación de un Modelo Predictivo (`predict_household_size.py`):**
    *   Desarrollé un script en Python ubicado en `ETL/tamaño_medio_hogares_ccaa/predict_household_size.py`.
    *   Este script carga los datos de `ETL/tamaño_medio_hogares_ccaa/data_final/tamaño_medio_hogares_ccaa_completo.csv`.
    *   Para cada CCAA presente en los datos:
        *   Utiliza los datos de los años 2021-2025 como conjunto de entrenamiento.
        *   Entrena un modelo de Regresión Lineal simple (`sklearn.linear_model.LinearRegression`) donde el tamaño medio del hogar es la variable dependiente y el año es la variable independiente.
        *   Calcula estadísticas del modelo sobre los datos de entrenamiento (2021-2025), como R² (coeficiente de determinación), la pendiente y el intercepto de la regresión.
        *   Utiliza el modelo entrenado para predecir (extrapolar hacia atrás) los valores del tamaño medio del hogar para los años 2010 a 2020 (incluyendo el año de simulación 2014).
    *   **Salidas del Script:**
        *   Guarda un archivo CSV (`ETL/tamaño_medio_hogares_ccaa/datos_prediccion/predicted_household_sizes_by_ccaa.csv`) que contiene tanto los datos reales (2021-2025) como los predichos (2010-2020) para cada CCAA, con una columna `is_predicted` para diferenciarlos.
        *   Guarda un archivo CSV (`ETL/tamaño_medio_hogares_ccaa/datos_prediccion/prediction_model_stats_by_ccaa.csv`) con las estadísticas R², pendiente e intercepto para el modelo de cada CCAA.
        *   Genera y guarda gráficos de dispersión para cada CCAA en `ETL/tamaño_medio_hogares_ccaa/datos_prediccion/plots/`. Estos gráficos muestran los datos reales, los datos predichos, la línea de tendencia de la regresión y el valor de R² del ajuste a los datos de entrenamiento.
    *   Ejecuté el script (versión actualizada), que generó exitosamente los archivos CSV de predicciones, estadísticas del modelo y los gráficos. Los valores de R² para el ajuste en los datos de 2021-2025 variaron por CCAA (ej. desde ~0.1 hasta ~0.8), lo que indica diferentes grados de ajuste lineal en el periodo de entrenamiento y, por ende, diferentes niveles de confianza en la extrapolación.

2.  **Integración de los Datos Predichos en la Simulación:**
    *   **Modificación de `world/generator.py` (Clase `Generator`):**
        *   En el método `__init__`:
            *   Se carga el archivo `predicted_household_sizes_by_ccaa.csv`.
            *   Los datos se almacenan en `self.avg_household_size_data` como una Serie de pandas con un MultiIndex (`ccaa_code`, `year`) para una búsqueda eficiente.
        *   En el método `create_all` (dentro del bucle que itera por regiones):
            *   Se obtiene el `ccaa_code` correspondiente al `region_id` (código INE municipal) utilizando el mapeo `self.df_equivalencias_map_ine_to_ccaa`.
            *   Se obtiene el año actual de la simulación (`self.sim.clock.year`).
            *   Se busca el tamaño medio del hogar para la CCAA y el año específicos en `self.avg_household_size_data`.
            *   Si se encuentra un valor válido, se utiliza para calcular `num_families` para esa región.
            *   Si no se encuentra (o el `ccaa_code` no se puede mapear), se recurre al valor global `self.sim.PARAMS['MEMBERS_PER_FAMILY']` y se registra una advertencia.
    *   **Modificación de `world/population.py` (Función `immigration`):**
        *   Se implementó una lógica similar para utilizar el tamaño medio del hogar específico de la CCAA (obtenido de `sim.generator.avg_household_size_data`) al calcular el número de familias para los nuevos agentes inmigrantes. También incluye un fallback al parámetro global.

3.  **Ajuste del Parámetro `PERCENTAGE_ACTUAL_POP`:**
    *   Como parte de las mejoras generales y para obtener una escala de simulación más representativa, el parámetro `PERCENTAGE_ACTUAL_POP` en `conf/default/params.py` se ajustó de `0.01` (1%) a `0.1` (10%).

4.  **Resultado de la Verificación (Simulación para 2014):**
    *   Tras aplicar todos los cambios, ejecuté la simulación (`python main.py run`) para el año 2014.
    *   Los logs confirmaron la carga exitosa de los datos predichos del tamaño medio de los hogares:
        `INFO:generator:Successfully loaded predicted average household size data from .../ETL/tamaño_medio_hogares_ccaa/datos_prediccion/predicted_household_sizes_by_ccaa.csv`
    *   Durante la creación de agentes, los logs mostraron el uso de valores específicos por CCAA, por ejemplo:
        `INFO:generator:Using CCAA 16 specific household size for year 2014: 2.35 for region 01001`
    *   La simulación se completó exitosamente con el nuevo `PERCENTAGE_ACTUAL_POP` de `0.1`, resultando en una población escalada total de `391900`.

## Estado Actual
El modelo ahora utiliza estimaciones del tamaño medio de los hogares específicas por CCAA y año (para 2014, basadas en predicciones), en lugar de un único parámetro global. Esto debería mejorar la heterogeneidad regional de las estructuras familiares en la simulación. El parámetro de escala de población también se ha incrementado.
