# Desarrollo del servidor MCP

En [`../conversacion_desarrollo.md`](../conversacion_desarrollo.md), buscar «servidor MCP»: descarga del proyecto de
la sesión 04, instalación de `uv`, escritura de `mcp/server.py` (`serie`, `resumen`, `valor_real`, `graficar_serie`,
recurso y prompt), las 2 pruebas propias, el resultado `10 passed`, y las correcciones:

- la API del BCRP pega un aviso HTML de PHP después del JSON y no responde en UTF-8 → `raw_decode` + latin-1;
- `valor_real` aceptaba por error una serie de variación porcentual → se exige un índice;
- títulos y notas largas se cortaban en `graficar_serie` → se parten en líneas.
