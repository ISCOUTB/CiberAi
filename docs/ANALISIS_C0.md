# Análisis de la corrida C0 (control: modelo base sin few-shot)

Corrida sobre las 141 alertas del conjunto de evaluación (91 reales, 50 falsos
positivos) con `qwen2.5-coder:1.5b`, temperatura 0 y el **mismo formato de
alerta que D, sin ejemplos resueltos**. Es el control que aísla el efecto del
ajuste fino: C0 y D comparten prompt, conjunto y temperatura; solo cambia el
modelo. Datos completos en `eval/resultados_C0.json`.

## Matriz de confusión

| | Recomendada descarte (SAFE) | Conservada (VULNERABLE/SOSPECHOSA) |
|---|---|---|
| **Alerta real (91)** | 2 (FN) | 89 (VP) |
| **Falso positivo (50)** | 11 (VN) | 39 (FP) |

- FPRR = 11 / 50 = **22,0 %** (IC95 12,8–35,2 %)
- FNR = 2 / 91 = **2,2 %** (IC95 0,6–7,7 %)
- FOR = 2 / 13 = **15,4 %**
- Precisión = 89 / 128 = **69,5 %**
- Exactitud CWE = 40 / 89 = **44,9 %**
- Respuestas inválidas: **1** (B605, conservada como `SOSPECHOSA`)

## Lectura

Quitar el few-shot cambia radicalmente el comportamiento del modelo base. C,
con dos ejemplos resueltos, descarta 1 de 50 falsos positivos; C0, sin esos
ejemplos, descarta 11. El modelo no se volvió más capaz: el prompt dejó de
inclinarlo hacia `VULNERABLE`.

El costo aparece en las alertas reales: C0 descarta 2 de 91 (una B403 y una
B404), mientras C no descarta ninguna. La tasa sigue por debajo de la meta de
5 %, pero ya no es cero. Quitar el few-shot compra ahorro y paga con una pequeña
tasa de omisión.

## Resultado por regla de Bandit

Solo se muestran las reglas con falsos positivos o descartes reales.

| Regla | Alertas | Reales | Reales descartadas | FP | FP descartados | FPRR | FNR |
|---|---|---|---|---|---|---|---|
| B403 | 28 | 21 | 1 | 7 | 1 | 14,3 % | 4,8 % |
| B301 | 25 | 19 | 0 | 6 | 1 | 16,7 % | 0,0 % |
| B307 | 21 | 19 | 0 | 2 | 0 | 0,0 % | 0,0 % |
| B404 | 16 | 2 | 1 | 14 | 6 | 42,9 % | 50,0 % |
| B605 | 11 | 9 | 0 | 2 | 0 | 0,0 % | 0,0 % |
| B201 | 10 | 8 | 0 | 2 | 0 | 0,0 % | 0,0 % |
| B102 | 7 | 2 | 0 | 5 | 0 | 0,0 % | 0,0 % |
| B603 | 7 | 0 | 0 | 7 | 3 | 42,9 % | — |
| B602 | 5 | 2 | 0 | 3 | 0 | 0,0 % | 0,0 % |
| B104 | 1 | 0 | 0 | 1 | 0 | 0,0 % | — |
| B311 | 1 | 0 | 0 | 1 | 0 | 0,0 % | — |

El ahorro se concentra en B404 (6 de 14 falsos positivos) y B603 (3 de 7). El
error de omisión aparece en B403 y B404. B301 y B307, las reglas con más
alertas reales, no pierden ninguna.

## C, C0 y D: qué explica cada diferencia

| Métrica | C (few-shot) | C0 (sin few-shot) | D (afinado) |
|---|---|---|---|
| FPRR | 2,0 % | 22,0 % | 48,0 % |
| FNR | 0,0 % | 2,2 % | 5,5 % |
| FOR | 0,0 % | 15,4 % | 17,2 % |
| Precisión | 65,0 % | 69,5 % | 76,8 % |
| Exactitud CWE | 37,4 % | 44,9 % | 43,0 % |
| Respuestas inválidas | 1 | 1 | 0 |

Hay dos saltos distintos:

1. **C → C0 (efecto del prompt).** Quitar los ejemplos resueltos sube el FPRR
   20 puntos y el FNR 2,2 puntos. La mayor parte del cambio entre C y D no
   proviene del ajuste fino, sino de dejar de empujar al modelo hacia
   `VULNERABLE` con ejemplos.
2. **C0 → D (efecto del ajuste).** Con el mismo prompt, el modelo afinado sube
   el FPRR otros 26 puntos (22 % → 48 %) y el FNR 3,3 puntos (2,2 % → 5,5 %).
   El ajuste fino compra ahorro adicional a cambio de más omisiones.

Por eso la comparación que atribuye el efecto al entrenamiento es **D contra
C0**, no D contra C. D sigue siendo el que más ahorra, pero ya no es cierto que
casi todo el mérito sea del ajuste: una parte importante es del prompt.

## CWE

C0 copia el CWE del SAST en las **89 de 89** alertas reales conservadas. Su
exactitud CWE (44,9 %) es apenas mayor que la de D (43,0 %) y que la de C
(37,4 %), pero esa diferencia está dominada por qué alertas conserva cada
configuración, no por conocimiento del modelo. El producto debe seguir mostrando
el CWE del SAST.

## Conclusión

C0 demuestra que el prompt por sí solo produce un ahorro sustancial y que el
ajuste fino agrega una segunda capa de ahorro con un costo en omisiones. La
lectura honesta del proyecto es que **el ajuste fino no es la única causa de la
mejora frente a C**: parte del salto se explica por eliminar el few-shot. D
mantiene la mejor reducción de ruido y el mejor formato (0 respuestas inválidas),
pero su FNR de 5,5 % sigue sin habilitar el descarte automático.
