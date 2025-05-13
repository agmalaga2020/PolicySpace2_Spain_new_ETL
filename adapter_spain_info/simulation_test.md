# simulation_test.md

Este documento se ha creado para pruebas y documentación adicional relacionada con la simulación PolicySpace2 adaptada para España.

- Fecha de creación: 2025-05-12
- Ubicación: adapter_spain_info/

---

## Objetivo de la sesión

Registrar los cambios, observaciones y TODO realizados durante la sesión. El objetivo es ejecutar la simulación en modo test y documentar los fallos o incidencias que aparezcan.

### TODO

- [x] Ejecutar la simulación en modo test.
- [x] Registrar errores o advertencias que surjan.
- [x] Analizar y documentar los fallos detectados.
- [x] Proponer soluciones o próximos pasos.

---

## Sesión 2025-05-13

### Error Detectado: `KeyError: 3` en `world/demographics.py`

Al ejecutar `tests.py`, se produjo un `KeyError: 3` durante la función `check_demographics`.

**Causa Raíz:**
El error se debe a que los datos de mortalidad (cargados desde archivos CSV como `mortality_men_01.csv`) no contienen entradas para todas las edades individuales (0-100). En su lugar, tienen datos para edades específicas (0, 1, 5, 10, 15, ...). Cuando la simulación intenta obtener la tasa de mortalidad para un agente con una edad que no está explícitamente en el archivo (por ejemplo, edad 3), se produce un `KeyError` porque el método `get_group(age)` de pandas no encuentra ese grupo.

**Fragmento del Traceback:**
```
Traceback (most recent call last):
  File "/home/agmalaga/Documentos/GitHub/PolicySpace2_Spain_ETL_IDHM_revised/home/ubuntu/PolicySpace2_Spain_new_ETL/PolicySpace2_adapted_for_Spain/tests.py", line 22, in <module>
    sim.run()
  File "/home/agmalaga/Documentos/GitHub/PolicySpace2_Spain_ETL_IDHM_revised/home/ubuntu/PolicySpace2_Spain_new_ETL/PolicySpace2_adapted_for_Spain/simulation.py", line 302, in run
    self.monthly()
  File "/home/agmalaga/Documentos/GitHub/PolicySpace2_Spain_ETL_IDHM_revised/home/ubuntu/PolicySpace2_Spain_new_ETL/PolicySpace2_adapted_for_Spain/simulation.py", line 400, in monthly
    demographics.check_demographics(self, birthdays, self.clock.year,
  File "/home/agmalaga/Documentos/GitHub/PolicySpace2_Spain_ETL_IDHM_revised/home/ubuntu/PolicySpace2_Spain_new_ETL/PolicySpace2_adapted_for_Spain/world/demographics.py", line 13, in check_demographics
    prob_mort_m = mortality_men.get_group(age)[str(year)].iloc[0]
                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/agmalaga/miniconda3/lib/python3.12/site-packages/pandas/core/groupby/groupby.py", line 1114, in get_group
    raise KeyError(name)
KeyError: 3
```

**Solución Implementada:**
Se modificó la función `check_demographics` en `world/demographics.py` para manejar los casos en que una edad específica no se encuentra en los datos de mortalidad o fertilidad. La lógica implementada es la siguiente:
1. Intenta obtener el grupo para la `current_agent_age`.
2. Si no se encuentra (KeyError implícito manejado por la lógica `in mortality_men.groups`):
    a. Busca todas las `available_ages` en los datos que sean menores o iguales a `current_agent_age`.
    b. Si se encuentran `available_ages`, se usa la `max(available_ages)` (la edad más cercana inferior o igual presente en los datos).
    c. Si no hay `available_ages` (es decir, `current_agent_age` es menor que la primera edad en los datos), se usa la `min(mortality_men.groups.keys())` (la primera edad disponible en los datos) como fallback.
Esta misma lógica se aplicó para `mortality_women` y `fertility`.

**Próximos Pasos:**
- Volver a ejecutar `tests.py` para verificar que el error `KeyError: 3` (y similares para otras edades) se haya resuelto.
- Continuar con las pruebas de simulación.
