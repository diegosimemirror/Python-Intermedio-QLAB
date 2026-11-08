"""Cruce BCRP × ENAHO 2024 y contraste con Trivelli y Mendoza (2026), DT IEP 309.

Entradas:
  - Valores BCRP: se piden en cada ejecución al servidor MCP `bcrp` (serie y valor_real), en el mismo proceso
    (escrito por el agente el 2026-11-08 con constantes copiadas; corregido en la verificación).
  - salidas/indicadores.csv y salidas/hogares_2024.parquet: Skill `limpiando-enaho` (INEI, ENAHO 2024).
  - referencias/contraste_dt309.csv: cifras publicadas (solo para contrastar).

Salidas:
  - salidas/cruce.csv
  - salidas/contraste_dt309_resultado.csv

Uso: uv run python scripts/cruce_y_contraste.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
API = "https://estadisticas.bcrp.gob.pe/estadisticas/series/api"

# --- Valores del BCRP: se piden al servidor MCP `bcrp` en cada ejecución (antes: copiados a mano) ------------
# El script carga mcp/server.py y llama a sus herramientas con el cliente de FastMCP, igual que Claude Code.
import asyncio
sys.path.insert(0, str(RAIZ / "mcp"))
from fastmcp import Client          # cliente MCP en el mismo proceso
from server import mcp as servidor_bcrp

PEDIDOS_SERIE = [("PN38705PM", "2006-12"), ("PN38705PM", "2024-12"), ("PN38705PM", "2026-08"),
                 ("PN38705PM", "2026-10"), ("PN39445PM", "2006-12"), ("PN39445PM", "2024-12"),
                 ("PN39445PM", "2026-10"), ("PN38706PM", "2006-12"), ("PN38706PM", "2026-10"),
                 ("PN01273PM", "2024-12"), ("PN01273PM", "2026-10"), ("PN09822PM", "2024-12"),
                 ("PN09822PM", "2026-10"), ("PN09823PM", "2026-10")]
PEDIDOS_VALOR_REAL = {
    "juntos_100_ago2026_en_dic2006": (100, "2026-08", "2006-12", "PN38705PM"),
    "juntos_100_oct2026_en_dic2006": (100, "2026-10", "2006-12", "PN38705PM"),
    "juntos_100_oct2026_en_dic2006_alimentos": (100, "2026-10", "2006-12", "PN39445PM"),
    "juntos_mediana_enaho_dic2024_en_dic2006": (1202 / 12, "2024-12", "2006-12", "PN38705PM"),
}


async def _pedir_al_mcp():
    bcrp, vreal = {}, {}
    async with Client(servidor_bcrp) as c:
        for cod, mes in PEDIDOS_SERIE:
            r = (await c.call_tool("serie", {"codigo": cod, "desde": mes, "hasta": mes})).data
            bcrp[(cod, mes)] = r["datos"][0]["valor"]
        for clave, (monto, desde, hasta, cod) in PEDIDOS_VALOR_REAL.items():
            r = (await c.call_tool("valor_real", {"monto": monto, "desde": desde, "hasta": hasta,
                                                  "codigo_ipc": cod})).data
            vreal[clave] = (r["valor"], cod, f"{desde} → {hasta}")
    return bcrp, vreal


BCRP, VALOR_REAL = asyncio.run(_pedir_al_mcp())
ULTIMO_MES = "2026-10"


def url(codigo: str, desde: str, hasta: str) -> str:
    return f"{API}/{codigo}/json/{desde}/{hasta}"


def ind(tabla: pd.DataFrame, indicador: str, grupo: str) -> float:
    fila = tabla[(tabla["indicador"] == indicador) & (tabla["grupo"] == grupo)]
    if len(fila) != 1:
        raise KeyError(f"No encuentro {indicador} / {grupo} en indicadores.csv")
    return float(fila["valor"].iloc[0])


def media_ponderada(x: pd.Series, w: pd.Series) -> float:
    return float(np.average(x, weights=w))


def mediana_ponderada(x: pd.Series, w: pd.Series) -> float:
    orden = np.argsort(x.to_numpy())
    xs, ws = x.to_numpy()[orden], w.to_numpy()[orden]
    acum = np.cumsum(ws)
    return float(xs[np.searchsorted(acum, acum[-1] / 2)])


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # la consola de Windows (cp1252) no imprime «→»
    tabla =pd.read_csv(RAIZ / "salidas" / "indicadores.csv", dtype={"grupo": str})
    hog = pd.read_parquet(RAIZ / "salidas" / "hogares_2024.parquet")
    filas = []

    def agregar(nombre, valor, unidad, fuente):
        filas.append({"indicador": nombre, "valor": round(valor, 4), "unidad": unidad, "fuente": fuente})

    enaho = "INEI, ENAHO 2024 (módulos 34 y 02), salidas/indicadores.csv"

    # 1. Poder de compra de los S/ 100 de Juntos -------------------------------------------------------------
    for clave, (valor, cod, per) in VALOR_REAL.items():
        agregar(clave, valor, "soles de dic. 2006", f"BCRP {cod}, valor_real {per}")
    agregar("perdida_poder_compra_ago2026", 100 - VALOR_REAL["juntos_100_ago2026_en_dic2006"][0],
            "% del valor de 2006", "BCRP PN38705PM, 2006-12 y 2026-08")
    agregar("perdida_poder_compra_oct2026", 100 - VALOR_REAL["juntos_100_oct2026_en_dic2006"][0],
            "% del valor de 2006", "BCRP PN38705PM, 2006-12 y 2026-10")
    agregar("perdida_poder_compra_oct2026_en_alimentos",
            100 - VALOR_REAL["juntos_100_oct2026_en_dic2006_alimentos"][0],
            "% del valor de 2006", "BCRP PN39445PM, 2006-12 y 2026-10")

    # 2. Alimentos frente al resto de precios (2006-12 → 2026-10) ---------------------------------------------
    var = {}
    for cod in ("PN38705PM", "PN39445PM", "PN38706PM"):
        var[cod] = (BCRP[(cod, ULTIMO_MES)] / BCRP[(cod, "2006-12")] - 1) * 100
        agregar(f"variacion_acumulada_{cod}", var[cod], "% 2006-12 → 2026-10",
                url(cod, "2006-12", ULTIMO_MES))
    rel = ((1 + var["PN39445PM"] / 100) / (1 + var["PN38706PM"] / 100) - 1) * 100
    agregar("precio_relativo_alimentos_vs_resto", rel, "% (alimentos / sin alimentos) 2006-12 → 2026-10",
            "BCRP PN39445PM y PN38706PM")

    # 3. Juntos en la ENAHO 2024 ------------------------------------------------------------------------------
    juntos_anual = ind(tabla, "monto_anual_mediano", "Juntos")
    agregar("juntos_mediana_anual_enaho", juntos_anual, "soles al año", enaho + " (sin ponderar)")
    agregar("juntos_mediana_mensual_enaho", juntos_anual / 12, "soles al mes", enaho + " (anual / 12)")
    rec = hog[hog["juntos_anual"] > 0]
    agregar("juntos_mediana_anual_ponderada_factor07", mediana_ponderada(rec["juntos_anual"], rec["factor07"]),
            "soles al año", "INEI, ENAHO 2024, hogares_2024.parquet (sensibilidad, factor07)")
    agregar("juntos_hogares_receptores_muestra", len(rec), "hogares (sin ponderar)", "hogares_2024.parquet")
    for q in (0.05, 0.95):
        agregar(f"juntos_monto_anual_p{int(q * 100):02d}", rec["juntos_anual"].quantile(q),
                "soles al año (sin ponderar)", "hogares_2024.parquet (dispersión del monto declarado)")

    # 4. Aporte de los alimentos al alza del costo de vida (último mes) ------------------------------------------
    inf_alim = BCRP[("PN09822PM", ULTIMO_MES)]
    inf_resto = BCRP[("PN09823PM", ULTIMO_MES)]
    for grupo in ("Pobres", "No pobres"):
        s = ind(tabla, "share_gasto_alimentos", grupo) / 100
        aporte = s * inf_alim
        total = aporte + (1 - s) * inf_resto
        g = grupo.lower().replace(" ", "_")
        agregar(f"aporte_alimentos_{g}", aporte, "puntos porcentuales",
                f"share ENAHO 2024 × PN09822PM {ULTIMO_MES}")
        agregar(f"inflacion_implicita_{g}", total, "% 12 meses",
                f"share ENAHO 2024 con PN09822PM y PN09823PM {ULTIMO_MES}")
        agregar(f"peso_alimentos_en_alza_{g}", aporte / total * 100, "% del alza",
                "aporte_alimentos / inflacion_implicita")
        # mismo ejercicio con la variación acumulada 2006-12 → 2026-10 (canasta fija de 2024)
        ap_acum = s * var["PN39445PM"]
        tot_acum = ap_acum + (1 - s) * var["PN38706PM"]
        agregar(f"alza_acumulada_implicita_{g}", tot_acum, "% 2006-12 → 2026-10",
                "share ENAHO 2024 con PN39445PM y PN38706PM")
        agregar(f"peso_alimentos_en_alza_acumulada_{g}", ap_acum / tot_acum * 100, "% del alza",
                "share ENAHO 2024 con PN39445PM y PN38706PM")
        agregar(f"juntos_100_oct2026_en_dic2006_canasta_{g}", 100 / (1 + tot_acum / 100), "soles de dic. 2006",
                "S/ 100 deflactados con el alza acumulada de la canasta (participación ENAHO 2024 fija)")

    # 5. ¿A quién llega Juntos? (complemento, ponderado con peso_personas) ---------------------------------------
    hog = hog.assign(recibe=hog["juntos_anual"] > 0, pobre_b=hog["pobre"].astype(bool),
                     extremo_b=hog["pobre_extremo"].astype(bool), menor5=hog["con_menor_5"].astype(bool))
    w = hog["peso_personas"]
    cob = {
        "Pobres": hog["pobre_b"],
        "Pobres extremos": hog["extremo_b"],
        "Pobres con menores de 5": hog["pobre_b"] & hog["menor5"],
        "Pobres urbanos": hog["pobre_b"] & (hog["area"] == "Urbano"),
        "Pobres rurales": hog["pobre_b"] & (hog["area"] == "Rural"),
        "No pobres": ~hog["pobre_b"],
    }
    for nombre, m in cob.items():
        agregar(f"cobertura_juntos: {nombre}", media_ponderada(hog.loc[m, "recibe"], w[m]) * 100,
                "% de personas en hogares que reciben Juntos", "hogares_2024.parquet, peso_personas")
    m = hog["recibe"]
    agregar("pobres_entre_receptores_juntos", media_ponderada(hog.loc[m, "pobre_b"], w[m]) * 100,
            "% de personas en hogares Juntos que son pobres", "hogares_2024.parquet, peso_personas")
    agregar("pobres_en_hogares_con_menor5", (w[hog["pobre_b"] & hog["menor5"]].sum() / w[hog["pobre_b"]].sum())
            * 100, "% de los pobres", "hogares_2024.parquet, peso_personas")

    cruce = pd.DataFrame(filas)
    cruce.to_csv(RAIZ / "salidas" / "cruce.csv", index=False, encoding="utf-8")
    print("CRUCE (salidas/cruce.csv)")
    print(cruce.to_string(index=False))

    # 6. Contraste con el DT 309 -------------------------------------------------------------------------------
    ref = pd.read_csv(RAIZ / "referencias" / "contraste_dt309.csv")

    def pub(indicador, grupo, anio):
        f = ref[(ref["indicador"] == indicador) & (ref["grupo"] == grupo) & (ref["anio"] == anio)]
        r = f.iloc[0]
        return float(r["valor"]), f"{r['fuente_original']}; {r['citado_en']}, p. {r['pagina']}"

    pares = [
        # (etiqueta, valor informe, fuente informe, (indicador, grupo, año) publicado, comparable)
        ("Pobreza nacional 2024 (%)", ind(tabla, "pobreza", "Nacional"), "ENAHO 2024, pobreza/Nacional",
         ("pobreza", "Nacional", 2024), "sí"),
        ("Pobreza urbana 2024 (%)", ind(tabla, "pobreza", "Urbano"), "ENAHO 2024, pobreza/Urbano",
         ("pobreza", "Urbano", 2024), "sí"),
        ("Pobreza rural 2024 (%)", ind(tabla, "pobreza", "Rural"), "ENAHO 2024, pobreza/Rural",
         ("pobreza", "Rural", 2024), "sí"),
        ("Pobreza extrema nacional 2024 (%)", ind(tabla, "pobreza_extrema", "Nacional"),
         "ENAHO 2024, pobreza_extrema/Nacional", ("pobreza_extrema", "Nacional", 2024), "sí"),
        ("Pobreza extrema rural 2024 (%)", ind(tabla, "pobreza_extrema", "Rural"),
         "ENAHO 2024, pobreza_extrema/Rural", ("pobreza_extrema", "Rural", 2024), "sí"),
        ("Pobreza extrema Lima Metropolitana 2024 (%)", ind(tabla, "pobreza_extrema", "Lima Metropolitana"),
         "ENAHO 2024, pobreza_extrema/Lima Metropolitana", ("pobreza_extrema", "Lima Metropolitana", 2024), "sí"),
        ("Brecha de pobreza FGT1 2024 (% de la línea)", ind(tabla, "brecha_pobreza_fgt1", "Nacional"),
         "ENAHO 2024, brecha_pobreza_fgt1/Nacional", ("brecha_pobreza_fgt1", "Nacional", 2024), "sí"),
        ("IPC Lima dic-2006 (dic. 2021 = 100)", BCRP[("PN38705PM", "2006-12")], "BCRP PN38705PM, 2006-12",
         ("ipc_lima_indice", "dic-2006", 2006), "sí"),
        ("IPC Lima ago-2026 (dic. 2021 = 100)", BCRP[("PN38705PM", "2026-08")], "BCRP PN38705PM, 2026-08",
         ("ipc_lima_indice", "ago-2026", 2026), "sí"),
        ("S/ 100 de Juntos (ago-2026) en soles de dic-2006", VALOR_REAL["juntos_100_ago2026_en_dic2006"][0],
         "BCRP PN38705PM, valor_real 2026-08 → 2006-12",
         ("juntos_valor_real", "S/ 100 de 2026 en soles de 2006", 2026), "sí"),
        ("Hogares con Juntos (miles)", ind(tabla, "hogares_receptores", "Juntos"),
         "ENAHO 2024, hogares_receptores/Juntos (factor07)", ("juntos_hogares_usuarios", "Nacional", 2026),
         "no: 2024 encuesta vs. 2026 padrón"),
        ("No pobre vulnerable (%)", ind(tabla, "condicion_vulnerabilidad", "No pobre vulnerable"),
         "ENAHO 2024, condicion_vulnerabilidad", ("no_pobre_vulnerable", "Nacional", 2025),
         "no: 2024 vs. 2025"),
        ("Canasta básica alimentaria / línea extrema (S/ por persona al mes)",
         ind(tabla, "linea_pobreza_extrema", "Nacional"), "ENAHO 2024, linea_pobreza_extrema (promedio de linpe)",
         ("canasta_basica_alimentaria", "Nacional", 2025), "no: 2024 vs. 2025"),
    ]
    contraste = []
    for etiqueta, mio, fuente_mia, clave, comparable in pares:
        publicado, fuente_pub = pub(*clave)
        contraste.append({
            "cifra": etiqueta, "informe": round(mio, 3), "fuente_informe": fuente_mia,
            "publicado": publicado, "anio_publicado": clave[2], "fuente_publicada": fuente_pub,
            "diferencia": round(mio - publicado, 3),
            "diferencia_pct": round((mio - publicado) / publicado * 100, 2), "comparable": comparable,
        })
    contraste = pd.DataFrame(contraste)
    contraste.to_csv(RAIZ / "salidas" / "contraste_dt309_resultado.csv", index=False, encoding="utf-8")
    print("\nCONTRASTE (salidas/contraste_dt309_resultado.csv)")
    print(contraste[["cifra", "informe", "publicado", "anio_publicado", "diferencia", "diferencia_pct",
                     "comparable"]].to_string(index=False))


if __name__ == "__main__":
    main()
