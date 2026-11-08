# Evidencias del uso de IA

Todo el proyecto se desarrolló con **Claude Code** (Claude Opus 5.5) en una sola conversación, más las sesiones
no interactivas (`claude -p`) del agente y de la evaluación. Antes de publicar se ocultaron correos, rutas del
perfil de Windows, tokens y menciones a trabajos ajenos a la tarea (`scripts/copiar_evidencias.py`).

| Carpeta / archivo | Qué contiene |
|---|---|
| [`conversacion_desarrollo.md`](conversacion_desarrollo.md) | La conversación completa de desarrollo, en orden: lectura del enunciado, guía de variables, lectura del DT 309 de Trivelli y Mendoza, plan, servidor MCP, Skills, evaluación, ejecución del agente, correcciones e informe |
| [`mcp/`](mcp/) | Dónde está, dentro de la conversación, el desarrollo y las pruebas del servidor MCP |
| [`skills/`](skills/) | Dónde está el desarrollo de las tres Skills y sus correcciones |
| [`integracion/`](integracion/) | La ejecución integrada del agente (MCP + Skills en una sola corrida): salida cruda `ejecucion_agente.jsonl` y versión legible `ejecucion_agente.md` |
| [`evaluacion/`](evaluacion/) | Las 20 corridas del experimento (`A_*.jsonl` sin herramientas, `B_*.jsonl` con MCP y Skills) |
