"""Mapa coroplético de la pobreza monetaria por departamento con la ENAHO 2024 ya limpia.

    uv run python .claude/skills/mapeando-enaho/scripts/mapear.py

Une por código (ubigeo[:2] = FIRST_IDDP, como texto), nunca por nombre. Exige 25 departamentos con dato,
Lima (15) y Callao (07) separados. Compara con referencias/pobreza_departamento_2024.csv (sesión 16).
Sale: mapas/pobreza_departamento_2024.png y salidas/comparacion_mapa.csv.
"""
# ── Paquetes ─────────────────────────────────────────────────────────────────────────────────
import sys
from pathlib import Path

import geopandas as gpd               # leer el GeoJSON y dibujar polígonos
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import pandas as pd

RAIZ = Path.cwd()
SALIDAS, MAPAS = RAIZ / "salidas", RAIZ / "mapas"
GEO = RAIZ / "datos" / "peru_departamental_simple.geojson"
URL_GEO = ("https://raw.githubusercontent.com/d2cml-ai/Data-Science-Python/main/sessions/06-geoespacial/lab/Data/"
           "peru_departamental_simple.geojson")
FONDO, TXT, TXT2 = "#fcfcfb", "#0b0b0b", "#52514e"
# un solo azul de claro a oscuro (pasos 250 → 700 de la paleta validada); nunca arcoíris
AZULES = LinearSegmentedColormap.from_list("azules", ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#104281", "#0d366b"])


def coma(v, d=1):
    return f"{v:.{d}f}".replace(".", ",")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    hog = SALIDAS / "hogares_2024.parquet"
    if not hog.exists():
        sys.exit("FALTA LA BASE LIMPIA: no existe salidas/hogares_2024.parquet. Corre primero la skill "
                 "limpiando-enaho (uv run python .claude/skills/limpiando-enaho/scripts/limpiar.py) y luego el mapa.")
    if not GEO.exists():
        sys.exit(f"FALTA EL GEOJSON: bájenlo a {GEO.relative_to(RAIZ)} desde {URL_GEO} "
                 "(o corran uv run python scripts/descargar_datos.py).")

    # ── 1. Indicador ponderado por departamento ──────────────────────────────────────────────
    h = pd.read_parquet(hog)
    dep = (h.assign(pw=h.pobre * h.peso_personas).groupby("departamento")
           .agg(pw=("pw", "sum"), w=("peso_personas", "sum")))
    dep["pobreza_pct"] = dep.pw / dep.w * 100
    dep = dep.reset_index()[["departamento", "pobreza_pct"]]

    # ── 2. Unir por código ───────────────────────────────────────────────────────────────────
    geo = gpd.read_file(GEO)
    geo["FIRST_IDDP"] = geo["FIRST_IDDP"].astype(str).str.zfill(2)    # antes: '1' o '01' → después: '01'
    m = geo.merge(dep, left_on="FIRST_IDDP", right_on="departamento", how="left", validate="1:1")
    faltan = m[m.pobreza_pct.isna()].NOMBDEP.tolist()
    if len(m) != 25 or faltan or not {"07", "15"} <= set(m.FIRST_IDDP):
        sys.exit(f"ERROR EN LA UNIÓN: {len(m)} polígonos, sin dato: {faltan}. Revisen que las llaves sean texto.")

    # ── 3. Comparar con la referencia de la sesión 16 ────────────────────────────────────────
    ref = pd.read_csv(RAIZ / "referencias" / "pobreza_departamento_2024.csv", dtype={"ccdd": str})
    comp = ref.merge(dep, left_on="ccdd", right_on="departamento", validate="1:1")
    comp = comp.rename(columns={"pobreza_pct_x": "referencia_pct", "pobreza_pct_y": "calculado_pct"})
    comp["diferencia_pp"] = (comp.calculado_pct - comp.referencia_pct).round(3)
    comp[["ccdd", "departamento_x", "referencia_pct", "calculado_pct", "diferencia_pp"]].rename(
        columns={"departamento_x": "departamento"}).to_csv(SALIDAS / "comparacion_mapa.csv", index=False)
    dmax = comp.diferencia_pp.abs().max()

    # ── 4. Dibujar ───────────────────────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(7.5, 9), facecolor=FONDO)
    vmax = 50
    m.plot(column="pobreza_pct", cmap=AZULES, vmin=0, vmax=vmax, edgecolor="white", linewidth=0.6, ax=ax,
           legend=True, legend_kwds={"label": "% de personas en pobreza monetaria", "shrink": 0.55,
                                     "orientation": "vertical"})
    for _, f in m.iterrows():
        if f.FIRST_IDDP == "07":
            continue                                   # el Callao es muy pequeño: va en la nota
        x, y = f.geometry.representative_point().coords[0]
        oscuro = f.pobreza_pct / vmax > 0.45
        ax.text(x, y, coma(f.pobreza_pct), ha="center", va="center", fontsize=7,
                color="white" if oscuro else TXT)
    ax.set_axis_off()
    top = m.sort_values("pobreza_pct", ascending=False).head(3)
    nombres = ", ".join(n.title() for n in top.NOMBDEP[:2]) + " y " + top.NOMBDEP.iloc[2].title()
    fig.suptitle(f"{nombres} tienen la pobreza más alta del país", x=0.02, ha="left", fontsize=12,
                 fontweight="bold", color=TXT)
    ax.set_title("Pobreza monetaria por departamento, Perú 2024 (% de personas)", loc="left", fontsize=9, color=TXT2)
    callao = m.loc[m.FIRST_IDDP == "07", "pobreza_pct"].iloc[0]
    fig.text(0.02, 0.015, f"Callao: {coma(callao)} % (no rotulado por su tamaño). Lima incluye Lima Metropolitana y "
             f"Lima Provincias.\nFuente: INEI, ENAHO 2024 (módulos 34 y 02), ponderado con factor07 × mieperho. "
             f"Límites: repositorio del curso.", fontsize=7, color=TXT2)
    MAPAS.mkdir(exist_ok=True)
    ruta = MAPAS / "pobreza_departamento_2024.png"
    fig.savefig(ruta, dpi=200, facecolor=FONDO, bbox_inches="tight")
    plt.close(fig)

    print(f"{ruta.relative_to(RAIZ)}: 25 departamentos unidos por código, Lima y Callao separados.")
    print(f"Comparación con la referencia de la sesión 16: diferencia máxima {dmax:.2f} pp "
          f"({'coincide' if dmax <= 0.1 else 'REVISAR'}). Detalle en salidas/comparacion_mapa.csv")
    for _, f in m.sort_values("pobreza_pct", ascending=False).iterrows():
        print(f"  {f.FIRST_IDDP} {f.NOMBDEP.title()}: {coma(f.pobreza_pct, 2)} %")


if __name__ == "__main__":
    main()
