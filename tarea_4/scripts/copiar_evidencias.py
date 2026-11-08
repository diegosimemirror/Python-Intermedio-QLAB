"""Copia la conversación de desarrollo (exportada a Markdown) a evidencias_ia/ ocultando datos sensibles.

    uv run python scripts/copiar_evidencias.py <conversacion.md> [<otra.md> ...]

Oculta correos, rutas del perfil de Windows, tokens y menciones a trabajo ajeno a la tarea. Escribe
evidencias_ia/conversacion_<nombre>.md y lista cuántos reemplazos hizo de cada tipo.
"""
import re
import sys
from pathlib import Path

DESTINO = Path.cwd() / "evidencias_ia"
REGLAS = [
    ("correo", re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "[correo oculto]"),
    ("token", re.compile(r"\b(?:ghp|gho|sk-ant|sk|xox[bp])[-_][A-Za-z0-9_-]{16,}\b"), "[token oculto]"),
    ("ruta de usuario", re.compile(r"C:[\\/]+Users[\\/]+(?:Diego Sime|DIEGOS~1)", re.I), r"C:\\Users\\[usuario]"),
    ("ruta de usuario", re.compile(r"/c/Users/(?:Diego Sime|DIEGOS~1)", re.I), "/c/Users/[usuario]"),
]
# Términos de otros trabajos del autor: se leen de un archivo local que no se sube a Git (scripts/ocultar_local.txt,
# un término por línea), para no publicar la lista misma.
_LOCAL = Path(__file__).with_name("ocultar_local.txt")
if _LOCAL.exists():
    _terminos = sorted({t.strip() for t in _LOCAL.read_text(encoding="utf-8").splitlines()
                        if t.strip() and not t.startswith("#")}, key=len, reverse=True)
    if _terminos:
        REGLAS.append(("trabajo ajeno", re.compile(r"\b(" + "|".join(map(re.escape, _terminos)) + r")\b"),
                       "[otro proyecto]"))

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    DESTINO.mkdir(exist_ok=True)
    for origen in map(Path, sys.argv[1:]):
        texto = origen.read_text(encoding="utf-8", errors="replace")
        cuenta = {}
        for nombre, patron, reemplazo in REGLAS:
            texto, n = patron.subn(reemplazo, texto)
            cuenta[nombre] = cuenta.get(nombre, 0) + n
        nombre = "desarrollo" if len(sys.argv) == 2 else origen.stem   # una sola conversación → nombre fijo
        destino = DESTINO / f"conversacion_{nombre}.md"
        destino.write_text(texto, encoding="utf-8")
        print(destino.relative_to(Path.cwd()), cuenta)
