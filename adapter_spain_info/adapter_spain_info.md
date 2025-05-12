# Informe de Adaptación de PolicySpace2 para España

## Estado Actual (2025-05-10)

### Ejecución de Simulación
- Se ha logrado ejecutar la simulación principal (`main.py run`) hasta su finalización.
- El año de simulación es **2014**.
- Se han corregido errores de carga para todos los conjuntos de datos principales (Población, Cualificación, Mortalidad, Fertilidad, PIE).
- La lógica de matrimonio ha sido deshabilitada.
- Se ha integrado un modelo predictivo para el tamaño medio de los hogares por CCAA.
- El parámetro `PERCENTAGE_ACTUAL_POP` se ha ajustado a `0.1` (10%).

### Estado de Carga de Datos para Simulación 2014:
- **Datos de Población:** (Corregido) Para la simulación de 2014, los datos de población se cargan directamente desde los archivos ETL en `ETL/cifras_poblacion_municipio/data_final/drive-download-20250506T180657Z-001/` (ej. `cifras_municipio_hombres_2014.csv`). Estos archivos contienen datos de edad simple que se procesan en grupos de edad estándar ('0--4', '5--9', etc.) para la simulación. Total escalado de población con `PERCENTAGE_ACTUAL_POP = 0.1` es de 391,900.
- **Datos de Cualificación:** (Corregido) El mecanismo de carga de datos de cualificación usa archivos CSV anuales por CCAA. Para la simulación de 2014, los datos de `nivel_educativo_comunidades_2014.csv` se cargan directamente.
- **Datos de Mortalidad:** (Corregido) El mecanismo de carga de datos de mortalidad usa archivos CSV individuales por CCAA/sexo. Para la simulación de 2014, los datos del año 2014 se cargan directamente.
- **Datos de Fertilidad:** (Corregido) El mecanismo de carga de datos de fertilidad usa archivos CSV individuales por provincia. Para la simulación de 2014, los datos del año 2014 se cargan directamente.
- **Datos de Tamaño Medio de Hogares:** (Corregido) Se utiliza un modelo predictivo (regresión lineal) para estimar el tamaño medio de los hogares por CCAA para 2014, basado en datos de 2021-2025. Estos valores específicos por CCAA se utilizan en la simulación, con fallback al parámetro global `MEMBERS_PER_FAMILY` si es necesario.
- **Datos de Empresas (`FirmData`):** (Corregido) Se inicializan usando datos de los años 2014 (t0) y 2019 (t1) para calcular el crecimiento. Carga desde ETL.
- **Datos de Matrimonio:** (INFO) La lógica de matrimonio ha sido deshabilitada en la simulación debido a la falta de datos y por directriz del usuario. Las probabilidades de matrimonio son cero.
- **Salarios y PIE:**
    - `WARNING:simulation:No last_wage data available to calculate wage_deciles. Using default.` (Mensual). Esto es esperable al inicio de la simulación con agentes nuevos.
    - Para los municipios de prueba ('01001', '01008'), la advertencia sobre PIE total cero **no apareció** para la simulación de 2014, indicando que los datos son procesables.
- **Estadísticas de Salida:** Con `PERCENTAGE_ACTUAL_POP` en `0.1`, las estadísticas de salida deberían ser más representativas, aunque aún pueden reflejar una población relativamente pequeña para ciertas dinámicas complejas.

### Próximos Pasos Sugeridos (según feedback del usuario):
1.  **Definir Alcance de Simulación:** Utilizar la lista de municipios comunes (`adapter_spain_info/common_municipalities_for_simulation.csv`, actualmente con 2168 municipios) para las simulaciones. Esto asegura que se utilicen municipios con datos consistentes a través de las fuentes principales (PIE, Población, IDHM, Proporción Urbana, Empresas).
2.  **Revisar Datos Pendientes:**
    *   **Estimaciones de Población (Inmigración):** La clase `PopulationEstimates` actualmente usa `input/estimativas_pop.csv`. Considerar si este archivo debe ser reemplazado o complementado con datos del ETL.
3.  **Investigar Advertencia de Deciles Salariales:** Analizar el impacto de la advertencia `No last_wage data available...` (prioridad más baja).


### Verificación de Origen de Datos (ETL vs. Input)
Se ha verificado que la mayoría de los datos cruciales para la simulación se cargan desde la carpeta `ETL/`.
- **Datos desde `ETL/`**:
    - Datos de Población (archivos por sexo/año con edad simple)
    - Datos de Tamaño Medio de Hogares (predicciones basadas en datos ETL)
    - Datos de Empresas (`FirmData`)
    - Datos PIE (FPM)
    - Shapefiles (Geometrías municipales)
    - Datos de Cualificación (Nivel Educativo)
    - Datos de Mortalidad
    - Datos de Fertilidad
    - Datos de IDHM (Índice de Desarrollo Humano Municipal)
    - Datos de Proporción Urbana
    - Datos de Interés (primariamente)
- **Datos aún desde `input/`**:
    - **Datos de Estimaciones de Población (para inmigración):** `input/estimativas_pop.csv`.
    - **Datos de Edad de Matrimonio** (`marriage_age_men.csv`, `marriage_age_women.csv`): La lógica que los usaría está deshabilitada.
- **Datos No Utilizados (Decisión):**
    - **Datos AP (Área de Ponderación):** Confirmado que no son necesarios para la adaptación española; la simulación se enfoca en niveles municipal, provincial y/o autonómico.

La simulación ahora se ejecuta para el año 2014 con la mayoría de los datos principales cargados desde ETL y con ajustes para mejorar su representatividad. La fiabilidad de los resultados dependerá de la calidad y alineación temporal de todos los datos de entrada y de la calibración de parámetros.

---
## TODO (mapeo de datos)

Leyenda:
- `[X]` -> Completado
- `[]` -> Pendiente

### Carga y Procesamiento de Datos (Simulación Año 2014)
- `[X]` **Datos de Población:** Carga desde ETL (`ETL/cifras_poblacion_municipio/data_final/.../cifras_municipio_{sexo}_{año}.csv`). Procesamiento de formato largo (edad simple) a formato ancho (grupos de edad '0--4', etc.). Archivos de 2014 cargados directamente.
- `[X]` **Datos de Fertilidad:** Carga de datos de 2014 desde archivos CSV por provincia (`ETL/indicadores_fecundidad_municipio_provincias/tasas_fertilidad_provincias/`).
- `[X]` **Datos de Mortalidad:** Carga de datos de 2014 desde archivos CSV por CCAA y sexo (`ETL/df_mortalidad_ccaa_sexo/mortalidad_policyspace_es/`).
- `[X]` **Datos PIE (FPM):**
    - `mun_code` generado correctamente en `ETL/PIE/procesar_pie.py`.
    - `world/funds.py` usa `mun_code`. Datos para 2014 procesables para municipios de prueba.
- `[X]` **Datos de Cualificación:** Carga de datos de 2014 desde archivo CSV anual por CCAA (`ETL/nivel_educativo_comunidades/data_final/`).
- `[X]` **Datos de Matrimonio:** Lógica de matrimonio deshabilitada.
- `[X]` **Lista de Municipios Comunes:** Generado `adapter_spain_info/common_municipalities_for_simulation.csv` (2168 municipios) con datos consistentes entre PIE, Población, IDHM, Proporción Urbana y Empresas.
- `[X]` **Datos AP (Área de Ponderación):** Confirmado que no son necesarios para la adaptación española.
- `[X]` **Modelo Predictivo Tamaño Medio Hogares:** Creado modelo para predecir valores para 2014 por CCAA desde datos 2021-2025. Guardado en `ETL/tamaño_medio_hogares_ccaa/datos_prediccion/`. Integrado en simulación.
- `[X]` **Ajustar `PERCENTAGE_ACTUAL_POP`:** Ajustado a `0.1` para una escala de simulación más representativa.
- `[X]` **Datos de Empresas (`FirmData`):** Alineados años `t0` (a 2014) y `t1` (a 2019) para el cálculo de crecimiento, usando datos ETL.
- `[X]` **Generación de archivos de salida de simulación:** Confirmado que la simulación produce correctamente archivos de salida en `output/latest/0/` (`temp_banks.csv`, `temp_construction.csv`, `temp_firms.csv`, `temp_regional.csv`, `temp_stats.csv`), lo que valida la integración de logs y resultados.

### Problemas de Datos y Tareas Pendientes (Contexto 2014 y General)
- `[]` **Datos de Estimaciones de Población (Inmigración):** Revisar si `input/estimativas_pop.csv` es adecuado o si debe usarse una fuente ETL.
- `[]` **Advertencia de Deciles Salariales:** Investigar impacto o si es aceptable (prioridad más baja).
