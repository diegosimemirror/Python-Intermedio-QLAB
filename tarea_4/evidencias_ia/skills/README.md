# Desarrollo de las Skills

En [`../conversacion_desarrollo.md`](../conversacion_desarrollo.md), buscar «limpiando-enaho», «graficando-enaho» y
«mapeando-enaho»: escritura de los scripts y `SKILL.md`, la validación (`salidas/validacion.txt`, 15/16 aprobadas),
y las correcciones:

- `mieperho` llega como int8 y desborda en `12 × mieperho` → conversión a decimal;
- la consola de Windows no imprimía UTF-8 → `sys.stdout.reconfigure`;
- falsa alarma revisada: en `sumaria-2024.dta` las variables `gru1*` son solo alimentos (los grupos 10 a 12 están
  en `sumaria-2024-12g.dta`);
- la suma de los grupos de gasto no es `gashog2d` → la validación se cambió por «alimentos entre 0 y el gasto total»
  (19 hogares fuera, se avisa);
- títulos largos cortados en los gráficos → `textwrap`.
