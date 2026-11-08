"""Servidor MCP del BCRP para el agente de investigación socioeconómica (Tarea 4).

    uv run pytest                     # 8 pruebas originales de la sesión 04 + 2 propias -> 10 passed
    uv run python mcp/server.py       # el servidor, por stdio (Claude Code lo lanza con .mcp.json)

Herramientas: buscar_series, serie, resumen, valor_real (propia) y graficar_serie.
Recurso: bcrp://serie/{codigo}. Prompt: informe(tema).
Las cuentas las hace Python, no el modelo: cada cifra sale de una llamada que se puede repetir.
"""
# ── Paquetes ─────────────────────────────────────────────────────────────────────────────────
import json          # leer la respuesta de la API y guardar la caché
import re            # reconocer los formatos de fecha del BCRP (Ene.2025, 01.Oct.26, T1.25)
import time          # esperar antes de reintentar y vencer la caché
import unicodedata   # quitar tildes para buscar en el catálogo
from functools import cache
from pathlib import Path

import httpx                      # llamadas HTTP a la API del BCRP
import pandas as pd               # el catálogo de 17 mil series
from fastmcp import FastMCP       # el servidor MCP
from fastmcp.exceptions import ToolError  # errores que el cliente ve con un mensaje claro

AQUI = Path(__file__).parent
CATALOGO = AQUI / "datos" / "catalogo_bcrp.csv"
CACHE = AQUI / "cache"
FIGURAS = AQUI.parent / "figuras"
URL_CATALOGO = "https://estadisticas.bcrp.gob.pe/estadisticas/series/metadata"
API = "https://estadisticas.bcrp.gob.pe/estadisticas/series/api"
SOLO_LECTURA = {"readOnlyHint": True, "openWorldHint": True}
HORAS_CACHE = 6
MESES = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6, "jul": 7, "ago": 8,
         "sep": 9, "set": 9, "oct": 10, "nov": 11, "dic": 12}

mcp = FastMCP("bcrp", instructions=(
    "Series oficiales del Banco Central de Reserva del Perú (BCRP). Primero busca el código con buscar_series; "
    "luego usa resumen para variaciones, promedios y extremos, serie para los datos, valor_real para llevar un "
    "monto en soles a precios de otra fecha con el IPC, y graficar_serie para guardar un gráfico. No calcules a "
    "mano: cita siempre el código de la serie, el periodo y la fuente."))


# ── 1. Catálogo oficial ──────────────────────────────────────────────────────────────────────
def _sin_tildes(s):
    return unicodedata.normalize("NFD", str(s).lower()).encode("ascii", "ignore").decode()


@cache
def catalogo():
    """El catálogo oficial: 17 mil series en unos 7 MB. Se baja una vez y queda en mcp/datos/."""
    if not CATALOGO.exists():
        CATALOGO.parent.mkdir(exist_ok=True)
        r = httpx.get(URL_CATALOGO, timeout=120)
        r.raise_for_status()
        CATALOGO.write_text(r.content.decode("latin-1"), encoding="utf-8")   # antes: latin-1 → después: utf-8
    df = pd.read_csv(CATALOGO, sep=";", dtype=str).fillna("")
    df = df.rename(columns={"Código de serie": "codigo", "Categoría de serie": "categoria", "Grupo de serie": "grupo",
                            "Nombre de serie": "nombre", "Frecuencia": "frecuencia", "Unidad de medida": "unidad",
                            "Fecha de actualización": "actualizada", "Fecha de inicio": "inicio",
                            "Fecha de fin": "fin"})
    df["texto"] = (df.categoria + " " + df.grupo + " " + df.nombre).map(_sin_tildes)
    return df


def _ficha(codigo):
    fila = catalogo().query("codigo == @codigo")
    if fila.empty:
        raise ToolError(f"No existe el código de serie {codigo!r}. Búsquenlo con buscar_series.")
    f = fila.iloc[0]
    return {"codigo": f.codigo, "nombre": f"{f.grupo} - {f.nombre}", "categoria": f.categoria,
            "frecuencia": f.frecuencia, "inicio": f.inicio, "actualizada": f.actualizada}


@mcp.tool(annotations=SOLO_LECTURA)
def buscar_series(texto: str, frecuencia: str | None = None, limite: int = 10) -> list[dict]:
    """Busca series del BCRP por palabras: todas deben aparecer en la categoría, el grupo o el nombre.

    Ejemplos: "ipc 12 meses", "ipc alimentos y bebidas", "tipo de cambio interbancario venta",
    "reservas internacionales netas", "tasa de referencia", "pbi pesca". frecuencia: "Diaria", "Mensual",
    "Trimestral" o "Anual". Devuelve el código, el nombre completo, la frecuencia y desde cuándo hay datos.
    Si no hay resultados, prueben con menos palabras.
    """
    df = catalogo()
    m = pd.Series(True, index=df.index)
    for palabra in _sin_tildes(texto).split():
        m &= df.texto.str.contains(re.escape(palabra))
    if frecuencia:
        m &= df.frecuencia.str.lower() == frecuencia.lower()
    # primero las series vigentes y, entre ellas, las de nombre más corto (las más generales)
    sel = df[m]
    orden = sel.assign(vieja=sel.actualizada < "2025", largo=(sel.grupo + sel.nombre).str.len())
    return [_ficha(c) for c in orden.sort_values(["vieja", "largo"]).head(limite).codigo]


# ── 2. Fechas: lo que pide la API y lo que devuelve ──────────────────────────────────────────
def _fecha_api(fecha, frecuencia):
    """Antes: '2025-01', '2025-T1', '2026-10-01', '2025' → después: lo que pide la API para esa frecuencia."""
    f = str(fecha).strip()
    frec = frecuencia.lower()
    try:
        if frec.startswith("diar"):
            a, m, d = f.split("-")
            return f"{int(a):04d}-{int(m):02d}-{int(d):02d}"
        if frec.startswith("anual"):
            return f"{int(f[:4])}"
        a, resto = f.split("-")[:2]
        return f"{int(a)}-{int(resto.upper().lstrip('TQ'))}"     # mensual: 2025-1 ; trimestral: 2025-1
    except ValueError:
        raise ToolError(f"Fecha {fecha!r} no válida para una serie {frecuencia}. Usen 2025-01 (mensual), "
                        "2025-T1 (trimestral), 2026-10-01 (diaria) o 2025 (anual).") from None


def _periodo(nombre):
    """Antes: 'Ene.2025', 'Set.2025', '01.Oct.26', 'T1.25', '2025' → después: '2025-01', '2025-09', '2026-10-01',
    '2025-T1', '2025'."""
    n = nombre.strip()
    if m := re.fullmatch(r"([A-Za-z]{3})\.(\d{4})", n):
        return f"{m[2]}-{MESES[m[1].lower()]:02d}"
    if m := re.fullmatch(r"(\d{2})\.([A-Za-z]{3})\.(\d{2})", n):
        return f"20{m[3]}-{MESES[m[2].lower()]:02d}-{m[1]}"
    if m := re.fullmatch(r"T(\d)\.(\d{2})", n):
        return f"20{m[2]}-T{m[1]}"
    if re.fullmatch(r"\d{4}", n):
        return n
    return n


# ── 3. Descarga con reintentos y caché ───────────────────────────────────────────────────────
def _leer_json(contenido: bytes):
    """La API puede pegar un aviso HTML de PHP después del JSON y no siempre responde en UTF-8.
    Antes: bytes con basura al final → después: el diccionario JSON (o None si vino una página HTML)."""
    try:
        texto = contenido.decode("utf-8")
    except UnicodeDecodeError:
        texto = contenido.decode("latin-1")
    inicio = texto.find("{")
    if inicio < 0:
        return None
    try:
        return json.JSONDecoder().raw_decode(texto[inicio:])[0]
    except json.JSONDecodeError:
        return None


def _descargar(codigo, desde_api, hasta_api):
    CACHE.mkdir(exist_ok=True)
    archivo = CACHE / f"{codigo}_{desde_api}_{hasta_api}.json"
    if archivo.exists() and time.time() - archivo.stat().st_mtime < HORAS_CACHE * 3600:
        return json.loads(archivo.read_text(encoding="utf-8"))
    url = f"{API}/{codigo}/json/{desde_api}/{hasta_api}"
    ultimo_error = ""
    for intento in range(5):
        try:
            r = httpx.get(url, timeout=60, headers={"User-Agent": "tarea4-agente-socioeconomico"})
            d = _leer_json(r.content)
            if d is not None and "periods" in d:
                archivo.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
                return d
            ultimo_error = f"respuesta sin datos (HTTP {r.status_code})"
        except httpx.HTTPError as e:
            ultimo_error = str(e)
        time.sleep(2 + 3 * intento)     # muchos pedidos seguidos: la API responde HTML; esperar y reintentar
    raise ToolError(f"La API del BCRP no devolvió datos para {codigo} ({desde_api} a {hasta_api}): {ultimo_error}. "
                    f"URL: {url}")


def _datos(codigo, desde, hasta):
    ficha = _ficha(codigo)
    d_api, h_api = _fecha_api(desde, ficha["frecuencia"]), _fecha_api(hasta, ficha["frecuencia"])
    crudo = _descargar(codigo, d_api, h_api)
    datos = []
    for p in crudo.get("periods", []):
        v = (p.get("values") or ["n.d."])[0]
        try:
            datos.append({"periodo": _periodo(p["name"]), "valor": float(v)})
        except (TypeError, ValueError):
            continue                     # "n.d.": sin dato, se salta
    if not datos:
        raise ToolError(f"La serie {codigo} no tiene datos entre {desde} y {hasta}.")
    return ficha, datos, f"{API}/{codigo}/json/{d_api}/{h_api}"


# ── 4. Herramientas de consulta ──────────────────────────────────────────────────────────────
@mcp.tool(annotations=SOLO_LECTURA)
def serie(codigo: str, desde: str, hasta: str) -> dict:
    """Descarga los datos oficiales de una serie del BCRP entre dos fechas (incluidas).

    Fechas: 2025-01 (mensual), 2025-T1 (trimestral), 2026-10-01 (diaria) o 2025 (anual).
    Devuelve codigo, nombre, frecuencia, datos [{periodo, valor}] y fuente (la URL de la API).
    """
    ficha, datos, url = _datos(codigo, desde, hasta)
    return {"codigo": codigo, "nombre": ficha["nombre"], "frecuencia": ficha["frecuencia"], "datos": datos,
            "fuente": url}


@mcp.tool(annotations=SOLO_LECTURA)
def resumen(codigo: str, desde: str, hasta: str) -> dict:
    """Resume una serie del BCRP en un periodo: primero, último, cambio (último − primero), variacion_pct,
    promedio, máximo y mínimo (con su periodo) y número de datos. Úsenla en lugar de hacer cuentas a mano."""
    ficha, datos, url = _datos(codigo, desde, hasta)
    s = pd.Series([x["valor"] for x in datos], index=[x["periodo"] for x in datos])
    primero, ultimo = datos[0], datos[-1]
    return {"codigo": codigo, "nombre": ficha["nombre"], "frecuencia": ficha["frecuencia"],
            "primero": primero, "ultimo": ultimo,
            "cambio": round(ultimo["valor"] - primero["valor"], 6),
            "variacion_pct": round((ultimo["valor"] / primero["valor"] - 1) * 100, 6) if primero["valor"] else None,
            "promedio": round(float(s.mean()), 6),
            "maximo": {"periodo": s.idxmax(), "valor": float(s.max())},
            "minimo": {"periodo": s.idxmin(), "valor": float(s.min())},
            "n": len(s), "fuente": url}


# ── 5. Herramienta propia: valor real de un monto en soles ───────────────────────────────────
def _ipc_en(codigo, mes):
    """El valor del índice en un mes exacto, o un error que dice qué mes falta."""
    try:
        _, datos, url = _datos(codigo, mes, mes)
    except ToolError as e:
        raise ToolError(f"No hay dato del índice {codigo} para {mes}: {e}") from None
    return datos[0]["valor"], url


@mcp.tool(annotations=SOLO_LECTURA)
def valor_real(monto: float, desde: str, hasta: str, codigo_ipc: str = "PN38705PM") -> dict:
    """Lleva un monto en soles de la fecha `desde` a soles de la fecha `hasta` con un índice de precios del BCRP.

    Responde: ¿a cuánto equivalen `monto` soles de `desde` en soles de `hasta`?
    valor = monto × IPC[hasta] / IPC[desde].
    Ejemplo: cuánto valen los S/ 100 de Juntos de agosto de 2026 en soles de diciembre de 2006:
    valor_real(100, desde="2026-08", hasta="2006-12") → ≈ 51,8.
    Meses en formato 2026-08. Por defecto usa el IPC de Lima Metropolitana (índice dic-2021 = 100, PN38705PM);
    para precios de alimentos usen PN39445PM. Solo acepta índices mensuales.
    """
    ficha = _ficha(codigo_ipc)
    nombre = _sin_tildes(ficha["nombre"])   # una variación porcentual (var%) no sirve para deflactar
    if ficha["frecuencia"].lower() != "mensual" or "var" in nombre or "indice" not in nombre:
        raise ToolError(f"{codigo_ipc} no es un índice mensual de precios ({ficha['nombre']}). Usen PN38705PM.")
    ipc_d, url_d = _ipc_en(codigo_ipc, desde)
    ipc_h, url_h = _ipc_en(codigo_ipc, hasta)
    factor = ipc_h / ipc_d
    valor = monto * factor
    antes, despues = sorted([(desde, ipc_d), (hasta, ipc_h)])
    inflacion = (despues[1] / antes[1] - 1) * 100
    return {"monto": monto, "desde": desde, "hasta": hasta, "codigo_ipc": codigo_ipc, "indice": ficha["nombre"],
            "ipc_desde": round(ipc_d, 4), "ipc_hasta": round(ipc_h, 4), "factor": round(factor, 6),
            "valor": round(valor, 4),
            "inflacion_acumulada_pct": round(inflacion, 4),
            "interpretacion": f"S/ {monto:,.2f} de {desde} equivalen a S/ {valor:,.2f} de {hasta} "
                              f"(precios: {inflacion:+.1f} % entre {antes[0]} y {despues[0]}).",
            "fuente": [url_d, url_h]}


# ── 6. Gráfico de una o varias series ────────────────────────────────────────────────────────
@mcp.tool(annotations={"readOnlyHint": False, "openWorldHint": True})
def graficar_serie(codigos: list[str], desde: str, hasta: str, titulo: str, archivo: str,
                   base_100: bool = False, nota: str = "") -> dict:
    """Grafica una o más series del BCRP en el mismo periodo y guarda el PNG en figuras/.

    base_100=True reexpresa cada serie con su primer dato = 100 (sirve para comparar índices de precios).
    titulo: una frase que diga qué muestra el gráfico. archivo: nombre del PNG, por ejemplo "bcrp_ipc.png".
    Devuelve la ruta del archivo, los códigos, el último dato de cada serie y la fuente.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    FIGURAS.mkdir(exist_ok=True)
    fig, ax = plt.subplots(figsize=(9, 5))
    ultimos, fuentes = {}, []
    for cod in codigos:
        ficha, datos, url = _datos(cod, desde, hasta)
        s = pd.Series([x["valor"] for x in datos], index=[x["periodo"] for x in datos])
        if base_100:
            s = s / s.iloc[0] * 100
        etiqueta = f"{ficha['nombre'].split(' - ')[-1]} ({cod})"
        ax.plot(range(len(s)), s.values, lw=2, label=etiqueta)
        paso = max(1, len(s) // 8)
        ax.set_xticks(range(0, len(s), paso), s.index[::paso], rotation=45, ha="right", fontsize=8)
        ax.annotate(f"{s.iloc[-1]:.1f}", (len(s) - 1, s.iloc[-1]), fontsize=8, xytext=(4, 0),
                    textcoords="offset points", va="center")
        ultimos[cod] = {"periodo": s.index[-1], "valor": round(float(s.iloc[-1]), 4)}
        fuentes.append(url)
    ax.set_title(titulo, fontsize=11, loc="left")
    ax.set_ylabel(f"Índice ({desde} = 100)" if base_100 else ficha["nombre"].split("(")[-1].rstrip(")"))
    ax.grid(alpha=0.3)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(fontsize=8, frameon=False)
    fig.text(0.01, 0.01, f"Fuente: BCRP, series {', '.join(codigos)} ({desde} a {hasta}). {nota}".strip(),
             fontsize=7, color="#555")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    ruta = FIGURAS / Path(archivo).name
    fig.savefig(ruta, dpi=200)
    plt.close(fig)
    return {"archivo": str(ruta.relative_to(AQUI.parent)).replace("\\", "/"), "codigos": codigos,
            "base_100": base_100, "ultimos": ultimos, "fuente": fuentes}


# ── 7. Recurso y prompt ──────────────────────────────────────────────────────────────────────
@mcp.resource("bcrp://serie/{codigo}", mime_type="application/json")
def ficha_serie(codigo: str) -> str:
    """Ficha descriptiva de una serie: nombre, categoría, frecuencia, unidad, fechas de inicio, fin y actualización."""
    fila = catalogo().query("codigo == @codigo")
    if fila.empty:
        raise ToolError(f"No existe el código de serie {codigo!r}.")
    f = fila.iloc[0]
    return json.dumps({"codigo": f.codigo, "nombre": f.nombre, "grupo": f.grupo, "categoria": f.categoria,
                       "frecuencia": f.frecuencia, "unidad": f.unidad, "inicio": f.inicio, "fin": f.fin,
                       "actualizada": f.actualizada, "fuente": "BCRP, " + URL_CATALOGO}, ensure_ascii=False)


@mcp.prompt()
def informe(tema: str) -> str:
    """Plantilla para un informe breve con series del BCRP sobre un tema."""
    return (f"Prepara un informe breve sobre: {tema}.\n"
            "1. Busca las series con buscar_series y elige las oficiales vigentes.\n"
            "2. Obtén las cifras con resumen, serie o valor_real; nunca hagas cuentas a mano.\n"
            "3. Cada cifra va con su código de serie, el periodo y la fuente (URL de la API).\n"
            "4. Si una herramienta falla o no hay datos, dilo; no inventes valores.\n"
            "5. No presentes asociaciones como causas.")


if __name__ == "__main__":
    mcp.run()
