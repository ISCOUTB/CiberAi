# Borrador — Conclusiones (Sprint 8)

> Documento de trabajo. Las cifras de desarrollo provienen de
> `eval/resultados_{A,C,C0,D}.json`; las de generalización, del holdout
> ejecutado una sola vez en el Sprint 7 (`eval/resultados_holdout_{A,C0,D}.json`
> y `docs/ANALISIS_HOLDOUT.md`). La evidencia posterior del banco sintético
> (`eval/banco_sintetico.json`) y de los repositorios reales
> (`eval/corrida_repos_reales.json`) se reporta aparte y no se mezcla con las
> anteriores.

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

La evidencia posterior del banco sintético refuerza la segunda parte. Medido con
verdad de referencia por alerta, D descarta 5 de 14 alertas reales (FNR 35,7 %) y
su decisión se reproduce 26/26 con una regla sobre la severidad del SAST. El
holdout sigue siendo la referencia de generalización; el banco explica el
mecanismo y confirma que el ahorro no equivale a comprensión del contexto.

## 8.2 Respuesta a las hipótesis secundarias

**El modelo copia el CWE del SAST.** Confirmada. En desarrollo, el CWE predicho
coincide con el del SAST en 86 de 86 alertas reales conservadas por D; en el
holdout, en 59 de 59. La exactitud CWE (43,0 % en desarrollo, 32,2 % en el
holdout) mide la concordancia entre la etiqueta del SAST y la del dataset, no
capacidad de clasificación. El producto debe conservar el CWE del SAST.

**D decide por la severidad del SAST.** Confirmada en el banco sintético y en los
repositorios reales. En el banco, la regla «`SAFE` si la severidad es baja»
reproduce **26 de 26** veredictos; en la corrida real, D descarta 34 de 34
alertas bajas y 0 de 4 medias o altas. La severidad entra en el prompt y el
modelo la usa como atajo. El FPRR alto no es evidencia de que lea el contexto del
código.

**El error de omisión se concentra en reglas de baja severidad.** Confirmada con
un matiz importante. En desarrollo las cinco alertas reales descartadas eran
B403. En el holdout son 4 B403 y **2 B311**; el banco sintético añade B105, B110,
B101 y B603. El patrón común no es la importación, sino la severidad baja del
SAST. B403 es la parte mitigable; B311 aparece como riesgo nuevo y no se
convierte en regla después de ver el holdout.

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

El banco sintético agrega el caso adversarial que la corrida real no pone a
prueba: con etiqueta por alerta, D descarta 5 de 14 reales (FNR 35,7 %, IC95
16,3–61,2 %) y acierta 7 de 12 falsos positivos (FPRR 58,3 %, IC95
32,0–80,7 %). La auditoría manual de repos reales es favorable (FPRR 100 %, FNR
0 %), pero su muestra es pequeña y elegida; el banco muestra que, fuera de ese
caso favorable, el ahorro se apoya en la severidad y no en el contexto. Por eso
el modo asesor se mantiene. La conclusión de producto no depende del 35,7 %
puntual, sino de que la decisión se reproduce con una regla sobre la severidad.

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
6. **Cobertura OWASP medida y declarada.** Las 141 alertas de desarrollo y las
   111 del holdout se ubican en el Top 10 2021 por el CWE que reporta Bandit: A03
   y A08 concentran más del 95 % y el resto del Top 10 queda fuera del alcance de
   un SAST de reglas. El agente se analiza además con el Top 10 for LLM
   Applications 2025, donde ocho riesgos tienen evidencia propia, y con una
   checklist parcial de ASVS 5.0.0. El aporte metodológico es la distinción entre
   «lo que el producto cubre» y «lo que la norma incluye».
7. **Un banco adversarial y una auditoría de repos reales como control del
   mecanismo.** El banco etiquetado (26 alertas, 13 reglas) muestra que la
   decisión de D se explica por la severidad del SAST y no por el contexto; la
   auditoría manual de 38 alertas sobre tres repositorios pinneados confirma el
   comportamiento sobre código real fuera del dataset. Juntas separan «ahorro de
   revisión» de «comprensión del código», que es la distinción que el FPRR por sí
   solo no puede hacer.

## 8.5 Trabajo futuro

- **Validar los casi-duplicados entre train y holdout.** La comparación exacta
  de hashes normalizados dio 0 coincidencias, pero el análisis de similitud de
  tokens (`eval/casi_duplicados.py`) encontró que el **70,3 % de las funciones
  del holdout tienen un vecino ≥ 0,8** en train/val, y 45/111 tienen similitud ≥
  0,9. Hay que determinar si esos pares son realmente variantes del mismo
  proyecto o solo coinciden de patrón, y construir una partición agrupada por
  repositorio si se consiguen los metadatos.
- **Auditoría humana de explicaciones** con la rúbrica de cuatro criterios y
  kappa de Cohen entre dos revisores ciegos. Debe reportar también la diversidad
  de salidas, porque D colapsó a plantillas.
- **Regla B311 para un conjunto nuevo.** El holdout mostró 2 falsos negativos
  B311, pero agregar la regla ahora sería post hoc. Se propone como hipótesis a
  validar con datos independientes.
- **Regla B403 basada en el punto de uso**: no descartar por el `import`, sino
  por la ausencia de un `pickle.load` alcanzable. Requiere análisis de flujo que
  Bandit no ofrece.
- **Reentrenar contra el atajo de severidad.** El banco mostró que D decide por la
  severidad del SAST. Un conjunto nuevo con contraejemplos de la misma regla y
  severidad permitiría comprobar si el modelo puede aprender el contexto. No se
  hace con el banco actual porque se contaminaría.
- **Alinear el prompt del producto con el de entrenamiento.** El banco usa
  `triage.build_prompt` y D se entrenó con `prompt_d`; medir esa diferencia con
  un conjunto independiente separaría el efecto del cambio de plantilla del
  colapso de las explicaciones.
- **Segundo anotador y kappa para el banco.** Sus 26 etiquetas las puso el autor.
  Un segundo revisor ciego convertiría el acuerdo en una cifra reportable y
  reduciría el sesgo del evaluador.
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

## 8.7 Qué agregaron el banco y los repositorios

El holdout midió generalización; el banco y la corrida real midieron el
mecanismo. Agregaron seis hechos que la memoria debe conservar:

1. La decisión de D se reproduce 26/26 con una regla sobre la severidad del SAST.
2. Con etiquetas por alerta, D descarta 5 de 14 reales (FNR 35,7 %, IC95
   16,3–61,2 %) y acierta 7 de 12 falsos positivos (FPRR 58,3 %, IC95
   32,0–80,7 %); el ahorro no prueba comprensión. La exactitud de D (61,5 %) no
   supera de forma demostrable a la del base (53,8 %): sus intervalos se solapan.
3. Sobre 38 alertas de tres repositorios reales, D descarta 34 de 34 bajas y 0 de
   4 medias o altas, sin eliminar ninguna alerta.
4. La auditoría manual de esos 38 casos da FPRR 100 % y FNR 0 %, con precisión
   de descartes 91,2 %. La muestra es pequeña y elegida por el autor, pero es
   código real fuera del dataset de entrenamiento.
5. Las explicaciones de D son dos plantillas también con el prompt del producto,
   no solo en el arnés de evaluación.
6. La validez externa está debilitada: el 70,3 % de las funciones del holdout
   tienen un vecino ≥ 0,8 en train/val; la partición aleatoria por función no
   garantiza independencia.

También dejaron una advertencia de alcance: el banco es pequeño, adversarial y de
un solo anotador; la corrida real está etiquetada por un solo auditor y sus
repos fueron elegidos por el autor. Sirven para explicar por qué el modo asesor
es necesario, no para estimar el FPRR o el FNR de producción.
Esa estimación sigue dependiendo del holdout y de su intervalo. Ninguna de las dos
pruebas se usó para ajustar prompts, reglas ni umbrales, y el holdout permaneció
intacto.

## 8.8 Cierre

El proyecto demuestra que un modelo pequeño, ajustado de forma eficiente y
ejecutado localmente, puede ahorrar revisión en un conjunto acotado de alertas de
Bandit. También demuestra, con la misma medición, que ese ahorro no autoriza a
sustituir al analista. La contribución no es el ahorro en sí, sino la comparación
que permite saber cuándo es aceptable y cuándo no. En esta versión la respuesta
es que todavía no lo es: el modo asesor se mantiene, B403 es obligatorio y el
descarte automático queda fuera de alcance.
