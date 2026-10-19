# Dashboard de la Tarea 1: ¿Pueden los titulares peruanos convertirse en un clasificador?
# Ejecutar desde la carpeta tarea_1 con:  streamlit run app.py
# Insumos: datos/noticias.csv, datos/etiquetas_llm.csv y la carpeta modelo/ (Parte 2).

# PROCESO 0: Importar paquetes y definir constantes.
# Insumo: paquetes de requirements.txt.
# Resultado: página configurada, rutas, nombres de categorías y textos del glosario.

# json: lee las métricas guardadas en la Parte 2.
import json

# pathlib: localiza los archivos a partir de la ubicación de este script.
from pathlib import Path

# pandas: organiza noticias, etiquetas y resultados en tablas.
import pandas as pd

# plotly.express: crea los gráficos interactivos (información al pasar el mouse).
import plotly.express as px

# streamlit: convierte este script en una página web interactiva.
import streamlit as st

st.set_page_config(
    page_title="Clasificador de titulares peruanos",
    page_icon="📰",
    layout="wide",
)

CARPETA = Path(__file__).parent
CARPETA_DATOS = CARPETA / "datos"
CARPETA_MODELO = CARPETA / "modelo"
FECHA_DESCARGA = "18 de octubre de 2026"

CATEGORIAS = ["politica", "economia", "deportes", "ciencia_tecnologia"]
NOMBRES = {
    "politica": "Política",
    "economia": "Economía",
    "deportes": "Deportes",
    "ciencia_tecnologia": "Ciencia y tecnología",
}
MESES = ["ene", "feb", "mar", "abr", "may", "jun",
         "jul", "ago", "sep", "oct", "nov", "dic"]

# Dos tonos de un mismo azul: oscuro = coincide / elegido; claro = difiere / resto.
AZUL_OSCURO = "#256abf"
AZUL_CLARO = "#9ec5f4"

EJEMPLOS = {
    "Ejemplo claro": "BCR advierte que El Niño afectará el crecimiento",
    "Ejemplo ambiguo": "Gobierno anuncia nuevo impuesto a la minería",
}

GLOSARIO = """
- **Etiqueta:** la categoría correcta de cada noticia; aquí, la sección del diario.
- **Modelo:** programa que aprende patrones a partir de ejemplos.
- **Fine-tuning:** especializar un modelo ya existente con ejemplos propios.
- **Zero-shot:** clasificar sin haber visto ningún ejemplo de la tarea.
- **LLM:** modelo de lenguaje grande que responde a instrucciones escritas.
- **Token:** pieza de palabra con la que el modelo lee el texto.
- **Conjunto de prueba:** noticias reservadas que el modelo nunca vio; funcionan como examen.
- **Accuracy:** porcentaje de aciertos totales.
- **F1 macro:** nota de 0 a 1 que promedia el desempeño de cada categoría con igual peso.
- **Latencia:** tiempo que tarda el modelo en responder.
"""


def coma(valor, decimales=3):
    """Número con punto (0.949) → texto con coma decimal (0,949)."""
    return f"{valor:.{decimales}f}".replace(".", ",")


def fecha_corta(fecha):
    """Fecha (2026-09-17) → texto breve en español (17 sep 2026)."""
    return f"{fecha.day} {MESES[fecha.month - 1]} {fecha.year}"


# PROCESO 1: Cargar datos, métricas y modelo.
# Insumo: archivos de las Partes 1 y 2.
# Resultado: tabla de noticias con la etiqueta del LLM, métricas y clasificador.

@st.cache_data
def cargar_noticias():
    """noticias.csv + etiquetas_llm.csv → 400 filas con la etiqueta del diario y la del LLM."""
    noticias = pd.read_csv(CARPETA_DATOS / "noticias.csv", encoding="utf-8-sig")
    llm = pd.read_csv(CARPETA_DATOS / "etiquetas_llm.csv", encoding="utf-8-sig")

    # merge(): 400 noticias + 400 etiquetas del LLM → una fila por noticia con ambas.
    tabla = noticias.merge(
        llm[["titular", "etiqueta_llm", "confianza"]], on="titular", how="left"
    )
    tabla["coincide_llm"] = tabla["etiqueta"] == tabla["etiqueta_llm"]

    # to_datetime(): "2026-10-18T19:32:25-05:00" → fecha de Lima 2026-10-18.
    tabla["fecha"] = (
        pd.to_datetime(tabla["fecha"], utc=True)
        .dt.tz_convert("America/Lima")
        .dt.date
    )
    return tabla


@st.cache_data
def cargar_metricas():
    """metricas.json y comparativa.csv (Parte 2) → diccionario y tabla."""
    metricas = json.loads(
        (CARPETA_MODELO / "metricas.json").read_text(encoding="utf-8")
    )
    comparativa = pd.read_csv(
        CARPETA_MODELO / "comparativa.csv", encoding="utf-8-sig"
    )
    return metricas, comparativa


@st.cache_resource
def cargar_clasificador():
    """Carpeta modelo/ → clasificador listo para usar; None si faltan los pesos."""
    if not (CARPETA_MODELO / "model.safetensors").exists():
        return None

    # transformers: ejecuta el modelo de la Parte 2. Se importa aquí porque tarda
    # unos segundos y solo hace falta cuando alguien pide una clasificación.
    from transformers import pipeline

    # top_k=None: devuelve la probabilidad de las 4 categorías, no solo la mayor.
    return pipeline("text-classification", model=str(CARPETA_MODELO), top_k=None)


def predecir(clasificador, titular):
    """Titular → tabla de 4 categorías ordenadas de mayor a menor probabilidad."""
    resultado = clasificador(titular)

    # Según la versión de transformers, llega como [[...]] o como [...]: se iguala.
    if resultado and isinstance(resultado[0], list):
        resultado = resultado[0]

    tabla = pd.DataFrame(resultado).rename(
        columns={"label": "categoria", "score": "probabilidad"}
    )
    tabla["nombre"] = tabla["categoria"].map(NOMBRES)
    return tabla.sort_values("probabilidad", ascending=False).reset_index(drop=True)


noticias = cargar_noticias()
metricas, comparativa = cargar_metricas()

# comparativa.csv guarda los F1 sin redondear (metricas.json los guarda con 4 decimales).
filas_comparativa = comparativa.set_index("modelo")
f1_test = filas_comparativa.loc["Transformer fine-tuned", "f1_macro_test60"]
f1_zero_shot = filas_comparativa.loc["Zero-shot (NLI)", "f1_macro_40"]
n_prueba = metricas["n_prueba"]
aciertos_prueba = round(metricas["accuracy_test"] * n_prueba)


# PROCESO 2: Barra lateral con filtros, fuente y glosario.
# Insumo: tabla noticias.
# Resultado: tabla filtradas, que alimenta el indicador, el gráfico y la tabla.

st.sidebar.header("Filtros")

medios = sorted(noticias["medio"].unique())
medios_elegidos = st.sidebar.multiselect("Medio", medios, default=medios)

categorias_elegidas = st.sidebar.multiselect(
    "Categoría", CATEGORIAS, default=CATEGORIAS, format_func=NOMBRES.get
)

st.sidebar.caption(
    "💡 Los filtros cambian el número de noticias, el gráfico y la tabla. "
    "Las métricas del modelo no cambian: se calcularon sobre el examen final."
)

# isin(): 400 filas → solo las que cumplen el filtro de medio y el de categoría.
filtradas = noticias[
    noticias["medio"].isin(medios_elegidos)
    & noticias["etiqueta"].isin(categorias_elegidas)
]

st.sidebar.divider()
st.sidebar.markdown(
    f"**Fuente:** La República  \n"
    f"**Publicación:** {fecha_corta(noticias['fecha'].min())} – "
    f"{fecha_corta(noticias['fecha'].max())}  \n"
    f"**Descarga:** {FECHA_DESCARGA}"
)

with st.sidebar.expander("Glosario"):
    st.markdown(GLOSARIO)


# PROCESO 3: Encabezado, respuesta y cómo se construyó.
# Insumo: métricas de la Parte 2.
# Resultado: pregunta, respuesta en una línea y flujo de 4 pasos con notas.

st.title("¿Pueden los titulares peruanos convertirse en un clasificador de noticias?")
st.markdown(
    f"**Sí.** Un modelo entrenado con {metricas['n_entrenamiento']} titulares acierta "
    f"**{aciertos_prueba} de {n_prueba}** titulares que nunca había visto "
    f"({metricas['accuracy_test']:.0%})."
)
st.caption(
    "💡 Arriba, los tres números que resumen el resultado. En las pestañas puedes "
    "probar el modelo con tus propios titulares, explorar las 400 noticias y "
    "comparar los tres enfoques."
)

st.subheader("Cómo se construyó")

pasos = [
    (
        "1. Recolectar",
        "Web de La República → un programa recorrió 4 secciones y guardó "
        "titular, sección y fecha → **400 noticias, 100 por sección**.",
        "La sección donde el diario publicó cada noticia sirve como "
        "«respuesta correcta» (etiqueta) para enseñar y para calificar.",
    ),
    (
        "2. Separar",
        f"400 noticias → **{metricas['n_entrenamiento']}** para aprender, "
        f"**{metricas['n_validacion']}** para ajustar y **{n_prueba}** "
        "guardadas como examen final.",
        "Como en un examen: si se califica con las mismas preguntas con que se "
        "estudió, la nota sale inflada. Las del examen no se tocan hasta el final.",
    ),
    (
        "3. Clasificar",
        "Las mismas noticias se clasifican de **tres maneras**: zero-shot, "
        "LLM y fine-tuning.",
        "**Zero-shot:** un lector que nunca vio nuestras noticias. "
        "**LLM:** un asistente general con instrucciones escritas. "
        "**Fine-tuning:** un modelo que ya lee español y se especializa con "
        f"{metricas['n_entrenamiento']} ejemplos.",
    ),
    (
        "4. Evaluar",
        f"Los tres enfoques → las mismas **{n_prueba} noticias del examen** → "
        "nota, costo y velocidad de cada uno.",
        "Es una comparación justa: los tres rinden el mismo examen.",
    ),
]

for columna, (titulo, proceso, nota) in zip(st.columns(4), pasos):
    with columna.container(border=True):
        st.markdown(f"**{titulo}**")
        st.markdown(proceso)
        st.caption(f"💡 {nota}")


# PROCESO 4: Indicadores clave.
# Insumo: tabla filtradas y métricas.
# Resultado: tres st.metric con su ayuda (?) y su nota de lectura.

st.divider()
indicador_1, indicador_2, indicador_3 = st.columns(3)

with indicador_1:
    st.metric(
        "Noticias",
        f"{len(filtradas)} de {len(noticias)}",
        help="Titulares que cumplen los filtros de la barra lateral. La base completa tiene 400.",
    )
    st.caption("💡 Cambia al usar los filtros de la izquierda.")

with indicador_2:
    st.metric(
        "F1 macro en el examen final",
        coma(f1_test),
        delta=f"+{coma(f1_test - f1_zero_shot, 2)} frente al zero-shot",
        help="Nota de 0 a 1 calculada sobre las noticias que el modelo nunca vio.",
    )
    st.caption(
        "💡 Mide qué tan bien acierta en **cada** categoría y promedia las cuatro "
        "con el mismo peso, así una categoría mal resuelta no se esconde detrás "
        f"de las demás. Sin entrenamiento, el punto de partida era {coma(f1_zero_shot)}."
    )
    with st.expander("Saber más"):
        st.markdown(
            "F1 castiga dos errores: decir «economía» cuando no lo era y no "
            "reconocer una noticia que sí era de economía. El accuracy "
            f"({metricas['accuracy_test']:.0%}) solo cuenta los aciertos totales."
        )

with indicador_3:
    if metricas.get("aciertos_auditoria") is None:
        st.metric("Acuerdo LLM–humano", "Pendiente")
        st.caption("💡 Falta completar la auditoría en 02_clasificacion.ipynb.")
    else:
        st.metric(
            "Acuerdo LLM–humano",
            f"{metricas['aciertos_auditoria']}/20 "
            f"({metricas['acuerdo_llm_humano']:.0%})",
            help="Revisión manual de 20 etiquetas del LLM elegidas al azar.",
        )
        st.caption(
            f"💡 Una persona revisó 20 etiquetas del LLM y coincidió en "
            f"{metricas['aciertos_auditoria']}. Indica cuánto se puede confiar en "
            "etiquetar automáticamente sin revisar."
        )

st.divider()


# PROCESO 5: Pestañas de exploración.
# Insumo: clasificador, tabla filtradas y comparativa.
# Resultado: probador en vivo, gráfico + tabla descargable y comparación de modelos.

pestana_probador, pestana_explorar, pestana_modelos = st.tabs(
    ["Probador en vivo", "Explorar noticias", "Comparar modelos"]
)

# PROCESO 5.1: Probador en vivo (núcleo de la demo).
with pestana_probador:
    st.markdown(
        "Escribe un titular como aparecería en un diario. "
        "El modelo elegirá una de las 4 categorías."
    )

    def usar_ejemplo(texto):
        """Botón de ejemplo → copia el titular en el campo y pide clasificarlo."""
        st.session_state["titular"] = texto
        st.session_state["clasificar_ejemplo"] = True

    st.text_input(
        "Titular",
        key="titular",
        placeholder="Ej.: Alianza Lima vence a Sporting Cristal en el clásico",
    )

    boton, *botones_ejemplo = st.columns([1, 1, 1, 3])
    clasificar = boton.button("Clasificar", type="primary")
    for columna, (nombre, texto) in zip(botones_ejemplo, EJEMPLOS.items()):
        columna.button(nombre, on_click=usar_ejemplo, args=(texto,), help=texto)

    # pop(): lee la señal del botón de ejemplo y la borra para la siguiente vez.
    pedido_por_ejemplo = st.session_state.pop("clasificar_ejemplo", False)
    titular = st.session_state.get("titular", "").strip()

    if clasificar or pedido_por_ejemplo:
        if not titular:
            st.warning("Escribe un titular antes de pulsar Clasificar.")
        else:
            with st.spinner("Cargando el modelo (solo la primera vez)…"):
                clasificador = cargar_clasificador()

            if clasificador is None:
                st.error(
                    "No se encontró `modelo/model.safetensors`. Los pesos del modelo "
                    "no se suben a GitHub (pesan 516 MB): genéralos ejecutando "
                    "`02_clasificacion.ipynb`."
                )
            else:
                probabilidades = predecir(clasificador, titular)
                primera = probabilidades.iloc[0]
                segunda = probabilidades.iloc[1]

                st.success(f"**{primera['nombre']}** · {primera['probabilidad']:.0%}")

                # Barra oscura para la categoría elegida, claras para las demás.
                probabilidades["color"] = [
                    "elegida" if i == 0 else "resto" for i in probabilidades.index
                ]
                grafico_probabilidades = px.bar(
                    probabilidades,
                    x="probabilidad",
                    y="nombre",
                    orientation="h",
                    color="color",
                    color_discrete_map={"elegida": AZUL_OSCURO, "resto": AZUL_CLARO},
                    text=probabilidades["probabilidad"].map(lambda p: f"{p:.0%}"),
                    range_x=[0, 1.08],
                    labels={"probabilidad": "Probabilidad", "nombre": ""},
                    hover_data={"probabilidad": ":.1%", "color": False, "nombre": False},
                )
                grafico_probabilidades.update_traces(
                    textposition="outside", marker_line_width=0
                )
                grafico_probabilidades.update_layout(
                    showlegend=False,
                    height=230,
                    margin=dict(l=0, r=0, t=10, b=0),
                    yaxis=dict(categoryorder="total ascending"),
                    xaxis=dict(tickformat=".0%", showgrid=False),
                )
                st.plotly_chart(grafico_probabilidades)

                if primera["probabilidad"] - segunda["probabilidad"] < 0.20:
                    st.info(
                        f"Las dos categorías más probables están cerca "
                        f"({primera['nombre']} y {segunda['nombre']}): "
                        "el titular mezcla temas."
                    )

    st.caption(
        "💡 El titular se divide en piezas de palabras (tokens), el modelo calcula "
        "un puntaje para cada categoría y lo convierte en probabilidades que suman "
        "100 %. La probabilidad indica qué tan seguro está el modelo, no si tiene razón."
    )
    with st.expander("Saber más"):
        st.markdown(
            "- Si dos categorías tienen porcentajes parecidos, el titular mezcla temas. "
            "Prueba el **ejemplo ambiguo**: un impuesto a la minería es a la vez "
            "una decisión política y un tema económico.\n"
            "- El modelo solo conoce estas 4 categorías: un titular de espectáculos "
            "o del clima igual será asignado a alguna de ellas."
        )

# PROCESO 5.2: Gráfico de categorías y tabla descargable.
with pestana_explorar:
    if filtradas.empty:
        st.warning("Ninguna noticia cumple los filtros. Marca al menos un medio y una categoría.")
    else:
        # groupby().size(): noticias sueltas → conteo por categoría y coincidencia con el LLM.
        conteo = (
            filtradas.groupby(["etiqueta", "coincide_llm"])
            .size()
            .reset_index(name="noticias")
        )
        conteo["nombre"] = conteo["etiqueta"].map(NOMBRES)
        conteo["llm"] = conteo["coincide_llm"].map(
            {True: "El LLM coincide con el diario", False: "El LLM eligió otra categoría"}
        )

        # Categoría con más discrepancias, para que el título diga la conclusión.
        totales = filtradas.groupby("etiqueta").size()
        discrepancias = filtradas.loc[~filtradas["coincide_llm"]].groupby("etiqueta").size()
        if discrepancias.empty:
            titulo = "El LLM coincide con el diario en todas las noticias filtradas"
        else:
            peor = discrepancias.idxmax()
            titulo = (
                f"El LLM discrepa más en {NOMBRES[peor].lower()}: "
                f"{discrepancias[peor]} de {totales[peor]} noticias"
            )

        grafico_categorias = px.bar(
            conteo,
            x="noticias",
            y="nombre",
            color="llm",
            orientation="h",
            title=titulo,
            text="noticias",
            category_orders={
                "llm": ["El LLM coincide con el diario", "El LLM eligió otra categoría"],
                "nombre": [NOMBRES[c] for c in CATEGORIAS],
            },
            color_discrete_map={
                "El LLM coincide con el diario": AZUL_OSCURO,
                "El LLM eligió otra categoría": AZUL_CLARO,
            },
            labels={"noticias": "Número de noticias", "nombre": "", "llm": ""},
        )
        # Separación blanca de 2 px entre tramos para distinguirlos sin depender del color.
        grafico_categorias.update_traces(
            marker_line_color="white", marker_line_width=2, textposition="inside"
        )
        grafico_categorias.update_layout(
            legend=dict(orientation="h", y=-0.2, x=0),
            height=360,
            margin=dict(l=0, r=0, t=50, b=0),
            xaxis=dict(showgrid=False),
        )
        st.plotly_chart(grafico_categorias)

        st.caption(
            "💡 Cada barra son las noticias de una sección. El tramo oscuro muestra "
            "dónde el LLM coincidió con el diario y el claro, dónde eligió otra categoría."
        )
        with st.expander("Saber más: ¿por qué discrepa el LLM?"):
            st.markdown(
                "- **Deportes → política (20 casos):** conflictos entre técnicos y "
                "dirigentes, sanciones y polémicas («Franco Velazco arremetió contra "
                "Pablo Guede…»). El LLM asocia ese lenguaje de conflicto e instituciones "
                "con la política.\n"
                "- **Ciencia → economía (15 casos):** historias con cifras, toneladas o "
                "electricidad («China genera electricidad con paneles solares…»). En "
                "estos casos el LLM suele estar poco seguro (51–79 %)."
            )

        # Tabla interactiva: columnas útiles para leer y verificar cada noticia.
        columnas_tabla = ["titular", "etiqueta", "etiqueta_llm", "confianza",
                          "fecha", "medio", "url"]
        st.dataframe(
            filtradas[columnas_tabla],
            hide_index=True,
            column_config={
                "titular": st.column_config.TextColumn("Titular", width="large"),
                "etiqueta": "Sección (etiqueta)",
                "etiqueta_llm": "Etiqueta del LLM",
                "confianza": st.column_config.NumberColumn(
                    "Confianza del LLM", format="%.2f"
                ),
                "fecha": st.column_config.DateColumn("Fecha", format="YYYY-MM-DD"),
                "medio": "Medio",
                "url": st.column_config.LinkColumn("Enlace", display_text="Abrir"),
            },
        )

        # to_csv(): tabla filtrada → texto CSV que el navegador descarga como archivo.
        st.download_button(
            "Descargar CSV",
            data=filtradas[columnas_tabla].to_csv(index=False).encode("utf-8-sig"),
            file_name="noticias_filtradas.csv",
            mime="text/csv",
        )
        st.caption(
            "💡 Cada fila es una noticia. «Sección» es la etiqueta del diario y "
            "«Etiqueta del LLM» es la respuesta del LLM. Haz clic en una columna "
            "para ordenar y descarga lo filtrado en CSV."
        )

# PROCESO 5.3: Comparación de los tres enfoques.
with pestana_modelos:
    tabla_modelos = comparativa[[
        "modelo", "f1_macro_40", "f1_macro_test60",
        "parametros_millones", "latencia_ms",
    ]]
    st.dataframe(
        tabla_modelos,
        hide_index=True,
        column_config={
            "modelo": "Enfoque",
            "f1_macro_40": st.column_config.NumberColumn(
                "F1 macro (40 comunes)", format="%.3f"
            ),
            "f1_macro_test60": st.column_config.NumberColumn(
                "F1 macro (examen, 60)", format="%.3f"
            ),
            "parametros_millones": st.column_config.NumberColumn(
                "Parámetros (millones)", format="%.0f"
            ),
            "latencia_ms": st.column_config.NumberColumn(
                "Latencia (ms por titular)", format="%.0f"
            ),
        },
    )
    st.caption(
        "💡 Tres criterios: precisión (F1); costo, es decir, cuántos números "
        "internos ajusta el modelo (parámetros): a más parámetros, más memoria; "
        "y latencia, el tiempo que tarda en responder por titular. El zero-shot "
        "solo se evaluó con 40 titulares, por eso no tiene nota sobre 60."
    )

    # Cifras para la decisión, tomadas de la tabla comparativa.
    latencia_llm = filas_comparativa.loc["LLM débil (Qwen local)", "latencia_ms"]
    latencia_ft = filas_comparativa.loc["Transformer fine-tuned", "latencia_ms"]
    st.success(
        f"**Decisión: el Transformer fine-tuned.** Es el más preciso, responde "
        f"{latencia_llm / latencia_ft:.0f} veces más rápido que el LLM "
        f"({latencia_ft:.0f} ms frente a {coma(latencia_llm / 1000, 1)} s) y "
        "funciona en una laptop sin internet."
    )

    archivo_matriz = CARPETA_MODELO / "matriz_confusion.png"
    if archivo_matriz.exists():
        st.image(str(archivo_matriz), width=560)
        st.caption(
            f"💡 Las filas son la sección real y las columnas, lo que predijo el "
            f"modelo. La diagonal son los aciertos ({aciertos_prueba} de {n_prueba}). "
            "Los errores son noticias de política sobre minería, pagos o facultades "
            "que el modelo leyó como economía, temas que el diario también publica "
            "en Economía."
        )

st.divider()
st.caption(
    "Tarea 1 · Data Science con Python · Diego Enrique Sime Rendón · "
    "Datos: La República · Modelo: distilbert-base-multilingual-cased ajustado"
)
