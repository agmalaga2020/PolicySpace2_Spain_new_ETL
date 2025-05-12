# Adaptación de Datos: Mortalidad por CCAA y Sexo

**Ruta Relativa de los Datos Fuente:** `ETL/df_mortalidad_ccaa_sexo/mortalidad_policyspace_es/`
**Ejemplos de Nombres de Archivo:** `mortality_men_{ccaa_code}.csv`, `mortality_women_{ccaa_code}.csv`

Este documento describe los pasos que realicé para adaptar y verificar el uso de los datos de mortalidad para la simulación de PolicySpace2 con datos españoles.

## Problema Inicial Identificado

Durante las ejecuciones de la simulación (inicialmente para el año 2010, ahora para 2014), observé la siguiente advertencia/error (antes de la corrección):
```
ERROR:simulation:ERROR loading/processing Spanish mortality data: 'year'. Mortality data might be incomplete/incorrect.
```
Este error ocurría porque la lógica inicial en `simulation.py` intentaba cargar los datos de mortalidad desde un único archivo agregado (`ETL/df_mortalidad_ccaa_sexo/df_mortalidad_final.csv`) y encontraba problemas al procesar o filtrar por la columna de año para el año de simulación.

## Pasos de Adaptación y Verificación

1.  **Identificación de la Fuente de Datos Correcta:**
    *   Se me indicó que los datos de mortalidad desglosados se encuentran en archivos individuales por Comunidad Autónoma (CCAA) y sexo, dentro del directorio `ETL/df_mortalidad_ccaa_sexo/mortalidad_policyspace_es/`.
    *   Verifiqué que los nombres de archivo siguen el patrón `mortality_{sexo}_{ccaa_code}.csv` (ej. `mortality_men_01.csv`).
    *   Confirmé la estructura de estos archivos: contienen una columna `Edad` y luego columnas por año con las tasas de mortalidad.

2.  **Modificación de la Lógica de Carga en `simulation.py`:**
    *   Actualicé el método `__init__` de la clase `Simulation` para implementar una nueva estrategia de carga:
        1.  **Mapeo CPRO a CCAA:** Cargué el archivo `ETL/indicadores_fecundidad_municipio_provincias/codigos_ccaa_provincias.csv` para obtener un mapeo de los códigos de provincia (`CPRO`) a los códigos de Comunidad Autónoma (`CODAUTO`). Limpié y formateé los códigos para asegurar la correspondencia.
        2.  **Iteración por Sexo y Provincia:** El código ahora itera para cada sexo (`male`, `female`) y para cada código de provincia (`cpro_code`) que se está simulando.
        3.  **Determinación del Archivo:** Para cada combinación de sexo y provincia, obtengo el `ccaa_code` correspondiente y construyo el nombre del archivo de mortalidad específico.
        4.  **Lectura y Procesamiento del Archivo Específico:**
            *   Leo el archivo CSV de mortalidad para la CCAA y sexo determinados.
            *   Busco la columna correspondiente al año de simulación (`self.geo.year`, actualmente 2014). Si no se encuentra, implemento una lógica de fallback para usar el año más reciente disponible en el archivo que sea menor o igual al año de simulación. (Para 2014, los datos se cargan directamente ya que están disponibles).
            *   Extraigo la columna de edad (`Edad`) y la columna de tasas del año seleccionado.
            *   Renombro estas columnas a `age` y `rate` respectivamente.
            *   Convierto los datos a tipo numérico y elimino filas con NaNs.
        5.  **Almacenamiento de Datos:** Si el procesamiento es exitoso, el DataFrame resultante se agrupa por `age` y se almacena en `self.mortality[sex_label_loop][cpro_code]`.
        6.  **Manejo de Errores:** Incluí bloques `try-except` para `FileNotFoundError` y otras excepciones, asignando un DataFrame agrupado vacío por defecto y registrando una advertencia/error si es necesario.

3.  **Resultado de la Verificación (Simulación para 2014):**
    *   Tras aplicar los cambios, ejecuté la simulación (`python main.py run`) para el año 2014 con los municipios '01001' y '01008'.
    *   El error `ERROR:simulation:ERROR loading/processing Spanish mortality data: 'year'.` (que ocurría con la lógica anterior) **no apareció**.
    *   En su lugar, aparecieron mensajes informativos indicando la carga exitosa para 2014:
        ```
        INFO:simulation:Starting Spanish mortality data loading process...
        INFO:simulation:Successfully loaded mortality data for CPRO 01 (CCAA 16), Sex male, Year 2014.
        INFO:simulation:Successfully loaded mortality data for CPRO 01 (CCAA 16), Sex female, Year 2014.
        INFO:simulation:Finished processing Spanish mortality data based on individual CCAA/sex files.
        ```

## Estado Actual del Procesamiento de Datos de Mortalidad
He corregido la lógica para cargar los datos de mortalidad, y ahora utiliza los archivos individuales por CCAA y sexo. Los datos para el año de simulación 2014 se cargan directamente y correctamente para las provincias/CCAA procesadas.
