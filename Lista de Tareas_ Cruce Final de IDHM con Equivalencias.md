# Lista de Tareas: Cruce Final de IDHM con Equivalencias

- [x] Modificar `read_input_data.py`:
    - En la carga de `df_equivalencias_municipio_CORRECTO.csv`:
        - Asegurar que la columna `mun_code` (INE de 5 dígitos) se procese como `ine_code`.
        - Crear una nueva columna `mun_code_short_equiv` concatenando `str(int(CPRO)) + CMUN`.
    - En la carga de `IRPFmunicipios_final_IDHM.csv`:
        - Asegurar que su `mun_code` (código corto) se lea como string.
    - Ajustar el merge entre `df_idhm` y `df_equivalencias` para usar `df_idhm["mun_code"]` y `df_equivalencias["mun_code_short_equiv"]`.
    - Asegurar que el filtrado final para `test_municipalities` use la columna `ine_code` (5 dígitos) del dataframe resultante del merge.
- [x] Realizar pruebas funcionales ejecutando el script `read_input_data.py` modificado.
- [x] Validar que los datos de IDHM se cargan, cruzan y filtran correctamente para los municipios de prueba.
- [x] Documentar en el informe `informe_MANUS.md` los ajustes finales, los resultados de las pruebas y reiterar la explicación sobre la metodología de prueba profesional.
- [x] Preparar y entregar el informe actualizado, el código modificado y esta lista de tareas al usuario.