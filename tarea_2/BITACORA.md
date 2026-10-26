# Bitácora de desarrollo · Tarea 2

Registro por etapa, una sección por cada issue del repositorio: [#4](https://github.com/diegosimemirror/Python-Intermedio-QLAB/issues/4), [#5](https://github.com/diegosimemirror/Python-Intermedio-QLAB/issues/5) y [#6](https://github.com/diegosimemirror/Python-Intermedio-QLAB/issues/6).

---

## Issue #4 · T2 – Parte 1: Corpus y extracción (OCR + ASR)

**Bitácora – Parte 1** (25-10-2026)

**Corpus**
- Insumos recolectados de Wikimedia Commons y OpenSLR 73: 25 documentos (8 impresos, 8 fotos, 9 manuscritos) y 23 clips.
- `clip_021` (mezcla sintética de 2 hablantes) se descartó: la tarea prohíbe material sintético. Quedan 22 clips, 40,9 min.
- Licencias y forma de recuperar cada archivo en `datos/fuentes.csv`. Sin duplicados por MD5; el VAD detecta voz en todos los clips (35–90 %).

**Decisiones técnicas**
- PaddleOCR 3.7 en CPU (2 núcleos, la laptop se recalienta): el modelo por defecto (PP-OCRv6 medium) tardó 117–126 s por página. Se eligió **PP-OCRv5 mobile** (36 s). La decisión se tomó solo por latencia, sin mirar métricas.
- oneDNN falla en Windows (mismo error PIR que la Sesión 10) → `enable_mkldnn=False`.
- ASR: faster-whisper `small` int8 + VAD Silero. Diarización con `voz.py` (WeSpeaker + clustering).

**Resultados**
- OCR: 25 documentos en 13,8 min. Confianza media: impresos 0,86, fotos 0,79, manuscritos 0,57.
- ASR: 40,9 min de audio en 11,7 min (RTF 0,27).
- Diarización: 2 hablantes en `clip_023`; 3 en `clip_022` (sobresegmentación de un tramo < 1 s, se reporta tal cual).
- Seudonimización: 7 nombres de personas privadas reemplazados en las entrevistas.

**Problemas resueltos**
- El kernel `python3` de Jupyter apuntaba al Anaconda base → se ejecutó con el kernel `pucp`.
- El histograma de longitudes compartía intervalos entre OCR y ASR → se separó en 3a y 3b.

Cerrado con `fda2720`. Desarrollado con apoyo de Claude Code (capturas en `evidencias_ia/`).

---

## Issue #5 · T2 – Parte 2: Evaluación y extracción estructurada

**Bitácora – Parte 2** (25-10-2026)

**Muestra (fijada antes de correr los modelos)**
- 10 documentos (4 impresos, 3 fotos, 3 manuscritos), evaluados sobre un recorte fijo.
- 10 clips: 8 de OpenSLR (semilla 2026, 4 voces femeninas y 4 masculinas) + 2 entrevistas (primeros 60 s).

**Referencias**
- Transcripción manual de los 10 recortes y de las 2 entrevistas, revisada contra la imagen para corregir erratas de tipeo.
- OpenSLR: guion humano oficial del corpus.
- Normalización definida antes de medir: sin `[HABLANTE_n]`, `[?]` ni muletillas, en ambos lados.

**Modelos (mismas muestras, misma laptop)**

| | Modelo | Error | Latencia |
|---|---|---|---|
| OCR | PaddleOCR mobile | CER 0,228 | 9,2 s |
| OCR | EasyOCR | CER 0,334 | 21,0 s |
| ASR | Whisper small | WER 0,065 | RTF 0,29 |
| ASR | Parakeet v3 | WER 0,052 | RTF 0,23 |

**Hallazgo:** Paddle falló en 2 impresos nítidos. El diagnóstico mostró que su clasificador de orientación de línea volteó 180° varias líneas del recorte (6 de 8 en `doc_007`). Se documentó sin cambiar la configuración evaluada.

**LLM y auditoría**
- Qwen2.5-1.5B-Instruct local: 47 textos, 53 s por texto, 47/47 JSON válidos, 0 claves inventadas.
- Auditoría humana de 20 casos al azar: **7/20**. Criterio: "no especificado" se acepta como `null`.
- Error más frecuente: inventa un tema cuando el OCR es ilegible.

**Problema resuelto:** Parakeet requería `librosa` → instalada.

**Decisión:** PaddleOCR mobile para documentos y Parakeet v3 para audio.

Cerrado con `0216fcd`. Desarrollado con apoyo de Claude Code.

---

## Issue #6 · T2 – Parte 3: Dashboard y despliegue

**Bitácora – Parte 3** (25-10-2026)

- `app.py` solo lee los CSV precalculados: no carga modelos y es liviano para el plan gratuito.
- 5 pestañas:
  - Resumen
  - Explorador de documentos: imagen, OCR, campos LLM y referencia con CER.
  - Explorador de audios: `st.audio`, transcripción con hablantes y WER de cada modelo.
  - Evaluación
  - Datos con descarga CSV.
- Búsqueda sin distinguir tildes y filtros por tipo, modelo, origen y duración. `st.metric` con totales, CER/WER de los 4 modelos y concordancia LLM-humano.
- Muestra publicable: 25 miniaturas (dominio público o CC) y 3 fragmentos de 30 s de OpenSLR. Las entrevistas aparecen solo como texto seudonimizado: la voz de una persona privada no se puede anonimizar.
- Probado en local con `streamlit.testing` (sin excepciones; la búsqueda "Lima" devuelve 6 documentos).
- Desplegado en Streamlit Community Cloud (Python 3.12): https://python-intermedio-qlab-aeod9u3y4jl5hta8gpphg4.streamlit.app/
- Ajuste posterior: una tarjeta de indicador por cada modelo evaluado.

Cerrado con `311b098`; ajustes en `dfdd066` y `ba1930c`. Desarrollado con apoyo de Claude Code.
