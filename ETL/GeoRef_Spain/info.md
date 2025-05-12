# 🗺️ Proceso de Mapeo Geográfico de España: Municipios y Comunidades Autónomas

Este documento describe el flujo de trabajo para obtener, procesar y visualizar datos geoespaciales de los municipios y comunidades autónomas de España.

## 🔢 Orden de Ejecución de Scripts:

1.  **📥 Extracción de Datos Geoespaciales**
    *   **Script**: `download_georef_spain.py`
    *   **Acción**: Este script se encarga de descargar los datos geoespaciales necesarios (archivos GeoJSON) que contienen las geometrías de los municipios y comunidades autónomas de España.
    *   **Resultado**: Archivos GeoJSON (`georef-spain-municipio.geojson`, `georef-spain-comunidad-autonoma.geojson`, etc.) guardados localmente en la carpeta `ETL/GeoRef_Spain/`.

2.  **📍 Mapeo de Coordenadas de Municipios (Cálculo de Centroides)**
    *   **Script**: `mapear_coordenadas.py`
    *   **Acción**: Lee el archivo `georef-spain-municipio.geojson`, extrae el código y nombre de cada municipio, calcula las coordenadas del centroide (latitud y longitud) de su geometría.
    *   **Resultado**: Un archivo CSV llamado `municipios_coordenadas.csv` que contiene el código del municipio, nombre del municipio, y las coordenadas de su centroide.

3.  **📍 Mapeo de Coordenadas de Comunidades Autónomas (Cálculo de Centroides)**
    *   **Script**: `mapear_coordenadas_comunidades.py`
    *   **Acción**: Lee el archivo `georef-spain-comunidad-autonoma.geojson`, extrae el código y nombre de cada comunidad autónoma, calcula las coordenadas del centroide (latitud y longitud) de su geometría.
    *   **Resultado**: Un archivo CSV llamado `comunidades_coordenadas.csv` que contiene el código de la comunidad, nombre de la comunidad, y las coordenadas de su centroide.

4.  **🌍 Visualización de Centroides de Municipios en Mapa Interactivo**
    *   **Script**: `visualizar_mapa_municipios.py`
    *   **Acción**: Lee el archivo `municipios_coordenadas.csv` generado en el paso anterior y utiliza la librería Folium para crear un mapa HTML interactivo. Cada municipio se representa con un marcador en sus coordenadas de centroide, mostrando su nombre y código al hacer clic.
    *   **Resultado**: Un archivo HTML llamado `mapa_municipios.html` que se puede abrir en un navegador web para explorar los municipios en un mapa.

5.  **🗺️ Visualización de Polígonos de Municipios en Mapa Interactivo**
    *   **Script**: `visualizar_mapa_poligonos_municipios.py`
    *   **Acción**: Lee el archivo GeoJSON `georef-spain-municipio.geojson` y utiliza Folium para crear un mapa HTML interactivo que muestra los polígonos reales de cada municipio. Permite visualizar la forma y extensión de los municipios.
    *   **Resultado**: Un archivo HTML llamado `mapa_poligonos_municipios.html`.

6.  **🏞️ Visualización de Polígonos de Comunidades Autónomas en Mapa Interactivo**
    *   **Script**: `visualizar_mapa_poligonos_comunidades.py`
    *   **Acción**: Lee el archivo GeoJSON `georef-spain-comunidad-autonoma.geojson` y utiliza Folium para crear un mapa HTML interactivo que muestra los polígonos reales de cada comunidad autónoma.
    *   **Resultado**: Un archivo HTML llamado `mapa_poligonos_comunidades.html`.

  **🏞️ TODO**

    * [] Añadir datos provinciales. 
---

¡Sigue estos pasos en orden para asegurar que los datos se procesan correctamente y las visualizaciones se generan con la información esperada! ✨
