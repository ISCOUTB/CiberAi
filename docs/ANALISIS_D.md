# Análisis de la corrida D (modelo afinado)

Corrida sobre las 141 alertas del conjunto de evaluación de desarrollo (91
reales, 50 falsos positivos) con `qwen2.5-coder-triage`, temperatura 0 y modo
asesor. Datos completos en `eval/resultados_D.json`.

> **Actualización del Sprint 7.** Este documento describe la corrida de
> desarrollo. El holdout de 111 alertas (65 reales, 46 falsos positivos) se
> ejecutó después y cambió la conclusión: D crudo obtuvo FPRR 30,4 % y FNR 9,2 %
> (4 B403 y 2 B311); con la política B403, FNR 3,1 % (IC95 0,8–10,5 %) y FPRR
> 19,6 %. El detalle está en `docs/ANALISIS_HOLDOUT.md`. Las cifras de este
> archivo no deben citarse como resultado final.

## Matriz de confusión

| | Recomendada descarte (SAFE) | Conservada (VULNERABLE/SOSPECHOSA) |
|---|---|---|
| **Alerta real (91)** | 5 (FN) | 86 (VP) |
| **Falso positivo (50)** | 24 (VN) | 26 (FP) |

- FPRR = 24 / 50 = **48,0 %**
- FNR = 5 / 91 = **5,5 %**
- FOR = 5 / 29 = **17,2 %**
- Precisión = 86 / 112 = **76,8 %**
- Exactitud CWE = 37 / 86 = **43,0 %**
- Respuestas inválidas: **0**

## Resultado por regla de Bandit

| Regla | Alertas | Reales | Reales descartadas | FP | FP descartados | FPRR | FNR |
|---|---|---|---|---|---|---|---|
| B404 | 16 | 2 | 0 | 14 | 9 | 64,3 % | 0,0 % |
| B403 | 28 | 21 | 5 | 7 | 5 | 71,4 % | 23,8 % |
| B603 | 7 | 0 | 0 | 7 | 4 | 57,1 % | 0,0 % |
| B102 | 7 | 2 | 0 | 5 | 1 | 20,0 % | 0,0 % |
| B104 | 1 | 0 | 0 | 1 | 1 | 100,0 % | 0,0 % |
| B201 | 10 | 8 | 0 | 2 | 1 | 50,0 % | 0,0 % |
| B307 | 21 | 19 | 0 | 2 | 1 | 50,0 % | 0,0 % |
| B311 | 1 | 0 | 0 | 1 | 1 | 100,0 % | 0,0 % |
| B602 | 5 | 2 | 0 | 3 | 1 | 33,3 % | 0,0 % |
| B108 | 2 | 2 | 0 | 0 | 0 | 0,0 % | 0,0 % |
| B301 | 25 | 19 | 0 | 6 | 0 | 0,0 % | 0,0 % |
| B310 | 1 | 1 | 0 | 0 | 0 | 0,0 % | 0,0 % |
| B605 | 11 | 9 | 0 | 2 | 0 | 0,0 % | 0,0 % |
| B608 | 6 | 6 | 0 | 0 | 0 | 0,0 % | 0,0 % |

Lectura: el modelo es conservador donde debe serlo. En B301, B307, B605 y
B608 no descartó ninguna alerta real. Todo el FNR se concentra en B403.

## Las cinco alertas reales descartadas

| ID | Regla | CWE dataset | ¿Qué hace el código? |
|---|---|---|---|
| f12443.py:1 | B403 | CWE-502 | `pickle.dump` + `pickle.load` + `pickle.loads` |
| f1448.py:1 | B403 | CWE-502 | Solo `pickle.dump` (serializa) |
| f14508.py:1 | B403 | CWE-502 | `pickle.dump` + `pickle.load` |
| f2077.py:1 | B403 | CWE-502 | Solo `pickle.dump` (serializa) |
| f8631.py:1 | B403 | CWE-787 | `pickle.dumps` + `pickle.loads` |

Tres casos deserializan datos y dos solo serializan. La etiqueta del dataset
marca la función como vulnerable; en los dos casos de solo serialización la
etiqueta es discutible, porque serializar no ejecuta código del atacante. Aun
así, el modelo no debe recomendar descarte para B403 sin revisar el sink.

## CWE: el modelo copia al SAST

En las 86 alertas reales conservadas, el CWE predicho coincide exactamente con
el CWE reportado por Bandit en **86 de 86** casos. Por lo tanto, la exactitud
CWE de 43,0 % no mide clasificación independiente: mide la concordancia entre
el CWE del SAST y la etiqueta del dataset, sobre el subconjunto que el modelo
conservó. El producto debe seguir mostrando el CWE del SAST y no pedirle al
modelo que lo reclasifique.

Esto también explica la diferencia con C: C también copia el CWE del SAST en la
mayoría de los casos, de modo que la comparación de exactitud CWE entre C y D
está dominada por qué alertas conserva cada configuración, no por conocimiento
del modelo.

## Mitigación de producto: excluir B403 del descarte

Si se mantiene el modo asesor y se agrega una regla de negocio que **nunca
recomienda descarte para B403**, el resultado sobre el mismo conjunto de
desarrollo es:

- FPRR = 19 / 50 = **38,0 %**
- FNR = 0 / 91 = **0,0 %**
- Se pierden 5 descartes de falsos positivos (los B403), pero desaparecen los 5
  falsos negativos.

Es una política defendible porque la alerta B403 apunta al `import` y no al
punto de uso; el modelo no siempre puede distinguir una importación inofensiva
de una deserialización explotable. La regla se implementó en el producto
(`DEFAULT_NEVER_DISCARD = {"B403"}`).

**El holdout no confirmó el FNR 0 %:** con la política, D deja 2 falsos
negativos B311 y obtiene FNR 3,1 % (IC95 0,8–10,5 %). B403 sigue siendo
obligatoria, pero no suficiente. Para B311 no se agrega una regla post hoc; se
reporta como riesgo nuevo en `docs/ANALISIS_HOLDOUT.md`.

## Conclusión

En desarrollo, D reduce el ruido de forma real (48 % de los falsos positivos) sin
romper el formato, pero no cumple la meta estricta de FNR ≤ 5 % (5,5 %) y no
aporta clasificación CWE. El holdout confirma la dirección y empeora el
resultado: FPRR 30,4 % y FNR 9,2 % crudos; con B403, FPRR 19,6 % y FNR 3,1 %
(IC95 0,8–10,5 %). El producto debe mantenerse en modo asesor, con B403
obligatoria y sin agregar B311 después de ver el holdout.
