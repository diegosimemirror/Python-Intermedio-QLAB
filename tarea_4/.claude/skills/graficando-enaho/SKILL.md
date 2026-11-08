---
name: graficando-enaho
description: Hace gráficos ponderados de la pobreza monetaria con la ENAHO 2024 del INEI - por área urbana y rural, por sexo o jefatura del hogar, por tipo de hogar (con niños menores de 5 años, con adultos mayores) y por departamento - y los guarda en figuras/. Úsala cuando pidan graficar, visualizar o comparar la pobreza o la ENAHO entre grupos o regiones.
argument-hint: [area | sexo | hogares | departamentos | todos]
---
# Graficar la pobreza con la ENAHO 2024

1. Trabaja desde `tarea_4/`. **Si no existe `salidas/hogares_2024.parquet` o `salidas/personas_2024.parquet`, usa
   primero la skill `limpiando-enaho`** y comprueba que `salidas/validacion.txt` diga `VÁLIDA`.
2. Elige el gráfico según el pedido y corre exactamente:
   ```bash
   uv run python .claude/skills/graficando-enaho/scripts/graficar.py <grafico>
   ```
   | Pedido | `<grafico>` | Archivo |
   |---|---|---|
   | urbano y rural, área, Lima | `area` | `figuras/enaho_pobreza_area.png` |
   | sexo, hombres y mujeres, jefa o jefe de hogar | `sexo` | `figuras/enaho_pobreza_sexo.png` |
   | niños, menores de 5, adultos mayores, tipo de hogar | `hogares` | `figuras/enaho_pobreza_hogares.png` |
   | departamentos, regiones, ranking | `departamentos` | `figuras/enaho_pobreza_departamentos.png` |
   | todos | `todos` | los cuatro |
   Usa `$ARGUMENTS` si el usuario lo dio.
3. El script imprime la cifra de cada barra: cítalas tal cual (no recalcules a mano) e indica la ruta del PNG.
4. Reglas que el script ya cumple y que no debes romper si lo modificas: estimaciones ponderadas
   (`peso_personas` para hogares, `facpob07` para personas), barras desde cero en un solo color, el valor escrito
   en cada barra, un título que dice qué muestra, periodo y unidad en el subtítulo, "Fuente: INEI, ENAHO 2024" al
   pie y PNG a 200 dpi.
5. Describe las diferencias como asociaciones, no como causas.
