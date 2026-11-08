"""Limpia la ENAHO 2024 (módulos 34 y 02), une personas y hogares, construye indicadores y valida.

    uv run python .claude/skills/limpiando-enaho/scripts/limpiar.py            # desde la carpeta tarea_4/

Entra:  datos/966-Modulo34.zip y datos/966-Modulo02.zip (INEI, código 966 = ENAHO 2024)
Sale:   salidas/personas_2024.parquet, salidas/hogares_2024.parquet,
        salidas/indicadores.csv y salidas/validacion.txt
Si una validación esencial falla, escribe validacion.txt con el detalle y termina con error (código 1).
"""
# ── Paquetes ─────────────────────────────────────────────────────────────────────────────────
import sys
import zipfile                 # sacar los .dta de los zip del INEI
from pathlib import Path

import numpy as np             # máscaras y brecha de pobreza
import pandas as pd            # lectura de Stata, uniones y promedios ponderados

RAIZ = Path.cwd()
DATOS, SALIDAS = RAIZ / "datos", RAIZ / "salidas"
LLAVES = ["conglome", "vivienda", "hogar"]
REF = {"pobreza": 27.6, "residentes": 108_664, "urbano": 24.8, "rural": 39.3, "departamentos": 25}
TOL = 0.1   # puntos porcentuales

# ── 1. Leer ──────────────────────────────────────────────────────────────────────────────────
def extraer(zip_nombre, dta):
    """Antes: el zip del INEI → después: la ruta del .dta extraído en datos/."""
    z = DATOS / zip_nombre
    destino = DATOS / dta
    if not destino.exists():
        if not z.exists():
            sys.exit(f"ERROR: falta {z}. Bájenlo de https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/{zip_nombre}")
        with zipfile.ZipFile(z) as f:
            f.extract(dta, DATOS)
    return destino


def leer(ruta, columnas=None):
    """Lee Stata sin convertir etiquetas; nombres en minúscula (antes: 'aÑo', 'P204' → después: 'año', 'p204');
    llaves como texto para no perder ceros iniciales."""
    df = pd.read_stata(ruta, convert_categoricals=False, columns=columnas)
    df.columns = [c.lower() for c in df.columns]
    for k in LLAVES + ["codperso", "ubigeo"]:
        if k in df.columns:
            df[k] = df[k].astype(str).str.strip()
    return df


def pct(mascara, peso):
    return float(peso[mascara].sum() / peso.sum() * 100)


def main():
    sys.stdout.reconfigure(encoding="utf-8")   # la consola de Windows no es UTF-8
    SALIDAS.mkdir(exist_ok=True)
    chequeos = []   # (nombre, ok, detalle, esencial)

    def chequear(nombre, ok, detalle, esencial=True):
        chequeos.append((nombre, bool(ok), detalle, esencial))

    s = leer(extraer("966-Modulo34.zip", "966-Modulo34/sumaria-2024.dta"))
    p = leer(extraer("966-Modulo02.zip", "966-Modulo02/enaho01-2024-200.dta"),
             ["conglome", "vivienda", "hogar", "codperso", "ubigeo", "dominio", "estrato", "p203", "p204", "p205",
              "p206", "p207", "p208a", "facpob07"])

    # ── 2. Hogares: tipos y variables derivadas ──────────────────────────────────────────────
    chequear("Llaves de hogar únicas en la sumaria", not s.duplicated(LLAVES).any(), f"{len(s):,} hogares")
    # antes: mieperho int8 (12 × 11 = 132 desborda a −124) → después: decimal
    s["mieperho"] = s["mieperho"].astype(float)
    s["peso_personas"] = s["factor07"] * s["mieperho"]
    s["gasto_pc_mes"] = s["gashog2d"] / (12 * s["mieperho"])
    s["departamento"] = s["ubigeo"].str[:2]
    s["urbano"] = s["estrato"] <= 5
    s["area"] = np.where(s["urbano"], "Urbano", "Rural")
    s["pobre"] = s["pobreza"] <= 2
    s["pobre_extremo"] = s["pobreza"] == 1
    s["lima_metropolitana"] = s["dominio"] == 8
    alimentos = [c for c in s.columns if c.startswith("gru1")]          # grupo 1: alimentos (dentro y fuera)
    s["gasto_alimentos"] = s[alimentos].fillna(0).sum(axis=1)
    s["share_alimentos"] = s["gasto_alimentos"] / s["gashog2d"]
    s["juntos_anual"] = s["ingtpu01"].fillna(0)
    s["pension65_anual"] = s["ingtpu03"].fillna(0)

    regla = np.where(s.gasto_pc_mes < s.linpe, 1, np.where(s.gasto_pc_mes < s.linea, 2, 3))
    chequear("La regla gasto per cápita < línea reproduce 'pobreza'", (regla == s.pobreza).mean() == 1,
             f"coincide en {100 * (regla == s.pobreza).mean():.2f} % de los hogares")
    # en sumaria-2024.dta gru1* es solo el grupo 1 (alimentos); los grupos 10-12 existen solo en sumaria-2024-12g
    ok_ali = (s.gasto_alimentos <= s.gashog2d + 1).all() and s.share_alimentos.between(0, 1).all()
    chequear("Gasto en alimentos (grupo 1) entre 0 y el gasto total en todos los hogares", ok_ali,
             f"{len(alimentos)} variables gru1*; mediana del share = {s.share_alimentos.median():.3f}; "
             f"{int((~s.share_alimentos.between(0, 1)).sum())} hogares fuera de [0, 1]", esencial=False)

    # ── 3. Personas: residentes habituales ───────────────────────────────────────────────────
    chequear("Llaves de persona únicas en el módulo 02", not p.duplicated(LLAVES + ["codperso"]).any(),
             f"{len(p):,} filas")
    residente = ((p.p204 == 1) & (p.p205 == 2)) | ((p.p204 == 2) & (p.p206 == 1))
    p = p[residente].copy()
    chequear("Residentes habituales = 108,664", len(p) == REF["residentes"], f"{len(p):,} personas")
    p["mujer"] = p.p207 == 2
    p["sexo"] = np.where(p.mujer, "Mujer", "Hombre")
    p["edad"] = p.p208a

    # características del hogar que salen de sus miembros
    jefe = p.loc[p.p203 == 1, LLAVES + ["p207"]].rename(columns={"p207": "sexo_jefe"})
    chequear("Un jefe de hogar por hogar", not jefe.duplicated(LLAVES).any(), f"{len(jefe):,} jefes", esencial=False)
    hog_p = (p.assign(con_menor_5=p.edad < 5, con_adulto_65=p.edad >= 65)
             .groupby(LLAVES, as_index=False)[["con_menor_5", "con_adulto_65"]].max())
    s = s.merge(hog_p, on=LLAVES, how="left", validate="1:1").merge(jefe, on=LLAVES, how="left", validate="1:1")
    s["jefatura"] = s["sexo_jefe"].map({1: "Masculina", 2: "Femenina"})

    # ── 4. Unir personas (m) con hogares (1) ─────────────────────────────────────────────────
    cols_h = LLAVES + ["pobreza", "pobre", "pobre_extremo", "linea", "linpe", "gasto_pc_mes", "mieperho",
                       "factor07", "departamento", "urbano", "area", "lima_metropolitana", "share_alimentos",
                       "con_menor_5", "con_adulto_65", "jefatura"]
    antes = len(p)
    per = p.drop(columns=["ubigeo", "dominio", "estrato"]).merge(
        s[cols_h], on=LLAVES, how="left", validate="m:1", indicator=True)
    chequear("La unión m:1 no pierde ni duplica personas", len(per) == antes, f"{antes:,} → {len(per):,}")
    sin_hogar = int((per["_merge"] != "both").sum())
    chequear("Toda persona encuentra su hogar", sin_hogar == 0, f"{sin_hogar} sin hogar")
    per = per.drop(columns="_merge")
    chequear("Factor facpob07 sin nulos ni ceros", per.facpob07.notna().all() and (per.facpob07 > 0).all(),
             f"suma = {per.facpob07.sum() / 1e6:.2f} millones de personas")
    chequear("Factor factor07 sin nulos ni ceros", s.factor07.notna().all() and (s.factor07 > 0).all(),
             f"suma = {s.factor07.sum() / 1e6:.2f} millones de hogares; "
             f"factor07×mieperho = {s.peso_personas.sum() / 1e6:.2f} millones de personas")

    # ── 5. Validar contra el INEI ────────────────────────────────────────────────────────────
    w = s.peso_personas
    pob_h = pct(s.pobre, w)
    pob_p = pct(per.pobre, per.facpob07)
    chequear("Pobreza nacional (sumaria, factor07×mieperho) a ±0,1 de 27,6 %", abs(pob_h - REF["pobreza"]) <= TOL,
             f"{pob_h:.2f} %")
    chequear("Pobreza nacional (personas, facpob07) a ±0,1 de 27,6 %", abs(pob_p - REF["pobreza"]) <= TOL,
             f"{pob_p:.2f} %")
    urb, rur = pct(s.pobre[s.urbano], w[s.urbano]), pct(s.pobre[~s.urbano], w[~s.urbano])
    chequear("Pobreza urbana a ±0,1 de 24,8 %", abs(urb - REF["urbano"]) <= TOL, f"{urb:.2f} %")
    chequear("Pobreza rural a ±0,1 de 39,3 %", abs(rur - REF["rural"]) <= TOL, f"{rur:.2f} %")
    deps = sorted(s.departamento.unique())
    chequear("25 códigos de departamento (01 a 25)", deps == [f"{i:02d}" for i in range(1, 26)],
             f"{len(deps)} códigos: {deps[0]} … {deps[-1]}")
    ref = pd.read_csv(RAIZ / "referencias" / "pobreza_departamento_2024.csv", dtype={"ccdd": str})
    dep = s.groupby("departamento").apply(lambda g: pct(g.pobre, g.peso_personas), include_groups=False)
    dmax = (dep.reindex(ref.ccdd).values - ref.pobreza_pct.values).__abs__().max()
    chequear("Pobreza por departamento a ±0,1 de la referencia de la sesión 16", dmax <= TOL + 0.05,
             f"diferencia máxima {dmax:.2f} pp (la referencia está redondeada a 1 decimal)")

    # ── 6. Indicadores ───────────────────────────────────────────────────────────────────────
    fil = []

    def ind(indicador, grupo, valor, unidad, peso, nota=""):
        fil.append({"indicador": indicador, "grupo": grupo, "valor": round(float(valor), 4), "unidad": unidad,
                    "ponderador": peso, "nota": nota})

    WH = "factor07×mieperho"
    ind("pobreza", "Nacional", pob_h, "% de personas", WH)
    ind("pobreza", "Nacional (personas)", pob_p, "% de personas", "facpob07")
    ind("pobreza_extrema", "Nacional", pct(s.pobre_extremo, w), "% de personas", WH)
    for nombre, m in [("Urbano", s.urbano), ("Rural", ~s.urbano), ("Lima Metropolitana", s.lima_metropolitana)]:
        ind("pobreza", nombre, pct(s.pobre[m], w[m]), "% de personas", WH)
        ind("pobreza_extrema", nombre, pct(s.pobre_extremo[m], w[m]), "% de personas", WH)
    brecha = ((s.linea - s.gasto_pc_mes.clip(lower=0)) / s.linea).where(s.gasto_pc_mes < s.linea, 0)
    ind("brecha_pobreza_fgt1", "Nacional", (brecha * w).sum() / w.sum() * 100, "% de la línea", WH)
    pobres = w[s.pobre].sum()
    ind("pobres", "Nacional", pobres / 1e6, "millones de personas", WH)
    ind("distribucion_pobres", "Urbano", w[s.pobre & s.urbano].sum() / pobres * 100, "% de los pobres", WH)
    ind("distribucion_pobres", "Rural", w[s.pobre & ~s.urbano].sum() / pobres * 100, "% de los pobres", WH)
    ind("distribucion_pobres", "Lima Metropolitana", w[s.pobre & s.lima_metropolitana].sum() / pobres * 100,
        "% de los pobres", WH, "dominio 8: Lima Metropolitana y Callao")
    for k, nombre in {1: "Pobre extremo", 2: "Pobre no extremo", 3: "No pobre vulnerable",
                      4: "No pobre no vulnerable"}.items():
        ind("condicion_vulnerabilidad", nombre, pct(s.pobrezav == k, w), "% de personas", WH, "variable pobrezav")
    for sx in ["Hombre", "Mujer"]:
        m = per.sexo == sx
        ind("pobreza", f"Sexo: {sx}", pct(per.pobre[m], per.facpob07[m]), "% de personas", "facpob07")
    for col, si, no in [("con_menor_5", "Hogar con menores de 5 años", "Hogar sin menores de 5 años"),
                        ("con_adulto_65", "Hogar con adultos de 65+", "Hogar sin adultos de 65+")]:
        for valor, nombre in [(True, si), (False, no)]:
            m = s[col] == valor
            ind("pobreza", nombre, pct(s.pobre[m], w[m]), "% de personas", WH)
            ind("pobreza_extrema", nombre, pct(s.pobre_extremo[m], w[m]), "% de personas", WH)
    for j in ["Femenina", "Masculina"]:
        for area in ["Urbano", "Rural", None]:
            m = (s.jefatura == j) & ((s.area == area) if area else True)
            ind("pobreza", f"Jefatura {j.lower()}" + (f" ({area.lower()})" if area else ""),
                pct(s.pobre[m], w[m]), "% de personas", WH)
    for g, nombre in [(s.pobre, "Pobres"), (~s.pobre, "No pobres")]:
        ind("share_gasto_alimentos", nombre, (s.share_alimentos[g] * w[g]).sum() / w[g].sum() * 100,
            "% del gasto del hogar", WH, "grupo 1 (gru1*) / gashog2d, promedio ponderado")
    for cod, nombre in [("juntos_anual", "Juntos"), ("pension65_anual", "Pensión 65")]:
        rec = s[cod] > 0
        ind("hogares_receptores", nombre, s.factor07[rec].sum() / 1e3, "miles de hogares", "factor07",
            "ingtpu01" if nombre == "Juntos" else "ingtpu03")
        ind("monto_anual_mediano", nombre, s.loc[rec, cod].median(), "soles al año", "sin ponderar",
            "mediana entre hogares receptores")
    lineas = (s.linpe * w).sum() / w.sum()
    ind("linea_pobreza_extrema", "Nacional", lineas, "soles por persona al mes", WH, "promedio ponderado de linpe")
    ind("linea_pobreza", "Nacional", (s.linea * w).sum() / w.sum(), "soles por persona al mes", WH)
    for d, v in dep.items():
        ind("pobreza_departamento", d, v, "% de personas", WH)
    pd.DataFrame(fil).to_csv(SALIDAS / "indicadores.csv", index=False, encoding="utf-8")

    # ── 7. Guardar y escribir la validación ──────────────────────────────────────────────────
    fallas = [c for c in chequeos if c[3] and not c[1]]
    lineas_txt = ["VALIDACIÓN ENAHO 2024 (módulos 34 y 02)", "=" * 60]
    for nombre, ok, detalle, esencial in chequeos:
        marca = "APROBADA" if ok else ("FALLIDA " if esencial else "AVISO   ")
        lineas_txt.append(f"[{marca}] {nombre}: {detalle}")
    lineas_txt += ["=" * 60, f"Aprobadas: {sum(c[1] for c in chequeos)}/{len(chequeos)}. "
                   + ("RESULTADO: VÁLIDA" if not fallas else f"RESULTADO: NO VÁLIDA ({len(fallas)} esenciales fallaron)")]
    (SALIDAS / "validacion.txt").write_text("\n".join(lineas_txt) + "\n", encoding="utf-8")
    print("\n".join(lineas_txt))
    if fallas:
        sys.exit(1)       # no se guardan bases con errores
    per.to_parquet(SALIDAS / "personas_2024.parquet", index=False)
    extra = ["peso_personas", "pobrezav", "juntos_anual", "pension65_anual", "gashog2d", "dominio", "estrato",
             "ubigeo"]
    s[cols_h + extra].to_parquet(SALIDAS / "hogares_2024.parquet", index=False)
    print(f"\nGuardado: salidas/personas_2024.parquet ({len(per):,}), salidas/hogares_2024.parquet ({len(s):,}), "
          "salidas/indicadores.csv")


if __name__ == "__main__":
    main()
