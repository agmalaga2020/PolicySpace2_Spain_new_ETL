# Adaptación de Datos: Nivel Educativo por Comunidades Autónomas

**Ruta Relativa de los Datos Fuente:** `ETL/nivel_educativo_comunidades/data_final/`
**Ejemplos de Nombres de Archivo:** `nivel_educativo_comunidades_{YYYY}.csv` (ej. `nivel_educativo_comunidades_2014.csv`)

Este documento describe los pasos que realicé para adaptar y verificar el uso de los datos de nivel educativo (cualificación) para la simulación de PolicySpace2 con datos españoles.

## Problema Inicial Identificado

Durante las ejecuciones de la simulación (inicialmente para el año 2010, ahora para 2014), observé la siguiente advertencia/error (antes de la corrección):
```
ERROR:generator:Error loading or processing Spanish qualification data: 'year'. Qualification will be default.
```
Este error ocurría porque la lógica inicial en `world/generator.py` (método `load_quali`) intentaba cargar los datos de cualificación desde un único archivo agregado (`nivel_educativo_comunidades_completo.csv`) y encontraba problemas al procesar o filtrar por la columna `year` para el año de simulación.

## Pasos de Adaptación y Verificación

1.  **Identificación de la Fuente y Estructura de Datos Correcta:**
    *   Observé que los datos de nivel educativo se encuentran en archivos individuales por año, con el año codificado en el nombre del archivo (ej. `nivel_educativo_comunidades_2014.csv`), dentro del directorio `ETL/nivel_educativo_comunidades/data_final/`.
    *   Verifiqué que los datos para el año de simulación 2014 están disponibles directamente en dicha carpeta (`nivel_educativo_comunidades_2014.csv`).
    *   Analicé la estructura del archivo `nivel_educativo_comunidades_2014.csv`: la primera columna es `ccaa_code`, y las siguientes son los niveles educativos (ej. '1.0', '2.0', '3.0', '5.0', '6.0', '7.0', notando la ausencia del nivel '4.0'), con valores porcentuales.

2.  **Modificación de la Lógica de Carga en `world/generator.py`:**
    *   **Actualización del método `__init__`:**
        *   Almacené los parámetros del método `years_study` en `self.years_study_parameters` para un acceso más fácil.
        *   Inicialicé `self.df_equivalencias` y `self.df_equivalencias_map_ine_to_ccaa` para el mapeo de códigos INE a CCAA.
    *   **Actualización del método `create_regions`:**
        *   Después de cargar `df_equivalencias` (tabla de equivalencias de municipios), la asigné a `self.df_equivalencias` para que esté disponible en otros métodos.
    *   **Reescritura completa del método `load_quali`:**
        1.  Construye el nombre del archivo esperado para el año de simulación (ej. `nivel_educativo_comunidades_2014.csv`).
        2.  Si el archivo del año de simulación no se encuentra, implementa una lógica de fallback (aunque para 2014, el archivo se encontró directamente).
        3.  Lee el archivo CSV seleccionado.
        4.  Establece `ccaa_code` como índice (asegurando que sea un string de 2 dígitos con ceros iniciales).
        5.  Renombra las columnas de niveles educativos (ej. de '1.0' a '1').
        6.  Convierte los valores porcentuales a proporciones (dividiendo por 100).
        7.  Calcula las proporciones acumulativas a través de los niveles (ordenados numéricamente). Se asegura que la última columna de probabilidad acumulada sea 1.0.
    *   **Reescritura completa del método `qual`:**
        1.  Verifica si `self.quali` (el DataFrame cargado por `load_quali`) está vacío; si es así, retorna una cualificación por defecto.
        2.  Utiliza `self.df_equivalencias` para mapear el `region_id_ine5` (código INE municipal de 5 dígitos) a su correspondiente `ccaa_code` (código de CCAA de 2 dígitos). Este mapeo se crea una vez y se almacena en `self.df_equivalencias_map_ine_to_ccaa`.
        3.  Si no se puede obtener el `ccaa_code` o este no se encuentra en `self.quali`, retorna una cualificación por defecto.
        4.  Selecciona un nivel de cualificación basado en una tirada aleatoria contra las probabilidades acumulativas de la CCAA correspondiente.
        5.  Mapea el nivel de cualificación obtenido (que puede ser '1', '2', '3', '5', '6', '7') a un nivel compatible con el método `self.years_study` (que espera '1'-'5'). Actualmente, los niveles '5', '6', '7' se mapean al nivel '5' para `years_study`. El nivel '4', ausente en los datos, se mapea a '3' si, hipotéticamente, fuera elegido.
        6.  Llama a `self.years_study` con el nivel mapeado para obtener los años de estudio.

3.  **Resultado de la Verificación (Simulación para 2014):**
    *   Tras aplicar los cambios, ejecuté la simulación (`python main.py run`) para el año 2014.
    *   El error `ERROR:generator:Error loading or processing Spanish qualification data: 'year'.` (que ocurría con la lógica anterior) **no apareció**.
    *   En su lugar, aparecieron mensajes informativos indicando la carga directa y correcta de los datos de 2014:
        ```
        INFO:generator:Starting Spanish qualification data loading process...
        INFO:generator:Found qualification data for simulation year 2014: .../ETL/nivel_educativo_comunidades/data_final/nivel_educativo_comunidades_2014.csv
        INFO:generator:Successfully loaded and processed qualification data from year 2014.
        ```

## Estado Actual del Procesamiento de Datos de Cualificación
He corregido la lógica para cargar los datos de cualificación. Ahora utiliza archivos anuales específicos por CCAA. Para la simulación del año 2014, los datos se cargan directamente desde `nivel_educativo_comunidades_2014.csv`. El sistema procesa estos datos y los utiliza para asignar cualificaciones a los agentes.
