# 📝 Dashboard Streamlit: Lista de Tareas

Este archivo documenta las tareas para el desarrollo del dashboard interactivo con Streamlit.

## 🚀 Fase 1: Estructura y Configuración Inicial

- [X] Crear carpeta `dashboard/`
- [X] Crear `dashboard/TODO.md` (este archivo)
- [X] Crear `dashboard/app.py` (script principal de Streamlit)
- [X] Crear `dashboard/pages/` (para informes y secciones adicionales)
- [X] Crear `dashboard/assets/` (para imágenes, CSS personalizado si es necesario)
- [X] Crear `dashboard/requirements.txt` con dependencias iniciales:
    - `streamlit`
    - `pandas`
    - `sqlalchemy`
    - `plotly` (para gráficos interactivos)
    - `matplotlib` (para gráficos estáticos si se requieren)
    - `openpyxl` (para exportar a Excel)
- [X] Configurar un entorno virtual y instalar dependencias.

## 📊 Fase 2: Funcionalidad Principal - Explorador de Datos

- [X] **Conexión a la Base de Datos:**
    - [X] Implementar función para conectar a `datawarehouse.db` (ubicada en `../data base/datawarehouse.db` relativo a `dashboard/app.py`).
- [X] **Página Principal (`app.py`):**
    - [X] Título y descripción del dashboard.
    - [X] Selector (dropdown o radio buttons) para elegir una tabla de la base de datos.
    - [X] Mostrar las primeras N filas de la tabla seleccionada (`st.dataframe` o `st.table`).
    - [X] Permitir la descarga de la tabla completa o filtrada como CSV.
    - [X] Permitir la descarga de la tabla completa o filtrada como Excel.
- [X] **Filtros Dinámicos:**
    - [X] Para cada tabla, identificar columnas clave para filtrado (ej: `year`, `mun_code`, `cpro`, `ccaa_code`, `sexo`, `CNAE`).
    - [X] Generar widgets de Streamlit (sliders, multiselect, text_input) para aplicar filtros sobre las columnas seleccionadas.
    - [X] Actualizar la tabla mostrada según los filtros aplicados.
- [X] **Visualizaciones Básicas:**
    - [X] Selector para elegir columnas numéricas para graficar.
    - [X] Selector de tipo de gráfico (barras, líneas, dispersión).
    - [X] Generar gráfico interactivo (Plotly) con los datos filtrados.

## 📄 Fase 3: Sección de Informes (`pages/`)

- [X] **Estructura Multipage:**
    - [X] Configurar `app.py` para soportar múltiples páginas desde la carpeta `pages/`. (Streamlit lo hace automáticamente si existe `pages/`)
    - [X] Crear una página de ejemplo en `pages/` (ej: `01_Informe_Poblacion.py`).
    - [X] Crear segunda página de ejemplo en `pages/` (ej: `02_Informe_IDHM.py`).
- [X] **Generación de Informes:**
    - [X] Permitir al usuario "guardar" una configuración de filtros y visualización como un "informe".
        - [X] Opción 1: Guardar parámetros en un archivo JSON/SQLite y regenerar el informe dinámicamente. (Implementado guardado en JSON)
        - [X] Opción 2: Crear scripts `.py` en `pages/` para informes predefinidos o comunes. (Implementado con ejemplos)
    - [X] Listar informes guardados/disponibles en la navegación. (Implementado en `03_Informes_Guardados.py`)
- [X] **Contenido de Informes:**
    - [X] Cada informe debe mostrar:
        - Título y descripción del informe.
        - Los datos (tabla) con los filtros aplicados.
        - Las visualizaciones (gráficos) correspondientes.
        - Opción para descargar el informe (datos + gráficos, quizás como PDF o HTML estático si es posible).

## ✨ Fase 4: Mejoras y Refinamiento

- [X] **Diseño y Estilo:**
    - [X] Mejorar la apariencia visual (CSS personalizado en `assets/style.css`, aplicado en `app.py`).
    - [ ] Añadir logo o branding si es necesario.
- [ ] **Usabilidad:**
    - [X] Añadir mensajes de ayuda, tooltips, y descripciones claras. (Added to main widgets in app.py)
    - [ ] Optimizar la carga de datos y la respuesta de la interfaz. (Partially done with @st.cache)
    - [ ] Manejo de errores y excepciones. (Basic handling exists)
- [ ] **Documentación:**
    - [ ] Comentarios en el código.
    - [ ] Actualizar este `TODO.md` y `README.md` del proyecto.

## 💡 Anotaciones y Próximos Pasos

- *Aquí se pueden añadir notas durante el desarrollo.*
- Considerar el uso de `st.cache_data` y `st.cache_resource` para optimizar el rendimiento al cargar datos y recursos.
- Explorar componentes de la comunidad de Streamlit para funcionalidades avanzadas.

---
*Este TODO se irá actualizando a medida que avance el proyecto.*
