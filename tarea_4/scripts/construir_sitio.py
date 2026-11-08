"""Construye el sitio web de la tarea 4 (GitHub Pages) con las salidas del proyecto.

    uv run python scripts/construir_sitio.py

Qué hace, en orden:
  1. Pide al servidor MCP `bcrp` las series mensuales del IPC (total, alimentos y sin alimentos), como el agente.
  2. Lee las salidas de las Skills, del cruce y de la evaluación (salidas/*.csv, evaluacion/resultados.csv).
  3. Convierte los límites departamentales (GeoJSON) en trazos SVG para el mapa interactivo.
  4. Escribe sitio/datos.js (los datos de todos los gráficos) y sitio/informe.html (el informe completo en HTML).
  5. Copia las figuras y el mapa PNG que generaron las herramientas.

sitio/index.html, sitio/estilo.css y sitio/graficos.js se escriben a mano: este script solo les entrega datos.
Requiere haber corrido la Skill limpiando-enaho y scripts/cruce_y_contraste.py. Si falta el GeoJSON
(scripts/descargar_datos.py), el sitio muestra el mapa PNG en lugar del interactivo.
"""

import asyncio
import html
import json
import shutil
import sys
from datetime import date
from pathlib import Path

import markdown        # convierte el informe de Markdown a HTML
import pandas as pd    # lee los CSV de salida

RAIZ = Path(__file__).resolve().parents[1]
SITIO = RAIZ / "sitio"
REPO = "https://github.com/diegosimemirror/Python-Intermedio-QLAB/blob/main/tarea_4"

sys.path.insert(0, str(RAIZ / "mcp"))
from fastmcp import Client                  # cliente MCP en el mismo proceso, igual que en cruce_y_contraste.py
from server import mcp as servidor_bcrp

NOMBRES = {"01": "Amazonas", "02": "Áncash", "03": "Apurímac", "04": "Arequipa", "05": "Ayacucho",
           "06": "Cajamarca", "07": "Callao", "08": "Cusco", "09": "Huancavelica", "10": "Huánuco", "11": "Ica",
           "12": "Junín", "13": "La Libertad", "14": "Lambayeque", "15": "Lima", "16": "Loreto",
           "17": "Madre de Dios", "18": "Moquegua", "19": "Pasco", "20": "Piura", "21": "Puno", "22": "San Martín",
           "23": "Tacna", "24": "Tumbes", "25": "Ucayali"}

PREGUNTAS_CORTAS = {
    "ipc_oct26": "Inflación a 12 meses, octubre de 2026",
    "alimentos_oct26": "Inflación de alimentos a 12 meses, octubre de 2026",
    "juntos_real_2006": "S/ 100 de agosto de 2026 en soles de 2006",
    "pesca_may26": "PBI pesca, variación anual, mayo de 2026",
    "pobreza_2024": "Pobreza monetaria nacional 2024",
    "extrema_rural": "Pobreza extrema rural 2024",
    "pobres_urbanos": "Porcentaje de los pobres que vive en ciudades",
    "dep_mas_pobre": "Pobreza del departamento más pobre",
    "juntos_enaho_real_2006": "Mediana de Juntos (ENAHO) en soles de 2006",
    "aporte_alimentos_pobres": "Aporte de los alimentos al costo de vida de los pobres",
}


# ── 1. Series del IPC desde el servidor MCP ─────────────────────────────────────────────────────────────
SERIES_IPC = {"total": "PN38705PM", "alimentos": "PN39445PM", "sin_alimentos": "PN38706PM"}
DESDE, HASTA = "2006-12", "2026-10"          # el mismo periodo del informe


async def pedir_ipc():
    async with Client(servidor_bcrp) as c:
        series = {}
        for clave, codigo in SERIES_IPC.items():
            r = (await c.call_tool("serie", {"codigo": codigo, "desde": DESDE, "hasta": HASTA})).data
            series[clave] = r
    return series


def armar_ipc(series):
    meses = [d["periodo"] for d in series["total"]["datos"]]
    salida = {"meses": meses, "codigos": SERIES_IPC, "fuente": series["total"]["fuente"]}
    for clave, r in series.items():
        valores = {d["periodo"]: d["valor"] for d in r["datos"]}
        if list(valores) != meses:
            sys.exit(f"La serie {r['codigo']} no tiene los mismos meses que {SERIES_IPC['total']}.")
        salida[clave] = [valores[m] for m in meses]
        salida[f"nombre_{clave}"] = r["nombre"]
    return salida


# ── 2. Salidas de las Skills, del cruce y de la evaluación ──────────────────────────────────────────────
def leer_indicadores():
    ind = pd.read_csv(RAIZ / "salidas" / "indicadores.csv", dtype={"grupo": str})

    def v(indicador, grupo):
        fila = ind[(ind.indicador == indicador) & (ind.grupo == grupo)]
        return None if fila.empty else round(float(fila.valor.iloc[0]), 4)

    def grupo(etiquetas):
        return [{"etiqueta": e, "pobreza": v("pobreza", g), "extrema": v("pobreza_extrema", g)}
                for e, g in etiquetas]

    return {
        "nacional": {"pobreza": v("pobreza", "Nacional"), "extrema": v("pobreza_extrema", "Nacional"),
                     "pobres_millones": v("pobres", "Nacional"), "brecha": v("brecha_pobreza_fgt1", "Nacional")},
        "grupos": {
            "area": grupo([("Nacional", "Nacional"), ("Urbano", "Urbano"), ("Rural", "Rural"),
                           ("Lima Metropolitana", "Lima Metropolitana")]),
            "hogar": grupo([("Con menores de 5 años", "Hogar con menores de 5 años"),
                            ("Sin menores de 5 años", "Hogar sin menores de 5 años"),
                            ("Con adultos de 65 o más", "Hogar con adultos de 65+"),
                            ("Sin adultos de 65 o más", "Hogar sin adultos de 65+")]),
            "jefatura": grupo([("Jefa mujer", "Jefatura femenina"), ("Jefe hombre", "Jefatura masculina"),
                               ("Jefa mujer, rural", "Jefatura femenina (rural)"),
                               ("Jefe hombre, rural", "Jefatura masculina (rural)")]),
            "sexo": grupo([("Mujeres", "Sexo: Mujer"), ("Hombres", "Sexo: Hombre")]),
        },
        "vulnerabilidad": [{"etiqueta": g, "valor": v("condicion_vulnerabilidad", g)}
                           for g in ["Pobre extremo", "Pobre no extremo", "No pobre vulnerable",
                                     "No pobre no vulnerable"]],
        "alimentos": {"pobres": v("share_gasto_alimentos", "Pobres"),
                      "no_pobres": v("share_gasto_alimentos", "No pobres")},
    }


def leer_departamentos():
    dep = pd.read_csv(RAIZ / "salidas" / "comparacion_mapa.csv", dtype={"ccdd": str})
    return [{"id": f.ccdd, "nombre": NOMBRES[f.ccdd], "valor": round(f.calculado_pct, 2),
             "referencia": f.referencia_pct} for f in dep.itertuples()]


def leer_cruce():
    cruce = pd.read_csv(RAIZ / "salidas" / "cruce.csv")
    valores = dict(zip(cruce.indicador, cruce.valor.round(4)))
    cobertura = [{"etiqueta": k.split(": ", 1)[1], "valor": round(valores[k], 2)}
                 for k in valores if k.startswith("cobertura_juntos: ")]
    return valores, cobertura


def leer_evaluacion():
    res = pd.read_csv(RAIZ / "evaluacion" / "resultados.csv", dtype=str, keep_default_na=False)
    filas = {}
    for f in res.itertuples():
        fila = filas.setdefault(f.id, {"id": f.id, "corta": PREGUNTAS_CORTAS[f.id], "tipo": f.tipo,
                                       "pregunta": f.pregunta, "esperada": float(f.esperada),
                                       "tolerancia": float(f.tolerancia), "unidad": f.unidad})
        fila[f.modo] = {"valor": float(f.valor) if f.valor else None, "resultado": f.resultado,
                        "segundos": float(f.segundos), "herramientas": [h.replace("mcp__bcrp__", "")
                                                                        for h in f.herramientas.split(";") if h],
                        "skills": [s for s in f.skills.split(";") if s], "fuente": f.fuente}
    return list(filas.values())


# ── 3. Mapa: GeoJSON → trazos SVG ──────────────────────────────────────────────────────────────────────
def trazos_mapa():
    ruta = RAIZ / "datos" / "peru_departamental_simple.geojson"
    if not ruta.exists():
        print("Aviso: no está el GeoJSON; el sitio usará el mapa PNG.")
        return None
    import geopandas as gpd   # solo para leer y simplificar los polígonos
    import math

    g = gpd.read_file(ruta)
    g["geometry"] = g.geometry.simplify(0.01, preserve_topology=True)   # ~1 km: basta para la pantalla
    x0, y0, x1, y1 = g.total_bounds
    k_lon = math.cos(math.radians((y0 + y1) / 2))    # corrige el ancho de un grado de longitud
    escala = 400 / ((x1 - x0) * k_lon)

    def punto(lon, lat):
        return f"{(lon - x0) * k_lon * escala:.1f},{(y1 - lat) * escala:.1f}"

    def anillo(coords):
        return "M" + "L".join(punto(lon, lat) for lon, lat in coords) + "Z"

    trazos = {}
    for f in g.itertuples():
        polis = [f.geometry] if f.geometry.geom_type == "Polygon" else list(f.geometry.geoms)
        trazos[f.FIRST_IDDP] = "".join(anillo(p.exterior.coords) + "".join(anillo(i.coords) for i in p.interiors)
                                       for p in polis)
    return {"ancho": 400, "alto": round((y1 - y0) * escala, 1), "trazos": trazos}


# ── 4. Informe en HTML ─────────────────────────────────────────────────────────────────────────────────
def informe_html():
    texto = (RAIZ / "informes" / "informe_final.md").read_text(encoding="utf-8")
    texto = texto.replace("](../figuras/", "](figuras/").replace("](../mapas/", "](mapas/")
    # El informe sangra las listas anidadas con 2 espacios; Python-Markdown pide 4. Se duplica la sangría
    # (fuera de los bloques de código) para que las sublistas se vean como sublistas.
    lineas, en_codigo = [], False
    for linea in texto.splitlines():
        if linea.startswith("```"):
            en_codigo = not en_codigo
        if not en_codigo and linea.startswith(" "):
            sangria = len(linea) - len(linea.lstrip(" "))
            linea = " " * (2 * sangria) + linea.lstrip(" ")
        lineas.append(linea)
    md = markdown.Markdown(extensions=["tables", "fenced_code", "toc", "sane_lists"],
                           extension_configs={"toc": {"toc_depth": "2-3"}})
    cuerpo = md.convert("\n".join(lineas))
    cuerpo = cuerpo.replace("<table>", '<div class="tabla"><table>').replace("</table>", "</table></div>")
    plantilla = (RAIZ / "scripts" / "plantilla_informe.html").read_text(encoding="utf-8")
    return plantilla.replace("{{indice}}", md.toc).replace("{{cuerpo}}", cuerpo).replace(
        "{{fecha}}", html.escape(date.today().strftime("%d-%m-%Y")))


# ── 5. Escribir el sitio ───────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ipc = armar_ipc(asyncio.run(pedir_ipc()))
    cruce, cobertura = leer_cruce()
    datos = {
        "generado": date.today().isoformat(),
        "repo": REPO,
        "ipc": ipc,
        "enaho": leer_indicadores(),
        "departamentos": leer_departamentos(),
        "cruce": cruce,
        "cobertura_juntos": cobertura,
        "evaluacion": leer_evaluacion(),
        "mapa": trazos_mapa(),
    }
    (SITIO / "datos.js").write_text(
        "// Generado por scripts/construir_sitio.py: no editar a mano.\n"
        "window.DATOS = " + json.dumps(datos, ensure_ascii=False, separators=(",", ":")) + ";\n",
        encoding="utf-8")
    (SITIO / "informe.html").write_text(informe_html(), encoding="utf-8")
    for carpeta in ("figuras", "mapas"):
        (SITIO / carpeta).mkdir(exist_ok=True)
        for png in (RAIZ / carpeta).glob("*.png"):
            shutil.copy2(png, SITIO / carpeta / png.name)

    n = len(ipc["meses"])
    print(f"IPC: {n} meses ({ipc['meses'][0]} a {ipc['meses'][-1]}), último total {ipc['total'][-1]}, "
          f"alimentos {ipc['alimentos'][-1]}")
    print(f"Departamentos: {len(datos['departamentos'])}; mapa interactivo: {'sí' if datos['mapa'] else 'no'}")
    print(f"Preguntas de evaluación: {len(datos['evaluacion'])}")
    for f in sorted(SITIO.rglob("*")):
        if f.is_file():
            print(f"  {f.relative_to(RAIZ)}  {f.stat().st_size / 1024:.0f} KB")
