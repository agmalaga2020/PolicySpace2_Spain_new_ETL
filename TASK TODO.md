# Lista de Tareas para la Adaptación de PolicySpace2 a Datos Españoles

## Fase de Integración y Corrección de Datos (Continuación)
- [X] Comprobar `ETL/cifras_poblacion_municipio/cifras_poblacion_municipio.csv` -> `mun_code`. (Nota: `mun_code` son '1.0', '2.0', etc. No son códigos INE de 5 dígitos. Mapeo a nivel municipal no posible sin tabla de correspondencia adicional o clarificación de estos códigos. El script `read_input_data.py` ya advierte sobre esto.)
- [X] Comprobar `ETL/empresas_municipio_actividad_principal/preprocesados/empresas_municipio_actividad_principal.csv` -> `municipio_code` y mapear a códigos INE de 5 dígitos. (Mapeo implementado y probado en `auxiliary/read_input_data.py` usando `mun_code_short_equiv` de la tabla de equivalencias.)

## Fase de Adaptación del Modelo y Simulación
- [ ] Adaptar la lógica central de simulación del modelo (agentes, mercados en `agents/`, `markets/`, `world/`) para la granularidad de datos española (municipal/provincial/autonómica en lugar de APs).
    - [X] Revisar y adaptar `world/geography.py` para asegurar la correcta gestión de los códigos y nombres municipales españoles. (Rutas corregidas, carga de datos de equivalencia validada).
    - [X] Revisar y adaptar cómo los agentes (`agents/family.py`, `agents/firm.py`, `agents/house.py`, `agents/region.py`) y el generador (`world/generator.py`) acceden y utilizan los datos geográficos y económicos. (Adaptaciones iniciales realizadas, archivos de datos redirigidos a ETL. Pendiente: mapeo INE a CCAA para algunos datos, adaptación de `FirmData`, `pop_age_data`, `prepare_shapes`).
    - [X] Revisar y adaptar la lógica de los mercados (`markets/housing.py`, `markets/labor.py`, `markets/rentmarket.py`, `markets/goods.py`) para operar con la estructura de datos española. (Revisión completada. Los módulos de mercado son mayormente genéricos; su adaptación depende de la correcta inicialización de agentes, regiones y parámetros).
- [X] Calibrar los parámetros del modelo en `conf/default/params.py` para el contexto español (ej. `MEMBERS_PER_FAMILY`, `NEIGHBORHOOD_EFFECT`, `FPM_DISTRIBUTION` (PIE), tasas económicas, etc.). (Revisión inicial realizada, comentarios añadidos para impuestos y parámetros clave. `TAXES_STRUCTURE` 'fpm' key cambiada a 'pie'. Calibración detallada es un proceso iterativo y requiere más investigación/pruebas.)
- [ ] Ejecutar simulaciones completas utilizando `runner.py` o `main.py` (o el script de adaptación principal si se crea uno específico para orquestar la ejecución con datos españoles).
    - [ ] Depurar errores de ejecución que surjan durante las simulaciones.
    - [ ] Asegurar la correcta generación de logs y datos de salida en `analysis/`.

## Fase de Validación y Análisis
- [ ] Validar los resultados del modelo:
    - [ ] Comparar los resultados de la simulación con datos históricos españoles conocidos (si aplica).
    - [ ] Realizar análisis de sensibilidad a los parámetros clave.
- [ ] Adaptar los módulos de análisis y visualización:
    - [ ] Revisar y adaptar scripts en `analysis/` (e.g., `analysis/report.py`, `analysis/plotting/`) para que funcionen con la estructura de salida y los identificadores geográficos españoles.
    - [ ] Revisar y adaptar scripts en `post_analysis/` para generar los informes y gráficos deseados con los datos españoles.

## Fase de Documentación y Entrega
- [ ] Actualizar la documentación del proyecto para reflejar las adaptaciones realizadas para España.
- [ ] Preparar el informe final de adaptación y resultados.
