# Comparación: Claude Code sin y con MCP + Skills

Las mismas 10 preguntas ([`preguntas.csv`](preguntas.csv): 4 del BCRP, 4 de la ENAHO y 2 que combinan ambas), cada
una en una sesión nueva de `claude -p`, con el mismo modelo (Claude Sonnet 5.5), la misma instrucción y la misma
tolerancia. Las respuestas esperadas se calcularon antes de evaluar con un camino independiente
([`verificacion_independiente.py`](verificacion_independiente.py): lee los `.dta` y la API del BCRP sin el servidor ni
las Skills) y se guardaron en Git en el commit `08a323e`, antes de la primera corrida. Detalle por pregunta:
[`resultados.csv`](resultados.csv). Salida completa de cada corrida (stream-json): `evidencias_ia/evaluacion/`.

## Condiciones

| | Modo A · sin MCP ni Skills | Modo B · con MCP y Skills |
|---|---|---|
| Carpeta de trabajo | carpeta vacía fuera del repositorio (no puede leer respuestas calculadas) | `tarea_4/` |
| Herramientas de Claude Code | ninguna (`--tools ""`), solo la respuesta estructurada | `Bash`, `Read`, `Glob`, `Grep`, `Skill` |
| MCP | ninguno (`--strict-mcp-config`) | solo `bcrp` (`--mcp-config .mcp.json --strict-mcp-config`) |
| Skills del proyecto | no visibles | `limpiando-enaho`, `graficando-enaho`, `mapeando-enaho` |
| Web (WebSearch, WebFetch) | no | no |
| Otras | las Skills de usuario de Claude Code estaban instaladas pero no se podían invocar sin la herramienta `Skill` | las mismas Skills de usuario, ninguna usada |

## Resultados

| | Modo A | Modo B |
|---|:-:|:-:|
| Correctas (dentro de la tolerancia) | **1/10** | **10/10** |
| Incorrectas | 0 | 0 |
| No responde (`valor = null`) | 9 | 0 |
| Tiempo promedio por pregunta | 6,1 s | 20,6 s |
| Tiempo máximo | 7,5 s | 32,2 s |
| Turnos promedio | 2,0 | 5,4 |
| Costo total de las 10 (US$) | 0,08 | 0,56 |

Por tipo de pregunta:

| Tipo | A correctas | B correctas | Tiempo A | Tiempo B |
|---|:-:|:-:|:-:|:-:|
| BCRP (4) | 0 | 4 | 5,4 s | 13,8 s |
| ENAHO (4) | 1 | 4 | 6,8 s | 25,5 s |
| Mixtas (2) | 0 | 2 | 5,9 s | 24,6 s |

**Preguntas que mejoraron:** 9 de 10 (todas salvo `pobreza_2024`, que A ya acertaba). **Empeoraron:** ninguna.

## Qué herramientas usó el modo B

| Pregunta | Herramientas |
|---|---|
| ipc_oct26, alimentos_oct26, pesca_may26 | `buscar_series` → `serie` |
| juntos_real_2006 | `valor_real` (una sola llamada) |
| pobreza_2024, extrema_rural, dep_mas_pobre | `Bash` sobre los microdatos o las salidas de la limpieza |
| pobres_urbanos | Skill `limpiando-enaho` + `Bash` sobre `salidas/hogares_2024.parquet` |
| juntos_enaho_real_2006 | `Bash` (mediana de `ingtpu01`) + `buscar_series` + `valor_real` |
| aporte_alimentos_pobres | `Grep` en `salidas/indicadores.csv` + `buscar_series` + `serie` |

Las dos preguntas mixtas combinaron una herramienta del MCP con una salida de la ENAHO, como se esperaba. La
calificación usa solo la cifra y su tolerancia, fijadas antes. Como control de coherencia, revisado después y sin
cambiar la calificación, la `fuente` de ambas respuestas cita las dos partes: la serie del BCRP (`PN38705PM`,
`PN09822PM`) y la variable o el indicador de la ENAHO (`ingtpu01`, participación de alimentos de los pobres).

## Principales errores y hallazgos

1. **El modo A no inventó cifras: se abstuvo.** La instrucción permite responder `null` si no hay certeza, y el
   modelo lo usó en 9 de 10 preguntas, explicando que no tiene datos de 2026 ni los microdatos. Solo dio la pobreza
   nacional 2024 (27,6 %), que el INEI publicó en mayo de 2025 y el modelo recuerda. Sin MCP ni Skills el agente es
   prudente pero inútil para cifras recientes o calculadas.
2. **El modo B acertó todas, pero no siempre por la vía prevista.** En 5 de las 6 preguntas que usan la ENAHO
   (4 de ENAHO y 2 mixtas) no invocó la Skill de forma explícita: calculó con `Bash` sobre los `.dta` o sobre `salidas/`, que la Skill ya había generado.
   Las cifras coinciden porque aplicó las mismas reglas (ponderación `factor07 × mieperho`, `estrato`, `pobreza`).
   El riesgo es que, sin la Skill, una regla (por ejemplo el filtro de residentes) podría omitirse; la mejora
   sería describir en la `description` de la Skill que toda cifra de la ENAHO debe salir de `indicadores.csv`.
3. **Las herramientas cuestan tiempo:** B tarda 3,4 veces más que A y cuesta unas 7 veces más, sobre todo en las
   preguntas de la ENAHO (lectura de microdatos).
4. **Redondeo:** B redondeó algunas cifras (5,25 frente a 5,2510; 45,00 frente a 45,0069), siempre dentro de la
   tolerancia definida.

## Conclusión

El MCP y las Skills convierten preguntas que el modelo no puede responder (series de 2026, microdatos, cálculos
combinados) en respuestas correctas con su fuente: de 1/10 a 10/10 con las mismas preguntas e instrucciones. Su
valor no está en que el modelo "sepa más", sino en que cada cifra sale de una llamada que se puede repetir y citar
(código de serie, archivo y fórmula). El costo es tiempo (unos 15 s más por pregunta) y que el agente puede
saltarse la Skill si tiene acceso a los archivos.

Limitaciones del experimento: una sola corrida por pregunta y modo (sin repeticiones para medir variabilidad), un
solo modelo, y una instrucción que favorece la abstención (otra instrucción podría producir cifras inventadas en
el modo A).
