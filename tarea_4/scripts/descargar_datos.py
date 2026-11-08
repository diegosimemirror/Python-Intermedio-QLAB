"""Baja a datos/ los archivos oficiales que el proyecto no sube a Git.

    uv run python scripts/descargar_datos.py        # desde tarea_4/
"""
import sys
from pathlib import Path

import httpx   # descargas HTTP

DATOS = Path.cwd() / "datos"
ARCHIVOS = {
    "966-Modulo34.zip": "https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/966-Modulo34.zip",
    "966-Modulo02.zip": "https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/966-Modulo02.zip",
    "peru_departamental_simple.geojson": ("https://raw.githubusercontent.com/d2cml-ai/Data-Science-Python/main/"
                                          "sessions/06-geoespacial/lab/Data/peru_departamental_simple.geojson"),
}

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    DATOS.mkdir(exist_ok=True)
    for nombre, url in ARCHIVOS.items():
        destino = DATOS / nombre
        if destino.exists():
            print(f"ya existe: {destino.relative_to(Path.cwd())}")
            continue
        print(f"bajando {url} ...")
        with httpx.stream("GET", url, timeout=300, follow_redirects=True) as r:
            r.raise_for_status()
            with open(destino, "wb") as f:
                for trozo in r.iter_bytes():
                    f.write(trozo)
        print(f"  listo: {destino.stat().st_size / 1e6:.1f} MB")
