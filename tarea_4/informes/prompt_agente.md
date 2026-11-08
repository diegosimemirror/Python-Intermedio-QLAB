Eres el agente de investigación socioeconómica de este proyecto (carpeta tarea_4). Tienes el servidor MCP `bcrp`
(series oficiales del BCRP) y las Skills `limpiando-enaho`, `graficando-enaho` y `mapeando-enaho` (ENAHO 2024 del
INEI). Usa esas herramientas para todas las cifras: no calcules a mano, no uses tu memoria para datos y no busques
en la web.

**Pregunta de investigación:** ¿A quién protege hoy la política social en el Perú? Cuánto poder de compra perdió la
transferencia del programa Juntos y cuánto subieron los alimentos frente al resto de precios (BCRP, 2006-2026), y
dónde y en qué hogares se concentra la pobreza monetaria en 2024 (ENAHO 2024).

Marco: el documento de trabajo de Trivelli y Mendoza (2026), «Repensar y rearmar la política social para retomar
la senda perdida» (IEP, DT 309). Sus cifras publicadas están en `referencias/contraste_dt309.csv`, con su fuente
original y su página. Úsalas solo para contrastar tus resultados, nunca como resultados propios.

Pasos:

1. **Plan.** Escribe primero un plan breve: qué series y qué indicadores necesitas y con qué herramienta.
2. **BCRP (MCP).**
   - Con `buscar_series`, ubica el IPC de Lima Metropolitana (índice dic. 2021 = 100), el IPC de Alimentos y
     Bebidas (índice) y la variación a 12 meses del IPC total y del de alimentos.
   - Con `resumen`, describe esas series en los periodos que uses.
   - Con `valor_real`, calcula a cuántos soles de diciembre de 2006 equivalen los S/ 100 de Juntos de agosto de 2026
     y de octubre de 2026.
   - Con `graficar_serie`, guarda `figuras/bcrp_ipc_alimentos.png` con el IPC total y el de alimentos, base
     dic. 2006 = 100, de 2006-12 al último mes disponible, con un título que diga qué muestra.
3. **ENAHO (Skills).**
   - Usa `limpiando-enaho` y confirma en `salidas/validacion.txt` que la base es válida.
   - Usa `graficando-enaho` para los gráficos por área y por tipo de hogar.
   - Usa `mapeando-enaho` para el mapa departamental.
   - Toma de `salidas/indicadores.csv`: pobreza por área y por tipo de hogar, distribución de los pobres, gasto en
     alimentos de pobres y no pobres, y la mediana del monto de Juntos.
4. **Cruce.** Con `valor_real`, expresa en soles de diciembre de 2006 la mediana mensual de Juntos que registra la
   ENAHO 2024, usando el IPC de diciembre de 2024. Calcula en Python, no a mano, cuánto del alza del costo de vida
   de un hogar pobre se explica por los alimentos: participación de los alimentos en su gasto × inflación de
   alimentos a 12 meses del último mes.
5. **Contraste.** Compara tus cifras 2024 con las publicadas en `referencias/contraste_dt309.csv` y anota las
   diferencias. Si algo no cuadra, dilo y explica la posible razón.
6. **Informe.** Escribe `informes/informe_final.md` en español claro, con estas secciones:
   1. Pregunta de investigación: tema, objetivo y delimitación.
   2. Fuentes y metodología: datos, procesamiento, ponderación e indicadores, con los códigos de serie.
   3. Resultados: al menos 3 hallazgos numerados, cada cifra con su fuente (código de serie y periodo, o
      indicador de la ENAHO).
   4. Visualizaciones: inserta `../figuras/bcrp_ipc_alimentos.png`, `../figuras/enaho_pobreza_hogares.png`,
      `../figuras/enaho_pobreza_area.png` y `../mapas/pobreza_departamento_2024.png`, cada una con un comentario
      de una o dos líneas.
   5. Interpretación: los patrones principales. Asociaciones, no causas.
   6. Limitaciones: cobertura temporal (ENAHO 2024 frente a series al 2026), niveles de agregación distintos,
      calidad de los datos y alcance. Incluye lo que no se puede medir con los módulos 34 y 02.
   7. Reproducibilidad: comandos, scripts, archivos de salida y series usadas.
   8. Contraste con cifras publicadas: una tabla con la cifra del informe, la cifra publicada, la fuente y la
      diferencia.
   Si una herramienta falla o no encuentra datos, dilo en el informe; no inventes valores.
7. Al final, resume en pocas líneas qué herramientas MCP y qué Skills usaste.
