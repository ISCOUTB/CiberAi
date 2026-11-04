# Borrador — Conclusiones (Sprint 8)

> Documento de trabajo. Las conclusiones sobre generalización quedan
> condicionadas a la evaluación única del holdout del Sprint 7. Las cifras de
> este borrador provienen de `eval/resultados_A.json`, `eval/resultados_C.json`
> y `eval/resultados_D.json`.

## 8.1 Respuesta a la pregunta de investigación

La pregunta era si un Qwen2.5-Coder-1.5B ajustado con QLoRA reduce el FPRR
frente al mismo modelo con el mismo prompt, sin superar un FNR del 5 %.

La respuesta, sobre las 141 alertas del conjunto de desarrollo, es **parcial**:

- **Sí reduce el ruido.** D descarta 24 de 50 falsos positivos (FPRR 48,0 %)
  frente a 1 de 50 en C (2,0 %). La diferencia no se explica por el prompt,
  porque C y D comparten prompt, conjunto y temperatura.
- **No cumple la meta de omisión.** D descarta 5 de 91 alertas reales
  (FNR 5,5 %, IC95 2,4–12,2 %). El valor puntual supera el 5 % y el intervalo
  incluye tasas considerablemente peores.

La hipótesis principal se confirma en la dirección del ahorro y se rechaza en el
umbral de seguridad. El ajuste fino vuelve al modelo más decidido, no más
certero: aprende a decir `SAFE` con más frecuencia y esa frecuencia produce a la
vez el ahorro y el riesgo.

## 8.2 Respuesta a las hipótesis secundarias

**El modelo copia el CWE del SAST.** Confirmada. En las 86 alertas reales
conservadas por D, el CWE predicho coincide con el del SAST en 86 casos; en C,
en 84 de 91. La exactitud CWE (43,0 % en D, 37,4 % en C) mide la concordancia
entre la etiqueta del SAST y la del dataset, no capacidad de clasificación. El
producto debe conservar el CWE del SAST.

**El error de omisión se concentra en reglas de importación.** Confirmada con un
matiz. Las cinco alertas reales descartadas por D son todas B403
(`import pickle`, CWE-502); tres deserializan y dos solo serializan. En B301,
B307, B605 y B608 D no descartó ninguna alerta real. El error es de una regla,
no sistémico, pero la regla afectada es precisamente una de las más ruidosas.

**El coste permite ejecutar el modelo en una GPU de 4 GB.** Confirmada. El
Q4_K_M ocupa 1.115 MB de VRAM y el proceso `llama-server` unos 700 MB de RAM;
la latencia mediana es de 4,1 s por alerta en una GTX 1650, con 4,9 s de media
incluyendo la carga inicial. Cabe una instancia, no varias en paralelo sin medir
el intercambio a disco.

## 8.3 ¿Sirve para descarte automático?

No. Con FNR 5,5 % el producto no puede eliminar alertas sin supervisión. Un
`SAFE` formalmente válido puede ser un falso negativo real y el sistema no tiene
forma de detectarlo. Eliminar la alerta trasladaría el error al analista, que ya
no sabría que existió.

La decisión de producto es el **modo asesor**: el veredicto `SAFE` recomienda
descarte, pero la alerta permanece visible y auditable. Ante un JSON inválido,
un timeout o un servicio caído, la alerta se conserva como `SOSPECHOSA`. Esa
política no es una limitación temporal; es la respuesta correcta a la evidencia
disponible.

La mitigación propuesta —nunca recomendar descarte para B403— lleva el FNR a
0 % y deja el FPRR en 38 % (19 de 50) sobre el mismo conjunto. Se pierden cinco
descartes correctos de B403, pero desaparecen los cinco falsos negativos. La
regla debe validarse con el holdout antes de codificarla.

## 8.4 Aportes del proyecto

1. **Una tubería local completa y reproducible.** Bandit, normalización,
   deduplicación, extracción de contexto por AST, prompt, validación, reporte
   JSON/SARIF y CLI, con un modelo de 1,5B cuantizado que cabe en 4 GB de VRAM.
   El código no sale de la máquina.
2. **Una evaluación pareada A/B/C/D.** C y D comparten prompt, conjunto y
   temperatura; solo cambia el modelo. Esa simetría permite atribuir la
   diferencia al ajuste fino y no a la ingeniería de prompts.
3. **Modo asesor justificado con medición.** La política conservadora se deriva
   del FNR observado y de la concentración del error en B403, no de una
   preferencia de diseño.
4. **Artefactos trazables.** Conjunto de evaluación, prompts, resultados crudos,
   hashes de los modelos, scripts de entrenamiento y de generación de
   documentos. Cada cifra del documento se rastrea hasta un archivo y un
   comando.

## 8.5 Trabajo futuro

- **Partición agrupada por proyecto o archivo** antes de abrir el holdout, para
  reducir el riesgo de filtración entre repositorios.
- **Evaluación única del test reservado** (17.542 muestras, ~140 alertas
  Python), con el protocolo congelado y sin reutilizarlo.
- **Auditoría humana de explicaciones** con la rúbrica de cuatro criterios y
  kappa de Cohen entre dos revisores ciegos.
- **Regla B403 basada en el punto de uso**: no descartar por el `import`, sino
  por la ausencia de un `pickle.load` alcanzable. Requiere análisis de flujo que
  Bandit no ofrece.
- **Medir el efecto de la cuantización**: comparar el Q4_K_M contra el modelo
  fusionado en f16 para separar ajuste de cuantización.
- **Ampliar la batería de prompt injection** con más patrones y documentar la
  política de llamadas externas y de descarga de repositorios.
- **Escalar la latencia**: batching, concurrencia medida y una política de
  reinicio del runner tras un truncamiento.

## 8.6 Condición sobre el holdout

Las conclusiones de este capítulo son válidas para el conjunto de desarrollo.
El holdout puede confirmar o refutar tres afirmaciones:

1. Que el FPRR de D se mantiene en un conjunto no usado para ajustar.
2. Que el FNR sigue concentrado en B403 o aparece en otras reglas.
3. Que la exclusión de B403 mantiene el FNR en 0 % sin destruir el ahorro.

Si el holdout confirma un FNR ≤ 5 % y el error se concentra en B403, el producto
podría habilitar una recomendación de descarte más visible, pero nunca
automática. Si el FNR supera el 5 % o se dispersa entre reglas, el modo asesor
se mantiene sin cambios y la exclusión de B403 pasa de mitigación propuesta a
regla obligatoria.

El holdout no puede confirmar que el modelo detecta vulnerabilidades que Bandit
no reporta, que el CWE predicho es correcto de forma independiente ni que el
resultado se sostiene en otros lenguajes o SAST. No es una prueba de producción;
es la última medición no contaminada de una hipótesis acotada.

## 8.7 Cierre

El proyecto demuestra que un modelo pequeño, ajustado de forma eficiente y
ejecutado localmente, puede ahorrar revisión en un conjunto acotado de alertas
de Bandit. También demuestra, con la misma medición, que ese ahorro no autoriza
a sustituir al analista. La contribución no es el ahorro en sí, sino la
comparación que permite saber cuándo es aceptable y cuándo no.
