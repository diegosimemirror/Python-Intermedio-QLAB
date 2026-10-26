# Tarea 2 · Voces y documentos peruanos: del archivo escaneado al texto buscable

**Estudiante:** Diego Enrique Sime Rendón (@diegosimemirror)
**Dashboard público:** https://python-intermedio-qlab-aeod9u3y4jl5hta8gpphg4.streamlit.app/

## Pregunta del proyecto

¿Pueden convertir documentos escaneados y entrevistas en audio en un archivo de texto estructurado y buscable?

**Respuesta corta:** sí para los impresos, las fotos y la voz; todavía no para los manuscritos ni para extraer campos de forma automática.
- Con **PaddleOCR** y **Parakeet**, la muestra evaluada queda en **CER 0,23** y **WER 0,05**: el texto es buscable.
- Los manuscritos (CER 0,47) y la extracción con un LLM pequeño (7/20 correctas) siguen necesitando revisión humana.

## Corpus, fuentes y licencias

**Fecha de extracción:** 25 de octubre de 2026 (America/Lima). Cada archivo, con su URL, licencia y forma de recuperarlo, está en `datos/fuentes.csv`.

| Corpus | Volumen | Fuente | Licencia |
|---|---|---|---|
| A. Documentos impresos | 8 | Wikimedia Commons: revista *Variedades* (1908-1910), *El Comercio* n.º 1 (1839), Constituciones de 1828 y 1856, cartas mecanografiadas de C. Bachmann a R. Palma (1914, Biblioteca Nacional del Perú) y de C. Vallejo a J. C. Mariátegui (1926) | PD-Peru-organization, PD-old-100, PD-Peru-1961law, CC0 |
| A. Fotos con sombra o inclinación | 8 | Wikimedia Commons: placas de Salaverry, de Grau y del Edificio Fénix, una carta en vitrina (Tacna), un libro de bautismos de Lampa (1832), una gramática latina (1865), una carta de Velasco Alvarado (1972) y el *Estado General* de Grau enmarcado | CC BY-SA 3.0/4.0, CC BY 2.0/4.0 y CC0, según el autor de cada foto |
| A. Manuscritos | 9 | Wikimedia Commons: cartas de Gamarra, San Román y Piérola (Academia Nacional de la Historia, Argentina), documentos coloniales de 1544 a 1694, un parte de Grau (1879) y una carta de Vallejo a Eguren (1917) | PD-old-100, PD-Peru-1961law |
| B. Audio leído | 20 clips, 34,9 min | OpenSLR 73 (Google, *Crowdsourced high-quality Peruvian Spanish speech*). Cada clip une los enunciados de un hablante anónimo | CC BY-SA 4.0 |
| B. Entrevistas (2 hablantes) | 2 clips, 6,0 min | Wikimedia Commons: `Entrevista_4.wav` y `Entrevista_1,.wav` (estudiante de la UNMSM) | CC BY-SA 4.0. Autor: Gianpier Yair Venegas Ambia |

**Total:** 25 documentos (8 impresos, 8 fotos y 9 manuscritos) y 22 clips con **40,9 min** de audio.

**Descartes:** `clip_021` era una mezcla sintética de dos hablantes de OpenSLR y no entró al corpus. No hubo duplicados por hash ni documentos ilegibles según los criterios fijados (detalle en `datos/descartes.csv`).

**Seudonimización:**
- En las entrevistas se reemplazaron por `[PERSONA_n]` los **7 nombres de personas privadas** que se mencionan: el entrevistador y los dos entrevistados.
- El diccionario de nombres reales no se publica.
- El audio de las entrevistas tampoco se publica, porque la voz no se puede seudonimizar.
- El nombre del autor aparece solo en la atribución que exige la licencia CC BY-SA.
- Los documentos son históricos y solo nombran figuras públicas ya fallecidas, así que se conservan.

## Metodología

1. **`01_extraccion.ipynb`:**
   - Inventario y licencias; limpieza por hash MD5 y por VAD.
   - **OCR** con PaddleOCR 3.7: PP-OCRv5 *mobile*, con clasificación de orientación, en CPU.
   - **ASR** con faster-whisper `small` (int8) y VAD Silero.
   - **Diarización** de las entrevistas con huellas WeSpeaker y agrupamiento (`voz.py` de la Sesión 13).
   - Seudonimización y EDA con Plotly.
   - Exportación de los CSV y de los SRT/TXT seudonimizados (`datos/salidas_asr/`).
2. **`02_evaluacion.ipynb`:**
   - **Muestra:** 10 documentos (4 impresos, 3 fotos y 3 manuscritos), evaluados sobre un recorte fijo transcrito a mano, y 10 clips: 8 de OpenSLR con el guion humano del corpus como referencia, y 2 entrevistas transcritas a mano en sus primeros 60 s.
   - **Comparación sobre las mismas muestras:** PaddleOCR frente a **EasyOCR**, y faster-whisper `small` frente a **Parakeet TDT 0.6B v3**.
   - **Extracción JSON** con **Qwen2.5-1.5B-Instruct** local para los 47 textos y **auditoría humana** de 20 casos al azar.
3. **`app.py`:** dashboard Streamlit que solo lee los CSV precalculados.

## Resultados (muestra de 10 documentos y 10 clips)

| Modalidad | Modelo | Error (muestra de 10) | Latencia (CPU, 2 núcleos) | Tamaño |
|---|---|---|---|---|
| Documentos | **PaddleOCR 3.7 PP-OCRv5 mobile** (línea base, elegido) | **CER 0,228** | 9,2 s por recorte | ≈ 20 MB |
| Documentos | EasyOCR 1.7 (`es`) | CER 0,334 | 21,0 s por recorte | ≈ 95 MB |
| Audio | faster-whisper `small` int8 (línea base) | WER 0,065 | RTF 0,29 | ≈ 250 MB |
| Audio | **Parakeet TDT 0.6B v3** (elegido) | **WER 0,052** | RTF 0,23 | ≈ 2,4 GB |

| Por tipo | PaddleOCR | EasyOCR | | Por origen | Whisper `small` | Parakeet |
|---|---|---|---|---|---|---|
| Fotos | 0,015 | 0,115 | | OpenSLR (voz leída) | 0,040 | 0,029 |
| Impresos | 0,288 | 0,264 | | Entrevistas (espontánea) | 0,201 | 0,173 |
| Manuscritos | 0,466 | 0,763 | | | | |

**Acuerdo LLM-humano:** 7/20 extracciones completamente correctas (35 %). Además, 47/47 respuestas fueron JSON válidos y el modelo no agregó ninguna clave no pedida.

**Resultados Test:** WER 0.05 | CER 0.23 | Acuerdo LLM-Humano 7/20.

## Hallazgos

1. **El OCR depende más del tipo de letra que de la calidad de la foto.**
   - Las placas y portadas **fotografiadas** en ángulo fueron el mejor caso (CER 0,015), porque tienen letras grandes y en mayúsculas.
   - Los **manuscritos** fueron el peor (0,47), y los coloniales de 1544 a 1677 devuelven texto sin sentido con confianza menor que 0,5.
   - En dos impresos nítidos, PaddleOCR falló porque su **clasificador de orientación de línea volteó 180° varias líneas** del recorte (6 de 8 en `doc_007`), algo que no ocurrió con la página completa. Una confianza media menor que 0,5 sirve para mandar el documento a revisión humana.
2. **En audio, el tipo de habla pesa más que el modelo.**
   - La voz leída de OpenSLR tiene un WER de 0,03 a 0,04 y las entrevistas espontáneas, de 0,17 a 0,20, por las muletillas, las autocorrecciones y las frases cortadas.
   - Parakeet supera a Whisper `small` en las dos condiciones y además es más rápido en CPU. Su costo es la memoria: 2,4 GB frente a 250 MB.
3. **El LLM pequeño no sabe decir "no lo sé".** Siempre responde en el formato pedido, pero ante un OCR ilegible prefiere inventar un tema (4 de los 13 errores) y fuerza un tema único en clips de frases sueltas.

## Limitaciones técnicas

1. **La muestra y las referencias son pequeñas.**
   - La evaluación usa 10 documentos (un recorte de cada uno) y 10 clips. Las entrevistas se evalúan solo en sus primeros 60 s.
   - La referencia de OpenSLR es el guion oficial del corpus y no se volvió a verificar al oído.
   - El corpus no tiene audios con música ni en quechua, y no se intentó la bonificación con MMS.
   - La diarización sobresegmentó una entrevista: detectó 3 hablantes donde había 2.
2. **Solo hubo CPU.**
   - Todo corrió en CPU con 2 núcleos. Por eso se usó PaddleOCR *mobile* en lugar del modelo por defecto (`PP-OCRv6_medium`, que tardaba 3,5 veces más) y un LLM de 1.500 millones de parámetros, con la entrada recortada a 1.500 caracteres.
   - Los audios crudos y los pesos de los modelos no se suben a GitHub.
   - El dashboard solo reproduce 3 fragmentos de 30 s de OpenSLR. Las entrevistas se muestran como texto seudonimizado porque la voz de una persona privada no se puede anonimizar.

## Estructura

```
tarea_2/
├── 01_extraccion.ipynb        # OCR, ASR, diarización, seudonimización, limpieza y EDA
├── 02_evaluacion.ipynb        # CER/WER, comparación de modelos, LLM y auditoría
├── app.py                     # Dashboard Streamlit (solo lee CSV)
├── voz.py                     # Módulo de la Sesión 13 (carga de audio, VAD, diarización, CER/WER)
├── extraccion_llm.py          # Prompt + LLM local + lectura del JSON (con caché)
├── requirements.txt           # Dependencias del dashboard
├── .gitignore                 # Excluye datos/raw/, audios crudos y pesos de modelos
├── evidencias_ia/             # Capturas de la conversación con Claude Code
├── datos/
│   ├── documentos.csv         # 25 documentos (columnas obligatorias + apoyo)
│   ├── transcripciones.csv    # 22 clips, 40,9 min
│   ├── extraccion_llm.csv     # Campos JSON del LLM (47 registros)
│   ├── fuentes.csv            # URL, licencia y acceso de cada archivo
│   ├── evaluacion_modelos.csv # Error por caso y modelo
│   ├── comparativa_modelos.csv
│   ├── auditoria_llm.csv      # Revisión humana de 20 extracciones
│   ├── descartes.csv
│   ├── muestra_evaluacion.json
│   ├── referencias/           # Recortes y transcripciones manuales de los documentos
│   ├── salidas_asr/           # SRT y TXT seudonimizados
│   └── ejemplos/              # Miniaturas, 3 audios OpenSLR de 30 s y gráficos PNG
└── modelos/
    ├── prompt_extraccion.json # Prompt del LLM
    └── metricas.json          # CER, WER y acuerdo LLM-humano
```

## Cómo ejecutarlo en local

```bash
git clone https://github.com/diegosimemirror/Python-Intermedio-QLAB.git
cd Python-Intermedio-QLAB/tarea_2
pip install -r requirements.txt
streamlit run app.py
```

El dashboard se abre en http://localhost:8501.

**Para volver a ejecutar los notebooks** se necesitan Python 3.12 y estos paquetes:
- `paddlepaddle==3.3.1`, `paddleocr==3.7.0`, `faster-whisper==1.2.1`, `pyannote.audio==4.0.7`, `easyocr==1.7.2`, `transformers==5.20.1`, `torch==2.14.1` (CPU), `jiwer==4.0.0`, `rapidfuzz`, `soundfile`, `plotly` y `kaleido`.
- Son los mismos de `uv sync --group docai` y `uv sync --group audio` del repositorio del curso.
- Los archivos originales se recuperan con las URL de `datos/fuentes.csv` y van en `datos/raw/`.
- Todo se ejecutó en una laptop sin GPU utilizable, en CPU limitada a 2 núcleos: OCR 14 min, ASR 12 min y LLM 42 min.
