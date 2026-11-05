# Borrador — Introducción (Sprint 8)

> Documento de trabajo para la memoria final. Reutiliza el problema y el alcance
> de los Avances 1–5, pero ordena la pregunta de investigación y las
> contribuciones con la evidencia ya medida en el Sprint 6.

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
- El error de omisión se concentra en reglas de importación (B403, B404), no en
  reglas de sink explícito (B301, B602, B608).
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
   7 y documentar las amenazas a la validez.

## 1.5 Contribuciones

El proyecto no pretende superar el estado del arte en detección de
vulnerabilidades. Aporta una comparación honesta y reproducible de un triage
local, con cuatro contribuciones concretas:

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

## 1.6 Alcance y exclusiones

**Incluido:**

- Python y Bandit como único SAST.
- Funciones del split de validación y del test reservado de un dataset público,
  con etiquetas a nivel de función.
- Un modelo Qwen2.5-Coder-1.5B-Instruct, adaptador LoRA, fusión, GGUF Q4_K_M y
  Ollama.
- Evaluación de desarrollo (A/B/C/C0/D), holdout (A/C0/D) y batería funcional.
- Reporte JSON y SARIF en modo asesor.

**Excluido:**

- Detección de vulnerabilidades que Bandit no reporta.
- Otros lenguajes (Java, C, JavaScript) y otros SAST (CodeQL, Semgrep).
- Descarte automático de alertas.
- Despliegue en producción, autenticación, multiusuario y integración CI/CD.
- Evaluación de explicaciones con referencias humanas (la rúbrica queda
  diseñada, pero no aplicada).
- Entrenamiento con el split de test: se reservó y se usó una sola vez para la
  evaluación del Sprint 7.

La exclusión del descarte automático no es una limitación técnica sino una
decisión basada en la evidencia: con FNR 9,2 % en el holdout (3,1 % con la
política B403, pero IC95 hasta 10,5 %), el producto no cumple la meta de omisión
y no puede eliminar alertas sin supervisión.

## 1.7 Estructura de la memoria

La memoria se organiza en nueve capítulos. El capítulo 2 revisa el estado del
arte en SAST, LLM para seguridad, datos y ajuste eficiente. El capítulo 3 fija
requisitos y alcance. El capítulo 4 describe la arquitectura y el contrato de
datos. El capítulo 5 detalla la metodología: dataset, particiones,
entrenamiento, exportación y métricas. El capítulo 6 presenta los experimentos y
resultados (entrenamiento, A/B/C/C0/D, holdout, latencia, pruebas). El capítulo 7
discute el intercambio entre ahorro y omisión, el CWE copiado, el sesgo de B403 y
B311, el colapso de las explicaciones y las amenazas a la validez. El capítulo 8
responde a la hipótesis y enumera el trabajo futuro. El capítulo 9 reúne las
referencias y los anexos de reproducción.

El hilo argumental es único: un modelo pequeño, entrenado de forma eficiente y
ejecutado localmente, puede ahorrar revisión en un conjunto acotado, pero no
puede sustituir la decisión del analista. La contribución no es el ahorro en sí,
sino la medición que permite saber cuándo ese ahorro es aceptable y cuándo no.
