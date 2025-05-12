---

# Proyecto de Procesamiento de Liquidaciones Municipales (PIE) para PolicySpace2

Esta carpeta contiene scripts para descargar, organizar, limpiar y unificar los datos de liquidaciones municipales de la Participación en los Ingresos del Estado (PIE) en España, adaptados para su uso en el proyecto PolicySpace2.

## Orden recomendado de ejecución y descripción de scripts

### 1. **Descarga y organización de archivos originales**
- **`./PIE/scrap_liquidaciones.py`**
  - Descarga automáticamente todos los archivos de liquidación de municipios (formato .xls/.xlsx) desde la web del Ministerio de Hacienda y los guarda en `./PIE/data/raw/finanzas/liquidaciones/`.

### 2. **Selección y renombrado homogéneo**
- **`./PIE/select_liquidaciones_regimen_general.py`**
  - Selecciona, para cada año, el archivo más relevante (preferentemente el estándar y homogéneo).
  - Convierte todos los archivos a formato `.xlsx` y los renombra como `liquidacion_AÑO.xlsx`.
  - Copia los archivos a `./PIE/data/raw/finanzas/liquidaciones/por_municipios_regimen_general/`.

### 3. **Conteo y exploración de archivos**
- **`./PIE/count_liquidaciones_by_year.py`**
  - Cuenta cuántos archivos hay por año en la carpeta de liquidaciones y muestra el año detectado para cada archivo.

### 4. **Procesamiento y unificación final de datos**
- **`./PIE/procesar_liquidacion_pie_final.py`**
  - Procesa todos los archivos de liquidación usando la configuración definida.
  - Extrae variables clave como población, esfuerzo fiscal y participaciones.
  - Genera archivos de salida en formato CSV y Excel con todos los datos unificados.
  - Crea un archivo de estadísticas con resúmenes anuales.
  - Los resultados se guardan en el directorio de salida configurado.

### 5. **Filtrado adicional de datos PIE**
- **`./PIE/procesar_pie.py`**
  - Lee el archivo `pie_final.csv` (generado por `procesar_liquidacion_pie_final.py`).
  - Filtra los registros para excluir aquellos correspondientes al año 2005.
  - Guarda el resultado en `pie_final_final.csv` dentro del mismo subdirectorio (`./PIE/data/raw/finanzas/liquidaciones/preprocess/`).

### 6. **Visualización final**
- **PIE_solo_visualizacion.ipynb**: https://colab.research.google.com/drive/1ohhMYhB0jQyMdA9TV6y9UTfwVbh76Db5#scrollTo=QECBFbR2Zss9

---

## Flujo recomendado

1. Ejecuta `./PIE/scrap_liquidaciones.py` para descargar los archivos originales.
2. Ejecuta `./PIE/select_liquidaciones_regimen_general.py` para seleccionar, convertir y renombrar los archivos homogéneos.
3. (Opcional) Ejecuta `./PIE/count_liquidaciones_by_year.py` para verificar la cobertura anual.
4. Ejecuta `./PIE/procesar_liquidacion_pie_final.py` para procesar y unificar los datos, generando un conjunto de datos final.
5. Ejecuta `./PIE/procesar_pie.py` para filtrar los datos y excluir los registros del año 2005.

---

## Notas

- Todos los scripts están preparados para ejecutarse en orden, pero pueden adaptarse a nuevas fuentes o años si se actualizan los enlaces o formatos.
- El resultado final es una tabla homogénea de municipios y participaciones PIE por año, lista para análisis comparativo o modelización.

---

