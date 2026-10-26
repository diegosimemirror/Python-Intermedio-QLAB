"""Extracción estructurada (texto OCR/ASR → JSON) con un LLM local, para la Parte 2.

Modelo: Qwen/Qwen2.5-1.5B-Instruct en CPU (float32, 2 hilos, decodificación greedy).
Cada resultado se guarda en un JSON por registro (caché), así el notebook se puede volver
a ejecutar sin repetir la inferencia, que en CPU tarda cerca de un minuto por texto.

    from extraccion_llm import extraer, cargar_prompt
    r = extraer("doc_001", texto, "documento", cargar_prompt("modelos/prompt_extraccion.json"), Path("datos/raw/llm"))
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

MODELO_LLM = "Qwen/Qwen2.5-1.5B-Instruct"
MAX_CARACTERES = 1500          # el texto de entrada se recorta a este largo (periódicos de varias columnas)
MAX_TOKENS_SALIDA = 320
CLAVES = {
    "documento": ["modalidad", "tema", "resumen", "emisor", "fecha", "monto"],
    "audio": ["modalidad", "tema", "resumen", "numero_hablantes", "citas_clave"],
}
_MODELO = {}


def cargar_prompt(ruta) -> dict:
    """modelos/prompt_extraccion.json → dict con el mensaje de sistema y las reglas por modalidad."""
    return json.loads(Path(ruta).read_text(encoding="utf-8"))


def _cargar():
    """Primera llamada: carga el tokenizador y el modelo en CPU con 2 hilos (luego queda en memoria)."""
    if not _MODELO:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        torch.set_num_threads(2)
        _MODELO["tok"] = AutoTokenizer.from_pretrained(MODELO_LLM)
        _MODELO["llm"] = AutoModelForCausalLM.from_pretrained(MODELO_LLM, dtype=torch.float32).eval()
    return _MODELO["tok"], _MODELO["llm"]


def mensajes(texto: str, modalidad: str, prompt: dict) -> list[dict]:
    """texto + modalidad → mensajes de chat (sistema + usuario) con las claves exactas que se piden."""
    claves = ", ".join(f'"{c}"' for c in CLAVES[modalidad])
    usuario = (f"{prompt[modalidad]}\n\nDevuelve solo un objeto JSON con exactamente estas claves: {claves}.\n\n"
               f"TEXTO ({modalidad}):\n\"\"\"\n{texto[:MAX_CARACTERES]}\n\"\"\"")
    return [{"role": "system", "content": prompt["sistema"]}, {"role": "user", "content": usuario}]


def leer_json(salida: str, modalidad: str) -> tuple[dict | None, list[str]]:
    """respuesta cruda del LLM → (dict con solo las claves pedidas, claves inventadas); None si no hay JSON válido."""
    m = re.search(r"\{.*\}", salida, flags=re.S)
    if not m:
        return None, []
    try:
        datos = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None, []
    if not isinstance(datos, dict):
        return None, []
    extra = [k for k in datos if k not in CLAVES[modalidad]]
    limpio = {k: datos.get(k) for k in CLAVES[modalidad]}
    for k, v in limpio.items():  # "", "null", "N/A" → null
        if isinstance(v, str) and v.strip().lower() in {"", "null", "none", "n/a", "no aparece", "desconocido"}:
            limpio[k] = None
    return limpio, extra


def extraer(id_: str, texto: str, modalidad: str, prompt: dict, cache: Path) -> dict:
    """(id, texto, modalidad) → dict con campos JSON, salida cruda, validez y segundos. Usa caché por id."""
    archivo = Path(cache) / f"{id_}.json"
    if archivo.exists():
        return json.loads(archivo.read_text(encoding="utf-8"))
    import torch
    tok, llm = _cargar()
    entrada = tok.apply_chat_template(mensajes(texto, modalidad, prompt), add_generation_prompt=True,
                                      return_tensors="pt", return_dict=True)
    t0 = time.perf_counter()
    with torch.inference_mode():
        out = llm.generate(**entrada, max_new_tokens=MAX_TOKENS_SALIDA, do_sample=False)
    segundos = time.perf_counter() - t0
    salida = tok.decode(out[0, entrada["input_ids"].shape[1]:], skip_special_tokens=True).strip()
    campos, extra = leer_json(salida, modalidad)
    r = {"id": id_, "modalidad": modalidad, "campos": campos, "claves_inventadas": extra,
         "json_valido": campos is not None, "salida_cruda": salida, "segundos": round(segundos, 1),
         "modelo_llm": MODELO_LLM, "fecha": time.strftime("%Y-%m-%d")}
    archivo.parent.mkdir(parents=True, exist_ok=True)
    archivo.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    return r
