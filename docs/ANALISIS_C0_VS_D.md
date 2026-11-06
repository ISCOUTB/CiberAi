# Qwen base frente al modelo afinado (C0 vs. D)

Sección de comparación con el modelo base. Responde a la observación del director
de programa: el proyecto debe mostrar de forma explícita **qué aportó el ajuste
fino frente a usar Qwen2.5-Coder-1.5B sin entrenar**. No se ejecutaron corridas
nuevas: se reutilizan los resultados ya medidos en desarrollo y en el holdout.

Cifras reproducibles con:

```
python eval/analisis_c0_vs_d.py
```

El script lee `eval/resultados_{C0,D}.json` y
`eval/resultados_holdout_{C0,D}.json`, empareja las alertas por `id`, calcula la
matriz de acuerdo, la prueba de McNemar y un IC95 de la diferencia con bootstrap
agrupado por archivo. Escribe `eval/analisis_c0_vs_d.json`.

## 1. Por qué C0 es el control correcto

C0 y D comparten todo salvo la etiqueta del modelo:

| Elemento | C0 | D |
|---|---|---|
| Modelo | `qwen2.5-coder:1.5b` | `qwen2.5-coder-triage` (LoRA + fusión + Q4_K_M) |
| Prompt | `prompt_d` | `prompt_d` |
| Prompt de sistema | `SYSTEM` de `triage.py` | `SYSTEM` de `triage.py` |
| Temperatura | 0 | 0 |
| Límite de generación | `num_predict: 512` | `num_predict: 512` |
| Conjunto y orden | idénticos | idénticos |

La igualdad está en el código, no en la descripción: `eval/run_eval.py` usa
`p = prompt_d(row)` tanto para `D` como para `C0` (línea 195) y envía el mismo
`SYSTEM` en ambos casos. Por eso el par C0/D aísla el efecto del ajuste fino.
La comparación D contra C (few-shot) describe el resultado práctico frente a un
prompt cuidado, pero mezcla modelo y prompt y no sirve para atribuir la
diferencia al entrenamiento.

## 2. Resultado global

| Conjunto | Configuración | Alertas | FPRR | FNR | Exactitud de la decisión |
|---|---|---:|---:|---:|---:|
| Desarrollo | C0 | 141 | 22,0 % | 2,2 % | 70,9 % |
| Desarrollo | D | 141 | 48,0 % | 5,5 % | 78,0 % |
| Holdout | C0 | 111 | 10,9 % | 0,0 % | 63,1 % |
| Holdout | D | 111 | 30,4 % | 9,2 % | 65,8 % |

La exactitud de la decisión —el porcentaje de alertas clasificadas correctamente—
**sube** con D en ambos conjuntos. Es una métrica engañosa en este problema: como
hay más falsos positivos (50 de 141 en desarrollo, 46 de 111 en el holdout),
descartar mucho mejora la exactitud aunque se pierdan alertas reales. El FPRR y
el FNR separan los dos tipos de error y muestran lo contrario: **D no domina a
C0 en ninguna de las dos métricas, en ninguno de los dos conjuntos**.

En desarrollo, C0 descarta 11 de 50 falsos positivos y 2 de 91 reales; D descarta
24 de 50 y 5 de 91. En el holdout, C0 descarta 5 de 46 falsos positivos y ninguna
de 65 reales; D descarta 14 de 46 y 6 de 65. El ajuste más que duplicó la
reducción de ruido en desarrollo y casi la triplicó en el holdout, pero introdujo
omisiones que el modelo base no tenía.

## 3. Matriz de acuerdo alerta por alerta

| Conjunto | Ambos conservan | Ambos descartan | Solo D descarta | Solo C0 descarta |
|---|---:|---:|---:|---:|
| Desarrollo | 110 (85 reales, 25 FP) | 11 (1 real, 10 FP) | 18 (4 reales, 14 FP) | 2 (1 real, 1 FP) |
| Holdout | 88 (59 reales, 29 FP) | 2 (0 reales, 2 FP) | 18 (6 reales, 12 FP) | 3 (0 reales, 3 FP) |

La coincidencia es alta: en el holdout, 90 de 111 alertas reciben la misma
decisión (81 %). El desacuerdo tiene dirección clara y consistente: **D descarta
18 alertas que C0 conserva en los dos conjuntos**, mientras que C0 descarta entre
2 y 3 que D conserva. La prueba de McNemar sobre las discordancias es
significativa en ambos casos (desarrollo p = 0,0004; holdout p = 0,0015): el
cambio de comportamiento no es ruido de muestreo, es el efecto del ajuste.

## 4. Diferencia pareada con intervalo de confianza

Bootstrap de 2.000 remuestreos agrupados por archivo (85 archivos en desarrollo,
71 en el holdout), porque las alertas de un mismo archivo no son independientes.

| Conjunto | Δ FPRR (D − C0) | IC95 | Δ FNR (D − C0) | IC95 |
|---|---:|---|---:|---|
| Desarrollo | +26,0 pts | 9,4 a 43,6 | +3,3 pts | −1,2 a 8,2 |
| Holdout | +19,6 pts | 0,0 a 38,5 | +9,2 pts | 1,8 a 17,5 |

El aumento de FPRR es claro en desarrollo y roza el cero en el holdout: el
intervalo del holdout incluye el 0,0, así que la mejora en reducción de ruido
**no está demostrada** con 46 falsos positivos. El aumento de FNR sí es
consistente en el holdout (intervalo enteramente positivo), aunque el límite
inferior de 1,8 puntos es pequeño. En desarrollo el intervalo de FNR cruza el
cero: con 91 reales, tres omisiones adicionales no alcanzan para afirmar el
efecto. La lectura conjunta es la correcta: **el ajuste cambió el
comportamiento de forma medible; que ese cambio sea una mejora no está
demostrado.**

## 5. Dónde se concentra el cambio

Desacuerdos por regla en el holdout (solo se listan las reglas con discordancia):

| Regla | Alertas | Solo D | Reales entre las de D | Solo C0 |
|---|---:|---:|---:|---:|
| B403 (pickle) | 15 | 8 | 4 | 0 |
| B404 (subprocess) | 11 | 4 | 0 | 2 |
| B307 (eval) | 27 | 3 | 0 | 0 |
| B311 (random) | 3 | 2 | 2 | 0 |
| B201 (flask debug) | 9 | 1 | 0 | 0 |
| B603 (subprocess) | 3 | 0 | 0 | 1 |

Los 6 falsos negativos del holdout son 4 B403 y 2 B311. Los 4 B403 son la misma
familia que ya se había identificado en desarrollo: el modelo confunde «importar
pickle» con «deserializar datos no confiables». Los 2 B311 son un riesgo nuevo
que no apareció en desarrollo y que motivó la política reportada en
`docs/ANALISIS_HOLDOUT.md`.

En desarrollo el patrón es idéntico y aún más concentrado: los 4 descartes
indebidos de D son B403, y el quinto falso negativo es una B403 que C0 también
descarta. Es decir, **el ajuste no repartió el error: lo especializó en una
regla**. Eso tiene una consecuencia práctica: una política por regla (B403)
recupera la mayor parte del daño, que es exactamente lo que se midió en el
Sprint 7.

## 6. El intercambio, en términos de producto

| Conjunto | Descartes netos de D | FP netos eliminados | Reales netas perdidas | FP por cada real |
|---|---:|---:|---:|---:|
| Desarrollo | 16 | 13 | 3 | 4,3 |
| Holdout | 15 | 9 | 6 | 1,5 |

La tabla es la forma más honesta de resumir el ajuste: en el holdout, cada
alerta real que D pierde frente a C0 se paga con 1,5 falsos positivos
adicionales eliminados. Para un producto en modo asesor, donde el objetivo es
ahorrar revisión sin ocultar riesgo, ese intercambio es malo: el ahorro de
revisión es real pero modesto, y el costo se paga en la métrica que el producto
no puede permitirse.

## 7. Efecto sobre las explicaciones

El holdout conserva el texto generado; el conjunto de desarrollo solo guarda
veredicto, CWE y decisión.

| Configuración | Explicaciones únicas | Moda | Vectores únicos | Correcciones únicas |
|---|---:|---:|---:|---:|
| C0 | 108 | 2 | 103 | 106 |
| D | 11 | 47 | 8 | 2 |

D produjo 11 explicaciones para 111 alertas, con una repetida 47 veces, y solo 2
correcciones distintas para 91 respuestas VULNERABLE. C0 produjo 108
explicaciones únicas. El ajuste no solo no mejoró la decisión: **destruyó la
capacidad de explicar**. La causa está en el corpus de entrenamiento, donde
5.489 de 5.755 respuestas SAFE comparten la misma explicación. El modelo
aprendió la plantilla mayoritaria.

Consecuencia para el producto: D se usa como clasificador de triage, no como
generador de explicaciones. La rúbrica pendiente debe reportar la diversidad
junto con el kappa, porque un kappa alto sobre 11 plantillas no distingue
calidad de repetición.

## 8. Efecto sobre el CWE

| Conjunto | C0 copia el CWE del SAST | D copia el CWE del SAST | Exactitud CWE C0 | Exactitud CWE D |
|---|---:|---:|---:|---:|
| Desarrollo | 139 de 141 | 112 de 141 | 44,9 % | 43,0 % |
| Holdout | 110 de 111 | 91 de 111 | 33,8 % | 32,2 % |

C0 casi siempre repite el CWE que Bandit ya había asignado. D empezó a producir
su propio CWE en 29 de 141 alertas en desarrollo y en 20 de 111 en el holdout,
pero **sin mejorar la exactitud**: incluso la empeoró ligeramente. El ajuste
movió al modelo a opinar sobre una tarea para la que no fue entrenado con
suficiente señal. La decisión de producto ya tomada —conservar el CWE del SAST y
usar al modelo solo para el veredicto— queda respaldada por este resultado.

## 9. Qué se puede afirmar y qué no

Se puede afirmar:

- El ajuste fino cambió el comportamiento del modelo de forma estadísticamente
  detectable y en la dirección prevista: descarta más.
- El cambio se concentra en B403 y, en el holdout, en B311; no es un
  desplazamiento general.
- El modelo base es más conservador en ambos conjuntos y no produce ningún falso
  negativo en el holdout.
- El ajuste degradó la diversidad de las explicaciones hasta convertirla en
  plantillas.

No se puede afirmar:

- Que el modelo afinado sea mejor que el base. En FPRR y FNR, el base gana en
  los dos conjuntos.
- Que la mejora de FPRR esté demostrada en el holdout: su IC95 incluye el cero.
- Que el ajuste generalice a reglas que no aparecen en el corpus; el error se
  concentra en las familias con más ejemplos.
- Que el resultado se deba solo al entrenamiento en un sentido causal fuerte: el
  adaptador se entrenó sobre un corpus balanceado y se evalúa sobre la
  distribución natural del dataset.

## 10. Implicación para la memoria y para el producto

La comparación con Qwen base no respalda la hipótesis de que el ajuste fino
mejora la detección. Respalda una conclusión más específica y más útil: **un
modelo base de 1,5B ya es conservador y útil como segundo filtro, y el ajuste
fino compró decisión a cambio de omisiones**. El aporte del proyecto no es
«nuestro modelo supera a Qwen»; es el pipeline local completo, el protocolo de
medición pareado con intervalos agrupados por archivo, la política de no
descarte y la evidencia de que el ajuste, sin control por regla, no es una
mejora automática.

Esa es la sección que debe leerse antes que la tabla de resultados: si el jurado
pregunta por qué existe un modelo afinado que rinde peor que el base, la
respuesta está en el diseño experimental, no en una excusa.
