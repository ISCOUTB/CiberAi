# Agente inteligente para la revisión de seguridad de código fuente
## Trabajo de Fin de Grado — Memoria final

**Integrantes:** Santiago Reyes, Marien Daniela, Luis Patron, William Cuello  
**Asignatura:** Proyecto de Ingeniería  
**Fecha:** 9 de noviembre de 2026  
**Rama:** `feature/sprint-7`  

---

## Resumen

Este proyecto implementa un agente local de triage para alertas de Bandit sobre código Python, usando un Qwen2.5-Coder-1.5B afinado con QLoRA y cuantizado a Q4_K_M. El agente opera en modo asesor: recomienda descartar alertas que parecen falsos positivos, pero nunca las elimina del reporte. Sobre el conjunto de desarrollo, el modelo afinado (D) alcanza FPRR 48,0 % y FNR 5,5 %; en el holdout, FPRR 30,4 % y FNR 9,2 %. Con la política B403 obligatoria el FNR del holdout baja a 3,1 %, pero el intervalo de confianza superior (10,5 %) impide demostrar que se cumple la meta de ≤ 5 %. Un banco sintético de 26 alertas y una auditoría manual sobre tres repositorios reales complementan la evidencia: el banco muestra que D decide principalmente por la severidad del SAST, mientras que la auditoría de repos reales es favorable (FPRR 100 %, FNR 0 %) pero no generalizable. El análisis de casi-duplicados encuentra que el 70,3 % de las funciones del holdout tienen un vecino ≥ 0,8 en train/val, lo que debilita la independencia de la partición. La contribución principal no es el ahorro de revisión, sino la comparación rigurosa que permite saber cuándo es aceptable y cuándo no: en esta versión, el descarte automático queda fuera de alcance.

**Palabras clave:** análisis estático de seguridad, SAST, triage, modelos de lenguaje, fine-tuning, QLoRA, Bandit, Python, OWASP.

---

## Tabla de contenidos
- [1. Introducción](#1-introducción)
  - [1.1 Contexto](#11-contexto)
  - [1.2 Problema](#12-problema)
  - [1.3 Pregunta de investigación e hipótesis](#13-pregunta-de-investigación-e-hipótesis)
  - [1.4 Objetivos](#14-objetivos)
  - [1.5 Contribuciones](#15-contribuciones)
  - [1.6 Alcance y exclusiones](#16-alcance-y-exclusiones)
  - [1.7 Estructura de la memoria](#17-estructura-de-la-memoria)
- [2. Estado del arte](#2-estado-del-arte)
  - [2.1 El límite del análisis estático](#21-el-límite-del-análisis-estático)
  - [2.2 LLM para detección y triage](#22-llm-para-detección-y-triage)
  - [2.3 Datos y verdad de referencia](#23-datos-y-verdad-de-referencia)
  - [2.4 Ajuste eficiente y despliegue local](#24-ajuste-eficiente-y-despliegue-local)
  - [2.5 Métricas de evaluación](#25-métricas-de-evaluación)
  - [2.6 OWASP como marco de referencia](#26-owasp-como-marco-de-referencia)
  - [2.7 Síntesis y vacío que cubre el proyecto](#27-síntesis-y-vacío-que-cubre-el-proyecto)
  - [Referencias](#referencias)
- [3. Metodología](#3-metodología)
  - [3.1 Dataset y verdad de referencia](#31-dataset-y-verdad-de-referencia)
  - [3.2 Construcción de los ejemplos de ajuste](#32-construcción-de-los-ejemplos-de-ajuste)
  - [3.3 Ajuste QLoRA](#33-ajuste-qlora)
  - [3.4 Fusión, exportación y registro](#34-fusión-exportación-y-registro)
  - [3.5 Protocolo de evaluación](#35-protocolo-de-evaluación)
  - [3.6 Métricas](#36-métricas)
  - [3.7 Pruebas funcionales y de robustez](#37-pruebas-funcionales-y-de-robustez)
  - [3.8 Reproducibilidad](#38-reproducibilidad)
  - [3.9 Marco OWASP y cobertura declarada](#39-marco-owasp-y-cobertura-declarada)
- [4. Resultados y discusión](#4-resultados-y-discusión)
  - [4.1 El intercambio entre ahorro y omisión](#41-el-intercambio-entre-ahorro-y-omisión)
  - [4.2 El FNR ya no está solo en B403](#42-el-fnr-ya-no-está-solo-en-b403)
  - [4.3 El CWE no es una clasificación independiente](#43-el-cwe-no-es-una-clasificación-independiente)
  - [4.4 Validez de la partición y del holdout](#44-validez-de-la-partición-y-del-holdout)
  - [4.5 La pérdida no mide calidad de triage](#45-la-pérdida-no-mide-calidad-de-triage)
  - [4.6 Las explicaciones colapsaron a plantillas](#46-las-explicaciones-colapsaron-a-plantillas)
  - [4.7 Robustez operativa](#47-robustez-operativa)
  - [4.8 Implicaciones de producto](#48-implicaciones-de-producto)
  - [4.9 Amenazas a la validez](#49-amenazas-a-la-validez)
  - [4.10 Qué confirmó y qué no confirmó el holdout](#410-qué-confirmó-y-qué-no-confirmó-el-holdout)
  - [4.11 Lectura por categoría OWASP](#411-lectura-por-categoría-owasp)
  - [4.12 Evidencia posterior: banco sintético y repositorios reales](#412-evidencia-posterior-banco-sintético-y-repositorios-reales)
- [5. Conclusiones](#5-conclusiones)
  - [5.1 Respuesta a la pregunta de investigación](#51-respuesta-a-la-pregunta-de-investigación)
  - [5.2 Respuesta a las hipótesis secundarias](#52-respuesta-a-las-hipótesis-secundarias)
  - [5.3 ¿Sirve para descarte automático?](#53-sirve-para-descarte-automático)
  - [5.4 Aportes del proyecto](#54-aportes-del-proyecto)
  - [5.5 Trabajo futuro](#55-trabajo-futuro)
  - [5.6 Qué agregó el holdout](#56-qué-agregó-el-holdout)
  - [5.7 Qué agregaron el banco y los repositorios](#57-qué-agregaron-el-banco-y-los-repositorios)
  - [5.8 Cierre](#58-cierre)
- [Anexos](#anexos)
  - [Anexo A. Reproducción](#anexo-a-reproducción)
  - [Anexo B. Artefactos y hashes](#anexo-b-artefactos-y-hashes)
  - [Anexo C. Prompts](#anexo-c-prompts)
  - [Anexo D. Conjuntos de evaluación](#anexo-d-conjuntos-de-evaluación)
  - [Anexo E. Pruebas](#anexo-e-pruebas)
  - [Anexo F. Tablas por regla](#anexo-f-tablas-por-regla)
  - [Anexo G. Cobertura OWASP](#anexo-g-cobertura-owasp)

---


# 1. Introducción

## 1.1 Contexto

El análisis estático de seguridad (SAST) es una práctica extendida en el ciclón
de vida del software: se ejecuta sobre el código fuente, aplica reglas y reporta
posibles vulnerabilidades antes de que el programa se ejecute. Su ventaja es la
cobertura y la repetibilidad; su costo es el ruido. Un analizador de reglas como
Bandit puede señalar un `import pickle` sin distinguir si el programa
deserializa datos de un atacante o si solo serializa resultados internos. Esa
ambigüedad es inevitable en un análisis que no ejecuta el programa ni conoce el
contexto de despliegue.

El resultado práctico es que los equipos dedican una parte importante de la
revisión a descartar alertas que no son vulnerabilidades. En el estudio
industrial de Du et al. (2026), 328 de 433 alarmas de un SAST empresarial eran
falsos positivos (75,8 %) y cada revisión manual consumía entre 10 y 20 minutos.
No es un problema de herramientas mal calibradas: es el precio de detectar sin
contexto.

Los modelos de lenguaje ofrecen una forma de aportar ese contexto. Pueden leer
la función completa, reconocer si la entrada es externa, explicar el vector de
ataque y proponer una corrección. También pueden equivocarse con seguridad, y
ese es el riesgo central de este proyecto: un modelo que recomiende descartar
una vulnerabilidad real es peor que un SAST ruidoso, porque elimina la señal que
el analista necesitaba.

## 1.2 Problema

El proyecto parte de una herramienta concreta: la CLI `agente-seguridad`, que
ejecuta Bandit sobre un repositorio, normaliza las alertas, extrae la función
afectada y consulta a un modelo local servido por Ollama. El problema que queda
abierto al inicio del Sprint 6 es si el ajuste fino de un modelo pequeño mejora
el triage de esas alertas lo suficiente como para ahorrar revisión sin aumentar
la omisión de vulnerabilidades reales.

La pregunta no es "¿el modelo detecta vulnerabilidades?". La pregunta es más
acotada y medible: **dado un conjunto fijo de alertas de Bandit, ¿el modelo
afinado recomienda descartar más falsos positivos que el modelo base con el
mismo formato de alerta y sin ejemplos resueltos, manteniendo la tasa de falsos
negativos en un nivel aceptable?**

## 1.3 Pregunta de investigación e hipótesis

Pregunta principal:

> ¿Un modelo Qwen2.5-Coder-1.5B ajustado con QLoRA sobre alertas de Bandit
> reduce la tasa de falsos positivos recomendados para descarte (FPRR) frente al
> mismo modelo sin ajustar y con el mismo formato de alerta (sin ejemplos
> resueltos), sin superar un FNR del 5 %?

Hipótesis:

> El ajuste fino aumenta el FPRR de forma significativa respecto de la línea
> base con el mismo formato de alerta (configuración C0), porque el modelo
> aprende el formato y la distribución de las respuestas de triage. El FNR puede
> aumentar, pero se espera que se mantenga por debajo del 5 %; si lo supera, el
> producto no debe habilitar descarte automático.

Hipótesis secundarias:

- El modelo copia el CWE del SAST y no aporta una clasificación independiente.
- El error de omisión aparece en reglas de baja severidad (B403, B311, B101,
  B105, B110, B603), no solo en importaciones de deserialización.
- El coste de inferencia permite ejecutar el modelo en una GPU de 4 GB.

## 1.4 Objetivos

**Objetivo general.** Evaluar si el ajuste fino eficiente de un modelo de
lenguaje pequeño mejora el triage de alertas SAST en un entorno local, con una
medición pareada que separe el efecto del prompt del efecto del entrenamiento.

**Objetivos específicos.**

1. Construir un conjunto de evaluación reproducible a partir de funciones
   Python etiquetadas y alertas reales de Bandit.
2. Entrenar un adaptador LoRA con QLoRA sobre ejemplos de triage y exportarlo a
   GGUF Q4_K_M para ejecutarlo en Ollama.
3. Integrar el modelo en la CLI sin cambiar el contrato de datos ni el reporte
   SARIF.
4. Comparar cinco configuraciones sobre el mismo conjunto: A (solo SAST), B
   (cero-shot), C (modelo base con contexto y ejemplos), C0 (modelo base con el
   mismo formato de alerta que D, sin ejemplos) y D (modelo afinado).
5. Medir FPRR, FNR, FOR, precisión, exactitud CWE, latencia, memoria y
   respuestas inválidas.
6. Validar la robustez del producto ante repositorios vacíos, sintaxis inválida,
   otros lenguajes, Ollama caído, JSON inválido y prompt injection.
7. Reservar un conjunto de verificación para una evaluación única en el Sprint
   7 y documentar las amenazas a la validez, incluida la similitud con el
   entrenamiento.
8. Construir un banco sintético etiquetado y auditar repositorios reales como
   validaciones out-of-distribution del modo asesor.
9. Ubicar las alertas y los riesgos del componente inteligente en el OWASP Top 10
   2021, el OWASP Top 10 for LLM Applications 2025 y ASVS 5.0.0, y declarar la
   cobertura medida con sus exclusiones.

## 1.5 Contribuciones

El proyecto no pretende superar el estado del arte en detección de
vulnerabilidades. Aporta una comparación honesta y reproducible de un triage
local, con cinco contribuciones concretas:

1. **Una tubería local completa.** Bandit, normalización, deduplicación,
   extracción de contexto por AST, prompt, validación y reporte JSON/SARIF, con
   un modelo de 1,5B cuantizado que cabe en 4 GB de VRAM. El código no sale de
   la máquina.
2. **Una evaluación pareada A/B/C/C0/D.** C0 y D comparten prompt, conjunto y
   temperatura; solo cambia el modelo. Esa simetría permite atribuir la
   diferencia al ajuste fino y no a la ingeniería de prompts, algo que muchos
   reportes de "LLM para SAST" no separan. C, con ejemplos resueltos, mide el
   resultado práctico de un prompt cuidado frente al modelo afinado.
3. **Modo asesor como decisión de producto.** El veredicto `SAFE` recomienda
   descarte pero no elimina la alerta. Ante un JSON inválido, un timeout o un
   servicio caído, la alerta se conserva como `SOSPECHOSA`. La política se
   justifica con la medición, no con una preferencia estética.
4. **Artefactos reproducibles.** Conjunto de evaluación, prompts, resultados
   crudos, hashes de los modelos, scripts de entrenamiento y de generación de
   documentos. Cualquier resultado del documento puede rastrearse hasta un
   archivo y un comando.
5. **Cobertura OWASP medida, no declarada.** Las alertas se ubican en el Top 10
   2021 por el CWE del SAST, con la matriz de cobertura y las discrepancias del
   dataset documentadas; el agente se analiza además con el Top 10 for LLM
   Applications 2025 y una checklist parcial de ASVS 5.0.0. El proyecto declara
   qué categorías cubre y cuáles no puede cubrir con un SAST de reglas.
6. **Validaciones out-of-distribution.** Un banco sintético etiquetado (26
   alertas, 13 reglas) y una auditoría manual sobre tres repositorios reales
   pinneados (38 alertas) complementan al holdout. No reemplazan la evidencia de
   generalización, pero muestran el comportamiento del producto fuera del dataset
   de entrenamiento y fortalecen la justificación del modo asesor.

## 1.6 Alcance y exclusiones

**Incluido:**

- Python y Bandit como único SAST.
- Funciones del split de validación y del test reservado de un dataset público,
  con etiquetas a nivel de función.
- Un modelo Qwen2.5-Coder-1.5B-Instruct, adaptador LoRA, fusión, GGUF Q4_K_M y
  Ollama.
- Evaluación de desarrollo (A/B/C/C0/D), holdout (A/C0/D) y batería funcional.
- Reporte JSON y SARIF en modo asesor.
- Cobertura OWASP Top 10 2021 medida sobre las alertas evaluadas, con las
  categorías alcanzables por Bandit; modelo de amenaza del agente según el Top 10
  for LLM Applications 2025; checklist parcial de ASVS 5.0.0.

**Excluido:**

- Detección de vulnerabilidades que Bandit no reporta.
- Cobertura de las categorías OWASP que requieren análisis de flujo, inventario
  de dependencias o telemetría de runtime: A05, A06, A09 y A10, y el resto de
  A01, A02, A04 y A07 fuera de las reglas evaluadas.
- Cumplimiento de ASVS 5.0.0: se aplican seis capítulos de diecisiete, con
  exclusiones declaradas.
- Otros lenguajes (Java, C, JavaScript) y otros SAST (CodeQL, Semgrep).
- Descarte automático de alertas.
- Despliegue en producción, autenticación, multiusuario y integración CI/CD.
- Evaluación de explicaciones con referencias humanas (la rúbrica queda
  diseñada, pero no aplicada).
- Entrenamiento con el split de test: se reservó y se usó una sola vez para la
  evaluación del Sprint 7.
- Reconstrucción del split agrupado por repositorio: el dataset no tiene
  identificador de proyecto, y el análisis de casi-duplicados encontró 70,3 % de
  funciones del holdout con vecino ≥ 0,8 en train/val.

La exclusión del descarte automático no es una limitación técnica sino una
decisión basada en la evidencia: con FNR 9,2 % en el holdout (3,1 % con la
política B403, pero IC95 hasta 10,5 %), con FNR 35,7 % en el banco sintético
adversarial (IC95 16,3–61,2 %) y con FNR 0 % en la auditoría de repos reales
(muestra pequeña y elegida), el producto no cumple la meta de omisión de forma
generalizada y no puede eliminar alertas sin supervisión.

## 1.7 Estructura de la memoria

La memoria se organiza en nueve capítulos. El capítulo 2 revisa el estado del
arte en SAST, LLM para seguridad, datos y ajuste eficiente, y fija el marco OWASP
que ordena el alcance. El capítulo 3 fija requisitos y alcance. El capítulo 4
describe la arquitectura y el contrato de datos. El capítulo 5 detalla la
metodología: dataset, particiones, entrenamiento, exportación y métricas. El
capítulo 6 presenta los experimentos y resultados (entrenamiento, A/B/C/C0/D,
comparación con Qwen base, holdout, latencia, pruebas). El capítulo 7 discute el
intercambio entre ahorro y omisión, el CWE copiado, el sesgo de B403 y B311, el
colapso de las explicaciones, las amenazas a la validez y las validaciones
out-of-distribution (banco sintético y auditoría de repos reales). El capítulo 8 responde
a la hipótesis y enumera el trabajo futuro. El capítulo 9 reúne las referencias y
los anexos de reproducción.

El hilo argumental es único: un modelo pequeño, entrenado de forma eficiente y
ejecutado localmente, puede ahorrar revisión en un conjunto acotado, pero no
puede sustituir la decisión del analista. La contribución no es el ahorro en sí,
sino la medición que permite saber cuándo ese ahorro es aceptable y cuándo no.


# 2. Estado del arte

## 2.1 El límite del análisis estático

Los analizadores estáticos de seguridad (SAST) detectan patrones peligrosos sin
ejecutar el programa: reglas sintácticas, flujo de datos aproximado y
coincidencias de firmas. Son rápidos, auditables y no dependen de datos de
entrenamiento, pero pagan ese rigor con falsos positivos. Bandit, el analizador
elegido en este proyecto, aplica reglas sobre el AST de Python; una regla como
B403 señala cualquier `import pickle` aunque la función solo serialice datos
confiables, y B404 advierte por importar `subprocess` aunque no se ejecute nada.
La alerta es correcta en el plano sintáctico y ruidosa en el plano del riesgo
real.

Ese ruido tiene un costo medible. Du et al. (2026) estudiaron 433 alarmas de un
SAST empresarial de Tencent sobre software de publicidad y marketing: 328 eran
falsos positivos (75,8 %) y cada revisión manual consumía entre 10 y 20 minutos.
El dato no es una curiosidad académica; es el problema de negocio que justifica
el triage automático. La revisión humana no desaparece con un SAST, solo se
traslada a alertas que muchas veces no son vulnerabilidades.

La consecuencia de diseño para este proyecto es doble. Primero, el agente no
puede limitarse a repetir la alerta del SAST: tiene que aportar una decisión
sobre el riesgo. Segundo, esa decisión no puede ser destructiva. Si el SAST ya
produce ruido, un modelo que elimine alertas reales empeora el problema en lugar
de resolverlo. De ahí el modo asesor: la alerta siempre permanece visible y el
veredicto solo ordena la revisión.

## 2.2 LLM para detección y triage

El uso de modelos de lenguaje en seguridad de código se organiza en dos
familias. La primera intenta **detectar** vulnerabilidades directamente sobre el
código. La segunda intenta **priorizar o descartar** alertas que ya produjo otra
herramienta. Este proyecto pertenece a la segunda.

IRIS (Li et al., 2025) es un representante de la primera familia con un matiz
importante: combina el LLM con análisis estático (CodeQL) para razonar sobre
flujos y contextos que el modelo solo no vería. En su conjunto CWE-Bench-Java,
CodeQL detecta 27 de 120 vulnerabilidades y IRIS con GPT-4 detecta 55, además de
mejorar la tasa media de falsos descubrimientos en 5 puntos. Su lección para
este trabajo es que el LLM aporta más cuando recibe estructura del análisis
estático que cuando se le pide adivinar el flujo completo. Nuestro prompt sigue
esa idea: incluye la regla, el CWE, la severidad, la función afectada y el
contexto de código, en lugar de pedirle al modelo que descubra la vulnerabilidad
desde cero.

La segunda familia es más reciente en entornos industriales. Du et al. (2026)
comparan varias técnicas de reducción de falsos positivos y reportan que las
combinaciones híbridas de LLM y análisis estático eliminan entre 94 % y 98 % de
los falsos positivos con recall alto, a un costo de 2,1 a 109,5 segundos por
alarma. La cifra es optimista respecto de nuestro resultado (48 % de FPRR) y no
es directamente comparable: su SAST es empresarial, sus tipos de bug son tres y
el conjunto es más pequeño. Aun así, fija una expectativa: un triage útil debe
superar ampliamente el ahorro trivial.

El límite de estos resultados es metodológico. Ding et al. (2025) documentan
problemas de calidad, precisión de etiquetas y duplicación en los conjuntos
públicos, y muestran que un modelo de 7B que obtiene 68,26 % de F1 en BigVul
cae a 3,09 % de F1 en su benchmark PrimeVul; con los ajustes más estrictos,
GPT-3.5 y GPT-4 quedan cerca del azar. Un FPRR alto en un conjunto contaminado
no prueba capacidad de detección. Por eso este proyecto separa la partición de
desarrollo del test reservado y reporta el FNR junto con el FPRR: sin la tasa de
omisión, el ahorro de revisión es una métrica incompleta.

La consecuencia para el proyecto es que el resultado de D en desarrollo
(FPRR 48 %, FNR 5,5 %) debía leerse como una medición de desarrollo, no como una
promesa de producción. El holdout del Sprint 7 lo confirmó: el FPRR bajó a
30,4 % y el FNR subió a 9,2 %. La lección es la misma que documentan Ding et al.:
un número alto en un conjunto de desarrollo no se generaliza sin una medición
independiente.

## 2.3 Datos y verdad de referencia

Los conjuntos públicos de vulnerabilidades tienen tres problemas recurrentes:
etiquetas a nivel de función o de archivo, ausencia de alcanzabilidad y
duplicados entre particiones. SecurityEval (Siddiq y Santos, 2022) ofrece
ejemplos pequeños y controlados para evaluar generación de código seguro, pero
no representa la distribución de un repositorio real. CVEfixes (Bhandari et al.,
2021) extrae pares vulnerabilidad–corrección de CVE y es útil para estudiar
parches, aunque depende de que el CVE esté bien asociado al commit. DiverseVul
(Chen et al., 2023) amplía la diversidad de proyectos y lenguajes, con el mismo
riesgo de ruido en las etiquetas.

El dataset usado en este proyecto (`ayshajavd/code-security-vulnerability-dataset`)
hereda esas limitaciones. La etiqueta es a nivel de función, no indica si el
flujo es alcanzable y no incluye identificador de repositorio. Eso tiene dos
efectos concretos en nuestros números. Primero, una advertencia de importación
sobre una función vulnerable cuenta como alerta real aunque la línea señalada no
sea el defecto; eso favorece al SAST y explica parte de su 45,1 % de
concordancia CWE en desarrollo. Segundo, la partición aleatoria por función no
garantiza independencia entre repositorios: dos funciones del mismo proyecto
pueden caer en train y en test. El Sprint 7 evaluó el test sin reagrupar porque
el dataset no tiene identificador de repositorio; la comparación exacta de
hashes dio 0 coincidencias, pero los casi-duplicados quedan como limitación.

La consecuencia para el proyecto es que la verdad de referencia se trata como
aproximada. No se afirma que el modelo "detecta vulnerabilidades"; se afirma que
reordena alertas de Bandit sobre un conjunto con etiquetas imperfectas.

## 2.4 Ajuste eficiente y despliegue local

LoRA (Hu et al., 2021) congela los pesos del modelo y entrena matrices de bajo
rango sobre las proyecciones de atención. QLoRA (Dettmers et al., 2023) agrega
cuantización de 4 bits del modelo base y reduce la memoria necesaria para
afinar modelos grandes en una sola GPU. En este proyecto el modelo base es
Qwen2.5-Coder-1.5B (Hui et al., 2024), elegido por tres razones: tamaño
manejable en 4 GB de VRAM, buen desempeño relativo en código para su escala y
licencia permisiva. El adaptador resultante tiene 18,4 millones de parámetros
entrenables (1,18 % del total).

La cadena de despliegue importa tanto como el entrenamiento. El adaptador se
fusiona con los pesos base, se exporta a GGUF y se cuantiza a Q4_K_M para
ejecutarse con llama.cpp y Ollama. La cuantización reduce el modelo a 940 MB en
disco y 1.115 MB en VRAM, a costa de una posible pérdida de precisión que este
trabajo no midió contra el modelo fusionado sin cuantizar. Es una decisión de
despliegue, no una fuente de conocimiento: el ajuste fino ocurrió antes.

La consecuencia para el proyecto es que la comparación D contra C0 aísla el
efecto del ajuste fino, porque comparten el formato de alerta; C agrega dos
ejemplos resueltos y no es una comparación de solo modelo. Ninguna de las
corridas aísla la cuantización: para eso haría falta medir el modelo fusionado en
f16, fuera del alcance del Sprint 6.

## 2.5 Métricas de evaluación

La evaluación de un triage no se reduce a exactitud. Este proyecto reporta:

- **FPRR** (*false positive reduction rate*): proporción de falsos positivos que
  el agente recomienda descartar. Mide el ahorro de revisión.
- **FNR** (*false negative rate*): proporción de alertas reales que el agente
  recomienda descartar. Mide el riesgo de omitir una vulnerabilidad y es la
  métrica principal.
- **FOR** (*false omission rate*): proporción de alertas reales entre las
  recomendadas para descarte. Mide la calidad de los descartes.
- **Precisión** sobre las alertas conservadas: proporción de alertas reales
  entre las que el agente decide mantener.
- **Exactitud CWE**: concordancia entre el CWE predicho y el del dataset, solo
  sobre alertas reales conservadas.

La elección de FNR como métrica principal es una decisión de producto, no una
convención. Un falso positivo adicional cuesta minutos de revisión; un falso
negativo puede costar una vulnerabilidad no corregida. Por eso la meta es
FNR ≤ 5 % y el FPRR se reporta como beneficio subordinado.

Para las explicaciones cualitativas se propone una rúbrica con cuatro criterios
(CWE, vector de ataque, corrección y claridad), evaluada por dos revisores
ciegos, con kappa de Cohen para el acuerdo. BERTScore (Zhang et al., 2020) mide
similitud semántica con referencias humanas, pero no corrección técnica; se usa
solo como medida descriptiva. Sin referencias humanas, BERTScore no es
interpretable y no debe presentarse como validación.

La consecuencia para el proyecto es que el CWE no se trata como una métrica de
clasificación independiente. El prompt incluye el CWE del SAST y el modelo lo
copia en la mayoría de los casos; la exactitud CWE mide, sobre todo, qué alertas
conservó cada configuración.

## 2.6 OWASP como marco de referencia

El proyecto no usa OWASP como una lista de buenas prácticas al final: lo usa para
definir el alcance de lo que un SAST de reglas puede prometer. El OWASP Top 10
2021 publica, para cada categoría, la lista de CWE que le corresponden. Esa lista
es el puente entre la salida de Bandit —un CWE por alerta— y una taxonomía
comparable entre herramientas.

El marco se completa con dos documentos distintos, que no deben confundirse con
el Top 10 web:

- **OWASP Top 10 for LLM Applications 2025** describe riesgos del componente
  LLM: inyección de prompt, fuga de información, cadena de suministro del modelo,
  envenenamiento de datos, manejo de salida, agencia excesiva, fuga del prompt de
  sistema, debilidades de embeddings, desinformación y consumo no acotado. Aplica
  al agente porque el código analizado es entrada no confiable y la salida del
  modelo se interpreta como una recomendación.
- **OWASP ASVS 5.0.0** (mayo de 2025) es un estándar de verificación de
  aplicaciones. Se usa como checklist parcial, con exclusiones declaradas, porque
  el producto es una CLI local y no una aplicación web autenticada.

La consecuencia metodológica es que la cobertura se mide y se declara. Un SAST de
reglas sobre Python no cubre las diez categorías: A05 (configuración), A06
(componentes), A09 (registro y monitoreo) y A10 (SSRF) quedan fuera por
construcción, y A01, A02, A04 y A07 solo de forma parcial. Presentar el Top 10
como una lista de verificación completa sería una afirmación falsa sobre la
norma y sobre el producto.

## 2.7 Síntesis y vacío que cubre el proyecto

La literatura muestra que los LLM pueden reducir falsos positivos de SAST, que
el ajuste eficiente permite especializar modelos pequeños y que los benchmarks
públicos exageran el desempeño por filtración y etiquetas débiles. También
muestra que la mayoría de los trabajos reportan reducción de falsos positivos
sin una medición pareada de falsos negativos, y que pocos separan el efecto del
prompt del efecto del ajuste.

Este proyecto cubre ese vacío a escala acotada: mide A (solo SAST), B (cero-shot),
C (modelo base con contexto y ejemplos), C0 (modelo base con el mismo formato de
alerta que D) y D (modelo afinado) sobre el mismo conjunto de 141 alertas,
reporta FPRR y FNR por separado, y mantiene un test reservado para una
evaluación única. No pretende superar el estado del arte
en detección; pretende producir una comparación honesta y reproducible de un
triage local, con un modelo de 1,5B que cabe en una GPU de 4 GB.

## Referencias

- ayshajavd. Code Security Vulnerability Dataset. Hugging Face.
  https://huggingface.co/datasets/ayshajavd/code-security-vulnerability-dataset
- Bandit. Herramienta de análisis estático de seguridad para Python.
  https://bandit.readthedocs.io
- Bhandari, G., Naseer, A., y Moonen, L. (2021). CVEfixes: automated collection
  of vulnerabilities and their fixes from open-source software. PROMISE 2021.
  https://doi.org/10.1145/3475960.3475985
- Brown, S. (2022). The C4 model for visualising software architecture.
  https://c4model.com
- Chen, Y. et al. (2023). DiverseVul: A New Vulnerable Source Code Dataset for
  Deep Learning Based Vulnerability Detection. RAID 2023.
  https://arxiv.org/abs/2304.00409
- Dettmers, T. et al. (2023). QLoRA: Efficient Finetuning of Quantized LLMs.
  https://arxiv.org/abs/2305.14314
- Ding, Y. et al. (2025). Vulnerability Detection with Code Language Models: How
  Far Are We? ICSE 2025. https://arxiv.org/abs/2403.18624
- Du, X. et al. (2026). Reducing False Positives in Static Bug Detection with
  LLMs: An Empirical Study in Industry. ICSE 2026 SEIP.
  https://doi.org/10.1145/3786583.3786910
- Hu, E. J. et al. (2021). LoRA: Low-Rank Adaptation of Large Language Models.
  https://arxiv.org/abs/2106.09685
- Hui, B. et al. (2024). Qwen2.5-Coder Technical Report.
  https://arxiv.org/abs/2409.12186
- Li, H. et al. (2025). IRIS: LLM-Assisted Static Analysis for Detecting Security
  Vulnerabilities. ICLR 2025. https://arxiv.org/abs/2405.17238
- llama.cpp. Inferencia de modelos en formato GGUF.
  https://github.com/ggml-org/llama.cpp
- MITRE. Common Weakness Enumeration (CWE). https://cwe.mitre.org
- Ollama. Ejecución local de modelos de lenguaje. https://ollama.com
- OWASP. (2021). OWASP Top 10:2021. https://owasp.org/Top10/2021/
- OWASP. (2025). OWASP Top 10 for LLM Applications 2025.
  https://genai.owasp.org/llm-top-10/
- OWASP. (2025). Application Security Verification Standard 5.0.0.
  https://asvs.owasp.org/
- Siddiq, M. L., y Santos, J. C. (2022). SecurityEval dataset: mining
  vulnerability examples to evaluate machine learning-based code generation
  techniques. MSR4P&S 2022. https://doi.org/10.1145/3549035.3561184
- Starke, G., y Hruschka, P. (2026). arc42: Template for Architecture
  Communication and Documentation, versión 9.1 (release 2026.10.19).
  https://arc42.org
- Zhang, T. et al. (2020). BERTScore: Evaluating Text Generation with BERT.
  ICLR 2020. https://arxiv.org/abs/1904.09675


# 3. Metodología

## 3.1 Dataset y verdad de referencia

El punto de partida es el dataset público
`ayshajavd/code-security-vulnerability-dataset`, que etiqueta funciones como
vulnerables o seguras e incluye el CWE de referencia. La etiqueta es a nivel de
función: no indica si el flujo es alcanzable ni identifica el repositorio de
origen. El corpus es mayoritariamente C (94,1 %), pero el proyecto trabaja solo
con las funciones Python porque Bandit analiza Python.

Antes de dividir se depuró el corpus: se eliminaron duplicados exactos por hash
del código normalizado y las etiquetas contradictorias (433 hashes). La división
se hizo con semilla 42 y produjo tres particiones:

| Partición | Muestras | Uso |
|---|---|---|
| Entrenamiento | 80 % | Ajuste del adaptador |
| Validación total (`val_total`) | 42.536 | Validación del ajuste y conjunto de evaluación |
| Test reservado | 17.542 | Evaluación única del Sprint 7 |

El test se usó **una sola vez**, en el Sprint 7, y no se empleó para ajustar
prompts ni hiperparámetros. La partición es aleatoria por función y el dataset no
incluye identificador de proyecto, de modo que dos funciones del mismo
repositorio pueden caer en particiones distintas. Esa limitación se declara como
amenaza a la validez. No se rehizo la partición agrupada porque el dataset no
tiene metadatos de repositorio; la comparación exacta de hashes normalizados
contra `train_80` y `val_total` dio 0 coincidencias, pero el análisis de
casi-duplicados (`eval/casi_duplicados.py`) encontró que el **70,3 % de las
funciones del holdout tienen un vecino con similitud de tokens ≥ 0,8** en train o
val, y 45/111 alcanzan ≥ 0,9. Eso no demuestra fuga, pero sí debilita la
interpretación del holdout como medición pura de generalización.

## 3.2 Construcción de los ejemplos de ajuste

`training/prepare_sft.py` convierte las funciones en mensajes
sistema/usuario/asistente. El sistema fija el rol de analista y el contrato JSON;
el asistente contiene la respuesta objetivo. Se solicitan hasta 12.000 ejemplos:
tras descartar prompts de más de 8.000 caracteres quedan 5.755 funciones
vulnerables y el balance 50/50 limita el conjunto a **11.510 ejemplos de ajuste
y 1.000 de validación**.

En la mitad de los ejemplos se inyecta una alerta del SAST sintética para que el
modelo aprenda el formato de triage: regla, CWE, severidad, confianza y mensaje.
La otra mitad se entrena sin alerta, con el código solamente. El CWE de la
alerta se toma del dataset cuando la función es vulnerable y de un pool de CWEs
frecuentes cuando es segura. Esa decisión evita que el modelo aprenda a asociar
la presencia de una alerta con la respuesta `VULNERABLE`.

## 3.3 Ajuste QLoRA

![Curva de pérdida](reportes/curva_perdida.png)
*Figura 1. Pérdida de entrenamiento del adaptador LoRA (1 época, 11.510 ejemplos). La curva de validación no se incluye porque las evaluaciones intermedias quedaron invalidadas por truncamiento de ejemplos largos.*


El modelo base es Qwen2.5-Coder-1.5B-Instruct. El ajuste usa QLoRA con
cuantización de 4 bits en formato NF4, doble cuantización y cómputo en bfloat16.
Los hiperparámetros efectivos fueron:

| Parámetro | Valor |
|---|---|
| Rango LoRA (`r`) | 16 |
| `lora_alpha` | 32 |
| `lora_dropout` | 0,05 |
| Módulos objetivo | `q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj` |
| Longitud máxima | 2.048 tokens |
| Lote por dispositivo | 1 |
| Acumulación de gradiente | 8 (lote efectivo 8) |
| Tasa de aprendizaje | 2 × 10⁻⁴ |
| Épocas | 1 |
| Precisión | bfloat16 |

El entrenamiento se ejecutó en una RTX 4070 Super y completó **1.439 pasos en
1 h 50 min 56 s**. La pérdida de entrenamiento cayó de 1,11 a 0,36 y se estancó.
El adaptador resultante tiene **18.464.768 parámetros entrenables (1,18 % del
total)** y ocupa 70,5 MB en disco.

La pérdida de validación de la corrida original quedó en `nan` por truncamiento
de ejemplos largos. El generador se corrigió (`encode_rows`), pero no se
reentrenó: por eso la Figura 1 muestra solo la curva de entrenamiento. Presentar
una curva de validación inexistente o suavizada sería un error metodológico.

## 3.4 Fusión, exportación y registro

El adaptador se fusiona con los pesos base; el conversor oficial de llama.cpp
genera un GGUF f16 y `llama-quantize` lo reduce a Q4_K_M. Ambas etapas las
orquesta `training/export_gguf.py`, que descarga el binario si no está
disponible. Los artefactos son:

| Artefacto | Tamaño |
|---|---|
| Adaptador LoRA | 70,5 MB |
| Modelo fusionado | 2.950 MB (f16) |
| GGUF Q4_K_M | 940,4 MB |
| VRAM en inferencia | 1.115 MB (contexto 4.096) |
| RAM del proceso `llama-server` | ~700 MB |

El GGUF se registra en Ollama con la etiqueta `qwen2.5-coder-triage`. Los hashes
SHA-256 están en `training/out/SHA256SUMS.txt`. La cuantización reduce recursos,
no especializa: el ajuste ocurrió antes y este trabajo no mide la pérdida de
calidad frente al modelo fusionado sin cuantizar.

## 3.5 Protocolo de evaluación

La evaluación se ejecuta con `eval/run_eval.py` sobre las **141 alertas** que
Bandit produce en las funciones Python de `val_total`: **91 reales y 50 falsos
positivos**. Cada alerta incluye la regla, el CWE del SAST, la severidad, la
confianza, la función, el mensaje y el código del contexto. La temperatura es 0
y la generación se limita a 512 tokens.

Se comparan cuatro configuraciones sobre el mismo conjunto:

| Configuración | Modelo | Prompt |
|---|---|---|
| A. Solo SAST | Bandit 1.8.6 | Sin modelo; conserva todas las alertas |
| B. Cero-shot | Base | Solo el código, sin alerta ni ejemplos |
| C. Contexto + few-shot | Base | Alerta del SAST + dos ejemplos resueltos |
| C0. Contexto | Base | Alerta del SAST, sin ejemplos |
| D. Modelo afinado | Afinado | Alerta del SAST, sin ejemplos |

C y D **no** comparten el prompt: C agrega dos ejemplos resueltos y D no. Para
separar el efecto del ajuste fino del efecto de los ejemplos se agregó C0, que
usa el mismo prompt que D con el modelo base. La atribución rigurosa es D contra
C0; C contra D mide el resultado práctico de un prompt cuidado frente al modelo
afinado.

La respuesta se parsea como JSON. Si el JSON es inválido, el veredicto no es
`VULNERABLE` ni `SAFE`, o la petición falla, la alerta se conserva como
`SOSPECHOSA` y se cuenta como respuesta inválida. Un `SAFE` se interpreta como
**recomendación de descarte**, nunca como eliminación.

El análisis pareado entre C0 y D se calcula con `eval/analisis_c0_vs_d.py`. El
script empareja las alertas por `id`, construye la matriz de acuerdo, aplica la
prueba exacta de McNemar sobre las discordancias y estima la diferencia de FPRR y
FNR con un bootstrap agrupado por archivo. El resultado queda en
`eval/analisis_c0_vs_d.json` y se interpreta en `docs/ANALISIS_C0_VS_D.md`.

### 3.5.1 Holdout

El Sprint 7 generó un conjunto independiente con
`python eval/build_eval_set.py --split test --confirm-holdout`. El test tiene
17.542 muestras, de las cuales 300 son funciones Python; Bandit produjo **111
alertas** (65 reales, 46 falsos positivos) sobre 71 archivos y 98 funciones. Se
evaluaron A, C0 y D con el mismo protocolo. D y C0 comparten el formato de
alerta; C no se corrió en el holdout porque agrega few-shot y no es el control
que aísla el ajuste.

El conjunto tiene 71 códigos únicos y 40 filas que repiten código, así que las
observaciones no son independientes. Por eso, además de los intervalos de Wilson,
el análisis reporta un bootstrap agrupado por archivo. El holdout se ejecutó una
sola vez y no se reutiliza para ajustar prompts, hiperparámetros ni reglas. Las
reglas y los comandos quedan registrados en `docs/PROTOCOLO_HOLDOUT.md`.

### 3.5.2 Banco sintético etiquetado

Para probar si el modelo lee el contexto o solo la regla y la severidad se
construyó un banco nuevo, independiente del holdout. `eval/sinteticas/casos.jsonl`
declara **26 alertas** (14 reales, 12 falsos positivos) sobre 13 reglas; cada
caso es un archivo Python con una sola alerta y una justificación escrita. Doce
de las trece reglas tienen al menos un caso real y uno falso, de modo que la
regla por sí sola no predice la etiqueta. La construcción y el detalle están en
`docs/BANCO_SINTETICO.md`.

La validación previa ejecuta solo Bandit (`python eval/banco_sintetico.py
--validar`) y comprueba que cada caso dispara la regla esperada: **26/26**. La
corrida llama a los dos modelos con el prompt del producto (`triage.build_prompt`
y `triage.SYSTEM`), temperatura 0 y `num_predict = 512`, y conserva la política
B403. Los resultados quedan en `eval/banco_sintetico.json` y se interpretan en
`docs/ANALISIS_BANCO_SINTETICO.md`.

Los intervalos de las métricas son de Wilson al 95 %, con el mismo método que el
holdout (`wilson` en `eval/banco_sintetico.py`). Para que la inclusión de los
intervalos no cambiara los veredictos, se recalcularon sobre el JSON guardado con
`python eval/banco_sintetico.py --recalcular`, sin volver a llamar a los modelos.
Los valores puntuales previos quedaron idénticos.

Dos diferencias impiden comparar sus cifras con C0/D del holdout. Primero, el
banco es adversarial: busca el contraejemplo de cada regla, no la prevalencia del
corpus. Segundo, usa el prompt del producto y no `prompt_d`, el formato con el
que se entrenó y evaluó D. El banco mide el producto, no el arnés de evaluación.
Con 26 casos y un solo anotador tampoco produce una estimación poblacional: sirve
para detectar regresiones y para probar una hipótesis mecánica.

### 3.5.3 Repositorios reales pinneados

`eval/corrida_repos_reales.py` clona tres repositorios en un commit fijo y
escanea solo el paquete fuente: `itsdangerous` 2.2.0 (`096c8d4`), `pyjwt` 2.10.1
(`3ebbb22`) y `httpie` 3.2.4 (`2105caa`). Bandit produce **38 alertas** (2, 1 y
35). Los dos modelos se ejecutan con el mismo prompt del producto y la misma
política; ninguna alerta se elimina.

La corrida es una prueba de humo, no una evaluación etiquetada: no hay verdad de
referencia por línea y por eso no produce FPRR ni FNR. Mide cuántas alertas
recomienda descartar cada modelo y en qué coincide. Sus resultados están en
`eval/corrida_repos_reales.json` y `docs/CORRIDA_REPOS_REALES.md`.

Además, las 38 alertas se auditieron manualmente a nivel de alerta con
`eval/auditoria_repos.py` para obtener una medida out-of-distribution. El
resultado (FPRR 100 %, FNR 0 %, precisión 91,2 %) está en
`eval/auditoria_repos_metricas.json` y `docs/AUDITORIA_REPOS.md`. La muestra es
pequeña y elegida por el autor, así que no reemplaza al holdout, pero sí aporta
una validación sobre código real fuera del dataset de entrenamiento.

## 3.6 Métricas

- **FPRR** (*false positive reduction rate*): falsos positivos recomendados para
  descarte sobre el total de falsos positivos. Mide el ahorro de revisión.
- **FNR** (*false negative rate*): alertas reales recomendadas para descarte
  sobre el total de alertas reales. Es la métrica principal.
- **FOR** (*false omission rate*): alertas reales entre las recomendadas para
  descarte. Mide la calidad de los descartes.
- **Precisión**: alertas reales entre las alertas conservadas.
- **Exactitud CWE**: concordancia entre el CWE predicho y el CWE del dataset,
  solo sobre alertas reales conservadas, con equivalencias entre CWEs
  relacionados (por ejemplo, 78/77/88).
- **Respuestas inválidas**: JSON inválido, veredicto fuera del contrato o error
  de la petición.

Los intervalos de confianza se calculan con el método de Wilson. Cuando las
observaciones se agrupan por archivo, se agrega un bootstrap agrupado (5.000
remuestreos) porque las alertas de un mismo archivo no son independientes. Para
las explicaciones se diseñó una rúbrica de cuatro criterios (CWE, vector de
ataque, corrección y claridad) en escala 0–2, con dos revisores ciegos y kappa de
Cohen; la rúbrica queda diseñada pero no aplicada. El holdout agregó una medida
descriptiva previa: la cantidad de explicaciones, vectores y correcciones únicos,
porque D colapsó a plantillas.

## 3.7 Pruebas funcionales y de robustez

Además de la evaluación, se ejecutó una batería sin modelo (`--no-llm`) sobre
casos límite: repositorio vacío, archivo vacío, sintaxis inválida y otro
lenguaje, con 0 alertas y código de salida 0; inyección de código con 4 alertas;
y un repositorio de 40 archivos con 360 alertas y salida 0. Los reportes JSON y
SARIF se validaron en cada caso.

Con modelo se probaron: la integración sobre `examples/sample_repo` (9 alertas,
9 conservadas, 4 recomendadas, 0 errores), Ollama apuntado a una URL inexistente
(9 alertas, 9 conservadas como `SOSPECHOSA`, 9 errores de modelo, salida 0) y una
batería de prompt injection con instrucciones maliciosas dentro del código. Las
pruebas unitarias cubren contexto por AST, deduplicación, SARIF, parseo,
política conservadora, modo asesor, Bandit y el límite de generación del cliente.

## 3.8 Reproducibilidad

Los comandos de entrenamiento, exportación y evaluación están en `README.md`.
Los resultados crudos, el conjunto de evaluación y los prompts viven en `eval/`.
`scripts/check_consistencia.py` compara las tablas publicadas contra los JSON y
falla si una cifra no coincide. Cualquier número del documento se rastrea hasta
un archivo y un comando.

La cadena de evaluación, en orden:

```powershell
python eval\build_eval_set.py                                  # conjunto de desarrollo
python eval\run_eval.py --config A
python eval\run_eval.py --config C0 --model qwen2.5-coder:1.5b
python eval\run_eval.py --config D --model qwen2.5-coder-triage
python eval\analisis_c0_vs_d.py                                # pareado C0/D
python eval\cobertura_owasp.py                                 # matriz OWASP
python eval\banco_sintetico.py --validar                       # banco: solo Bandit
python eval\banco_sintetico.py                                 # banco: base y D
python eval\corrida_repos_reales.py                            # repos pinneados
python eval\auditoria_repos.py --preparar                      # plantilla auditoría
# editar eval\auditoria_repos.jsonl
python eval\auditoria_repos.py --calcular                      # métricas auditoría
python eval\casi_duplicados.py                                 # amenaza de validez
python scripts\check_consistencia.py                           # auditoría de cifras
python -m unittest discover -s agente\tests                    # pruebas del producto
```

El holdout no se reejecuta: `eval/resultados_holdout_*.json` es el registro de la
corrida única del Sprint 7 y sus comandos están en `docs/PROTOCOLO_HOLDOUT.md`.
El banco y los repositorios se añadieron después y no participaron en el ajuste
ni en la elección de reglas. `eval/corrida_repos_reales.py --refrescar` vuelve a
clonar los commits fijados si hace falta reconstruir el entorno.

## 3.9 Marco OWASP y cobertura declarada

![Cobertura OWASP](reportes/grafica_cobertura_owasp.png)
*Figura 4. Cobertura OWASP Top 10 2021 por categoría.*


La cobertura no se estima: se cuenta. `eval/cobertura_owasp.py` toma el CWE que
Bandit reporta para cada alerta (`cwe_sast`), lo ubica en la lista oficial de CWE
del OWASP Top 10 2021 y escribe la matriz en `eval/cobertura_owasp.json`. Un CWE
que no aparece en ninguna lista oficial se reporta como `sin_categoria`; no se
fuerza a la categoría más parecida.

Se usa el CWE del SAST y no la columna `owasp` del dataset porque esa columna
asigna categoría al CWE etiquetado en la función, no al que Bandit señala. El
contraste entre ambas fuentes se reporta como hallazgo de calidad de datos: 10 de
las 30 etiquetas del dataset no coinciden con la lista oficial y 7 están forzadas
a A03.

La misma lógica se aplica en dos direcciones:

- **Hacia las alertas:** la matriz A01–A10 indica qué categorías tienen evidencia
  medida en desarrollo y en el holdout, y cuáles quedan fuera del alcance de
  Bandit.
- **Hacia el agente:** el OWASP Top 10 for LLM Applications 2025 se usa como
  modelo de amenaza del componente inteligente. Cada riesgo se declara aplicable
  o excluido, con la prueba o el control que lo respalda.

La cobertura OWASP no reemplaza a las métricas de calidad. FPRR, FNR y la rúbrica
miden el desempeño; OWASP ordena el alcance y el modelo de amenaza. Mezclar ambas
cosas produciría una tabla de cumplimiento que el proyecto no puede sostener.


# 4. Resultados y discusión

## 4.1 El intercambio entre ahorro y omisión

![Comparativa desarrollo](reportes/grafica_comparativa_desarrollo.png)
*Figura 2. Comparativa de FPRR y FNR en desarrollo.*


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

## 4.2 El FNR ya no está solo en B403

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

## 4.3 El CWE no es una clasificación independiente

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

## 4.4 Validez de la partición y del holdout

![Comparativa holdout](reportes/grafica_comparativa_holdout.png)
*Figura 3. Comparativa de FPRR y FNR en el holdout.*

![Casi-duplicados](reportes/grafica_casi_duplicados.png)
*Figura 7. Similitud máxima entre funciones del holdout y train/val.*


La evaluación de desarrollo usa `val_total`, la misma partición que alimentó la
validación del ajuste. Es una medición de desarrollo, no de generalización. El
holdout usa el split `test`, que no se usó para entrenar ni para ajustar prompts
ni hiperparámetros y se evaluó **una sola vez**. Aun así, la partición sigue
siendo aleatoria por función: el dataset no incluye identificador de repositorio,
de modo que dos funciones del mismo proyecto pueden haber caído en train y en
test. La comparación exacta de hashes normalizados contra `train_80` y
`val_total` dio **0 coincidencias**, pero el análisis de similitud de tokens
(`eval/casi_duplicados.py`) encontró que el **70,3 % de las funciones del
holdout tiene un vecino ≥ 0,8** en train o val, y 45/111 tienen similitud ≥ 0,9.
Esa amenaza ya no es pendiente: está medida y debe reportarse junto con las
métricas de generalización.

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

La segunda limitación es el significado de esa similitud. Los pares más altos
son variantes del mismo patrón (`pickle.__reduce__`, Flask + `sqlite3`). El
proyecto no puede demostrar que sean fuga real, porque el dataset no tiene
identificador de repositorio, pero sí puede decir que la partición aleatoria por
función no garantiza independencia. Esa amenaza debe aparecer junto con las
métricas de generalización.

## 4.5 La pérdida no mide calidad de triage

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

## 4.6 Las explicaciones colapsaron a plantillas

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

## 4.7 Robustez operativa

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
4,9 s de media (4,1 s de mediana) en el piloto de 10 alertas sobre una GTX 1650.
C promedia ~4,3 s por alerta, salvo una B102 patológica que agotó el timeout de
180 s antes de acotar la generación. El modelo ocupa 1.115 MB de VRAM y unos 700
MB de RAM. En una GPU de 4 GB cabe una instancia, pero no hay margen para
paralelizar sin medir el intercambio a disco.

## 4.8 Implicaciones de producto

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

## 4.9 Amenazas a la validez

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

## 4.10 Qué confirmó y qué no confirmó el holdout

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

## 4.11 Lectura por categoría OWASP

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

## 4.12 Evidencia posterior: banco sintético y repositorios reales

![Banco sintético](reportes/grafica_banco_sintetico.png)
*Figura 5. Banco sintético: FPRR y FNR base vs D.*

![Auditoría repos](reportes/grafica_auditoria_repos.png)
*Figura 6. Auditoría manual de repos reales.*


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
altas. Las 38 alertas se conservan en ambos casos y D no produjo errores.

Para salir de la correlación, se auditó manualmente las 38 alertas con verdad de
referencia a nivel de alerta (`docs/AUDITORIA_REPOS.md`). El resultado es
favorable pero no generalizable: de 31 falsos positivos, D descarta 31 (FPRR
100 %); de 7 alertas reales, D no descarta ninguna (FNR 0 %). La precisión de
los descartes es 91,2 % (3 de 34 SAFE son reales). Esa muestra es pequeña,
está elegida por nosotros y está dominada por B101 en tests; no contradice el
FNR del 9,2 % del holdout, pero sí muestra que, en proyectos reales con mucho
ruido de test, el modo asesor puede ahorrar revisión sin pérdidas observadas.

La diferencia con el banco sintético (FNR 35,7 %) es esperable: el banco fue
construido para romper la correlación regla→veredicto con casos reales de
severidad baja; los repos reales no tienen esa adversarialidad. Ambas mediciones
son necesarias: el banco mide el peor caso mecánico; la auditoría de repos mide
el caso favorable real.

Esa distinción es la que separan el banco y la auditoría de repos. La auditoría
manual de repos reales es favorable (FPRR 100 %, FNR 0 %), pero su muestra es
pequeña, elegida por el autor y dominada por B101 en tests; el banco, con la
misma estructura regla×contexto, muestra que D descarta también 5 reales cuando
la severidad es baja. La conjunción de ambas pruebas es el argumento más fuerte
contra el descarte automático: el ahorro es real y barato en el caso favorable,
pero se apoya en una señal que no distingue contexto y que falla en el caso
adversarial.

Límites que deben citarse junto con estas cifras: el banco tiene 26 alertas y un
solo anotador; es adversarial y no representa la prevalencia del corpus; usa el
prompt del producto y no el de entrenamiento. La corrida real está etiquetada
por un solo auditor y sus repos fueron seleccionados por nosotros. El colapso de
las explicaciones aparece tanto con el prompt de entrenamiento como con el del
producto, así que la causa más probable está en los datos de ajuste, no en la
plantilla. Ninguna de las dos pruebas se usó para ajustar prompts, reglas ni
umbrales, y el holdout permaneció intacto. El detalle reproducible está en
`docs/BANCO_SINTETICO.md`, `docs/ANALISIS_BANCO_SINTETICO.md`,
`docs/CORRIDA_REPOS_REALES.md` y `docs/AUDITORIA_REPOS.md`.


# 5. Conclusiones

## 5.1 Respuesta a la pregunta de investigación

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

## 5.2 Respuesta a las hipótesis secundarias

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

## 5.3 ¿Sirve para descarte automático?

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

## 5.4 Aportes del proyecto

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

## 5.5 Trabajo futuro

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

## 5.6 Qué agregó el holdout

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

## 5.7 Qué agregaron el banco y los repositorios

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

## 5.8 Cierre

El proyecto demuestra que un modelo pequeño, ajustado de forma eficiente y
ejecutado localmente, puede ahorrar revisión en un conjunto acotado de alertas de
Bandit. También demuestra, con la misma medición, que ese ahorro no autoriza a
sustituir al analista. La contribución no es el ahorro en sí, sino la comparación
que permite saber cuándo es aceptable y cuándo no. En esta versión la respuesta
es que todavía no lo es: el modo asesor se mantiene, B403 es obligatorio y el
descarte automático queda fuera de alcance.


# Anexos

## Anexo A. Reproducción

Requisitos de inferencia: Python 3.10 o superior, Bandit 1.9, Ollama y un modelo
registrado. En la máquina de desarrollo se usó Python 3.14.7, Bandit 1.9.4,
Ollama 0.40.14, `requests` 2.34.2 y `python-docx` 1.2.0.

```powershell
# 1. Dependencias del agente
pip install -r agente\requirements.txt

# 2. Modelo en Ollama (ya registrado como qwen2.5-coder-triage)
ollama list

# 3. Escaneo de un repositorio en modo asesor
python agente\run.py scan examples\sample_repo --model qwen2.5-coder-triage `
    --out reportes\sample

# 4. Escaneo sin modelo (solo SAST)
python agente\run.py scan examples\sample_repo --no-llm --out reportes\sample_sast

# 5. Evaluación A/B/C/C0/D
python eval\run_eval.py --config A
python eval\run_eval.py --config B  --model qwen2.5-coder:1.5b
python eval\run_eval.py --config C  --model qwen2.5-coder:1.5b
python eval\run_eval.py --config C0 --model qwen2.5-coder:1.5b
python eval\run_eval.py --config D  --model qwen2.5-coder-triage

# 6. Cobertura OWASP y análisis pareado C0/D
python eval\cobertura_owasp.py
python eval\analisis_c0_vs_d.py

# 7. Pruebas y consistencia de cifras
python -m unittest discover -s agente\tests -v
python scripts\check_consistencia.py

# 8. Validaciones out-of-distribution
python eval\banco_sintetico.py --validar
python eval\banco_sintetico.py
python eval\corrida_repos_reales.py
python eval\auditoria_repos.py --preparar
# editar eval\auditoria_repos.jsonl
python eval\auditoria_repos.py --calcular
python eval\casi_duplicados.py
```

El entrenamiento se ejecutó en una RTX 4070 Super con `training\entrenar_windows.ps1`.
El adaptador se exportó con `training\export_gguf.py`; el registro en Ollama y la
prueba de tres alertas de control están descritos en `README.md`.

## Anexo B. Artefactos y hashes

| Artefacto | Ruta | Tamaño |
|---|---|---|
| Adaptador LoRA | `training/out/qwen-coder-1.5b-lora/` | 70,5 MB |
| Modelo fusionado f16 | `training/out/qwen-coder-1.5b-merged/` | 2.950 MB |
| GGUF f16 | `training/out/gguf/qwen-coder-1.5b-f16.gguf` | — |
| GGUF Q4_K_M | `training/out/gguf/qwen-coder-1.5b-q4_k_m.gguf` | 940,4 MB |
| Registro de hashes | `training/out/SHA256SUMS.txt` | — |
| Log de entrenamiento | `training/out/train.log` (UTF-16) | 414 KB |

Hashes SHA-256:

```
561F877723465779DC049D2B5C3AA2501982931FF01473B227A57ACE924B6D4E  qwen-coder-1.5b-q4_k_m.gguf
B2990C07C3B0FA788B052E879FDF05C8B82180A13E10F5688B144696823A93D5  adapter_model.safetensors
ED23ABB0F677473486977A22F58D4A4D90105336797EB082DB08A232E9FFA9AD  qwen-coder-1.5b-f16.gguf
```

## Anexo C. Prompts

**Sistema (idéntico en entrenamiento y evaluación):**

> Eres un analista de seguridad de software. Analizas un fragmento de código y
> decides si contiene una vulnerabilidad real (VULNERABLE) o si es seguro
> (SAFE). Responde SOLO con un objeto JSON con las claves: veredicto, cwe,
> severidad, explicacion, vector_ataque, correccion.

**Plantilla de alerta (D y C0):**

```
Alerta del SAST (triage):
- Regla: {rule_id}
- CWE reportado: {cwe_sast}
- Severidad: {severity}
- Confianza: {confidence}
- Funcion: {function}
- Mensaje: {message}

Codigo fuente:
<code>
{code}
</code>

Devuelve el JSON.
```

**C** antepone dos ejemplos resueltos (una inyección SQL y un `assert` de
prueba) al mismo bloque de alerta. **B** envía solo el código, sin alerta ni
ejemplos. El texto completo está en `eval/run_eval.py` (`SYSTEM`, `FEW_SHOT`,
`TEMPLATE_ALERTA`).

**Diferencia con el prompt del producto.** `agente/src/agente_seguridad/triage.py`
usa un `SYSTEM` y un `TEMPLATE` más detallados: agrega archivo, línea y una
descripción campo por campo de la salida. Las métricas del proyecto se midieron
con el prompt de evaluación, no con el del producto. La comparación C0/D no se
ve afectada —ambas usan el mismo prompt—, pero el FPRR y el FNR reportados no
describen exactamente el comportamiento de la CLI. Alinear ambos prompts y medir
el efecto sobre `examples/sample_repo` queda como trabajo futuro; no se hizo en
este sprint porque el holdout ya está cerrado y el cambio no está medido.

El delimitador `<code>` separa el código de las instrucciones. No es una defensa
completa contra prompt injection: reduce el riesgo de que el modelo confunda
datos con órdenes, pero la validación de la salida y la política conservadora son
las que impiden que una inyección convierta una alerta en un descarte silencioso.

## Anexo D. Conjuntos de evaluación

`eval/eval_set.jsonl` contiene 141 alertas de Bandit sobre funciones Python de
`val_total`: 91 reales y 50 falsos positivos. Cada línea incluye `id`, `rule_id`,
`cwe_sast`, `cwe_dataset`, `truth`, `severity`, `confidence`, `function`,
`message` y `code`. El conjunto se regenera con `eval/build_eval_set.py`.

`eval/holdout_set.jsonl` contiene las 111 alertas del test reservado (65 reales,
46 falsos positivos) sobre 300 funciones Python. Se generó una sola vez con
`--split test --confirm-holdout`, se evaluó con A, C0 y D, y no se reutiliza para
ajustar nada. Su SHA256 es
`D9A91DC4B41170E0E2427D202E05F44E777A61C2F9DD4D4196D7EC752EAB1E81`; los hashes
de los resultados y las reglas de lectura están en `docs/ANALISIS_HOLDOUT.md` y
`docs/PROTOCOLO_HOLDOUT.md`.

## Anexo E. Pruebas

`agente/tests/test_agente.py` cubre contexto por AST, deduplicación, SARIF,
parseo de la respuesta, política conservadora, modo asesor, ejecución de Bandit,
mapeo OWASP y el límite de generación del cliente: **22 pruebas**, todas
correctas. La batería funcional y de robustez está en `eval/pruebas/LEEME.md`:
repositorio vacío, archivo vacío, sintaxis inválida, otro lenguaje, repositorio
grande, Ollama caído, JSON inválido y prompt injection.

## Anexo F. Tablas por regla

Las tablas de resultados por regla de Bandit viven en `docs/ANALISIS_C.md`,
`docs/ANALISIS_D.md` y `docs/ANALISIS_HOLDOUT.md`. La tabla comparativa del
documento se genera desde `scripts/build_avance5.py` y se valida contra los JSON
con `scripts/check_consistencia.py`. El análisis del holdout se reproduce con
`python eval/analisis_holdout.py`.

## Anexo G. Cobertura OWASP

La matriz se calcula con `python eval/cobertura_owasp.py`, que escribe
`eval/cobertura_owasp.json`. Se usa el CWE que reporta Bandit (`cwe_sast`) y no
la columna `owasp` del dataset. Las tablas siguientes se regeneran desde ese JSON.

**Cobertura del OWASP Top 10 2021**

| Categoría | Nombre | Desarrollo (141) | Holdout (111) |
|---|---|---:|---:|
| A01 | Broken Access Control | 3 | 1 |
| A02 | Cryptographic Failures | 1 | 3 |
| A03 | Injection | 83 | 76 |
| A04 | Insecure Design | 0 | 0 |
| A05 | Security Misconfiguration | 0 | 0 |
| A06 | Vulnerable and Outdated Components | 0 | 0 |
| A07 | Identification and Authentication Failures | 0 | 0 |
| A08 | Software and Data Integrity Failures | 53 | 30 |
| A09 | Security Logging and Monitoring Failures | 0 | 0 |
| A10 | Server Side Request Forgery (SSRF) | 0 | 0 |
| — | Fuera del Top 10 2021 | 1 | 1 |

**Regla, CWE del SAST y categoría**

| Regla | CWE | Categoría | Desarrollo | Holdout |
|---|---|---|---:|---:|
| B102 | CWE-78 | A03 | 7 | 7 |
| B201 | CWE-94 | A03 | 10 | 9 |
| B307 | CWE-78 | A03 | 21 | 27 |
| B404 | CWE-78 | A03 | 16 | 11 |
| B602 | CWE-78 | A03 | 5 | 2 |
| B603 | CWE-78 | A03 | 7 | 3 |
| B605 | CWE-78 | A03 | 11 | 9 |
| B608 | CWE-89 | A03 | 6 | 8 |
| B301 | CWE-502 | A08 | 25 | 15 |
| B403 | CWE-502 | A08 | 28 | 15 |
| B310 | CWE-22 | A01 | 1 | 0 |
| B311 | CWE-330 | A02 | 1 | 3 |
| B104 | CWE-605 | sin categoría | 1 | 0 |
| B108 | CWE-377 | A01 | 2 | 1 |
| B110 | CWE-703 | sin categoría | 0 | 1 |

**Discrepancias entre el mapeo del dataset y las listas oficiales**

El dataset asigna categoría OWASP a 30 CWE; 10 no coinciden con la lista oficial
y 7 de esas 10 están forzadas a A03.

| CWE | Dataset | Oficial | Observación |
|---|---|---|---|
| CWE-119 | A03 | sin categoría | Desbordamiento de búfer; el Top 10 2021 no cubre memoria. |
| CWE-125 | A03 | sin categoría | Lectura fuera de límites; ídem. |
| CWE-190 | A03 | sin categoría | Desbordamiento de entero; ídem. |
| CWE-401 | A03 | sin categoría | Fuga de memoria; ídem. |
| CWE-416 | A03 | sin categoría | Uso después de liberar; ídem. |
| CWE-476 | A03 | sin categoría | Desreferencia de puntero nulo; ídem. |
| CWE-787 | A03 | sin categoría | Escritura fuera de límites; ídem. |
| CWE-362 | A04 | sin categoría | Condición de carrera; no está en A04. |
| CWE-399 | A04 | sin categoría | Gestión de recursos; no está en A04. |
| CWE-269 | A01 | A04 | Gestión de privilegios; A04 la incluye explícitamente. |

**Categorías no medidas y motivo**

| Categoría | Motivo |
|---|---|
| A04 | Requiere diseño y flujo; Bandit no distingue intención. |
| A05 | Depende de la configuración de despliegue, no del código fuente. |
| A06 | Requiere inventario y versiones de dependencias. |
| A07 | Solo credenciales embebidas (B105–B107), fuera del corpus evaluado. |
| A09 | Requiere observar el runtime y los registros. |
| A10 | Bandit no sigue destinos de red. |

El detalle del modelo de amenaza del agente (OWASP Top 10 for LLM Applications
2025 y ASVS 5.0.0) está en `docs/OWASP.md`.