"""Experimento: las mismas 10 preguntas a Claude Code sin y con el MCP del BCRP y las Skills de la ENAHO.

    uv run python evaluacion/evaluar.py                     # modos A y B, con Sonnet
    uv run python evaluacion/evaluar.py --modos B --ids pobreza_2024

Basado en evaluar.py de la sesión 04. Cada pregunta se hace en una sesión nueva de `claude -p`
(--no-session-persistence), con el mismo modelo y la misma instrucción. Se guarda la salida completa
(stream-json) de cada corrida en evidencias_ia/evaluacion/ y el resumen en evaluacion/resultados.csv.

Modo A: sin MCP ni Skills ni herramientas (solo la respuesta estructurada), en una carpeta vacía fuera del
        repositorio: no puede leer archivos con respuestas ya calculadas.
Modo B: en tarea_4/, con el MCP del BCRP (.mcp.json) y las Skills del proyecto, más Bash, Read, Glob, Grep y
        Skill para correrlas. En ambos: sin WebSearch ni WebFetch, y --strict-mcp-config (ningún otro MCP).
"""
# ── Paquetes ─────────────────────────────────────────────────────────────────────────────────
import argparse
import json
import subprocess          # lanzar claude -p
import sys
import tempfile            # carpeta vacía para el modo A
import time
from concurrent.futures import ThreadPoolExecutor   # 2 preguntas a la vez (son llamadas de red, no cómputo)
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent          # tarea_4/
EVID = RAIZ / "evidencias_ia" / "evaluacion"
ESQUEMA = {"type": "object", "required": ["valor", "fuente"],
           "properties": {"valor": {"type": ["number", "null"]}, "unidad": {"type": "string"},
                          "fuente": {"type": "string"}}}
INSTRUCCION = ("Responde con un solo número en «valor», en la unidad que pide la pregunta. Si no puedes saberlo "
               "con certeza, pon valor null: no estimes. En «fuente» di de dónde sale la cifra (código de serie, "
               "archivo o cálculo).\n\n")
VACIA = Path(tempfile.gettempdir()) / "tarea4_modoA_vacia"
MODOS = {
    "A": {"cwd": VACIA, "args": ["--tools", "", "--strict-mcp-config"]},
    "B": {"cwd": RAIZ, "args": ["--tools", "Bash,Read,Glob,Grep,Skill", "--strict-mcp-config",
                                "--mcp-config", str(RAIZ / ".mcp.json"),
                                "--allowedTools", "mcp__bcrp,Bash,Read,Glob,Grep,Skill"]},
}


def preguntar(q, modo, modelo):
    cmd = ["claude", "-p", INSTRUCCION + q.pregunta, "--output-format", "stream-json", "--verbose",
           "--json-schema", json.dumps(ESQUEMA), "--no-session-persistence", "--model", modelo,
           *MODOS[modo]["args"]]
    t = time.time()
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=900, cwd=MODOS[modo]["cwd"])
        crudo = proc.stdout.decode("utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        crudo = ""
    segundos = round(time.time() - t, 1)
    (EVID / f"{modo}_{q.id}.jsonl").write_text(crudo, encoding="utf-8")

    herramientas, skills, final, error = [], [], {}, ""
    for linea in crudo.splitlines():
        try:
            d = json.loads(linea)
        except json.JSONDecodeError:
            continue
        if d.get("type") == "assistant":
            for c in d["message"].get("content", []):
                if c.get("type") == "tool_use" and c.get("name") != "StructuredOutput":
                    herramientas.append(c["name"])
                    if c["name"] == "Skill":
                        skills.append(str(c.get("input", {}).get("skill", "")))
        if d.get("type") == "result":
            final = d
    r = final.get("structured_output") or {}
    if not final:
        error = "sin respuesta (tiempo agotado o error)"
    elif final.get("is_error"):
        error = str(final.get("result", ""))[:200]
    return {"valor": r.get("valor"), "fuente": r.get("fuente", ""), "segundos": segundos,
            "turnos": final.get("num_turns"), "herramientas": ";".join(dict.fromkeys(herramientas)),
            "skills": ";".join(dict.fromkeys(skills)), "costo_usd": final.get("total_cost_usd"), "error": error}


def calificar(valor, verdad, tol):
    if valor is None:
        return "no responde"
    return "correcta" if abs(float(valor) - verdad) <= tol else "incorrecta"


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser()
    p.add_argument("--modos", nargs="+", default=["A", "B"], choices=list(MODOS))
    p.add_argument("--modelo", default="sonnet")
    p.add_argument("--ids", nargs="*")
    p.add_argument("--paralelo", type=int, default=2)
    a = p.parse_args()
    VACIA.mkdir(exist_ok=True)
    EVID.mkdir(parents=True, exist_ok=True)

    preguntas = pd.read_csv(RAIZ / "evaluacion" / "preguntas.csv")
    if a.ids:
        preguntas = preguntas[preguntas.id.isin(a.ids)]
    casos = [(q, m) for m in a.modos for q in preguntas.itertuples()]
    print(f"{len(casos)} llamadas a claude -p con {a.modelo}...", flush=True)
    with ThreadPoolExecutor(a.paralelo) as ex:
        respuestas = list(ex.map(lambda c: preguntar(c[0], c[1], a.modelo), casos))

    filas = [{"id": q.id, "tipo": q.tipo, "modo": m, "pregunta": q.pregunta, "esperada": q.verdad,
              "tolerancia": q.tolerancia, "unidad": q.unidad, **r,
              "resultado": calificar(r["valor"], q.verdad, q.tolerancia), "modelo": a.modelo}
             for (q, m), r in zip(casos, respuestas)]
    nuevo = pd.DataFrame(filas)
    archivo = RAIZ / "evaluacion" / "resultados.csv"
    if archivo.exists() and a.ids:      # corrida parcial: reemplaza solo esas filas
        viejo = pd.read_csv(archivo)
        viejo = viejo[~(viejo.id.isin(nuevo.id) & viejo.modo.isin(nuevo.modo))]
        nuevo = pd.concat([viejo, nuevo], ignore_index=True)
    nuevo.to_csv(archivo, index=False, encoding="utf-8")

    print(nuevo.pivot(index="id", columns="modo", values="resultado").to_string())
    tabla = nuevo.groupby("modo").resultado.value_counts().unstack(fill_value=0)
    tabla["segundos_promedio"] = nuevo.groupby("modo").segundos.mean().round(1)
    print("\n" + tabla.to_string())
