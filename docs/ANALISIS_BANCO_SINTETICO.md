# Análisis del banco sintético etiquetado

Fecha: 8 de noviembre de 2026.

Este documento interpreta `docs/BANCO_SINTETICO.md`, que se regenera con
`python eval/banco_sintetico.py`. El banco no usa el holdout: son 26 casos nuevos,
con etiqueta a nivel de alerta, creados para medir si los modelos leen el contexto
o solo la regla y la severidad que reporta Bandit.

## 1. Qué se midió

- 26 alertas de Bandit: 14 reales y 12 falsos positivos.
- 13 reglas: B101, B105, B110, B201, B301, B307, B310, B311, B324, B602, B603,
  B605 y B608.
- Cada regla tiene al menos un caso real y uno falso positivo, salvo B201, que
  solo tiene un caso real. Esa simetría es deliberada: rompe la correlación
  «regla X siempre es real» o «regla X siempre es falsa» que el modelo pudo
  aprender del corpus de entrenamiento.
- Los dos modelos reciben el prompt del producto (`triage.build_prompt` y
  `triage.SYSTEM`), temperatura 0 y `num_predict = 512`. La política `B403`
  nunca se recomienda para descarte sigue activa.

## 2. Resultados

| Métrica | Base | IC95 base | D | IC95 D |
|---|---:|---:|---:|---:|
| SAFE (recomendaciones de descarte) | 0/26 | — | 12/26 (46,2 %) | — |
| FPRR (FP descartados) | 0,0 % | 0,0–24,3 % | 58,3 % (7/12) | 32,0–80,7 % |
| FNR (reales descartadas) | 0,0 % | 0,0–21,5 % | 35,7 % (5/14) | 16,3–61,2 % |
| Exactitud de decisión | 53,8 % | 35,5–71,2 % | 61,5 % | 42,5–77,6 % |
| Precisión de los descartes | n/a (no descartó nada) | n/a | 58,3 % | 32,0–80,7 % |
| Respuestas inválidas | 2 | — | 0 | — |

Los IC95 son de Wilson sobre 14 reales y 12 falsos positivos; son amplios. Dos
lecturas se desprenden de ellos. El FNR de D tiene límite inferior de 16,3 %, así
que supera de forma clara la meta de 5 %. La exactitud de D (61,5 %) no es
demostrablemente mayor que la del base (53,8 %): los intervalos se solapan. El +7,7
puntos debe presentarse como diferencia puntual.

El modelo base no hace triage: etiqueta casi todo como `VULNERABLE` y solo deja
dos alertas en `SOSPECHOSA` por respuestas inválidas (S02, un error 500 de Ollama
por límite de repetición de tokens; S21, JSON inválido). Su FPRR de 0 % no es un
mérito: es la consecuencia de no recomendar ningún descarte. Su exactitud del
53,8 % sale de acertar las 14 reales y fallar los 12 falsos positivos.

D sí descarta: acierta 7 de los 12 falsos positivos, pero también descarta 5 de
las 14 alertas reales. La exactitud sube 7,7 puntos y el ahorro de revisión es
real, pero el coste en FNR es alto. En modo asesor ninguna alerta se elimina; el
riesgo es que un revisor humano confíe en la recomendación y descarte una
vulnerabilidad real.

## 3. El atajo de severidad

La decisión de D se reproduce al 100 % con una sola regla:

> `SAFE` si la severidad que reporta Bandit es baja; `VULNERABLE` en cualquier
> otro caso.

| Severidad SAST | Casos | SAFE de D |
|---|---:|---:|
| baja | 12 | 12 (100 %) |
| media | 9 | 0 (0 %) |
| alta | 5 | 0 (0 %) |

La misma pauta aparece en los repositorios reales: D recomienda descartar 34 de
34 alertas de severidad baja y 0 de las 4 de severidad media o alta
(`docs/CORRIDA_REPOS_REALES.md`).

Las explicaciones de D son plantillas idénticas:

- `SAFE`: «El código no presenta el patrón vulnerable indicado.»
- `VULNERABLE`: «Se detecta un patrón asociado a CWE-XX en código Python.»

No hay una lectura del flujo ni del contexto. En este banco, D no distingue un
token generado con `random` de un `random` usado para un jitter, ni una
credencial de producción de un marcador de pruebas, ni un `assert` que protege
un borrado de un `assert` de una prueba unitaria.

## 4. Los cinco falsos negativos

| ID | Regla | Por qué es real | Veredicto D |
|---|---|---|---|
| S08 | B311 | El token de sesión se genera con `random`, que es predecible. | SAFE |
| S09 | B105 | `DB_PASSWORD` es una credencial de producción embebida. | SAFE |
| S11 | B603 | `sh -c` recibe un comando externo; la lista no evita la inyección. | SAFE |
| S13 | B101 | El control de privilegios usa `assert`; con `python -O` desaparece. | SAFE |
| S14 | B110 | El fallo de autenticación se silencia y la función devuelve `True`. | SAFE |

Los cinco tienen severidad baja. Los siete falsos positivos que D acierta
(S16, S17, S21, S22, S24, S25 y S26) también tienen severidad baja. Es el mismo
atajo en ambas direcciones.

## 5. Relación con el smoke y con la comparación C0/D

El smoke de `docs/SMOKE_REPOS.md` encontró 0 descartes incorrectos entre las 34
recomendaciones de D. Ese resultado sigue siendo válido para esos tres repos: la
mayoría de sus alertas de severidad baja son falsos positivos reales (asserts
internos, imports de `subprocess`, `Popen` con listas constantes). El banco
sintético no contradice la auditoría: muestra que el acierto del smoke se apoya
en una correlación favorable entre severidad baja y falso positivo, no en una
comprensión del contexto.

La comparación C0/D del holdout reporta FNR 9,2 % para D. El 35,7 % del banco no
es directamente comparable por tres motivos:

1. El banco es adversarial: se construyó para que la misma regla tenga casos
   reales y falsos, algo que el corpus no garantiza.
2. Es pequeño (26 alertas) y las etiquetas las puso el autor.
3. El prompt no es el mismo: el holdout usa `prompt_d`, el banco usa
   `triage.build_prompt`, que añade archivo y línea y cambia la redacción. D se
   entrenó con `prompt_d`; el cambio de plantilla es una hipótesis plausible del
   colapso a plantillas, pero no está probado.

Las tres razones impiden presentar el 35,7 % como una estimación de producción.
Lo que sí muestran los datos es que el FPRR alto de D no es evidencia de que
entienda el contexto.

## 6. Implicaciones

- **No automatizar el descarte.** El modo asesor deja de ser una precaución
  teórica: en este banco, D recomienda descartar 5 alertas reales.
- **No usar el FPRR solo.** Un modelo que descarta todo tiene FPRR del 100 % y
  FNR del 100 %. El banco reporta las dos métricas y la matriz de decisión.
- **La severidad es una señal, no una decisión.** El prompt incluye la
  severidad de Bandit; el modelo la usa como atajo. Si se quiere que el modelo
  lea el código, hay que entrenar con contraejemplos de la misma regla y
  severidad, y evaluar en un conjunto nuevo.
- **Alinear el prompt del producto con el de entrenamiento** es una tarea de
  ingeniería concreta, pero debe validarse en un conjunto nuevo. Reajustar el
  prompt mirando este banco lo convertiría en un conjunto de desarrollo y
  invalidaría su uso como evidencia.
- **No tocar el holdout.** Este banco es nuevo y no se usó para ajustar el
  modelo, las reglas ni los umbrales.

## 7. Reproducción

```powershell
python eval/banco_sintetico.py --validar
python eval/banco_sintetico.py
python eval/corrida_repos_reales.py
```

El primer comando solo ejecuta Bandit y comprueba que cada caso dispara la regla
esperada. El segundo llama a los dos modelos. El tercero clona los tres repos
pinneados en `eval/repos_reales/` y repite la corrida real.
