# Distribución Urbana - Preprocesamiento de Datos

Este documento explica cómo incorporar y preparar los datos pesados necesarios para el flujo ETL de distribución urbana.

## Estructura de Carpetas

Se espera que los datos de entrada estén disponibles en la siguiente ruta local:

```
/home/agmalaga/Documentos/GitHub/PolicySpace2_Spanish_data/ETL/distribucion_urbana/data/
```

## Datos de Entrada

* **Archivo:** `df_final` (tabla intermedia generada por el proceso de población municipal)
* **Origen:** Google Drive (extraído desde Google Colab)

> **Nota:** Este repositorio **no** contiene los datos pesados (`df_final`). Para incorporarlos manualmente, debe copiar el archivo correspondiente desde Google Drive al directorio indicado.

## Pasos para Incorporar los Datos

1. Abrir el cuaderno de Google Colab disponible en:

   [https://colab.research.google.com/drive/1V-Sg1CuK\_rsf0g08CiVmg8qCiDsPDXpQ?hl=es#scrollTo=k60rb008EL8n](https://colab.research.google.com/drive/1V-Sg1CuK_rsf0g08CiVmg8qCiDsPDXpQ?hl=es#scrollTo=k60rb008EL8n)

2. Ejecutar todas las celdas para generar `df_final`.

3. Descargar el resultado (`df_final`) a su máquina local.

4. Copiar el archivo descargado a la ruta de datos del proyecto:

   ```bash
   cp <ruta_local>/df_final.<ext> /home/agmalaga/Documentos/GitHub/PolicySpace2_Spanish_data/ETL/distribucion_urbana/data/
   ```

5. Una vez copiado, los scripts del ETL detectarán automáticamente el archivo y lo utilizarán como entrada.

## Estado Actual

* Por el momento, únicamente hemos copiado los datos extraídos desde Google Colab.
* No hay integración automatizada en el flujo principal; la incorporación es manual.

---

Para más detalles sobre el procesamiento de `df_final`, consulte el script `cifras_poblacion_municipio` en la carpeta correspondiente del proyecto.
