"""Respuestas esperadas de las 10 preguntas, calculadas SIN el servidor MCP ni las Skills.

    uv run python evaluacion/verificacion_independiente.py      # desde tarea_4/

Lee la ENAHO directamente de los .dta del INEI y las series directamente de la API del BCRP (otro código,
otro camino). Escribe evaluacion/respuestas_esperadas.csv. Se corrió y se guardó en Git ANTES de evaluar.
"""
import io
import json
import sys
import zipfile
from pathlib import Path

import httpx
import numpy as np
import pandas as pd

RAIZ = Path.cwd()
API = "https://estadisticas.bcrp.gob.pe/estadisticas/series/api"
MES = {"Ene": 1, "Feb": 2, "Mar": 3, "Abr": 4, "May": 5, "Jun": 6, "Jul": 7, "Ago": 8, "Sep": 9, "Set": 9,
       "Oct": 10, "Nov": 11, "Dic": 12}


def bcrp(codigo, desde, hasta):
    """Serie mensual del BCRP como {(año, mes): valor}, leyendo el JSON aunque traiga HTML pegado al final."""
    r = httpx.get(f"{API}/{codigo}/json/{desde}/{hasta}", timeout=60)
    texto = r.content.decode("latin-1")
    d = json.JSONDecoder().raw_decode(texto[texto.find("{"):])[0]
    out = {}
    for p in d["periods"]:
        m, a = p["name"].split(".")
        if p["values"][0] != "n.d.":
            out[(int(a), MES[m])] = float(p["values"][0])
    return out


def dta(zip_nombre, interno, cols=None):
    with zipfile.ZipFile(RAIZ / "datos" / zip_nombre) as z:
        df = pd.read_stata(io.BytesIO(z.read(interno)), convert_categoricals=False, columns=cols)
    df.columns = [c.lower() for c in df.columns]
    return df


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    R = {}
    # ── BCRP ──
    R["ipc_oct26"] = bcrp("PN01273PM", "2026-10", "2026-10")[(2026, 10)]
    R["alimentos_oct26"] = bcrp("PN09822PM", "2026-10", "2026-10")[(2026, 10)]
    ipc = bcrp("PN38705PM", "2006-12", "2026-10")
    R["juntos_real_2006"] = 100 * ipc[(2006, 12)] / ipc[(2026, 8)]
    R["pesca_may26"] = bcrp("PN01716AM", "2026-5", "2026-5")[(2026, 5)]

    # ── ENAHO (sumaria) ──
    s = dta("966-Modulo34.zip", "966-Modulo34/sumaria-2024.dta")
    s["mieperho"] = s.mieperho.astype(float)
    w = s.factor07 * s.mieperho
    pobre = s.pobreza <= 2
    rural = s.estrato > 5
    R["pobreza_2024"] = w[pobre].sum() / w.sum() * 100
    R["extrema_rural"] = w[rural & (s.pobreza == 1)].sum() / w[rural].sum() * 100
    R["pobres_urbanos"] = w[pobre & ~rural].sum() / w[pobre].sum() * 100
    dep = pd.DataFrame({"d": s.ubigeo.astype(str).str[:2], "p": pobre * w, "w": w}).groupby("d").sum()
    R["dep_mas_pobre"] = (dep.p / dep.w * 100).max()
    R["dep_mas_pobre_codigo"] = (dep.p / dep.w * 100).idxmax()

    # ── Mixtas ──
    juntos = s.loc[s.ingtpu01.fillna(0) > 0, "ingtpu01"].median() / 12        # soles por mes
    R["juntos_enaho_real_2006"] = juntos * ipc[(2006, 12)] / ipc[(2024, 12)]
    ali = [c for c in s.columns if c.startswith("gru1")]
    share = s[ali].fillna(0).sum(axis=1) / s.gashog2d
    share_pobres = (share[pobre] * w[pobre]).sum() / w[pobre].sum()
    R["aporte_alimentos_pobres"] = share_pobres * R["alimentos_oct26"]

    print(json.dumps(R, indent=1, ensure_ascii=False))
    pd.Series(R, name="valor").to_csv(RAIZ / "evaluacion" / "respuestas_esperadas.csv", index_label="id")
