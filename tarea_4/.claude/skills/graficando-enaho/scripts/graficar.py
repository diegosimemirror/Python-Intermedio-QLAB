"""Gráficos ponderados de pobreza con la ENAHO 2024 ya limpia (salidas/*.parquet).

    uv run python .claude/skills/graficando-enaho/scripts/graficar.py area
    uv run python .claude/skills/graficando-enaho/scripts/graficar.py sexo
    uv run python .claude/skills/graficando-enaho/scripts/graficar.py hogares
    uv run python .claude/skills/graficando-enaho/scripts/graficar.py departamentos
    uv run python .claude/skills/graficando-enaho/scripts/graficar.py todos

Cada gráfico: barras desde cero, un solo color, el valor escrito, título que dice qué muestra,
periodo y unidad en el subtítulo y la fuente al pie. PNG a 200 dpi en figuras/.
Imprime las cifras de cada barra para que el agente las cite sin calcular a mano.
"""
# ── Paquetes ─────────────────────────────────────────────────────────────────────────────────
import argparse
import sys
import textwrap                       # partir títulos largos en líneas
from pathlib import Path

import matplotlib
matplotlib.use("Agg")                 # sin ventana: solo archivos PNG
import matplotlib.pyplot as plt       # los gráficos
import pandas as pd                   # leer las bases limpias y ponderar

RAIZ = Path.cwd()
SALIDAS, FIGURAS = RAIZ / "salidas", RAIZ / "figuras"
AZUL, GRIS_TXT, GRIS_EJE, GRILLA, FONDO = "#2a78d6", "#52514e", "#898781", "#e1e0d9", "#fcfcfb"
FUENTE = "Fuente: INEI, ENAHO 2024 (módulos 34 y 02). Estimaciones ponderadas"
NOMBRES = {"01": "Amazonas", "02": "Áncash", "03": "Apurímac", "04": "Arequipa", "05": "Ayacucho", "06": "Cajamarca",
           "07": "Callao", "08": "Cusco", "09": "Huancavelica", "10": "Huánuco", "11": "Ica", "12": "Junín",
           "13": "La Libertad", "14": "Lambayeque", "15": "Lima", "16": "Loreto", "17": "Madre de Dios",
           "18": "Moquegua", "19": "Pasco", "20": "Piura", "21": "Puno", "22": "San Martín", "23": "Tacna",
           "24": "Tumbes", "25": "Ucayali"}


def coma(v, d=1):
    return f"{v:.{d}f}".replace(".", ",")


# ── 1. Cargar la base limpia (o pedir la limpieza) ───────────────────────────────────────────
def cargar():
    h, p = SALIDAS / "hogares_2024.parquet", SALIDAS / "personas_2024.parquet"
    if not (h.exists() and p.exists()):
        sys.exit("FALTA LA BASE LIMPIA: no existe salidas/hogares_2024.parquet o salidas/personas_2024.parquet. "
                 "Corre primero la skill limpiando-enaho "
                 "(uv run python .claude/skills/limpiando-enaho/scripts/limpiar.py) y vuelve a pedir el gráfico.")
    return pd.read_parquet(h), pd.read_parquet(p)


def tasa(df, mascara, peso, col="pobre"):
    """Porcentaje ponderado de personas con `col` verdadero dentro de `mascara`."""
    d = df[mascara]
    return float((d[col] * d[peso]).sum() / d[peso].sum() * 100)


# ── 2. Dibujo común: barras horizontales con el valor escrito ────────────────────────────────
def barras(etiquetas, valores, titulo, subtitulo, archivo, referencia=None, ancho=8.5):
    titulo = textwrap.fill(" ".join(titulo.split()), width=int(ancho * 10.5))
    lineas = titulo.count(chr(10))
    if referencia is not None:
        subtitulo += f". Línea punteada: {referencia[0].lower()} ({coma(referencia[1])} %)"
    alto = 1.4 + 0.42 * len(valores) + 0.25 * lineas
    fig, ax = plt.subplots(figsize=(ancho, alto), facecolor=FONDO)
    ax.set_facecolor(FONDO)
    y = range(len(valores))[::-1]
    ax.barh(list(y), valores, color=AZUL, height=0.62, edgecolor=FONDO, linewidth=2)
    for yi, v in zip(y, valores):
        ax.text(v + max(valores) * 0.01, yi, coma(v), va="center", fontsize=9, color="#0b0b0b")
    ax.set_yticks(list(y), etiquetas, fontsize=9, color="#0b0b0b")
    ax.set_xlim(0, max(valores) * 1.12)
    ax.xaxis.grid(True, color=GRILLA, lw=0.6)
    ax.set_axisbelow(True)
    ax.tick_params(axis="x", colors=GRIS_EJE, labelsize=8)
    ax.tick_params(axis="y", length=0)
    for lado in ["top", "right", "left"]:
        ax.spines[lado].set_visible(False)
    ax.spines["bottom"].set_color("#c3c2b7")
    if referencia is not None:
        ax.axvline(referencia[1], color=GRIS_TXT, lw=1, ls="--")
    fig.suptitle(titulo, x=0.01, ha="left", fontsize=11.5, fontweight="bold", color="#0b0b0b")
    ax.set_title(subtitulo, loc="left", fontsize=9, color=GRIS_TXT)
    fig.text(0.01, 0.005, FUENTE + ".", fontsize=7, color=GRIS_TXT)
    fig.tight_layout(rect=(0, 0.03, 1, 0.98 - 0.03 * lineas))
    FIGURAS.mkdir(exist_ok=True)
    ruta = FIGURAS / archivo
    fig.savefig(ruta, dpi=200, facecolor=FONDO)
    plt.close(fig)
    print(f"\n{ruta.relative_to(RAIZ)}")
    for e, v in zip(etiquetas, valores):
        print(f"  {e}: {coma(v, 2)} %")
    return ruta


# ── 3. Los gráficos ──────────────────────────────────────────────────────────────────────────
def area(h, p):
    w = "peso_personas"
    todos = pd.Series(True, index=h.index)
    v = {"Nacional": tasa(h, todos, w), "Urbano": tasa(h, h.urbano, w), "Rural": tasa(h, ~h.urbano, w),
         "Lima Metropolitana": tasa(h, h.lima_metropolitana, w)}
    t = (f"La pobreza rural ({coma(v['Rural'])} %) supera en {coma(v['Rural'] - v['Urbano'])} puntos "
         f"a la urbana ({coma(v['Urbano'])} %)")
    barras(list(v), list(v.values()), t, "Pobreza monetaria por área, Perú 2024 (% de personas)",
           "enaho_pobreza_area.png")


def sexo(h, p):
    v = {"Hombres": tasa(p, p.sexo == "Hombre", "facpob07"), "Mujeres": tasa(p, p.sexo == "Mujer", "facpob07"),
         "Hogares con jefe hombre": tasa(h, h.jefatura == "Masculina", "peso_personas"),
         "Hogares con jefa mujer": tasa(h, h.jefatura == "Femenina", "peso_personas")}
    t = (f"Por sexo la pobreza casi no cambia ({coma(v['Hombres'])} % hombres, {coma(v['Mujeres'])} % mujeres) "
         f"y los hogares con jefa\nmujer son algo menos pobres ({coma(v['Hogares con jefa mujer'])} % frente a "
         f"{coma(v['Hogares con jefe hombre'])} %)")
    barras(list(v), list(v.values()), t,
           "Pobreza monetaria por sexo de la persona y del jefe de hogar, Perú 2024 (% de personas)",
           "enaho_pobreza_sexo.png")


def hogares(h, p):
    w = "peso_personas"
    v = {"Con menores de 5 años": tasa(h, h.con_menor_5 == True, w),
         "Sin menores de 5 años": tasa(h, h.con_menor_5 == False, w),
         "Con adultos de 65 o más": tasa(h, h.con_adulto_65 == True, w),
         "Sin adultos de 65 o más": tasa(h, h.con_adulto_65 == False, w),
         "Jefa mujer": tasa(h, h.jefatura == "Femenina", w),
         "Jefe hombre": tasa(h, h.jefatura == "Masculina", w)}
    nac = tasa(h, pd.Series(True, index=h.index), w)
    r = v["Con menores de 5 años"] / v["Sin menores de 5 años"]
    t = (f"En los hogares con niños menores de 5 años la pobreza es {coma(r)} veces la de los hogares sin ellos "
         f"({coma(v['Con menores de 5 años'])} % frente a {coma(v['Sin menores de 5 años'])} %)")
    barras(list(v), list(v.values()), t, "Pobreza monetaria según el tipo de hogar, Perú 2024 (% de personas)",
           "enaho_pobreza_hogares.png", referencia=("Nacional", nac), ancho=9.5)


def departamentos(h, p):
    w = "peso_personas"
    dep = {NOMBRES[d]: tasa(h, h.departamento == d, w) for d in sorted(h.departamento.unique())}
    s = pd.Series(dep).sort_values(ascending=False)
    nac = tasa(h, pd.Series(True, index=h.index), w)
    t = (f"{s.index[0]} ({coma(s.iloc[0])} %) tiene {coma(s.iloc[0] / s.iloc[-1])} veces la pobreza "
         f"de {s.index[-1]} ({coma(s.iloc[-1])} %)")
    barras(list(s.index), list(s.values), t, "Pobreza monetaria por departamento, Perú 2024 (% de personas)",
           "enaho_pobreza_departamentos.png", referencia=("Nacional", nac))


GRAFICOS = {"area": area, "sexo": sexo, "hogares": hogares, "departamentos": departamentos}

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    a = argparse.ArgumentParser()
    a.add_argument("grafico", choices=[*GRAFICOS, "todos"])
    g = a.parse_args().grafico
    base = cargar()
    for nombre in (GRAFICOS if g == "todos" else [g]):
        GRAFICOS[nombre](*base)
