"""Convierte la salida stream-json de `claude -p` en un Markdown legible (evidencia de la ejecución).

    uv run python scripts/jsonl_a_md.py evidencias_ia/integracion/ejecucion_agente.jsonl

Escribe el .md al lado del .jsonl: cada mensaje del agente, cada herramienta llamada (con sus argumentos) y un
extracto de cada resultado, más un resumen de las herramientas MCP y Skills usadas.
"""
import json
import sys
from collections import Counter
from pathlib import Path


def corto(x, n=1500):
    s = x if isinstance(x, str) else json.dumps(x, ensure_ascii=False, indent=1)
    return s if len(s) <= n else s[:n] + f"\n… ({len(s) - n} caracteres más)"


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    origen = Path(sys.argv[1])
    md, usos, skills = [f"# Ejecución del agente: {origen.name}", ""], Counter(), []
    for linea in origen.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            d = json.loads(linea)
        except json.JSONDecodeError:
            continue
        t = d.get("type")
        if t == "system" and d.get("subtype") == "init":
            md += [f"- Modelo: `{d.get('model')}` · Claude Code {d.get('claude_code_version')} · cwd `{d.get('cwd')}`",
                   f"- Servidores MCP: {', '.join(m['name'] + ' (' + m['status'] + ')' for m in d.get('mcp_servers', []))}",
                   f"- Skills del proyecto: {', '.join(s for s in d.get('skills', []) if 'enaho' in s)}", ""]
        elif t == "assistant":
            for c in d["message"].get("content", []):
                if c.get("type") == "text" and c["text"].strip():
                    md += ["### Agente", "", c["text"].strip(), ""]
                elif c.get("type") == "tool_use":
                    usos[c["name"]] += 1
                    if c["name"] == "Skill":
                        skills.append(c.get("input", {}).get("skill"))
                    md += [f"#### → Herramienta `{c['name']}`", "", "```json", corto(c.get("input", {}), 2500), "```", ""]
        elif t == "user":
            for c in d.get("message", {}).get("content", []):
                if isinstance(c, dict) and c.get("type") == "tool_result":
                    contenido = c.get("content")
                    if isinstance(contenido, list):
                        contenido = "\n".join(x.get("text", "") for x in contenido if isinstance(x, dict))
                    md += ["<details><summary>Resultado</summary>", "", "```", corto(contenido or ""), "```",
                           "", "</details>", ""]
        elif t == "result":
            md += ["---", f"**Resultado final:** {d.get('subtype')} · {d.get('num_turns')} turnos · "
                          f"{round((d.get('duration_ms') or 0) / 60000, 1)} min · US$ {d.get('total_cost_usd')}", ""]
    resumen = ["## Resumen de herramientas usadas", "", "| Herramienta | Veces |", "|---|---|"]
    resumen += [f"| `{k}` | {v} |" for k, v in usos.most_common()]
    resumen += ["", f"Skills invocadas: {', '.join(dict.fromkeys(s for s in skills if s)) or 'ninguna'}", ""]
    destino = origen.with_suffix(".md")
    destino.write_text("\n".join(md[:5] + resumen + md[5:]), encoding="utf-8")
    print(f"{destino} · " + ", ".join(f"{k}×{v}" for k, v in usos.most_common()))
