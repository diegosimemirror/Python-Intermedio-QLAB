"""Las 2 pruebas propias de la herramienta valor_real (las 8 originales están en test_server.py, sin cambios)."""
import asyncio

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from server import mcp


def llamar(herramienta, **args):
    async def f():
        async with Client(mcp) as c:
            return await c.call_tool(herramienta, args)
    return asyncio.run(f()).data


def test_valor_real_reproduce_el_anexo_de_juntos():
    # Trivelli y Mendoza (2026, Anexo 2): IPC dic-2006 = 62,56 ; ago-2026 = 120,72 ; S/ 100 → S/ 51,82
    r = llamar("valor_real", monto=100, desde="2026-08", hasta="2006-12")
    assert r["ipc_desde"] == pytest.approx(120.72, abs=0.01)
    assert r["ipc_hasta"] == pytest.approx(62.56, abs=0.01)
    assert r["valor"] == pytest.approx(51.82, abs=0.01)
    assert r["inflacion_acumulada_pct"] == pytest.approx(92.97, abs=0.05)


def test_valor_real_sin_dato_o_serie_no_indice_da_error_claro():
    with pytest.raises(ToolError, match="1950-01"):
        llamar("valor_real", monto=100, desde="1950-01", hasta="2026-08")
    with pytest.raises(ToolError, match="no es un índice"):
        llamar("valor_real", monto=100, desde="2025-01", hasta="2026-08", codigo_ipc="PN01273PM")
