# Referencia: reglas y variables de la ENAHO 2024

## Archivos

| Archivo | Una fila por | Filas | Llaves | Factor |
|---|---|---|---|---|
| `966-Modulo34/sumaria-2024.dta` | hogar | 33,691 | `conglome`, `vivienda`, `hogar` | `factor07` (hogares) |
| `966-Modulo02/enaho01-2024-200.dta` | persona | 117,721 | las tres + `codperso` | `facpob07` (personas) |

Ojo: el zip del módulo 34 trae también `sumaria-2024-12g.dta`, con otra clasificación del gasto (12 grupos).
El script usa `sumaria-2024.dta` (8 grupos), donde `gru1*` es solo alimentos.

## Reglas que el script aplica siempre

| Paso | Regla |
|---|---|
| Lectura | `pd.read_stata(..., convert_categoricals=False)`; llaves y `ubigeo` como texto |
| Nombres | todo a minúscula (`aÑo` → `año`) |
| Residentes habituales | `((p204 == 1) & (p205 == 2)) \| ((p204 == 2) & (p206 == 1))` → 108,664 |
| Unión | personas (m) con hogares (1): `merge(..., validate="m:1")`; misma cantidad de filas antes y después |
| Departamento | `ubigeo[:2]` (01 a 25; Lima 15 y Callao 07 separados) |
| Área | urbano si `estrato <= 5` |
| Pobreza | pobre si `pobreza <= 2`; pobre extremo si `pobreza == 1` |
| Lima Metropolitana | `dominio == 8` (incluye el Callao) |
| `mieperho` | llega como int8: `12 * mieperho` desborda en hogares de 11 o más; se convierte a decimal |
| Ponderación de hogares | `peso_personas = factor07 * mieperho` (método del INEI) |
| Ponderación de personas | `facpob07` |

## Variables derivadas (en las bases de `salidas/`)

| Variable | Cálculo | Unidad |
|---|---|---|
| `gasto_pc_mes` | `gashog2d / (12 * mieperho)` | soles por persona al mes |
| brecha de pobreza (FGT1) | promedio ponderado de `(linea − gasto_pc_mes) / linea` entre los pobres (0 para los no pobres) | % de la línea |
| `share_alimentos` | suma de `gru1*` / `gashog2d` | proporción del gasto |
| `juntos_anual` | `ingtpu01` (transferencia de Juntos) | soles al año |
| `pension65_anual` | `ingtpu03` (Pensión 65) | soles al año |
| `pobrezav` | 1 pobre extremo, 2 pobre no extremo, 3 no pobre vulnerable, 4 no pobre no vulnerable (INEI) | categoría |
| `con_menor_5`, `con_adulto_65` | algún residente del hogar con `p208a < 5` o `>= 65` | sí/no |
| `jefatura` | sexo (`p207`) del residente con `p203 == 1` | Femenina/Masculina |

## Valores de referencia (INEI, 2024)

Pobreza 27.6 % (27.58 con la sumaria; 27.53 con personas); urbana 24.8 %; rural 39.3 %; extrema 5.5 %;
Lima Metropolitana 28.2 %. Por departamento: `referencias/pobreza_departamento_2024.csv` (sesión 16).

## Límites conocidos

- No hay datos de inseguridad alimentaria (FIES): el módulo empezó en 2025.
- Educación, lengua materna, empleo e informalidad, vivienda y servicios están en los módulos 100, 300 y 500,
  que esta tarea no usa.
- `ingtpu02` ("otras transferencias públicas") es el 78 % de `ingtpuhd`: no usar `ingtpuhd` como "programas
  sociales".
- 19 hogares tienen gasto en alimentos mayor que `gashog2d` (0,06 %); se dejan como están y se avisa.
- La ENAHO estima 1,04 millones de hogares con Juntos; el padrón del programa reporta unos 760 mil (InfoMidis).
