# Análisis de la corrida C (modelo base, prompt con contexto y few-shot)

Corrida sobre las 141 alertas del conjunto de evaluación (91 reales, 50 falsos
positivos) con `qwen2.5-coder:1.5b`, temperatura 0 y el prompt con contexto del
SAST más dos ejemplos resueltos. Es la línea base de prompt cuidado frente a D;
la comparación que aísla el ajuste fino es D contra C0. Datos completos en
`eval/resultados_C.json`.

## Matriz de confusión

| | Recomendada descarte (SAFE) | Conservada (VULNERABLE/SOSPECHOSA) |
|---|---|---|
| **Alerta real (91)** | 0 (FN) | 91 (VP) |
| **Falso positivo (50)** | 1 (VN) | 49 (FP) |

- FPRR = 1 / 50 = **2,0 %**
- FNR = 0 / 91 = **0,0 %**
- FOR = 0 / 1 = **0,0 %**
- Precisión = 91 / 140 = **65,0 %**
- Exactitud CWE = 34 / 91 = **37,4 %**
- Respuestas inválidas: **1** (B102, conservada como `SOSPECHOSA`)

## Lectura

El modelo base responde `VULNERABLE` a 139 de las 141 alertas y `SAFE` a una
sola: un B404 (import de `subprocess`). Esa cautela extrema explica el FNR nulo
y, al mismo tiempo, el escaso ahorro de revisión. No es un modelo que clasifique
mejor: es un modelo que casi no se compromete.

La única respuesta inválida fue una B102 (`f10496.py:31`), la alerta más larga
del conjunto (1.818 caracteres), con la que el modelo base entra en un bucle de
generación. El caso tiene dos versiones y conviene no confundirlas:

- **Corrida original, sin límite de tokens.** El cliente agotó el timeout de
  180 s y no recibió JSON. La alerta se conservó como `SOSPECHOSA`, pero el
  runner de Ollama siguió consumiendo CPU después de que el cliente abandonó.
  Esa corrida se conserva en `eval/resultados_C_sin_num_predict.json`.
- **Corrida definitiva, con `num_predict: 512`.** La generación se trunca en
  512 tokens en unos 8 s, la respuesta no cierra el JSON y la política
  conservadora la marca `SOSPECHOSA`. El resultado de la alerta es el mismo,
  pero el fallo queda acotado en tiempo. D, en cambio, responde `VULNERABLE` en
  unos 4 s con el mismo formato de alerta.

La lectura operativa es que el timeout y la política conservadora convierten un
fallo del modelo en una alerta conservada, no en una alerta perdida. Sin el
caso patológico, el promedio de C es de ~4,3 s por alerta, similar al de D.

## Resultado por regla de Bandit

| Regla | Alertas | Reales | Reales descartadas | FP | FP descartados | FPRR | FNR |
|---|---|---|---|---|---|---|---|
| B307 | 21 | 19 | 0 | 2 | 0 | 0,0 % | 0,0 % |
| B403 | 28 | 21 | 0 | 7 | 0 | 0,0 % | 0,0 % |
| B301 | 25 | 19 | 0 | 6 | 0 | 0,0 % | 0,0 % |
| B605 | 11 | 9 | 0 | 2 | 0 | 0,0 % | 0,0 % |
| B201 | 10 | 8 | 0 | 2 | 0 | 0,0 % | 0,0 % |
| B608 | 6 | 6 | 0 | 0 | 0 | 0,0 % | 0,0 % |
| B108 | 2 | 2 | 0 | 0 | 0 | 0,0 % | 0,0 % |
| B310 | 1 | 1 | 0 | 0 | 0 | 0,0 % | 0,0 % |
| B104 | 1 | 0 | 0 | 1 | 0 | 0,0 % | 0,0 % |
| B311 | 1 | 0 | 0 | 1 | 0 | 0,0 % | 0,0 % |
| B602 | 5 | 2 | 0 | 3 | 0 | 0,0 % | 0,0 % |
| B102 | 7 | 2 | 0 | 5 | 0 | 0,0 % | 0,0 % |
| B603 | 7 | 0 | 0 | 7 | 0 | 0,0 % | 0,0 % |
| B404 | 16 | 2 | 0 | 14 | 1 | 7,1 % | 0,0 % |

## D frente a C, regla por regla

Solo se muestran las reglas con falsos positivos; la columna final cuenta
cuántos descarta cada configuración.

| Regla | FP | C descarta | D descarta |
|---|---|---|---|
| B404 | 14 | 1 | 9 |
| B403 | 7 | 0 | 5 |
| B603 | 7 | 0 | 4 |
| B301 | 6 | 0 | 0 |
| B102 | 5 | 0 | 1 |
| B602 | 3 | 0 | 1 |
| B605 | 2 | 0 | 0 |
| B201 | 2 | 0 | 1 |
| B307 | 2 | 0 | 1 |
| B311 | 1 | 0 | 1 |
| B104 | 1 | 0 | 1 |

El ajuste fino no mejora todas las reglas por igual. Concentra el ahorro en
B404 (imports de `subprocess`), B403 y B603, que son precisamente las reglas
más ruidosas del conjunto. En B301 (pickle) no descarta nada, y el único falso
negativo de D en B403 aparece al intentar esa misma reducción de ruido.

## CWE

El modelo base también copia el CWE del SAST en la mayoría de las alertas
conservadas (84 de 91). La exactitud CWE de 37,4 % no mide clasificación
independiente: mide la concordancia entre el CWE del SAST y la etiqueta del
dataset. La diferencia con D (43,0 %) está dominada por qué alertas conserva
cada configuración.

## Conclusión

C es la línea base correcta para atribuir el efecto del ajuste fino. D pasa de
2,0 % a 48,0 % de FPRR y de 0,0 % a 5,5 % de FNR. El intercambio es real y
medible, pero el FNR resultante no permite descarte automático. El valor de C
no es ganar la comparación: es demostrar que el prompt por sí solo no produce
el ahorro que produce el modelo ajustado.
