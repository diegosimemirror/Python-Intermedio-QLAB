---
name: limpiando-enaho
description: Limpia y valida la ENAHO 2024 del INEI (módulo 34 sumaria y módulo 02 miembros), une personas y hogares y calcula indicadores ponderados de pobreza monetaria por área, departamento, sexo y tipo de hogar. Úsala cuando pidan limpiar, unir, validar o analizar la ENAHO, o calcular pobreza, pobreza extrema, brecha, vulnerabilidad, gasto en alimentos, Juntos o Pensión 65 con microdatos del INEI.
---
# Limpiar y validar la ENAHO 2024

1. Trabaja desde la carpeta `tarea_4/`. Si faltan `datos/966-Modulo34.zip` o `datos/966-Modulo02.zip`,
   corre `uv run python scripts/descargar_datos.py`; si no hay internet, pide al usuario bajarlos del INEI.
2. Corre exactamente:
   ```bash
   uv run python .claude/skills/limpiando-enaho/scripts/limpiar.py
   ```
3. Lee `salidas/validacion.txt`. Si dice `NO VÁLIDA`, detente y explica qué validación falló. Nunca ajustes
   cifras a mano para que coincidan con la referencia.
4. Las cifras se toman de `salidas/indicadores.csv` (una fila por indicador y grupo, con unidad y ponderador).
   Para un cruce que no esté ahí, usa `salidas/hogares_2024.parquet` (un hogar por fila, ponderar con
   `peso_personas` = factor07 × mieperho) o `salidas/personas_2024.parquet` (una persona por fila, ponderar con
   `facpob07`). Nunca promedios simples.
5. Al responder, cita el indicador, el grupo, la unidad y "Fuente: INEI, ENAHO 2024 (módulos 34 y 02)".
6. Antes de usar una variable que no está en las bases, lee `reference.md`.
