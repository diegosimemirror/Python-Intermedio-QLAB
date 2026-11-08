---
name: mapeando-enaho
description: Construye el mapa coroplético de la pobreza monetaria por departamento del Perú con la ENAHO 2024 del INEI, uniendo por código de ubigeo (25 departamentos, Lima y Callao separados) y comparándolo con la referencia oficial. Úsala cuando pidan un mapa, un coroplético o la distribución territorial de la pobreza por departamento o región.
---
# Mapa de la pobreza por departamento (ENAHO 2024)

1. Trabaja desde `tarea_4/`. **Si no existe `salidas/hogares_2024.parquet`, usa primero la skill
   `limpiando-enaho`** y comprueba que `salidas/validacion.txt` diga `VÁLIDA`.
2. Si falta `datos/peru_departamental_simple.geojson`, corre `uv run python scripts/descargar_datos.py`.
3. Corre exactamente:
   ```bash
   uv run python .claude/skills/mapeando-enaho/scripts/mapear.py
   ```
4. El script une `ubigeo[:2]` con `FIRST_IDDP` como texto (nunca por nombre), exige 25 departamentos con dato y
   Lima (15) y Callao (07) separados, y se detiene con un mensaje si la unión falla. No lo cambies a una unión por
   nombres.
5. Informa la ruta `mapas/pobreza_departamento_2024.png`, la diferencia máxima con la referencia de la sesión 16
   (`salidas/comparacion_mapa.csv`) y los departamentos con mayor y menor pobreza tal como los imprime el script.
6. Escala: un solo azul de claro a oscuro desde 0 y leyenda en "% de personas en pobreza monetaria".
