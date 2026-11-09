# Banco de casos sintéticos etiquetados

Generado por `eval/banco_sintetico.py` el 2026-11-08.

## 1. Qué mide

El banco contiene **26 alertas de Bandit**: 14 reales y 12 falsos positivos. Cada caso es un archivo `.py` con una sola alerta, y la etiqueta se declara a nivel de alerta en `eval/sinteticas/casos.jsonl` con su justificación. No se usa el holdout: los casos son nuevos y no participaron en el ajuste fino.

Los dos modelos reciben el prompt del producto (`triage.build_prompt` y `triage.SYSTEM`), la misma temperatura (0) y el mismo límite de generación. La política `B403` nunca se recomienda para descarte sigue activa. Por eso las cifras miden el producto, no el arnés `prompt_d` de la evaluación C0/D.

## 2. Casos por regla

| Regla | CWE | OWASP | Reales | FP | SAFE base | SAFE D |
|---|---|---|---:|---:|---:|---:|
| B101 | CWE-703 | sin_categoria | 1 | 1 | 0 | 2 |
| B105 | CWE-259 | A07 | 1 | 1 | 0 | 2 |
| B110 | CWE-703 | sin_categoria | 1 | 1 | 0 | 2 |
| B201 | CWE-94 | A03 | 1 | 0 | 0 | 0 |
| B301 | CWE-502 | A08 | 1 | 1 | 0 | 0 |
| B307 | CWE-78 | A03 | 1 | 1 | 0 | 0 |
| B310 | CWE-22 | A01 | 1 | 1 | 0 | 0 |
| B311 | CWE-330 | A02 | 1 | 1 | 0 | 2 |
| B324 | CWE-327 | A02 | 1 | 1 | 0 | 0 |
| B602 | CWE-78 | A03 | 1 | 1 | 0 | 1 |
| B603 | CWE-78 | A03 | 1 | 1 | 0 | 2 |
| B605 | CWE-78 | A03 | 1 | 1 | 0 | 1 |
| B608 | CWE-89 | A03 | 2 | 1 | 0 | 0 |

## 3. Resultados

| Métrica | Base | D | Δ puntos | Relativo |
|---|---:|---:|---:|---:|
| FPRR (FP recomendados para descarte) | 0,0 % | 58,3 % | +58,3 | n/a |
| FNR (reales recomendadas para descarte) | 0,0 % | 35,7 % | +35,7 | n/a |
| Exactitud de decisión | 53,8 % | 61,5 % | +7,7 | 14,3 % |
| Precisión de los descartes | n/a | 58,3 % | n/a | n/a |

Matriz de decisión (positivo = alerta real):

| Modelo | TP | FN | TN | FP | Inválidas |
|---|---:|---:|---:|---:|---:|
| Base | 14 | 0 | 0 | 12 | 2 |
| D | 9 | 5 | 7 | 5 | 0 |

## 4. Acuerdo entre modelos

Los dos modelos coinciden en **13/26 alertas (50,0 %)**.

| ID | Regla | Etiqueta | Base | D |
|---|---|---|---|---|
| S02 | B608 | real | SOSPECHOSA | VULNERABLE |
| S08 | B311 | real | VULNERABLE | SAFE |
| S09 | B105 | real | VULNERABLE | SAFE |
| S11 | B603 | real | VULNERABLE | SAFE |
| S13 | B101 | real | VULNERABLE | SAFE |
| S14 | B110 | real | VULNERABLE | SAFE |
| S16 | B602 | falso_positivo | VULNERABLE | SAFE |
| S17 | B605 | falso_positivo | VULNERABLE | SAFE |
| S21 | B311 | falso_positivo | SOSPECHOSA | SAFE |
| S22 | B105 | falso_positivo | VULNERABLE | SAFE |
| S24 | B603 | falso_positivo | VULNERABLE | SAFE |
| S25 | B101 | falso_positivo | VULNERABLE | SAFE |
| S26 | B110 | falso_positivo | VULNERABLE | SAFE |

## 5. Atajo de severidad

La regla «SAFE si la severidad del SAST es baja; VULNERABLE en otro caso» reproduce la decisión de D en **26/26 casos (100,0 %)**. No hay discrepancias: en este banco D no usa el contexto del código.

| ID | Regla | Severidad SAST | Veredicto D |
|---|---|---|---|
| S01 | B608 | media | VULNERABLE |
| S02 | B608 | media | VULNERABLE |
| S03 | B602 | alta | VULNERABLE |
| S04 | B605 | alta | VULNERABLE |
| S05 | B307 | media | VULNERABLE |
| S06 | B301 | media | VULNERABLE |
| S07 | B324 | alta | VULNERABLE |
| S08 | B311 | baja | SAFE |
| S09 | B105 | baja | SAFE |
| S10 | B310 | media | VULNERABLE |
| S11 | B603 | baja | SAFE |
| S12 | B201 | alta | VULNERABLE |
| S13 | B101 | baja | SAFE |
| S14 | B110 | baja | SAFE |
| S15 | B608 | media | VULNERABLE |
| S16 | B602 | baja | SAFE |
| S17 | B605 | baja | SAFE |
| S18 | B307 | media | VULNERABLE |
| S19 | B301 | media | VULNERABLE |
| S20 | B324 | alta | VULNERABLE |
| S21 | B311 | baja | SAFE |
| S22 | B105 | baja | SAFE |
| S23 | B310 | media | VULNERABLE |
| S24 | B603 | baja | SAFE |
| S25 | B101 | baja | SAFE |
| S26 | B110 | baja | SAFE |

## 6. Detalle por caso

| ID | Regla | OWASP | Etiqueta | Base | D |
|---|---|---|---|---|---|
| S01 | B608 | A03 | real | VULNERABLE | VULNERABLE |
| S02 | B608 | A03 | real | SOSPECHOSA | VULNERABLE |
| S03 | B602 | A03 | real | VULNERABLE | VULNERABLE |
| S04 | B605 | A03 | real | VULNERABLE | VULNERABLE |
| S05 | B307 | A03 | real | VULNERABLE | VULNERABLE |
| S06 | B301 | A08 | real | VULNERABLE | VULNERABLE |
| S07 | B324 | A02 | real | VULNERABLE | VULNERABLE |
| S08 | B311 | A02 | real | VULNERABLE | SAFE |
| S09 | B105 | A07 | real | VULNERABLE | SAFE |
| S10 | B310 | A01 | real | VULNERABLE | VULNERABLE |
| S11 | B603 | A03 | real | VULNERABLE | SAFE |
| S12 | B201 | A03 | real | VULNERABLE | VULNERABLE |
| S13 | B101 | sin_categoria | real | VULNERABLE | SAFE |
| S14 | B110 | sin_categoria | real | VULNERABLE | SAFE |
| S15 | B608 | A03 | falso_positivo | VULNERABLE | VULNERABLE |
| S16 | B602 | A03 | falso_positivo | VULNERABLE | SAFE |
| S17 | B605 | A03 | falso_positivo | VULNERABLE | SAFE |
| S18 | B307 | A03 | falso_positivo | VULNERABLE | VULNERABLE |
| S19 | B301 | A08 | falso_positivo | VULNERABLE | VULNERABLE |
| S20 | B324 | A02 | falso_positivo | VULNERABLE | VULNERABLE |
| S21 | B311 | A02 | falso_positivo | SOSPECHOSA | SAFE |
| S22 | B105 | A07 | falso_positivo | VULNERABLE | SAFE |
| S23 | B310 | A01 | falso_positivo | VULNERABLE | VULNERABLE |
| S24 | B603 | A03 | falso_positivo | VULNERABLE | SAFE |
| S25 | B101 | sin_categoria | falso_positivo | VULNERABLE | SAFE |
| S26 | B110 | sin_categoria | falso_positivo | VULNERABLE | SAFE |

## 7. Lectura y límites

- FPRR mide qué proporción de los falsos positivos etiquetados se recomienda descartar; FNR, qué proporción de las alertas reales se recomienda descartar. En modo asesor, un `SAFE` es una recomendación, no una supresión.
- El banco es pequeño y está construido por el autor. Sirve para detectar regresiones y comparar modelos con verdad de referencia, no para estimar el rendimiento en producción.
- Varias reglas de Bandit son heurísticas: la etiqueta depende del contexto del caso. La justificación de cada caso está en `casos.jsonl` para que la clasificación sea auditable.
- Reglas ignoradas por el emparejamiento (alertas no etiquetadas del mismo archivo): B403 en S06 x1, B403 en S19 x1, B404 en S03 x1, B404 en S11 x1, B404 en S16 x1, B404 en S24 x1, B607 en S11 x1, B607 en S16 x1, B607 en S17 x1, B607 en S24 x1.
