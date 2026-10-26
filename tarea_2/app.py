# Dashboard de la Tarea 2: Voces y documentos peruanos, del archivo escaneado al texto buscable.
# Ejecutar desde la carpeta tarea_2 con:  streamlit run app.py
# Insumos: CSV de las Partes 1 y 2 (datos/) y la muestra publicable (datos/ejemplos/).
# No ejecuta OCR, ASR ni LLM en vivo: solo lee resultados ya calculados en los notebooks.

# PROCESO 0: Importar paquetes y definir constantes.
# Insumo: paquetes de requirements.txt.
# Resultado: página configurada, rutas y textos fijos.

# json: lee los campos extraídos por el LLM y las métricas.
import json

# unicodedata: búsqueda sin distinguir tildes (Peru = Perú).
import unicodedata

# pathlib: localiza los archivos a partir de la ubicación de este script.
from pathlib import Path

# pandas: organiza documentos, clips y resultados en tablas.
import pandas as pd

# plotly.express: gráficos interactivos (información al pasar el mouse).
import plotly.express as px

# streamlit: convierte este script en una página web interactiva.
import streamlit as st

st.set_page_config(page_title="Voces y documentos peruanos", page_icon="🎙️", layout="wide")

CARPETA = Path(__file__).parent
DATOS = CARPETA / "datos"
EJEMPLOS = DATOS / "ejemplos"
SALIDAS_ASR = DATOS / "salidas_asr"
FECHA_EXTRACCION = "25 de octubre de 2026"
ORDEN_TIPOS = ["impreso", "foto", "manuscrito"]
CORRECTO = ["1", "si", "sí", "true", "x"]
NOMBRE_CORTO = {"PaddleOCR 3.7 PP-OCRv5 mobile (línea base)": "PaddleOCR", "EasyOCR 1.7 (es)": "EasyOCR",
                "faster-whisper small (línea base)": "Whisper small", "Parakeet TDT 0.6B v3": "Parakeet v3"}

GLOSARIO = """
- **OCR:** reconocimiento óptico de caracteres; convierte una imagen en texto.
- **ASR:** reconocimiento automático del habla; convierte audio en texto.
- **VAD:** detector de voz; evita transcribir silencios, que son una fuente típica de alucinaciones.
- **Diarización:** separar quién habla en cada momento ([HABLANTE_1], [HABLANTE_2]).
- **CER / WER:** proporción de caracteres o palabras erradas frente a una transcripción manual (0 = perfecto).
- **RTF (factor de tiempo real):** segundos de proceso ÷ segundos de audio; menos de 1 es más rápido que el audio.
- **Seudonimización:** reemplazar nombres reales de personas privadas por etiquetas como [PERSONA_1].
"""


def coma(valor, decimales=2):
    """Número con punto (0.249) → texto con coma decimal (0,25)."""
    return f"{valor:.{decimales}f}".replace(".", ",")


def sin_tildes(texto):
    """'Perú' → 'peru' (minúsculas y sin tildes) para buscar sin importar la acentuación."""
    texto = unicodedata.normalize("NFD", str(texto).lower())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


def leer_csv(nombre):
    """datos/<nombre> → DataFrame (vacío si el archivo aún no existe)."""
    ruta = DATOS / nombre
    return pd.read_csv(ruta, keep_default_na=False) if ruta.exists() else pd.DataFrame()


# PROCESO 1: Cargar los resultados de los notebooks.
# Insumo: CSV de datos/ y modelos/metricas.json.
# Resultado: tablas en memoria (se guardan en caché entre interacciones).
@st.cache_data
def cargar():
    """archivos de la carpeta datos/ → tablas listas para la app (números convertidos a float)."""
    tablas = {n: leer_csv(f"{n}.csv") for n in ["documentos", "transcripciones", "extraccion_llm", "evaluacion_modelos",
                                                  "comparativa_modelos", "auditoria_llm", "fuentes"]}
    for tabla in tablas.values():
        for col in ("n_caracteres", "n_lineas", "confianza_media", "duracion_seg", "n_palabras", "valor", "segundos",
                    "rtf", "n_hablantes", "factor_tiempo_real"):
            if col in tabla:
                tabla[col] = pd.to_numeric(tabla[col], errors="coerce")
    ruta = CARPETA / "modelos" / "metricas.json"
    metricas = json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {}
    return tablas, metricas


tablas, metricas = cargar()
docs, clips, llm = tablas["documentos"], tablas["transcripciones"], tablas["extraccion_llm"]
evaluacion, comparativa, auditoria, fuentes = (tablas["evaluacion_modelos"], tablas["comparativa_modelos"],
                                               tablas["auditoria_llm"], tablas["fuentes"])
campos_llm = {r["id"]: json.loads(r["campos_json"]) for _, r in llm.iterrows() if r["campos_json"]} if len(llm) else {}

# PROCESO 2: Encabezado y resumen metodológico.
# Insumo: textos fijos.
# Resultado: título centrado en la pregunta del trabajo.
st.title("¿Pueden convertir documentos escaneados y entrevistas en audio en un archivo de texto estructurado y buscable?")
st.markdown(
    f"""
**Voces y documentos peruanos.** Este dashboard muestra los resultados de un pipeline de IA que corrió sobre
**25 documentos peruanos** de Wikimedia Commons (8 impresos, 8 fotos y 9 manuscritos) y **22 clips de audio en español peruano**:
20 de OpenSLR 73 y 2 entrevistas de la UNMSM. El corpus se extrajo el {FECHA_EXTRACCION}.

**Método:**
- **OCR:** PaddleOCR (PP-OCRv5).
- **ASR:** faster-whisper `small` con VAD, y diarización de las entrevistas con pyannote.
- **Seudonimización** de las personas privadas.
- **Extracción de campos JSON** con un LLM local (Qwen2.5-1.5B-Instruct).
- **Evaluación con CER y WER** sobre 10 documentos y 10 clips transcritos a mano, comparando dos modelos por modalidad.

Todo se calculó antes en los notebooks; esta app no ejecuta modelos.
"""
)
with st.expander("Glosario"):
    st.markdown(GLOSARIO)

# PROCESO 3: Filtros y búsqueda (barra lateral).
# Insumo: tablas docs, clips y evaluacion.
# Resultado: subconjuntos filtrados que alimentan indicadores, gráficos, tablas y exploradores.
st.sidebar.header("Filtros")
busqueda = st.sidebar.text_input("Buscar palabra en textos OCR y ASR", placeholder="p. ej. Lima, Grau, constitución")
tipos = st.sidebar.multiselect("Tipo de documento", ORDEN_TIPOS, default=ORDEN_TIPOS)
modelos_eval = sorted(evaluacion["modelo"].unique()) if len(evaluacion) else []
modelos_sel = st.sidebar.multiselect("Modelo (evaluación)", modelos_eval, default=modelos_eval)
origenes = sorted(clips["origen"].unique())
origen_sel = st.sidebar.multiselect("Origen del audio", origenes, default=origenes)
dur_min, dur_max = int(clips["duracion_seg"].min()), int(clips["duracion_seg"].max()) + 1
rango = st.sidebar.slider("Duración del clip (s)", dur_min, dur_max, (dur_min, dur_max))
st.sidebar.caption("Los filtros actualizan los indicadores, los gráficos, las tablas y los exploradores.")

clave = sin_tildes(busqueda.strip())
docs_f = docs[docs["tipo"].isin(tipos)]
clips_f = clips[clips["origen"].isin(origen_sel) & clips["duracion_seg"].between(*rango)]
if clave:
    docs_f = docs_f[docs_f["texto_ocr"].map(sin_tildes).str.contains(clave, regex=False)]
    clips_f = clips_f[clips_f["texto_asr"].map(sin_tildes).str.contains(clave, regex=False)]
eval_f = evaluacion
if len(evaluacion):
    eval_f = evaluacion[evaluacion["modelo"].isin(modelos_sel)
                        & (evaluacion["tipo"].isin(tipos) | evaluacion["tipo"].isin(origen_sel))]

# PROCESO 4: Indicadores clave.
# Insumo: tablas filtradas, comparativa y métricas.
# Resultado: fila de st.metric.
c1, c2, c3 = st.columns(3)
c1.metric("Documentos procesados", f"{len(docs_f)} de {len(docs)}")
c2.metric("Minutos de audio transcritos", coma(clips_f["duracion_seg"].sum() / 60, 1))
if metricas.get("acuerdo_llm_humano") is not None:
    c3.metric("Concordancia LLM vs. auditoría humana", f"{metricas['acuerdo_llm_humano'] / 20:.0%}",
              help=f"{metricas['acuerdo_llm_humano']}/20 extracciones completamente correctas")

# Una tarjeta por modelo evaluado (CER en 10 documentos, WER en 10 clips); ✓ = el de menor error, elegido.
comp_f = comparativa[comparativa["modelo"].isin(modelos_sel)] if len(comparativa) else comparativa
if len(comp_f):
    comp_f = comp_f.sort_values(["metrica", "valor"])
    menor = comp_f.groupby("metrica")["valor"].transform("min")
    for col, (_, r), minimo in zip(st.columns(len(comp_f)), comp_f.iterrows(), menor):
        nombre = NOMBRE_CORTO.get(r["modelo"], r["modelo"])
        muestra = "10 docs" if r["metrica"] == "CER" else "10 clips"
        col.metric(f"{r['metrica']} · {nombre}{' ✓' if r['valor'] == minimo else ''} ({muestra})", coma(r["valor"], 3),
                   help=f"{r['modelo']} · latencia: {r['latencia']} · tamaño: {r['tamano']}")
    st.caption("Error de cada modelo sobre las mismas muestras de evaluación (menor es mejor). ✓ = modelo elegido.")
if clave:
    st.info(f"Búsqueda «{busqueda}»: {len(docs_f)} documentos y {len(clips_f)} clips contienen la palabra.")

tab_res, tab_doc, tab_aud, tab_eval, tab_datos = st.tabs(
    ["📊 Resumen", "📄 Explorador de documentos", "🎧 Explorador de audios", "⚖️ Evaluación de modelos", "⬇️ Datos y fuentes"])

# PROCESO 5: Gráficos interactivos del corpus.
# Insumo: tablas filtradas.
# Resultado: gráficos Plotly de tipos de documento, duración de audios y error por modalidad.
with tab_res:
    g1, g2 = st.columns(2)
    if len(docs_f):
        por_tipo = (docs_f.groupby("tipo").agg(documentos=("id", "count"), confianza=("confianza_media", "mean"))
                    .reindex([t for t in ORDEN_TIPOS if t in set(docs_f["tipo"])]).reset_index())
        fig = px.bar(por_tipo, x="tipo", y="documentos", color="confianza", text="documentos",
                     color_continuous_scale="RdYlGn", range_color=[0.5, 1],
                     labels={"tipo": "Tipo", "documentos": "Documentos", "confianza": "Confianza OCR"},
                     title="Documentos por tipo: el OCR confía menos en los manuscritos")
        g1.plotly_chart(fig, width="stretch")
    if len(clips_f):
        fig = px.bar(clips_f.sort_values("duracion_seg"), x="id", y="duracion_seg", color="origen",
                     labels={"id": "Clip", "duracion_seg": "Duración (s)", "origen": "Origen"},
                     title="Duración por clip: OpenSLR en clips parejos y entrevistas más largas")
        g2.plotly_chart(fig, width="stretch")
    if len(eval_f):
        errores = eval_f.groupby(["metrica", "tipo", "modelo"], as_index=False)["valor"].mean()
        fig = px.bar(errores, x="tipo", y="valor", color="modelo", barmode="group", facet_col="metrica",
                     labels={"valor": "Error medio por caso", "tipo": "Tipo / origen", "modelo": "Modelo"},
                     title="Error por modalidad y modelo en la muestra de evaluación (CER en documentos, WER en audio)")
        fig.update_xaxes(matches=None)
        fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
        st.plotly_chart(fig, width="stretch")

# PROCESO 6: Explorador de documentos.
# Insumo: docs_f, campos del LLM y evaluación.
# Resultado: imagen (licencia libre), texto OCR, campos JSON y CER cuando hay referencia manual.
with tab_doc:
    if not len(docs_f):
        st.warning("Ningún documento cumple los filtros.")
    else:
        opciones = {f"{r['id']} · {r['tipo']} · {r['titulo'][:70]}": r["id"] for _, r in docs_f.iterrows()}
        doc_id = opciones[st.selectbox("Documento (25 procesados)", list(opciones))]
        d = docs.set_index("id").loc[doc_id]
        col_img, col_txt = st.columns([2, 3])
        with col_img:
            imagen = EJEMPLOS / f"{doc_id}.jpg"
            if imagen.exists():
                st.image(str(imagen), caption=f"{d['titulo']} · {d['licencia']}")
            else:
                st.info("Imagen no publicada; se consulta solo como texto.")
            st.markdown(f"**Fuente:** [{d['fuente']}]({d['pagina_commons']})")
            st.markdown(f"**Modelo OCR:** {d['modelo_ocr']}  \n**Confianza media:** {coma(d['confianza_media'])} · "
                        f"**Líneas:** {int(d['n_lineas'])} · **Caracteres:** {int(d['n_caracteres'])}")
        with col_txt:
            st.markdown("**Texto OCR (PaddleOCR, página completa)**")
            st.text_area("Texto OCR", d["texto_ocr"], height=260, label_visibility="collapsed")
            st.markdown("**Campos extraídos por el LLM**")
            if doc_id in campos_llm:
                st.json(campos_llm[doc_id])
            else:
                st.caption("El LLM no devolvió un JSON válido para este documento.")
            if d.get("texto_referencia", ""):
                st.markdown("**Referencia manual del recorte evaluado y CER por modelo**")
                st.text_area("Referencia", d["texto_referencia"], height=120, label_visibility="collapsed")
                for _, r in evaluacion[evaluacion["id"] == doc_id].iterrows():
                    st.markdown(f"- **{r['modelo']}:** CER = {coma(r['valor'], 3)} · {coma(r['segundos'], 1)} s")
                    st.caption(r["texto"][:400])
            else:
                st.caption("Este documento no forma parte de la muestra de evaluación (sin referencia manual).")

# PROCESO 7: Explorador de audios.
# Insumo: clips_f, salidas TXT seudonimizadas, campos del LLM y evaluación.
# Resultado: reproducción (solo audios publicables), transcripción con hablantes y comparación de modelos.
with tab_aud:
    if not len(clips_f):
        st.warning("Ningún clip cumple los filtros.")
    else:
        opciones = {f"{r['id']} · {r['origen']} · {r['duracion_seg']:.0f} s": r["id"] for _, r in clips_f.iterrows()}
        clip_id = opciones[st.selectbox("Clip", list(opciones))]
        a = clips.set_index("id").loc[clip_id]
        col_a, col_b = st.columns([2, 3])
        with col_a:
            ejemplo = EJEMPLOS / f"{clip_id}_30s.ogg"
            if ejemplo.exists():
                st.audio(str(ejemplo), format="audio/ogg")
                st.caption(f"Primeros 30 s · {a['licencia']} · OpenSLR 73 (Google), hablante anónimo")
            else:
                st.info("Audio no publicado en el dashboard (voz de persona privada o fuera de la muestra ligera). "
                        "Se consulta como texto seudonimizado.")
            st.markdown(f"**Origen:** {a['origen']}  \n**Fuente:** {a['fuente']}  \n**Licencia:** {a['licencia']}")
            st.markdown(f"**Modelo ASR:** {a['modelo_asr']}  \n**Hablantes detectados:** {int(a['n_hablantes'])} · "
                        f"**Palabras:** {int(a['n_palabras'])} · **RTF:** {coma(a['factor_tiempo_real'])}")
        with col_b:
            txt = SALIDAS_ASR / f"{clip_id}.txt"
            st.markdown("**Transcripción ASR (marcas de tiempo y hablante)**")
            st.text_area("ASR", txt.read_text(encoding="utf-8") if txt.exists() else a["texto_asr"], height=260,
                         label_visibility="collapsed")
            st.markdown("**Campos extraídos por el LLM**")
            if clip_id in campos_llm:
                st.json(campos_llm[clip_id])
            else:
                st.caption("El LLM no devolvió un JSON válido para este clip.")
        ev = evaluacion[evaluacion["id"] == clip_id] if len(evaluacion) else evaluacion
        if len(ev):
            ventana = "primeros 60 s" if "Entrevista" in a["origen"] else "clip completo"
            st.markdown(f"**Comparación de modelos frente a la referencia ({ventana})**")
            cols = st.columns(len(ev) + 1)
            cols[0].markdown("*Referencia*")
            cols[0].caption(a["texto_referencia"][:900])
            for col, (_, r) in zip(cols[1:], ev.iterrows()):
                col.markdown(f"*{r['modelo']}* · WER {coma(r['valor'], 3)} · RTF {coma(r['rtf'])}")
                col.caption(r["texto"][:900])

# PROCESO 8: Evaluación de modelos y auditoría del LLM.
# Insumo: comparativa, evaluacion y auditoria.
# Resultado: tabla comparativa, error por caso y resultado de la auditoría humana.
with tab_eval:
    if len(comp_f):
        st.subheader("Comparativa (misma muestra, misma laptop en CPU)")
        st.dataframe(comp_f, width="stretch", hide_index=True)
    if len(eval_f):
        fig = px.strip(eval_f, x="modelo", y="valor", color="tipo", hover_data=["id"], facet_col="metrica",
                       labels={"valor": "Error por caso", "modelo": "Modelo", "tipo": "Tipo / origen"},
                       title="Cada punto es un documento o clip de la muestra de evaluación")
        fig.update_xaxes(matches=None)
        fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
        st.plotly_chart(fig, width="stretch")
    if len(auditoria):
        st.subheader("Auditoría humana del LLM (20 extracciones al azar)")
        ok = auditoria["correcto"].astype(str).str.strip().str.lower().isin(CORRECTO)
        st.markdown(f"**Completamente correctas: {int(ok.sum())}/20 ({ok.mean():.0%}).**")
        st.dataframe(auditoria.assign(correcto=ok)[["id", "modalidad", "correcto", "comentario", "campos_json"]],
                     width="stretch", hide_index=True)

# PROCESO 9: Tablas filtradas y descarga.
# Insumo: docs_f, clips_f, extracción LLM y fuentes.
# Resultado: st.dataframe con botón de descarga (solo textos revisados y seudonimizados).
with tab_datos:
    st.subheader("Documentos (filtrados)")
    cols_doc = ["id", "tipo", "titulo", "licencia", "confianza_media", "n_caracteres", "texto_ocr"]
    st.dataframe(docs_f[cols_doc], width="stretch", hide_index=True)
    st.download_button("Descargar documentos (CSV)", docs_f[cols_doc].to_csv(index=False).encode("utf-8"),
                       "documentos_filtrados.csv", "text/csv")
    st.subheader("Transcripciones (filtradas)")
    cols_aud = ["id", "origen", "duracion_seg", "n_hablantes", "n_palabras", "texto_asr"]
    st.dataframe(clips_f[cols_aud], width="stretch", hide_index=True)
    st.download_button("Descargar transcripciones (CSV)", clips_f[cols_aud].to_csv(index=False).encode("utf-8"),
                       "transcripciones_filtradas.csv", "text/csv")
    if len(llm):
        st.subheader("Extracción estructurada (LLM)")
        llm_f = llm[llm["id"].isin(set(docs_f["id"]) | set(clips_f["id"]))]
        st.dataframe(llm_f, width="stretch", hide_index=True)
        st.download_button("Descargar extracción LLM (CSV)", llm_f.to_csv(index=False).encode("utf-8"),
                           "extraccion_llm_filtrada.csv", "text/csv")
    st.subheader("Fuentes y licencias")
    st.dataframe(fuentes, width="stretch", hide_index=True)
    st.caption("Los audios y las imágenes originales no se publican en el repositorio; `fuentes.csv` indica cómo recuperarlos.")
