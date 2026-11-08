# Tarea 4 · Agente de investigación socioeconómica (MCP del BCRP + Skills de la ENAHO 2024)

**Pregunta de investigación:** ¿A quién protege hoy la política social en el Perú? Cuánto poder de compra perdió la
transferencia de Juntos y cuánto subieron los alimentos frente al resto de precios (BCRP, 2006-2026), y dónde y en
qué hogares se concentra la pobreza monetaria en 2024 (ENAHO 2024).

Informe: [`informes/informe_final.md`](informes/informe_final.md) · Enunciado: issue #201 de
[d2cml-ai/Data-Science-Python](https://github.com/d2cml-ai/Data-Science-Python/issues/201).

## 1. Objetivo

Un agente en Claude Code que responde preguntas sobre la economía y la pobreza del Perú con datos oficiales y
cálculos que se pueden repetir: las series del BCRP llegan por un servidor MCP y los microdatos de la ENAHO 2024 se
procesan con tres Skills. El modelo no hace cuentas a mano: cada cifra sale de una herramienta.

## 2. Arquitectura

```
                 pregunta en lenguaje natural
                              │
                     Claude Code (agente)
            ┌─────────────────┴──────────────────┐
     MCP «bcrp» (mcp/server.py)        Skills (.claude/skills/)
     buscar_series · serie · resumen    limpiando-enaho → salidas/*.parquet, validacion.txt, indicadores.csv
     valor_real · graficar_serie        graficando-enaho → figuras/enaho_*.png
     recurso bcrp://serie/{codigo}      mapeando-enaho  → mapas/pobreza_departamento_2024.png
     prompt informe(tema)               (gráficos y mapa piden la limpieza si falta la base)
            │                                    │
   API del BCRP (estadisticas.bcrp.gob.pe)   INEI: ENAHO 2024 módulos 34 y 02 + GeoJSON del curso
            └─────────────────┬──────────────────┘
                 informes/informe_final.md (+ contraste con cifras publicadas)
```

## 3. Herramientas MCP (`mcp/server.py`)

| Herramienta | Qué hace |
|---|---|
| `buscar_series(texto, frecuencia, limite)` | Busca en el catálogo oficial (17 mil series) por palabras |
| `serie(codigo, desde, hasta)` | Datos de una serie con su periodo normalizado (`2025-01`, `2025-T1`, `2026-10-01`, `2025`) y la URL de la fuente |
| `resumen(codigo, desde, hasta)` | Primero, último, cambio, variación %, promedio, máximo y mínimo con su periodo |
| **`valor_real(monto, desde, hasta, codigo_ipc)`** (propia) | Lleva un monto en soles de una fecha a soles de otra con el IPC del BCRP: `monto × IPC[hasta] / IPC[desde]`. Ej.: los S/ 100 de Juntos de ago-2026 valen S/ 51,82 de dic-2006 |
| `graficar_serie(codigos, desde, hasta, titulo, archivo, base_100)` | Guarda en `figuras/` un gráfico de 1 a 4 series, opcionalmente con base 100 |
| Recurso `bcrp://serie/{codigo}` | Ficha de la serie: nombre, grupo, frecuencia, unidad, fechas |
| Prompt `informe(tema)` | Plantilla que obliga a citar código, periodo y fuente y a no inventar cifras |

Detalles robustos: la API a veces pega un aviso HTML de PHP después del JSON y no responde en UTF-8 (se lee con
`raw_decode` y latin-1 si hace falta); si devuelve una página HTML por exceso de pedidos, reintenta con espera; las
respuestas quedan en caché 6 horas (`mcp/cache/`, fuera de Git).

## 4. Skills (`.claude/skills/`)

| Skill | Entra | Sale |
|---|---|---|
| `limpiando-enaho` | `datos/966-Modulo34.zip`, `datos/966-Modulo02.zip` | `salidas/personas_2024.parquet`, `salidas/hogares_2024.parquet`, `salidas/indicadores.csv`, `salidas/validacion.txt` |
| `graficando-enaho` | la base limpia + `area`, `sexo`, `hogares`, `departamentos` o `todos` | `figuras/enaho_pobreza_*.png` |
| `mapeando-enaho` | la base limpia + `datos/peru_departamental_simple.geojson` | `mapas/pobreza_departamento_2024.png`, `salidas/comparacion_mapa.csv` |

Reglas de `limpiando-enaho` (detalle en su `reference.md`): llaves como texto, nombres en minúscula, residentes
habituales `((p204==1)&(p205==2))|((p204==2)&(p206==1))`, unión `merge(validate="m:1")` sin perder ni duplicar
filas, `departamento = ubigeo[:2]`, `urbano = estrato <= 5`, `pobre = pobreza <= 2`, `mieperho` convertido a decimal
(llega como int8 y `12 × mieperho` desborda en hogares de 11 o más) y ponderación `factor07 × mieperho` (hogares) o
`facpob07` (personas). Si una validación esencial falla, escribe `validacion.txt` con el detalle y termina con error
sin guardar bases.

Validación obtenida ([`salidas/validacion.txt`](salidas/validacion.txt)): pobreza nacional **27,58 %** (27,53 % con
personas), **108 664** residentes, **25/25** departamentos, urbana 24,81 %, rural 39,30 %, unión 108 664 → 108 664,
diferencia máxima con la referencia departamental de la sesión 16: 0,05 puntos.

## 5. Fuentes y datos

| Fuente | Archivo | Enlace |
|---|---|---|
| INEI · ENAHO 2024 módulo 34 (sumaria) | `datos/966-Modulo34.zip` | https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/966-Modulo34.zip |
| INEI · ENAHO 2024 módulo 02 (miembros) | `datos/966-Modulo02.zip` | https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/966-Modulo02.zip |
| Curso · límites departamentales | `datos/peru_departamental_simple.geojson` | https://raw.githubusercontent.com/d2cml-ai/Data-Science-Python/main/sessions/06-geoespacial/lab/Data/peru_departamental_simple.geojson |
| BCRP · series estadísticas | vía MCP | https://estadisticas.bcrp.gob.pe/estadisticas/series/ |
| Curso · pobreza por departamento 2024 | `referencias/pobreza_departamento_2024.csv` | sesión 16 |
| Trivelli y Mendoza (2026), DT IEP 309 | `referencias/contraste_dt309.csv` (cifras publicadas, con página) | IEP, octubre de 2026 |

`datos/` no se sube a Git. Para bajar todo: `uv run python scripts/descargar_datos.py`.

## 6. Instalación con `uv`

```bash
git clone https://github.com/diegosimemirror/Python-Intermedio-QLAB
cd Python-Intermedio-QLAB/tarea_4
uv sync                                   # Python ≥ 3.11 con fastmcp, pandas, pyarrow, geopandas, matplotlib, pytest
uv run python scripts/descargar_datos.py  # ENAHO 2024 (módulos 34 y 02) y GeoJSON en datos/
```

## 7. Conectar el MCP a Claude Code

El archivo [`.mcp.json`](.mcp.json) ya registra el servidor (equivale a
`claude mcp add --scope project bcrp -- uv run python mcp/server.py`). Abran Claude Code en `tarea_4/`, aprueben el
servidor `bcrp` y revisen con `/mcp`. Las Skills se cargan solas desde `.claude/skills/` (véanlas con `/skills`).

## 8. Reproducir

```bash
uv run pytest                                                         # 10 passed (8 originales + 2 propias)
uv run python .claude/skills/limpiando-enaho/scripts/limpiar.py       # base, indicadores y validación
uv run python .claude/skills/graficando-enaho/scripts/graficar.py todos
uv run python .claude/skills/mapeando-enaho/scripts/mapear.py
uv run python evaluacion/verificacion_independiente.py                # respuestas esperadas (sin MCP ni Skills)
uv run python evaluacion/evaluar.py                                   # experimento A/B (20 llamadas a claude -p)
# ejecución integrada del agente (genera informes/informe_final.md):
claude -p "$(cat informes/prompt_agente.md)" --model opus --mcp-config .mcp.json --strict-mcp-config \
  --allowedTools "mcp__bcrp,Skill,Bash,Read,Write,Edit,Glob,Grep" --disallowedTools "WebSearch,WebFetch" \
  --output-format stream-json --verbose > evidencias_ia/integracion/ejecucion_agente.jsonl
uv run python scripts/jsonl_a_md.py evidencias_ia/integracion/ejecucion_agente.jsonl
```

## 9. Resultados de la evaluación

Mismas 10 preguntas (4 BCRP, 4 ENAHO, 2 mixtas), cada una en una sesión nueva de `claude -p` con Claude Sonnet 5.5,
respuestas esperadas fijadas en Git antes de evaluar (commit `08a323e`). Detalle en
[`evaluacion/comparacion.md`](evaluacion/comparacion.md) y [`evaluacion/resultados.csv`](evaluacion/resultados.csv).

| | Sin MCP ni Skills (A) | Con MCP y Skills (B) |
|---|:-:|:-:|
| Correctas | **1/10** | **10/10** |
| Incorrectas | 0 | 0 |
| No responde | 9 | 0 |
| Tiempo promedio | 6,1 s | 20,6 s |

Sin herramientas, Claude se abstuvo (no inventó) en todo lo que no recordaba; con ellas respondió con código de
serie, archivo y fórmula. En 5 de las 6 preguntas que usan la ENAHO el agente calculó con `Bash` sobre los
microdatos o las salidas de la limpieza en vez de invocar la Skill.

## 10. Limitaciones y problemas encontrados

| Problema | Qué se hizo |
|---|---|
| `mieperho` llega como int8: `12 × mieperho` desborda en hogares de 11+ y da gasto negativo | se convierte a decimal; la regla de pobreza reproduce el 100 % de los casos |
| La API del BCRP pega un aviso HTML de PHP después del JSON y no siempre responde en UTF-8 | lectura con `raw_decode` y respaldo latin-1; reintentos si llega una página HTML |
| El zip del módulo 34 trae dos sumarias (8 y 12 grupos de gasto) | se usa `sumaria-2024.dta`; en ella `gru1*` es solo alimentos |
| 19 hogares (0,06 %) tienen gasto en alimentos mayor que el gasto total | se avisa en `validacion.txt` y no se corrige |
| La ENAHO estima 1,04 millones de hogares con Juntos; el padrón tiene unos 760 mil | se reporta como discrepancia, no se usa el número de hogares de la ENAHO para costos |
| `ingtpuhd` (transferencias públicas) es 78 % "otros" (`ingtpu02`) | no se usa como "programas sociales" |
| Restar Juntos y Pensión 65 del gasto sube la pobreza 2024 solo 1,3 puntos; el DT 309 cita 3,9 puntos para 2025 (CIES) | no se reproduce; se reporta como diferencia de método y año |
| Sin inseguridad alimentaria (FIES desde 2025), educación, lengua, empleo ni vivienda (módulos 100, 300, 500) | se citan cifras publicadas solo como contraste |
| ENAHO es un corte de 2024; las series del BCRP llegan a 2026 | el informe no infiere causalidad ni mezcla periodos sin decirlo |

## 11. Ejemplo de una ejecución completa

La investigación del informe se hizo en **una sola ejecución** de Claude Code (Opus 5.5, unos 7 minutos) con el
pedido de [`informes/prompt_agente.md`](informes/prompt_agente.md). Registro completo:
[`evidencias_ia/integracion/ejecucion_agente.md`](evidencias_ia/integracion/ejecucion_agente.md) (crudo en
`ejecucion_agente.jsonl`).

| Paso | Qué hizo el agente |
|---|---|
| Plan | listó series, indicadores y herramientas antes de empezar |
| MCP | `buscar_series` ×4, `resumen` ×9, `serie` ×3, `valor_real` ×4, `graficar_serie` ×2 |
| Skills | `limpiando-enaho` (validación VÁLIDA), `graficando-enaho` (`area`, `hogares`), `mapeando-enaho` (25/25) |
| Cruce | escribió `scripts/cruce_y_contraste.py`: participación de alimentos de los pobres (ENAHO) × inflación de alimentos (BCRP) = 2,36 pp |
| Contraste | 13 cifras frente al DT 309: las 10 comparables difieren menos de 0,03 pp; 3 no son comparables (año o fuente) |
| Informe | [`informes/informe_final.md`](informes/informe_final.md): 4 hallazgos, gráfico BCRP, 2 gráficos ENAHO, mapa, interpretación, limitaciones |

Luego, la verificación manual (sección 9 del informe) comprobó 9 afirmaciones por otro camino: la página web del
BCRP, el INEI y `evaluacion/verificacion_independiente.py`. Corrigió una interpretación (el valor de Juntos con la
canasta de los pobres es S/ 50,65 de 2006, no cercano a S/ 43,53) y cambió el script del agente para que pida los
valores al MCP en lugar de tenerlos copiados.

## 12. Evidencias del uso de IA

Todo se desarrolló con Claude Code. Ver [`evidencias_ia/`](evidencias_ia/):

- [`conversacion_desarrollo.md`](evidencias_ia/conversacion_desarrollo.md): la conversación completa, desde la
  lectura del enunciado hasta la entrega, con los datos sensibles ocultos (`scripts/copiar_evidencias.py`).
- `mcp/` y `skills/`: guía de dónde está cada parte del desarrollo y sus correcciones.
- `integracion/`: la ejecución del agente con MCP y Skills.
- `evaluacion/`: las 20 corridas del experimento A/B.
