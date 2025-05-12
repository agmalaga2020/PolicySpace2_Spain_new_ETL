# Variables Clave para Adaptar el FPM Brasileño al Contexto Español

## Introducción

Para adaptar el FPM (Fundo de Participação dos Municípios) brasileño al contexto español a través de la PIE (Participación en los Ingresos del Estado), necesitamos identificar las variables clave que son esenciales para el funcionamiento del modelo PolicySpace2.

## Variables Esenciales

Basado en el análisis de los archivos de liquidación y los requisitos del proyecto PolicySpace2, las siguientes variables son fundamentales:

### 1. Identificadores de Municipio
- **codigo_provincia**: Código numérico de la provincia (equivalente a los estados en Brasil)
- **codigo_municipio**: Código numérico del municipio
- **nombre_municipio**: Nombre completo del municipio

### 2. Variables Demográficas
- **poblacion**: Número de habitantes del municipio (equivalente a la variable poblacional usada en el FPM)
- **año**: Año al que corresponden los datos

### 3. Variables Fiscales
- **esfuerzo_fiscal**: Indicador del esfuerzo fiscal del municipio (12,5% de la distribución en España)
- **inverso_capacidad_tributaria**: Inverso de la capacidad tributaria (12,5% de la distribución en España)

### 4. Variables de Distribución
- **participacion_poblacion**: Monto asignado por criterio de población (75% de la distribución)
- **participacion_esfuerzo_fiscal**: Monto asignado por criterio de esfuerzo fiscal
- **participacion_inverso_capacidad**: Monto asignado por criterio de inverso de capacidad tributaria
- **total_participacion_variables**: Suma total de las participaciones por variables

### 5. Variables de Liquidación
- **participacion_garantizada**: Monto garantizado de participación (cuando aplica)
- **liquidacion_final**: Liquidación final después de ajustes

## Correspondencia con el FPM Brasileño

| Variable PIE (España) | Variable FPM (Brasil) | Descripción |
|----------------------|---------------------|-------------|
| codigo_provincia + codigo_municipio | código municipio | Identificador único del municipio |
| poblacion | población | Base principal para la distribución de recursos |
| esfuerzo_fiscal | No tiene equivalente directo | En Brasil se usa principalmente población |
| inverso_capacidad_tributaria | No tiene equivalente directo | En Brasil se usa principalmente población |
| total_participacion_variables | valor FPM | Monto total asignado al municipio |

## Estructura de Datos Requerida

Para el correcto funcionamiento del modelo adaptado, necesitamos una tabla con la siguiente estructura:

```
año,codigo_provincia,codigo_municipio,nombre_municipio,poblacion,esfuerzo_fiscal,inverso_capacidad_tributaria,participacion_poblacion,participacion_esfuerzo_fiscal,participacion_inverso_capacidad,total_participacion_variables,participacion_garantizada,liquidacion_final
```

Esta estructura debe mantenerse consistente para todos los años disponibles (2004-2022), permitiendo un análisis temporal adecuado y la integración con otros datos municipales españoles.
