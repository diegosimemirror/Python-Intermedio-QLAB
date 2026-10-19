# Tarea 1 · Noticias peruanas: del titular al clasificador

**Estudiante:** Diego Enrique Sime Rendón · **Medio:** La República (opción A)

## Pregunta del proyecto

¿Pueden convertirse titulares de noticias peruanas en un clasificador automático que
asigne cada titular a una de cuatro categorías: `politica`, `economia`, `deportes` y
`ciencia_tecnologia`?

**Respuesta corta:** sí. Un modelo DistilBERT multilingüe ajustado con 280 titulares
acierta 57 de 60 titulares que nunca vio (accuracy 0,95; F1 macro 0,949).

## Datos: medio y fechas de extracción

| | |
|---|---|
| Medio | La República (https://larepublica.pe/) |
| Secciones | `/politica`, `/economia`, `/deportes`, `/ciencia` |
| Fecha de descarga | 18 de octubre de 2026 |
| Fechas de publicación | 17 de septiembre al 18 de octubre de 2026 |
| Volumen | 468 URLs candidatas → 400 noticias finales (100 por categoría) |
| Archivos | `datos/noticias.csv` (7 columnas) y `datos/etiquetas_llm.csv` |

**Cómo se recolectó:** se revisó `robots.txt`. El RSS y los sitemaps solo ofrecían
unas 19 noticias por sección y la consulta interna de "Ver más noticias" respondía
403 a `requests`. Por eso las páginas de sección se recorrieron con Selenium, pulsando
"Ver más noticias", con pausas de 2 segundos y una sola visita por artículo. Se
descartaron 68 URLs: 1 error de extracción, 1 noticia duplicada con otra URL y 66
excedentes sobre la cuota de 100 por categoría.

## Metodología

1. **Recolección y limpieza** (`01_recoleccion.ipynb`): extracción, deduplicación,
   mapeo sección → categoría y análisis exploratorio con Plotly.
2. **Partición** estratificada 70/15/15 con `random_state=42`: 280 / 60 / 60.
3. **Tres clasificadores** (`02_clasificacion.ipynb`):
   - Zero-shot `Recognai/bert-base-spanish-wwm-cased-xnli`, sin entrenamiento.
   - LLM local `Qwen/Qwen2.5-1.5B-Instruct` con prompt estructurado (supervisión
     débil), auditado a mano en 20 casos.
   - Fine-tuning de `distilbert/distilbert-base-multilingual-cased` durante 3 épocas.
4. **Evaluación** en el conjunto de prueba (60 titulares) y comparación de precisión,
   costo y latencia.

| Enfoque | F1 macro (40 comunes) | F1 macro (test, 60) | Parámetros | Latencia por titular (CPU) |
|---|---|---|---|---|
| Zero-shot | 0,639 | — | 110 M | 169 ms |
| LLM débil (Qwen) | 0,806 | 0,768 | 1 544 M | 3 158 ms |
| **Fine-tuned** | **0,975** | **0,949** | 135 M | **21 ms** |

Acuerdo LLM–humano en la auditoría: **17/20 (85 %)**.

## Hallazgos

1. **Pocos ejemplos bastan para superar a modelos mucho más grandes.** Con solo 280
   titulares, el modelo ajustado (F1 0,949) supera al LLM (0,768), que tiene 11 veces
   más parámetros, y al zero-shot (0,639). Además responde unas 150 veces más rápido
   que el LLM (21 ms frente a 3,2 s), lo que lo hace viable para un dashboard en vivo.
2. **Los errores aparecen donde la sección editorial y el tema no coinciden.** Los 3
   errores del modelo son noticias de Política sobre minería, pagos o facultades
   tributarias, clasificadas como economía. El LLM etiqueta como política 20 de las
   100 noticias de Deportes (conflictos entre técnicos y dirigentes, sanciones) y como
   economía 15 de las 100 de Ciencia (historias con cifras o electricidad).

## Limitaciones técnicas

1. **Etiquetas ruidosas y ventana corta.** La etiqueta es la sección donde el diario
   publicó la noticia, no su tema, así que las noticias mixtas (política económica,
   conflictos en el fútbol) quedan con una sola etiqueta. Además, todo proviene de un
   medio y de un mes; el vocabulario de coyuntura (pedido de facultades, El Niño)
   puede no generalizar a otros medios o periodos.
2. **Dependencias de cómputo y del sitio web.** La recolección depende de Selenium y
   de la estructura actual de La República (usó el User-Agent por defecto de Chrome).
   El LLM tarda unos 3 segundos por titular en CPU (unos 24 minutos para 400) y los
   pesos del modelo final (516 MB) superan el límite de GitHub, por lo que no se
   suben al repositorio.

## Estructura

```
tarea_1/
├── 01_recoleccion.ipynb     # Recolección, limpieza y EDA
├── 02_clasificacion.ipynb   # Zero-shot, LLM, fine-tuning y evaluación
├── app.py                   # Dashboard en Streamlit
├── requirements.txt
├── README.md
├── datos/
│   ├── noticias.csv         # 400 noticias, 7 columnas
│   ├── etiquetas_llm.csv    # Etiquetas débiles del LLM
│   ├── auditoria_llm.csv    # Revisión humana de 20 casos
│   └── particion.csv        # Conjunto (train/val/test) de cada noticia
└── modelo/                  # config, tokenizador, métricas y matriz de confusión
                             # (model.safetensors excluido por .gitignore)
```

## Cómo ejecutarlo en local

```bash
git clone https://github.com/diegosimemirror/Python-Intermedio-QLAB.git
cd Python-Intermedio-QLAB/tarea_1

conda create -n tarea1 python=3.12 -y
conda activate tarea1
pip install -r requirements.txt

# Los pesos del modelo no están en GitHub: genéralos ejecutando completo
# 02_clasificacion.ipynb (crea modelo/model.safetensors en ~10 minutos en CPU).

streamlit run app.py
```

El dashboard se abre en http://localhost:8501. Sin `model.safetensors`, todo funciona
salvo el probador en vivo, que indica cómo generar el modelo.

**Despliegue:** se ejecutó y comprobó en local. No se desplegó en Streamlit Community
Cloud porque los pesos del modelo superan el límite de 100 MB de GitHub; para hacerlo,
habría que alojarlos en Hugging Face Hub y cargarlos desde allí.
