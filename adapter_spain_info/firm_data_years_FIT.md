# Adaptación de Datos: Alineación de Años para `FirmData`

**Datos Fuente:** `ETL/empresas_municipio_actividad_principal/preprocesados/empresas_municipio_actividad_principal.csv`
**Módulo Afectado:** `world/firms.py` (Clase `FirmData`)

Este documento describe los pasos realizados para alinear los años `t0` y `t1` utilizados por la clase `FirmData` para calcular el crecimiento histórico de las empresas, con el objetivo de que sean más relevantes para el año de simulación (2014).

## Problema Inicial Identificado
La clase `FirmData` calculaba el crecimiento promedio mensual de las empresas basándose en el número de empleados en un año inicial `t0` y un año final `t1`. Originalmente, estos estaban configurados como `t0_year = 2013` y `t1_year = 2022`. Para una simulación que comienza en 2014, el año `t1=2022` resultaba distante, y el periodo de 9 años para calcular el crecimiento podría no reflejar las tendencias más pertinentes para la dinámica inicial de la simulación.

## Pasos de Adaptación y Verificación

1.  **Exploración de Datos Disponibles:**
    *   Se creó y ejecutó el script `auxiliary/explore_firm_data_periods.py` para analizar el archivo `ETL/empresas_municipio_actividad_principal/preprocesados/empresas_municipio_actividad_principal.csv`.
    *   Se encontró que existen datos consistentes para los años 2012 a 2024 inclusive, con 8115 registros por año.

2.  **Decisión sobre Nuevos Años `t0` y `t1`:**
    *   Para una simulación que comienza en 2014, se decidió utilizar:
        *   `t0_year = 2014`: El propio año de inicio de la simulación como base.
        *   `t1_year = 2019`: Un periodo de 5 años (2014-2019) para calcular la tasa de crecimiento. Esto utiliza datos posteriores al inicio de la simulación para proyectar el crecimiento, lo cual es una aproximación común, y acorta el periodo de cálculo respecto al anterior.

3.  **Modificación de `world/firms.py` (Clase `FirmData`):**
    *   En el método `__init__`:
        *   Se actualizaron las variables `t0_year` a `2014` y `t1_year` a `2019`.
        *   Se mejoró la lógica de fallback para `actual_t1_year_for_calc`:
            *   Primero intenta usar el `t1_year` especificado (2019).
            *   Si no hay datos para ese año, busca el año más reciente disponible que sea menor o igual a `t1_year` y mayor o igual a `t0_year`.
            *   Si no se encuentra un `actual_t1_year_for_calc` válido, o si es menor o igual a `t0_year`, el crecimiento (`avg_monthly_deltas`) se establece en 0.
    *   Se ajustó el cálculo de `num_months` para basarse en `actual_t1_year_for_calc` y `t0_year`.

4.  **Resultado de la Verificación:**
    *   Se ejecutó la simulación (`python main.py run`).
    *   Los logs de inicio confirmaron la correcta inicialización de `FirmData` con los nuevos años:
        `INFO:world.firms:FirmData initialized. t0_year=2014, Target t1_year=2019, Actual t1_year_used=2019.`
        `INFO:world.firms:Calculated avg_monthly_deltas for 8111 municipalities.`
    *   La simulación (aunque detenida manualmente por el usuario en una prueba anterior por otros motivos) inició correctamente con estos cambios, indicando que la lógica de `FirmData` es compatible con los nuevos años.

## Estado Actual
La clase `FirmData` ahora utiliza un periodo de referencia (2014-2019) más alineado con el año de inicio de la simulación (2014) para calcular las tasas de crecimiento de las empresas. La lógica de selección de años y cálculo de deltas se ha robustecido.
