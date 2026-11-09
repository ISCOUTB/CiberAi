# Borrador — Discusión (Sprint 8)

> Documento de trabajo basado en `eval/resultados_{A,C,C0,D}.json`, en los
> resultados del holdout (`eval/resultados_holdout_{A,C0,D}.json`), en
> `docs/ANALISIS_D.md` y `docs/ANALISIS_HOLDOUT.md`, y en la evidencia posterior
> del banco sintético (`eval/banco_sintetico.json`) y de los repositorios reales
> (`eval/corrida_repos_reales.json`). Las cifras de desarrollo, las del holdout y
> las del banco se reportan por separado; no se mezclan.

## 7.1 El intercambio entre ahorro y omisión

La comparación central del proyecto no es D contra A, sino D contra C. A no
decide: conserva las 141 alertas y su FPRR y FNR son cero por construcción. En
desarrollo, C y D no comparten prompt: C antepone dos ejemplos resueltos
(*few-shot*) y D no. Esa diferencia mezcla el efecto del ajuste con el de los
ejemplos. Para aislar el ajuste se agregó **C0**, el modelo base con el mismo
formato de alerta que D y sin ejemplos. La comparación que atribuye la
diferencia al entrenamiento es **D contra C0**; D contra C describe el resultado
práctico frente a un prompt cuidado, pero no aísla una sola variable.

En desarrollo el intercambio es nítido:

| Métrica | C (base + few-shot) | C0 (base sin few-shot) | D (afinado) |
|---|---:|---:|---:|
| FPRR | 2,0 % (IC95 0,4–10,5) | 22,0 % | 48,0 % (IC95 34,8–61,5) |
| FNR | 0,0 % (IC95 0,0–4,1) | 2,2 % | 5,5 % (IC95 2,4–12,2) |
| FOR | 0,0 % | 15,4 % | 17,2 % |
| Precisión | 65,0 % | — | 76,8 % |

El ajuste fino, frente a C0, suma 26 puntos de FPRR y 3,3 puntos de FNR. No
vuelve al modelo más inteligente en abstracto: lo vuelve más decidido. Aprende
a decir `SAFE` con más frecuencia, y esa frecuencia produce a la vez el ahorro y
el riesgo. Frente a C el contraste es mayor (+46 puntos), pero no es atribuible
solo al entrenamiento.

El holdout confirma la dirección y modera la magnitud:

| Métrica | C0 | D crudo | D + política B403 |
|---|---:|---:|---:|
| FPRR | 10,9 % (IC95 4,7–23,0) | 30,4 % (IC95 19,1–44,8) | 19,6 % (IC95 10,7–33,2) |
| FNR | 0,0 % (IC95 0,0–5,6) | **9,2 %** (IC95 4,3–18,7) | 3,1 % (IC95 0,8–10,5) |
| FOR | 0,0 % | 30,0 % | 18,2 % |
| Precisión | 61,3 % | 64,8 % | 63,0 % |

D descarta 18 alertas que C0 conserva: 6 reales y 12 falsos positivos. C0
descarta 3 que D conserva: 0 reales y 3 falsos positivos. En términos netos D
recomienda 15 descartes más, pero paga con 6 alertas reales adicionales. El
ahorro sobre C0 cae de +26 a **+19,6 puntos** crudos; con la política B403 queda
en **+8,7 puntos**. Los “+46 puntos” de desarrollo comparaban D contra C y no se
sostienen en el holdout.

La precisión de D es mayor que la de C0 porque conserva menos alertas falsas.
Pero la precisión no captura el costo del error: una alerta real descartada pesa
más que una falsa conservada. Por eso la meta principal es FNR y por eso D, con
9,2 % crudo, no habilita descarte automático aunque su FPRR sea apreciable.

La evidencia posterior del banco sintético (§7.12) refuerza esta lectura desde
otro ángulo: cuando el conjunto contiene la misma regla con casos reales y
falsos, D descarta 5 de 14 alertas reales (FNR 35,7 %) y acierta 7 de 12 falsos
positivos (FPRR 58,3 %). El ahorro que en el corpus parece comprensión del
contexto se reproduce con una regla trivial sobre la severidad. El banco no
reemplaza al holdout —es adversarial, pequeño y de un solo anotador—, pero
explica el mecanismo que el holdout solo puede medir.

## 7.2 El FNR ya no está solo en B403

En desarrollo las cinco alertas reales que D descartaba eran todas B403
(`import pickle`, CWE-502). Tres deserializaban y dos solo serializaban. En el
holdout el error se reparte entre dos reglas:

| Regla | Alertas | Reales | FN | FPRR de la regla |
|---|---:|---:|---:|---:|
| B403 | 15 | 8 | 4 | 5 de 7 falsos positivos |
| B311 | 3 | 3 | 2 | — |
| Resto | — | 54 | 0 | — |

Los cuatro B403 incluyen dos deserializaciones explotables (`f11445.py` y
`f1878.py`) y dos que solo serializan (`f15804.py` y `f2231.py`). Los dos B311
son líneas de un mismo ejemplo con `random.randint`, etiquetadas CWE-94 en el
dataset aunque Bandit reporta CWE-330; la etiqueta es ruidosa, pero el modelo no
debería descartarlas.

La lectura cambia respecto del Sprint 6. El error sigue concentrado en reglas de
importación, pero **B403 ya no explica todo el FNR**. La mitigación de producto
—nunca recomendar descarte para B403— rescata 4 de los 6 falsos negativos y baja
el FNR a **3,1 %**, pero deja 2 B311 y un intervalo superior de 10,5 %. No
alcanza para afirmar ≤ 5 %.

Agregar B311 a la política llevaría el FNR a 0 %, pero sería una decisión
post hoc: la regla se elegiría después de ver el holdout. No se adopta. Se
reporta como riesgo nuevo y como trabajo futuro que requiere un conjunto
independiente. Una alternativa más fina para B403 sigue siendo mover la decisión
al punto de uso: no descartar por el `import`, sino por la ausencia de un
`pickle.load` alcanzable. Eso requiere análisis de flujo, que Bandit no ofrece y
que el modelo de 1,5B no puede reconstruir con fiabilidad.

El banco sintético confirma que el problema no se limita a las reglas de
importación. Sus cinco falsos negativos son B311, B105, B603, B101 y B110, todos
de severidad baja; ninguno es B403. La coincidencia con el holdout es que B311
vuelve a aparecer, pero el banco añade reglas que el corpus de evaluación no
había puesto a prueba. El patrón común no es la regla: es la severidad baja. Eso
desplaza la política de «excluir B403» hacia una pregunta más incómoda: el modelo
no está leyendo el contexto que justifica cada excepción.

## 7.3 El CWE no es una clasificación independiente

En las 86 alertas reales conservadas por D en desarrollo, el CWE predicho
coincide con el CWE del SAST en 86 de 86 casos. En C ocurre lo mismo en 84 de 91.
En el holdout, D copia el CWE del SAST en **59 de 59** alertas reales
conservadas. El prompt incluye el CWE del SAST y el modelo lo copia; por lo
tanto, la exactitud CWE (43,0 % en D de desarrollo, 32,2 % en el holdout) no mide
capacidad de clasificación. Mide la concordancia entre la etiqueta del SAST y la
etiqueta del dataset sobre el subconjunto que cada configuración conservó.

Esa concordancia es baja porque la verdad de referencia es a nivel de función y
sin alcanzabilidad, no porque el modelo “se equivoque” al clasificar. Una
advertencia de importación sobre una función vulnerable cuenta como real aunque
la línea señalada no sea el defecto. El SAST acierta el 45,1 % del CWE en el
conjunto de desarrollo y el 35,4 % en el holdout; D no mejora esa base y no
debería presentarse como si lo hiciera.

La consecuencia de producto es conservar el CWE del SAST en el reporte. Pedirle
al modelo que reclasifique el CWE agrega una salida que no está validada y que
puede inducir a error al analista. El modelo aporta el veredicto; el CWE queda
como dato del SAST. En esta versión la explicación también es genérica, así que
el reporte debe apoyarse en el contexto del SAST y en la revisión humana.

## 7.4 Validez de la partición y del holdout

La evaluación de desarrollo usa `val_total`, la misma partición que alimentó la
validación del ajuste. Es una medición de desarrollo, no de generalización. El
holdout usa el split `test`, que no se usó para entrenar ni para ajustar prompts
ni hiperparámetros y se evaluó **una sola vez**. Aun así, la partición sigue
siendo aleatoria por función: el dataset no incluye identificador de repositorio,
de modo que dos funciones del mismo proyecto pueden haber caído en train y en
test. La comparación exacta de hashes normalizados contra `train_80` y
`val_total` dio **0 coincidencias**, pero no se midieron casi-duplicados. Esa
medición queda pendiente y se declara como amenaza a la validez.

El holdout tuvo 111 alertas sobre 71 archivos y 98 funciones, con solo 71 códigos
únicos: 40 filas repiten exactamente el mismo código. Las observaciones no son
independientes y el tamaño efectivo es menor que 111. Por eso, además del
intervalo de Wilson, se reporta un bootstrap agrupado por archivo. Con ese
remuestreo el FNR de D + B403 va de 0,0 % a 10,2 % y el FPRR de 9,4 % a 31,2 %.

La limitación más importante es la potencia. Con **65 alertas reales**, incluso
0 falsos negativos deja el límite superior del IC95 en 5,6 %. El holdout no
alcanza para demostrar estadísticamente que el FNR sea ≤ 5 %; solo permite
descartar tasas mucho peores. Esa frase debe quedar en la memoria y no
reemplazarse por el valor puntual.

La segunda limitación es más grave: la similitud entre funciones del holdout y
funciones de train/val. `eval/casi_duplicados.py` mide casi-duplicados por
tokens: el **70,3 % de las funciones del holdout tiene un vecino con similitud
≥ 0,8** en train o val, y 45/111 tienen similitud ≥ 0,9. Los pares más altos son
variantes del mismo patrón (`pickle.__reduce__`, Flask + `sqlite3`). El
proyecto no puede demostrar que esas similitudes sean fuga real, porque el
dataset no tiene identificador de repositorio, pero sí puede decir que la
partición aleatoria por función no garantiza independencia. Esa amenaza debe
aparecer junto con las métricas de generalización.

## 7.5 La pérdida no mide calidad de triage

La pérdida de entrenamiento cayó de 1,11 a 0,36 y se estancó. Ese descenso prueba
que el modelo aprendió el formato y la distribución de las respuestas, no que
clasifique mejor. La evidencia de calidad es la matriz de evaluación: en
desarrollo, 24 falsos positivos descartados, 5 reales descartados y 26 falsos
positivos conservados; en el holdout, 14 falsos positivos descartados, 6 reales
descartados y 32 conservados.

La pérdida de validación de la corrida original quedó en `nan` por truncamiento
de ejemplos largos; el generador ya se corrigió (`encode_rows`), pero no se
reentrenó. Por eso la Figura 1 muestra solo la curva de entrenamiento. Presentar
una curva de validación inexistente o “suavizada” sería un error metodológico.

## 7.6 Las explicaciones colapsaron a plantillas

El holdout agregó una evidencia que la matriz de confusión no muestra: D produce
**11 explicaciones, 8 vectores de ataque y 2 correcciones únicas** para 111
alertas. C0 produce 109, 103 y 106, respectivamente. Además, 91 de 91 respuestas
`VULNERABLE` de D comparten la misma corrección (“Aplicar validación de entradas
y sanitización”) y 47 comparten la misma explicación de CWE-78.

La causa está en los datos de entrenamiento: 5.489 de 5.755 respuestas seguras
tienen exactamente la misma explicación y solo hay 28 vectores distintos. El
modelo aprendió la plantilla, no un análisis específico del código. D sirve como
**clasificador de triage**, no como generador de explicaciones técnicas. La
rúbrica de explicaciones sigue pendiente, pero su resultado ya está condicionado
por esta falta de diversidad: no se puede evaluar la calidad técnica de una
plantilla repetida como si fuera análisis individual. La memoria debe reportar
la diversidad junto con el kappa.

El banco sintético reproduce el fenómeno con el prompt del producto: D usa
exactamente dos explicaciones, una para `SAFE` («El código no presenta el patrón
vulnerable indicado.») y otra para `VULNERABLE` («Se detecta un patrón asociado a
CWE-XX en código Python.»). No es un artefacto del arnés de evaluación: también
aparece en la ruta que usa la CLI. Cambiar el prompt no revirtió el colapso, así
que la causa más probable sigue estando en los datos de ajuste y no solo en la
plantilla de inferencia.

## 7.7 Robustez operativa

La política conservadora absorbe los fallos del modelo. Con Ollama apuntado a una
URL inexistente, las 9 alertas se conservan como `SOSPECHOSA` y la CLI termina
con código 0; el análisis SAST no se pierde. Con una respuesta JSON inválida (una
B102 en la corrida C y una en C0 del holdout), la alerta también se conserva. El
producto degrada la recomendación, no la detección.

La prueba de prompt injection incrustó un comentario que ordenaba responder
`SAFE`. El modelo afinado clasificó correctamente las dos vulnerabilidades reales
(B602 con `shell=True` y B301 con `pickle.load`) y solo marcó `SAFE` las dos
advertencias de importación, que es el comportamiento esperado. Un caso no
demuestra resistencia general, pero confirma que los delimitadores y el formato
JSON no colapsan ante una instrucción obvia.

El costo operativo es medible: 4,8 s por alerta en la corrida de integración y
4,9 s de media (4,1 s de mediana) en un banco de 10 alertas sobre una GTX 1650.
C promedia ~4,3 s por alerta, salvo una B102 patológica que agotó el timeout de
180 s antes de acotar la generación. El modelo ocupa 1.115 MB de VRAM y unos 700
MB de RAM. En una GPU de 4 GB cabe una instancia, pero no hay margen para
paralelizar sin medir el intercambio a disco.

## 7.8 Implicaciones de producto

El modo asesor no es una limitación temporal: es una decisión de diseño. Un
`SAFE` formalmente válido puede ser un falso negativo real, y el producto no
tiene forma de detectarlo. Eliminar la alerta trasladaría el error al analista,
que ya no sabría que existió. Conservarla con una recomendación de descarte
mantiene la auditabilidad y permite medir el FNR en producción.

Si se usa D, la política B403 es **obligatoria**, no opcional: sin ella el FNR
crudo es 9,2 % y con ella 3,1 %. Pero la política no vuelve seguro al modelo:
quedan 2 B311 y el intervalo superior sigue por encima de la meta. El producto
no debería vender “eliminación de falsos positivos” sino “priorización de
alertas”. La diferencia no es semántica: la primera promete una precisión que el
modelo no tiene; la segunda describe lo que el sistema hace y deja la decisión
final en el analista.

## 7.9 Amenazas a la validez

- **Validez interna:** partición aleatoria por función, posible filtración entre
  repositorios y etiquetas a nivel de función sin alcanzabilidad. El holdout se
  ejecutó sin reagrupar; la comparación exacta de hashes dio 0 coincidencias, y
  el análisis de casi-duplicados encontró que el 70,3 % de las funciones del
  holdout tienen un vecino ≥ 0,8 en train/val.
- **Validez externa:** un solo lenguaje (Python), un solo SAST (Bandit), un
  corpus con 94,1 % de código C y un modelo de 1,5B. Los resultados no
  generalizan a Java, a SAST comerciales ni a modelos más grandes.
- **Validez de constructo:** el FNR mide descartes recomendados, no
  vulnerabilidades explotadas. Una alerta real descartada puede ser inocua en
  contexto; una alerta conservada puede ser irrelevante. La etiqueta del dataset
  es la aproximación disponible.
- **Validez estadística:** 91 alertas reales en desarrollo y 65 en el holdout
  producen intervalos amplios. El piloto B (n=10) no permite inferencia. El
  bootstrap por archivo es más conservador que Wilson y debe citarse junto con
  él.
- **Validez del banco sintético:** 26 alertas, un solo anotador (el autor) y
  construcción adversarial. No es una estimación de producción; sirve para
  probar una hipótesis mecánica —si D lee el contexto o la severidad—, no para
  estimar FPRR ni FNR poblacionales. Además usa el prompt del producto y no
  `prompt_d`, así que sus cifras no son directamente comparables con C0/D.
- **Sesgo del evaluador:** el equipo conoce el conjunto y diseñó el prompt. La
  rúbrica ciega con dos revisores y el holdout reservado son las salvaguardas
  previstas; la rúbrica aún no se aplicó.

## 7.10 Qué confirmó y qué no confirmó el holdout

Confirmó:

- Que el FPRR de D cae respecto de desarrollo: 30,4 % crudo y 19,6 % con B403,
  frente a 48,0 % en desarrollo.
- Que el FNR no se concentra solo en B403: aparecen 2 B311.
- Que la exclusión de B403 mejora el FNR (3,1 %) pero **no lo lleva a 0 %**.
- Que la tasa de respuestas inválidas se mantiene baja: 0 en D y 1 en C0.
- Que las explicaciones de D son plantillas repetidas, no análisis individuales.

No confirmó:

- Que el modelo cumpla FNR ≤ 5 %: el valor puntual con B403 lo cumple, pero el
  IC95 llega a 10,5 % y el bootstrap a 10,2 %.
- Que la exclusión de B403 sea suficiente como política de producto.
- Que el CWE predicho sea correcto de forma independiente.
- Que el modelo detecte vulnerabilidades que Bandit no reporta.
- Que el resultado se sostenga en otros lenguajes o SAST.
- Que la partición sea independiente: el 70,3 % de las funciones del holdout
  tienen un vecino ≥ 0,8 en train/val, lo que deja abierta la hipótesis de fuga.

El holdout no es una prueba de producción; es la última medición no contaminada
de una hipótesis acotada. El resultado honesto es que D reduce el ruido de forma
modesta y que el costo en omisión sigue impidiendo el descarte automático.

## 7.11 Lectura por categoría OWASP

El mapeo por CWE muestra que el proyecto no cubre el Top 10 de forma uniforme:
A03 (Injection) y A08 (Software and Data Integrity Failures) concentran el 96,5 %
de las alertas de desarrollo y el 95,5 % del holdout. A01 y A02 aparecen de forma
marginal (3 y 1 alerta en desarrollo; 1 y 3 en el holdout), y A04, A05, A06, A07,
A09 y A10 no tienen ninguna alerta medida.

Esa concentración explica por qué la política B403 tiene tanto efecto: B403 y
B301 son las dos reglas de deserialización que sostienen A08, y B403 es la que
concentra los falsos negativos de D. También explica por qué el resultado no
generaliza a otras categorías: el modelo aprendió el patrón dominante del corpus,
no una noción general de «alerta real».

La lectura por categoría agrega una conclusión de alcance, no de desempeño. El
producto puede presentarse como un triage de alertas de Bandit con cobertura
medida en A01–A03 y A08, y no como un escáner del Top 10 completo. A05, A06, A09
y A10 quedan fuera por construcción: requieren configuración de despliegue,
inventario de dependencias, observación de runtime y seguimiento de red, que un
análisis estático del AST no provee.

La misma lógica se aplica al agente. Ocho de los diez riesgos del OWASP Top 10 for
LLM Applications 2025 tienen evidencia propia en el proyecto, LLM07 aplica con
riesgo bajo y solo LLM08 queda excluido porque no hay RAG. Ese mapeo no mejora
las métricas; hace visible qué controles ya existían y cuáles faltan. El detalle
está en `docs/OWASP.md` y la matriz se regenera con
`python eval/cobertura_owasp.py`.

## 7.12 Evidencia posterior: banco sintético y repositorios reales

Después de cerrar el holdout se construyeron dos pruebas que no lo reutilizan y
que no ajustaron el modelo, los prompts ni las reglas: un banco sintético
etiquetado de 26 alertas y una corrida sobre tres repositorios reales pinneados.
Ninguna de las dos reemplaza al holdout; agregan evidencia sobre el mecanismo, no
sobre la tasa poblacional.

El banco contiene 14 alertas reales y 12 falsos positivos, con al menos un caso
de cada tipo para 12 de las 13 reglas. Esa simetría rompe la correlación «esta
regla siempre es real» que el corpus de entrenamiento no garantiza. Los dos
modelos reciben el prompt del producto (`triage.build_prompt` y `triage.SYSTEM`),
no el `prompt_d` del arnés de evaluación.

| Métrica | Base | IC95 base | D | IC95 D |
|---|---:|---:|---:|---:|
| SAFE (recomendaciones de descarte) | 0/26 | — | 12/26 (46,2 %) | — |
| FPRR | 0,0 % | 0,0–24,3 % | 58,3 % (7/12) | 32,0–80,7 % |
| FNR | 0,0 % | 0,0–21,5 % | 35,7 % (5/14) | 16,3–61,2 % |
| Exactitud de decisión | 53,8 % | 35,5–71,2 % | 61,5 % | 42,5–77,6 % |
| Precisión de los descartes | n/a | n/a | 58,3 % | 32,0–80,7 % |
| Respuestas inválidas | 2 | — | 0 | — |

Los intervalos son de Wilson al 95 %. Con 14 reales y 12 falsos positivos son
amplios, y cambian la lectura de dos formas. Primero, el FNR de D tiene un límite
inferior de 16,3 %: incluso en el escenario más favorable supera la meta de 5 %,
así que el incumplimiento es claro. Segundo, la exactitud de D no es demostrablemente
mejor que la del base: los intervalos se solapan casi por completo (35,5–71,2 frente
a 42,5–77,6). El +7,7 puntos se reporta como diferencia puntual, no como mejora
estadística. Estos intervalos son independientes y no sustituyen una prueba pareada
sobre las mismas 26 alertas.

El resultado central no es el 35,7 % puntual: es que la decisión de D se reproduce
**26/26** con la regla «`SAFE` si la severidad del SAST es baja; `VULNERABLE` en
otro caso». Esa coincidencia tiene un IC95 de Wilson de 87,1–100 %. Los 12 casos de severidad baja reciben `SAFE`; los 9 medios y 5
altos, `VULNERABLE`. Los cinco falsos negativos son S08 (B311), S09 (B105), S11
(B603), S13 (B101) y S14 (B110). No hay lectura del flujo ni del contexto: el
modelo aprendió que severidad baja equivale a descarte.

La corrida real apunta en la misma dirección. Sobre 38 alertas de `itsdangerous`,
`pyjwt` y `httpie`, D recomienda descartar 34 (89,5 %) y el modelo base 4
(10,5 %); D descarta **34 de 34** alertas de severidad baja y **0 de 4** medias o
altas. Las 38 alertas se conservan en ambos casos y D no produjo errores. La
corrida no tiene verdad de referencia, así que no produce FPRR ni FNR: mide
cuánto ahorraría una revisión, no si el ahorro es correcto.

Esa distinción es la que el banco resuelve. La corrida real sola sugeriría que D
acierta porque descarta casi todo; el banco, con etiquetas, muestra que descarta
también 5 reales. La conjunción de ambas pruebas es el argumento más fuerte
contra el descarte automático: el ahorro es real y barato, pero se apoya en una
señal que no distingue contexto.

Límites que deben citarse junto con estas cifras: el banco tiene 26 alertas y un
solo anotador; es adversarial y no representa la prevalencia del corpus; usa el
prompt del producto y no el de entrenamiento, de modo que el cambio de plantilla
puede explicar parte del colapso de las explicaciones; y la corrida real no está
etiquetada. Ninguna de las dos se usó para ajustar prompts, reglas ni umbrales, y
el holdout permaneció intacto. El detalle reproducible está en
`docs/BANCO_SINTETICO.md`, `docs/ANALISIS_BANCO_SINTETICO.md` y
`docs/CORRIDA_REPOS_REALES.md`.
