# 📊 Información de Tablas en `datawarehouse.db` 🏦

Este documento resume las tablas principales cargadas en la base de datos `datawarehouse.db` a través del script ETL.

**Leyenda de Emojis:**
* 🗃️ Nombre de la Tabla
* 📄 Descripción Breve
* 🏷️ Columnas Principales (ejemplos)
* 🔑 Clave Primaria/Índice Común
* 🌍 Nivel Geográfico
* ⏳ Periodicidad

---

| Tabla 🗃️                               | Descripción 📄                                                                 | Columnas Principales 🏷️                                  | 🔑 Clave/Índice | 🌍 Nivel Geo | ⏳ Periodicidad |
|-----------------------------------------|--------------------------------------------------------------------------------|-----------------------------------------------------------|-----------------|--------------|-----------------|
| `tabla_equivalencias`                   | Códigos y nombres de municipios, provincias y CCAA.                            | `CMUN`, `CPRO`, `CCAA`, `NOMBRE_MUNICIPIO`, `NOMBRE_PROVINCIA` | `CMUN`          | Municipal    | Estática        |
| `cifras_poblacion_municipio`            | Cifras de población por municipio y año.                                       | `mun_code`, `year`, `poblacion_total`, `hombres`, `mujeres` | `mun_code`, `year` | Municipal    | Anual           |
| `df_mortalidad_ccaa_sexo`               | Defunciones por CCAA, sexo y año.                                              | `ccaa_code`, `sex`, `year`, `total_muertes`               | `ccaa_code`, `year`, `sex` | CCAA         | Anual           |
| `distribucion_urbana`                   | Proporción de suelo urbano por municipio y año.                                | `mun_code`, `year`, `proporcion_urbana`                   | `mun_code`, `year` | Municipal    | Anual           |
| `empresas_municipio_actividad_principal` | Número de empresas por municipio, actividad principal (CNAE) y año.            | `mun_code`, `year`, `CNAE`, `total_empresas`              | `mun_code`, `year`, `CNAE` | Municipal    | Anual           |
| `estimativas_pop`                       | Estimaciones de población por municipio y año (puede diferir de cifras oficiales). | `mun_code`, `year`, `poblacion`                           | `mun_code`, `year` | Municipal    | Anual           |
| `idhm_indice_desarrollo_humano_municipal` | Índice de Desarrollo Humano Municipal y sus componentes.                       | `mun_code`, `year`, `idh_municipal`, `renta_pc`, `esperanza_vida` | `mun_code`, `year` | Municipal    | Anual           |
| `indicadores_fecundidad_municipio_provincias` | Tasas de fecundidad estandarizadas por provincia y año.                      | `cpro`, `year`, `tasa_fert_prov`, `provincias_name`       | `cpro`, `year`  | Provincial   | Anual           |
| `interest_data_ETL`                     | Tipos de interés (fijo, nominal, real) a nivel nacional.                       | `date`, `interest_fixed`, `interest_nominal`, `interest_real` | `date`          | Nacional     | Diaria/Mensual  |
| `nivel_educativo_comunidades`           | Nivel educativo alcanzado por la población por CCAA, sexo, edad y año.         | `ccaa_code`, `year`, `nivel_educativo`, `sexo`, `edad_grupo` | `ccaa_code`, `year`, `nivel_educativo`, `sexo`, `edad_grupo` | CCAA         | Anual           |
| `PIE`                                   | Participación en Ingresos del Estado para municipios.                          | `mun_code`, `year`, `importe_total_PIE`, `poblacion_derecho` | `mun_code`, `year` | Municipal    | Anual           |

---

**Notas Adicionales:**
* Las columnas `mun_code`, `cpro`, `ccaa_code` suelen ser los códigos oficiales del INE.
* `year` representa el año al que se refieren los datos.
* Algunas tablas pueden tener más columnas no listadas aquí por brevedad.

**Notas Adicionales:**

TODO: Mejorar esquema relacional.

Este resumen debería facilitar la comprensión y el uso de las tablas en el data warehouse. ¡Feliz análisis de datos! 🚀
