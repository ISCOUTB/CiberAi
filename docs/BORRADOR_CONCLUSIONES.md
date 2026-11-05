# Borrador — Conclusiones (Sprint 8)

> Documento de trabajo. Las cifras de desarrollo provienen de
> `eval/resultados_{A,C,C0,D}.json`; las de generalización, del holdout
> ejecutado una sola vez en el Sprint 7 (`eval/resultados_holdout_{A,C0,D}.json`
> y `docs/ANALISIS_HOLDOUT.md`). Las dos mediciones se reportan por separado.

## 8.1 Respuesta a la pregunta de investigación

La pregunta era si un Qwen2.5-Coder-1.5B ajustado con QLoRA reduce el FPRR sin
superar un FNR del 5 %. La comparación que aísla el ajuste fino es **D contra
C0**, porque comparten formato de alerta, conjunto y temperatura; C agrega
few-shot y no sirve como control principal.

La respuesta es **parcial y condicionada**:

- **Sí reduce el ruido, pero menos de lo observado en desarrollo.** En
  desarrollo D descarta 24 de 50 falsos positivos (FPRR 48,0 %) frente a 11 de
  50 en C0 (22,0 %). En el holdout descarta 14 de 46 (30,4 %) frente a 5 de 46
  en C0 (10,9 %). La dirección se mantiene; la magnitud cae.
- **No cumple la meta de omisión en el holdout.** En desarrollo el FNR era
  5,5 % (5/91). En el holdout sube a **9,2 % (6/65)**: 4 B403 y 2 B311. La
  política B403 lo baja a 3,1 % (2/65, IC95 0,8–10,5 %), pero el intervalo
  superior sigue por encima del 5 % y el bootstrap por archivo llega a 10,2 %.
- **Con 65 alertas reales el holdout no tiene potencia para demostrar ≤ 5 %.**
  Incluso 0 falsos negativos dejaría el IC95 superior en 5,6 %. La conclusión no
  puede ser “cumple por el valor puntual”, sino “no se puede demostrar que
  cumpla”.

La hipótesis se confirma en la dirección del ahorro y se rechaza en el umbral de
seguridad. El ajuste fino vuelve al modelo más decidido, no más certero: aprende
a decir `SAFE` con más frecuencia y esa frecuencia produce a la vez el ahorro y
el riesgo.

## 8.2 Respuesta a las hipótesis secundarias

**El modelo copia el CWE del SAST.** Confirmada. En desarrollo, el CWE predicho
coincide con el del SAST en 86 de 86 alertas reales conservadas por D; en el
holdout, en 59 de 59. La exactitud CWE (43,0 % en desarrollo, 32,2 % en el
holdout) mide la concordancia entre la etiqueta del SAST y la del dataset, no
capacidad de clasificación. El producto debe conservar el CWE del SAST.

**El error de omisión se concentra en reglas de importación.** Confirmada con un
matiz importante. En desarrollo las cinco alertas reales descartadas eran B403.
En el holdout son 4 B403 y **2 B311**; el error sigue concentrado en reglas de
importación y aleatoriedad, pero ya no en una sola. B403 es la parte mitigable;
B311 aparece como riesgo nuevo y no se convierte en regla después de ver el
holdout.

**El coste permite ejecutar el modelo en una GPU de 4 GB.** Confirmada. El
Q4_K_M ocupa 1.115 MB de VRAM y el proceso `llama-server` unos 700 MB de RAM; la
latencia mediana es de 4,1 s por alerta en una GTX 1650, con 4,9 s de media
incluyendo la carga inicial. Cabe una instancia, no varias en paralelo sin medir
el intercambio a disco.

**Las explicaciones son un aporte de calidad.** Rechazada. D produce 11
explicaciones, 8 vectores y 2 correcciones únicas para 111 alertas; 91 de 91
`VULNERABLE` comparten la misma corrección. En el entrenamiento, 5.489 de 5.755
respuestas seguras tienen la misma explicación. D sirve para triage, no para
explicar.

## 8.3 ¿Sirve para descarte automático?

No. Con FNR crudo 9,2 % en el holdout el producto no puede eliminar alertas sin
supervisión. Un `SAFE` formalmente válido puede ser un falso negativo real y el
sistema no tiene forma de detectarlo. Eliminar la alerta trasladaría el error al
analista, que ya no sabría que existió.

La decisión de producto es el **modo asesor**: el veredicto `SAFE` recomienda
descarte, pero la alerta permanece visible y auditable. Ante un JSON inválido,
un timeout o un servicio caído, la alerta se conserva como `SOSPECHOSA`. Esa
política no es una limitación temporal; es la respuesta correcta a la evidencia
disponible.

La política **B403 obligatoria** es la única mitigación adoptada: sin ella el FNR
crudo es 9,2 %; con ella, 3,1 % (IC95 0,8–10,5 %) y el FPRR baja de 30,4 % a
19,6 %. Rescata 4 de los 6 falsos negativos, pero no los elimina todos. Agregar
B311 llevaría el FNR a 0 %; **no se adopta** porque la regla se elegiría después
de ver el holdout. Queda como trabajo futuro para un conjunto independiente.

## 8.4 Aportes del proyecto

1. **Una tubería local completa y reproducible.** Bandit, normalización,
   deduplicación, extracción de contexto por AST, prompt, validación, reporte
   JSON/SARIF y CLI, con un modelo de 1,5B cuantizado que cabe en 4 GB de VRAM.
   El código no sale de la máquina.
2. **Una evaluación pareada A/B/C/C0/D.** C0 aísla el efecto del ajuste frente
   al modelo base; C mide el resultado práctico frente a un prompt con few-shot;
   D mide el modelo afinado. La distinción evita atribuir al entrenamiento lo
   que produce la ingeniería de prompts.
3. **Un holdout ejecutado una sola vez y reportado sin maquillar.** El resultado
   de desarrollo no se generalizó: el FNR subió y el ahorro bajó. El valor
   metodológico está en mostrar ese contraste, no en ocultarlo.
4. **Modo asesor justificado con medición.** La política conservadora se deriva
   del FNR observado, de la concentración del error y de la imposibilidad de
   garantizar ≤ 5 % con este tamaño de muestra.
5. **Artefactos trazables.** Conjunto de evaluación, prompts, resultados crudos,
   hashes, scripts de entrenamiento, análisis reproducible y generación de
   documentos. Cada cifra se rastrea hasta un archivo y un comando.

## 8.5 Trabajo futuro

- **Casi-duplicados entre train y holdout.** La comparación exacta de hashes
  normalizados dio 0 coincidencias, pero falta medir similitud difusa. El
  dataset no tiene identificador de repositorio, así que una partición agrupada
  de verdad no es posible con los datos actuales; hay que declararlo como
  limitación o conseguir metadatos de origen.
- **Auditoría humana de explicaciones** con la rúbrica de cuatro criterios y
  kappa de Cohen entre dos revisores ciegos. Debe reportar también la diversidad
  de salidas, porque D colapsó a plantillas.
- **Regla B311 para un conjunto nuevo.** El holdout mostró 2 falsos negativos
  B311, pero agregar la regla ahora sería post hoc. Se propone como hipótesis a
  validar con datos independientes.
- **Regla B403 basada en el punto de uso**: no descartar por el `import`, sino
  por la ausencia de un `pickle.load` alcanzable. Requiere análisis de flujo que
  Bandit no ofrece.
- **Medir el efecto de la cuantización**: comparar el Q4_K_M contra el modelo
  fusionado en f16 para separar ajuste de cuantización.
- **Ampliar la batería de prompt injection** con más patrones y documentar la
  política de llamadas externas y de descarga de repositorios.
- **Escalar la latencia**: batching, concurrencia medida y una política de
  reinicio del runner tras un truncamiento.

## 8.6 Qué agregó el holdout

El holdout no confirmó la lectura optimista de desarrollo. Agregó cuatro hechos
que la memoria debe conservar:

1. El FNR crudo de D es 9,2 % y no 5,5 %; la política B403 lo baja a 3,1 %,
   pero el IC95 llega a 10,5 %.
2. El error ya no es solo B403: aparecen 2 B311.
3. El ahorro real sobre C0 es +8,7 puntos con la política, no +46.
4. Las explicaciones de D son plantillas: 11 textos únicos para 111 alertas.

También dejó una lección metodológica: con 65 alertas reales no se puede
demostrar un FNR ≤ 5 %. Un valor puntual favorable no reemplaza al intervalo de
confianza. Esa es, probablemente, la contribución más valiosa del Sprint 7.

El holdout no puede confirmar que el modelo detecta vulnerabilidades que Bandit
no reporta, que el CWE predicho es correcto de forma independiente ni que el
resultado se sostiene en otros lenguajes o SAST. No es una prueba de producción;
es la última medición no contaminada de una hipótesis acotada.

## 8.7 Cierre

El proyecto demuestra que un modelo pequeño, ajustado de forma eficiente y
ejecutado localmente, puede ahorrar revisión en un conjunto acotado de alertas de
Bandit. También demuestra, con la misma medición, que ese ahorro no autoriza a
sustituir al analista. La contribución no es el ahorro en sí, sino la comparación
que permite saber cuándo es aceptable y cuándo no. En esta versión la respuesta
es que todavía no lo es: el modo asesor se mantiene, B403 es obligatorio y el
descarte automático queda fuera de alcance.
