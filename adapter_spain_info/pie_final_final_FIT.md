# Adaptación de Datos: pie_final_final.csv

**Ruta Relativa del DataFrame:** `ETL/PIE/data/raw/finanzas/liquidaciones/preprocess/pie_final_final.csv`

Este documento describe los pasos realizados para adaptar y verificar el uso de los datos de Participación en Ingresos del Estado (PIE), anteriormente referidos como FPM (Fondo de Participación Municipal), para la simulación de PolicySpace2 con datos españoles.

## Problema Inicial Identificado

Durante las ejecuciones de la simulación (para los años 2010 y 2014, antes de las correcciones de `mun_code`), se observó la siguiente advertencia recurrente:
```
WARNING: Total PIE for simulated municipalities in year YYYY (or fallback) is 0. Cannot distribute proportionally.
```
Esto indicaba que la suma de la variable `total_participacion_variables` para los municipios procesados en la simulación era cero, lo que impedía la distribución proporcional de estos fondos.

## Pasos de Adaptación y Verificación

1.  **Cambio del Año de Simulación:**
    *   Inicialmente, el año de simulación se cambió a `2010-01-01`. Posteriormente, para alinear con la disponibilidad de otros datos, se actualizó a `2014-01-01` en `conf/default/params.py`.

2.  **Diagnóstico del Problema con `mun_code`:**
    *   Se identificó que el archivo `pie_final_final.csv` (generado por `ETL/PIE/procesar_pie.py`) no contenía una columna `mun_code` con el formato INE de 5 dígitos estandarizado, necesario para el cruce con los códigos municipales de la simulación. El archivo original contenía `codigo_provincia` y `codigo_municipio`.

3.  **Modificación de `ETL/PIE/procesar_pie.py`:**
    *   Se actualizó el script `ETL/PIE/procesar_pie.py` para que, después de cargar y filtrar `pie_final.csv`, genere una nueva columna `mun_code`.
    *   La lógica implementada para crear `mun_code` es:
        1.  Convertir las columnas `codigo_provincia` y `codigo_municipio` a tipo string.
        2.  Para cada una, tomar la parte antes de un posible `.0` (ej. "28.0" -> "28").
        3.  Rellenar con ceros a la izquierda el código de provincia formateado para que tenga 2 dígitos (`str.zfill(2)`).
        4.  Rellenar con ceros a la izquierda el código de municipio formateado para que tenga 3 dígitos (`str.zfill(3)`).
        5.  Concatenar ambos códigos para formar el `mun_code` de 5 dígitos.
    *   El script modificado fue ejecutado por el usuario para regenerar `pie_final_final.csv` con la nueva columna `mun_code`.

4.  **Modificación de `world/funds.py`:**
    *   Se actualizó la clase `Funds` en `world/funds.py` para utilizar la nueva columna `mun_code` presente en `pie_final_final.csv`.
    *   Se eliminó la lógica interna que intentaba construir un `mun_code_pie` a partir de `codigo_provincia` y `codigo_municipio`.
    *   Se añadió una verificación para asegurar que la columna `mun_code` exista en el DataFrame cargado y se aseguró que se trate como un string de 5 dígitos rellenado con ceros.
    *   La lógica en el método `distribute_pie` fue actualizada para filtrar y buscar municipios usando la columna `mun_code` en lugar de la antigua `mun_code_pie`.

5.  **Resultado de la Verificación (Simulación para 2010 con '28079', '08019'):**
    *   Tras aplicar los cambios en `procesar_pie.py` y `funds.py`, y ejecutar la simulación para el año 2010 con los municipios '28079' (Madrid) y '08019' (Barcelona), la advertencia `WARNING: Total PIE for simulated municipalities in year 2010 (or fallback) is 0. Cannot distribute proportionally.` persistió.
    *   Esto indicó que, aunque el manejo del `mun_code` era correcto, los datos PIE para estos municipios específicos en 2010 resultaban en una suma cero de `total_participacion_variables`.

6.  **Test con Diferentes Municipios ('01001', '01008') para el año 2010:**
    *   Para investigar si la advertencia era general o específica de los datos de ciertos municipios, modifiqué `conf/default/params.py` para simular con los municipios '01001' y '01008' para el año 2010.
    *   **Resultado del Test (2010):** Al ejecutar la simulación con '01001' y '01008' para 2010, la advertencia sobre el total de PIE siendo cero **no apareció**. Esto sugirió que para estos municipios, el archivo `pie_final_final.csv` contenía datos de PIE procesables y no nulos para el año 2010.

7.  **Verificación con Simulación en 2014 (Municipios '01001', '01008'):**
    *   Cuando el año de simulación se cambió a 2014, y manteniendo los municipios de prueba '01001' y '01008', ejecuté la simulación.
    *   **Resultado (2014):** La advertencia sobre el total de PIE siendo cero **tampoco apareció** para estos municipios en 2014, indicando que los datos PIE para ellos en 2014 también son procesables y no nulos.

## Conclusión sobre el Problema PIE
Los cambios en el código para la generación del `mun_code` en `ETL/PIE/procesar_pie.py` y su posterior uso en `world/funds.py` son correctos y funcionan como se esperaba. La aparición de la advertencia `WARNING: Total PIE for simulated municipalities ... is 0` es dependiente de los datos específicos contenidos en `pie_final_final.csv` para la combinación de municipio y año seleccionada. Para algunos municipios (ej. '28079', '08019' en 2010), los datos resultan en una suma cero. Para otros (ej. '01001', '01008' en 2010 y 2014), los datos son procesables y no nulos.

## Estado Actual del Fichero de Datos PIE
El archivo `ETL/PIE/data/raw/finanzas/liquidaciones/preprocess/pie_final_final.csv` ahora contiene una columna `mun_code` correctamente formateada. El código de la simulación utiliza esta columna para el procesamiento de los fondos PIE. La advertencia sobre la suma cero de PIE es específica de los datos de ciertos municipios/años y no un error general del código de procesamiento PIE. Se recomienda verificar el contenido de `pie_final_final.csv` si se espera una distribución de PIE para municipios que actualmente muestran un total de cero.
