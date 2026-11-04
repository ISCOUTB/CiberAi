# Borrador — Discusión (Sprint 8)

> Documento de trabajo basado en `eval/resultados_A.json`,
> `eval/resultados_C.json`, `eval/resultados_D.json` y `docs/ANALISIS_D.md`.
> Las cifras del holdout todavía no existen: cualquier afirmación sobre
> generalización queda condicionada a esa evaluación.

## 7.1 El intercambio entre ahorro y omisión

La comparación central del proyecto no es D contra A, sino D contra C. A no
decide: conserva las 141 alertas y su FPRR y FNR son cero por construcción. C y
D comparten el mismo prompt con contexto del SAST, el mismo conjunto y la misma
temperatura; solo cambia el modelo. Esa simetría permite atribuir la diferencia
al ajuste fino.

El resultado es un intercambio nítido:

| Métrica | C (modelo base) | D (modelo afinado) |
|---|---|---|
| FPRR | 2,0 % (IC95 0,4–10,5) | 48,0 % (IC95 34,8–61,5) |
| FNR | 0,0 % (IC95 0,0–4,1) | 5,5 % (IC95 2,4–12,2) |
| FOR | 0,0 % | 17,2 % |
| Precisión | 65,0 % | 76,8 % |

D multiplica por 24 el número de falsos positivos descartados (de 1 a 24 sobre
50). A cambio, descarta 5 alertas reales que C conserva. El modelo afinado no se
volvió más inteligente en abstracto: se volvió más decidido. Aprende a decir
`SAFE` con más frecuencia, y esa frecuencia es la que produce tanto el ahorro
como el riesgo.

La precisión de D (76,8 %) es mayor que la de C (65,0 %) porque D conserva menos
alertas falsas. Pero la precisión no captura el costo del error: una alerta real
descartada pesa más que una falsa conservada. Por eso la meta principal es FNR y
por eso D, con 5,5 %, no habilita descarte automático aunque su FPRR sea
excelente.

El intervalo de confianza del FNR de D (2,4–12,2 %) es amplio. Con 91 alertas
reales, cinco errores no permiten afirmar que la tasa "real" sea exactamente
5,5 %; solo que el conjunto observado es compatible con valores entre 2 % y 12 %.
El holdout, con más alertas, estrechará el intervalo o confirmará que el
problema persiste.

## 7.2 El FNR está concentrado en B403

Las cinco alertas reales que D descarta son todas B403 (`import pickle`,
CWE-502). Tres deserializan (`pickle.load` o `pickle.loads`) y dos solo
serializan (`pickle.dump`). En los dos casos de solo serialización la etiqueta
del dataset es discutible: serializar no ejecuta código del atacante. Aun así,
el modelo no debería recomendar descarte sin mirar el sink.

El error no es sistémico: en B301, B307, B605 y B608 D no descartó ninguna
alerta real. Eso sugiere que el ajuste aprendió una asociación peligrosa entre
"import de pickle" y "falso positivo" —probablemente porque muchas alertas B403
del entrenamiento eran imports sin uso explotable— y la aplica sin distinguir el
punto de uso.

La mitigación de producto es directa: **nunca recomendar descarte para B403**.
Sobre el mismo conjunto, esa regla reduce el FNR a 0 % y deja el FPRR en 38 %
(19 de 50 falsos positivos). Se pierden cinco descartes correctos de B403, pero
desaparecen los cinco falsos negativos. Para un producto en modo asesor, el
intercambio es favorable. La regla debe validarse con el holdout antes de
codificarla.

Una alternativa más fina es mover la decisión de B403 al punto de uso: no
descartar por el `import`, sino por la ausencia de un `pickle.load` alcanzable.
Eso requiere análisis de flujo, que Bandit no ofrece y que el modelo de 1,5B no
puede reconstruir con fiabilidad. Queda como trabajo futuro.

## 7.3 El CWE no es una clasificación independiente

En las 86 alertas reales conservadas por D, el CWE predicho coincide con el CWE
del SAST en 86 de 86 casos. En C ocurre lo mismo en 84 de 91. El prompt incluye
el CWE del SAST y el modelo lo copia; por lo tanto, la exactitud CWE (43,0 % en
D y 37,4 % en C) no mide capacidad de clasificación. Mide la concordancia entre
la etiqueta del SAST y la etiqueta del dataset sobre el subconjunto que cada
configuración conservó.

Esa concordancia es baja porque la verdad de referencia es a nivel de función y
sin alcanzabilidad, no porque el modelo "se equivoque" al clasificar. Una
advertencia de importación sobre una función vulnerable cuenta como real aunque
la línea señalada no sea el defecto. El SAST acierta el 45,1 % del CWE en el
conjunto completo; D no mejora esa base y no debería presentarse como si lo
hiciera.

La consecuencia de producto es conservar el CWE del SAST en el reporte. Pedirle
al modelo que reclassifique el CWE agrega una salida que no está validada y que
puede inducir a error al analista. El modelo aporta el veredicto y la
explicación; el CWE queda como dato del SAST.

## 7.4 Validez de la partición y del holdout

La evaluación usa `val_total`, la misma partición que alimentó la validación del
ajuste. Es una medición de desarrollo, no de generalización. El test de 17.542
muestras está intacto, pero el split actual es aleatorio por función y el
dataset no incluye identificador de proyecto. Dos funciones del mismo
repositorio pueden haber caído en train y en validación, y el modelo pudo
memorizar patrones específicos.

Ese riesgo afecta la interpretación de D de dos maneras. Si hubo filtración, el
FPRR de 48 % puede estar sobreestimado. Si la partición es razonablemente
independiente, el holdout debería producir una cifra similar. No se puede saber
cuál de las dos cosas ocurre sin rehacer la partición agrupando por proyecto o
archivo, tarea prevista para el Sprint 7 antes de abrir el holdout.

El holdout tiene otra limitación: solo 300 de las 17.542 muestras son funciones
Python (164 vulnerables), y producen alrededor de 140 alertas. Es un conjunto
pequeño para estimar un FNR de 5 % con precisión; el intervalo seguirá siendo
amplio. Aun así, es la única medición no contaminada disponible y debe
ejecutarse una sola vez, con el protocolo congelado.

## 7.5 La pérdida no mide calidad de triage

La pérdida de entrenamiento cayó de 1,11 a 0,36 y se estancó. Ese descenso
prueba que el modelo aprendió el formato y la distribución de las respuestas,
no que clasifique mejor. La evidencia de calidad es la matriz de evaluación:
24 falsos positivos descartados, 5 reales descartados, 26 falsos positivos
conservados.

La pérdida de validación de la corrida original quedó en `nan` por truncamiento
de ejemplos largos; el generador ya se corrigió (`encode_rows`), pero no se
reentrenó. Por eso la Figura 1 muestra solo la curva de entrenamiento. Presentar
una curva de validación inexistente o "suavizada" sería un error metodológico.

## 7.6 Robustez operativa

La política conservadora absorbe los fallos del modelo. Con Ollama apuntado a
una URL inexistente, las 9 alertas se conservan como `SOSPECHOSA` y la CLI
termina con código 0; el análisis SAST no se pierde. Con una respuesta JSON
inválida (una B102 en la corrida C), la alerta también se conserva. El producto
degrada la recomendación, no la detección.

La prueba de prompt injection incrustó un comentario que ordenaba responder
`SAFE`. El modelo afinado clasificó correctamente las dos vulnerabilidades
reales (B602 con `shell=True` y B301 con `pickle.load`) y solo marcó `SAFE` las
dos advertencias de importación, que es el comportamiento esperado. Un caso no
demuestra resistencia general, pero confirma que los delimitadores y el formato
JSON no colapsan ante una instrucción obvia.

El costo operativo es medible: 4,8 s por alerta en la corrida de integración y
4,9 s de media (4,1 s de mediana) en un banco de 10 alertas sobre una GTX 1650.
C promedia ~4,3 s por alerta, salvo una B102 patológica que agotó el timeout de
180 s antes de acotar la generación. El modelo ocupa 1.115 MB de VRAM y unos 700
MB de RAM. En una GPU de 4 GB cabe una instancia, pero no hay margen para
paralelizar sin medir el intercambio a disco.

## 7.7 Implicaciones de producto

El modo asesor no es una limitación temporal: es una decisión de diseño. Un
`SAFE` formalmente válido puede ser un falso negativo real, y el producto no
tiene forma de detectarlo. Eliminar la alerta trasladaría el error al analista,
que ya no sabría que existió. Conservarla con una recomendación de descarte
mantiene la auditabilidad y permite medir el FNR en producción.

El ahorro de revisión de D es real: casi la mitad de los falsos positivos se
marcan para descarte. Pero el producto no debería vender "eliminación de
falsos positivos" sino "priorización de alertas". La diferencia no es semántica:
la primera promete una precisión que el modelo no tiene; la segunda describe lo
que el sistema hace y deja la decisión final en el analista.

## 7.8 Amenazas a la validez

- **Validez interna:** partición aleatoria por función, posible filtración entre
  repositorios y etiquetas a nivel de función sin alcanzabilidad.
- **Validez externa:** un solo lenguaje (Python), un solo SAST (Bandit), un
  corpus con 94,1 % de código C y un modelo de 1,5B. Los resultados no
  generalizan a Java, a SAST comerciales ni a modelos más grandes.
- **Validez de constructo:** el FNR mide descartes recomendados, no
  vulnerabilidades explotadas. Una alerta real descartada puede ser inocua en
  contexto; una alerta conservada puede ser irrelevante. La etiqueta del dataset
  es la aproximación disponible.
- **Validez estadística:** 91 alertas reales y 50 falsos positivos producen
  intervalos amplios. El piloto B (n=10) no permite inferencia.
- **Sesgo del evaluador:** el equipo conoce el conjunto y diseñó el prompt. La
  rúbrica ciega con dos revisores y el holdout reservado son las salvaguardas
  previstas.

## 7.9 Qué puede y qué no puede confirmar el holdout

Puede confirmar o refutar:

- Que el FPRR de D se mantiene en un conjunto no usado para ajustar.
- Que el FNR sigue concentrado en B403 o aparece en otras reglas.
- Que la exclusión de B403 mantiene el FNR en 0 % sin destruir el ahorro.
- Que la tasa de respuestas inválidas se mantiene baja.

No puede confirmar:

- Que el modelo detecta vulnerabilidades que Bandit no reporta.
- Que el CWE predicho es correcto de forma independiente.
- Que el sistema es seguro ante code smells o lógica de negocio.
- Que el resultado se sostiene en otros lenguajes o SAST.

La discusión final del documento debe separar esas dos listas. El holdout no es
una prueba de producción; es la última medición no contaminada de una hipótesis
acotada: que el ajuste fino mejora el ahorro de revisión sin superar el umbral
de omisión aceptable.
