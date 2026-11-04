# Plan de trabajo y sprints: agente inteligente para la revisión de seguridad de código

**Equipo de 4 integrantes:** Santiago Reyes, Marien Daniela, Luis Patron, William Cuello  
**Versión:** 2 · 20 de octubre de 2026  
**Período de ejecución:** 13 de octubre al 15 de noviembre de 2026  

---

## 1. Qué cambió frente a la versión anterior

La estructura de 10 sprints (dos por semana) y la división clara de entregables se conserva. Los ajustes principales incorporados en esta versión son:

1. **Criterios de aceptación cuantitativos:** Los criterios incluyen métricas y números explícitos (tamaño del dataset, umbrales de $FPRR$ y $FOR$), marcados como metas propuestas a validar con el stakeholder.
2. **Estrategia de partición e higiene de datos:** El dataset se parte por repositorio completo (no por alerta individual) para evitar la fuga de datos (*data leakage*). Se agregan explicaciones de referencia escritas por humanos desde el Sprint 2 para permitir el cálculo de $BERTScore$.
3. **Escritura documental continua:** Cada sprint cierra actualizando una sección específica del documento académico final, atendiendo a la solicitud docente de no dejar la redacción para las semanas finales.
4. **Reorganización del ciclo de IA:** La fusión de pesos LoRA y la exportación a formato $GGUF$ pasan al final del Sprint 5. El Sprint 6 se reserva exclusivamente para la integración en la CLI, resiliencia y preparación del Avance 5.
5. **Consolidación del modelo base:** Se cierra la decisión del modelo base en `Qwen2.5-Coder-1.5B-Instruct`, dado que el flujo $QLoRA \rightarrow GGUF \rightarrow Ollama$ ya fue validado en el Avance 3. Gemma queda formalmente clasificada como trabajo futuro/comparativa opcional.
6. **Puntos de control internos y mitigación:** Se añade un cierre interno congelado un día antes de cada entrega oficial, un punto explícito de decisión al final del Sprint 6 y una tabla de riesgos con su respectivo Plan B.
7. **Verificación cualitativa de degradación:** Las pruebas de pérdida de capacidades generales del modelo se simplifican a una verificación cualitativa con un banco de 10 a 20 preguntas fuera de dominio.
8. **Evaluación de hipótesis no condicionada:** Los resultados experimentales dejan de darse por sentados; la hipótesis se evalúa formalmente como cumplida, parcialmente cumplida o no cumplida según los datos empíricos.

---

## 2. Reglas del plan

* **Cierre interno:** El entregable de cada avance oficial queda congelado un día antes de la fecha institucional. El día oficial se utiliza exclusivamente para verificación, ensayo de presentación y carga de archivos. *(Nota: El 26 de octubre, 2 de noviembre y 9 de noviembre son lunes; el 15 de noviembre es domingo. Por lo tanto, los cierres internos caen en fin de semana o sábado).*
* **Cierre de sprint:** Todo sprint se da por finalizado únicamente cuando cumple tres condiciones: código subido e integrado en el repositorio, sección correspondiente del documento redactada/actualizada y entrada registrada en la bitácora de decisiones.
* **Conjunto de verificación reservado:** El subconjunto de verificación manual (*holdout set*) se evalúa una sola vez en el Sprint 7. Todas las comparaciones e iteraciones intermedias se realizan estrictamente sobre el conjunto de validación.
* **Distribución de roles:** Cada sprint cuenta con un **Responsable Principal** y un **Revisor** designado (un integrante distinto del equipo).
* **Congelamiento de alcance (Code Freeze):** A partir del inicio del Sprint 8 queda estrictamente prohibido agregar nuevas funcionalidades o módulos al software; solo se permiten correcciones de errores bloqueantes.

---

## 3. Métricas y configuraciones a comparar

### Métricas de Evaluación

* **$FPRR$ (False Positive Reduction Rate / Tasa de Reducción de Falsos Positivos):** Proporción de alertas falsas generadas por el SAST que el agente descarta correctamente.
  $$FPRR = \frac{\text{Falsos Positivos Descartados por el Agente}}{\text{Total de Falsos Positivos del SAST}}$$
* **$FOR$ (False Omission Rate / Tasa de Omisión de Hallazgos Reales):** Proporción de vulnerabilidades reales detectadas por el SAST que el agente descarta por error (falsos negativos introducidos).
  $$FOR = \frac{\text{Vulnerabilidades Reales Descartadas por el Agente}}{\text{Total de Vulnerabilidades Reales del SAST}}$$
* **Exactitud CWE:** Proporción de hallazgos reales clasificados con el identificador $CWE$ correcto.
* **$BERTScore$:** Medida de similitud semántica contextual entre las explicaciones generadas por el agente y las explicaciones de referencia redactadas por el equipo.

### Configuraciones del Sistema
* **Configuración A:** SAST solo (Línea base determinista: toda alerta reportada se asume como positiva).
* **Configuración B:** Modelo base sin contexto del SAST (Zero-shot puro).
* **Configuración C:** Modelo base con contexto del SAST y ejemplos en el prompt (*Few-shot prompting*).
* **Configuración D:** Modelo afinado mediante $QLoRA$ con contexto del SAST.

> **Propósito de la comparación:** Comparar C contra D demuestra empíricamente que la mejora proviene del proceso de *fine-tuning* y no únicamente de la ingeniería de prompts.

### Metas Propuestas (a validar con el stakeholder)
1. **$FOR$ de Configuración D:** $\le 5\%$ en el conjunto de verificación (meta ideal: $0\%$).
2. **$FPRR$ de Configuración D:** Al menos $15\%$ por encima de la mejor configuración sin *fine-tuning* (B o C).
3. **Exactitud CWE de Configuración D:** Igual o superior a la Configuración C.
4. **$BERTScore$:** Se reporta de forma descriptiva sin umbral restrictivo.

*(Si las metas no se alcanzan, se informarán los resultados observados de manera transparente, acompañados de un análisis técnico de causas).*

---

## 4. Cronograma ejecutivo

| Sprint | Período | Cierre interno | Foco principal | Entregable clave |
| :--- | :--- | :--- | :--- | :--- |
| **1** | 13–15 oct | 15 oct | Decisiones base y documento | Alcance cerrado y documento actualizado |
| **2** | 16–19 oct | 19 oct | Dataset v1 | Dataset con partición por repositorio |
| **3** | 20–22 oct | 22 oct | Pipeline local base | CLI de extremo a extremo sin *fine-tuning* |
| **4** | 23–26 oct | 25 oct | Línea base y Avance 4 | Demo funcional y métricas de A, B y C (**Avance 4**) |
| **5** | 27–29 oct | 29 oct | Fine-tuning | Adaptador LoRA, modelo $GGUF$ en Ollama |
| **6** | 30 oct–2 nov | 1 nov | Integración de IA y Avance 5 | CLI con modelo afinado y 1.ª comparación (**Avance 5**) |
| **7** | 3–5 nov | 5 nov | Evaluación y pruebas | Tabla de experimentos y pruebas funcionales |
| **8** | 6–9 nov | 8 nov | Congelamiento y Avance 6 | Producto congelado y borrador completo (**Avance 6**) |
| **9** | 10–12 nov | 11 nov | Pendón y ensayo | Pendón, presentación y demo offline |
| **10** | 13–15 nov | 14 nov | Cierre y entrega final | Paquete final consolidado y cargado el 14 nov (**Entrega Final**) |

---

## 5. Definición detallada de sprints

### Sprint 1: Decisiones base y actualización documental (13–15 oct)
* **Período:** 13–15 de octubre | **Cierre interno:** 15 de octubre
* **Estado:** Completado.
* **Problema:** Existencia de decisiones abiertas que bloqueaban el avance técnico (lenguaje objetivo, familia de $CWE$, modelo base, fuentes del dataset) y necesidad de incorporar al documento las observaciones del Avance 3.
* **Criterios de aceptación:**
  * Decisiones registradas en bitácora: Lenguaje objetivo confirmado en Python (por madurez e integración con Bandit y Semgrep); modelo base fijado en `Qwen2.5-Coder-1.5B-Instruct`.
  * Recorte de seguridad delimitado por escrito con lista concreta de $CWE$: Credenciales embebidas ($CWE-798$), manejo inseguro de parámetros ($CWE-20$, $CWE-89$) y deserialización/hash débil.
  * Métricas y metas de la Sección 3 socializadas y validadas con el docente/stakeholder.
  * Repositorio organizado bajo estructura estándar y observaciones del Avance 3 resueltas en el documento.
* **Preguntas a resolver:** ¿La lista de $CWE$ elegida es lo suficientemente acotada para que un modelo pequeño aprenda y lo bastante amplia para contar con datos suficientes? ¿Las licencias de los repositorios seleccionados permiten su uso?
* **Documento:** Actualización de la Introducción, Planteamiento del Problema y Justificación.
* **Resultado / Conclusión:** Alcance técnico cerrado, decisiones registradas e historial documental al día.

---

### Sprint 2: Armado del Dataset Versión 1 (16–19 oct)
* **Período:** 16–19 de octubre | **Cierre interno:** 19 de octubre
* **Estado:** Completado.
* **Problema:** El dataset de demostración del Avance 3 (8 ejemplos) es insuficiente para entrenamiento o evaluación. Existe un riesgo elevado de contaminación o fuga de datos (*data leakage*) si los ejemplos de entrenamiento y prueba comparten fuentes.
* **Criterios de aceptación:**
  * Ejecución de Bandit/Semgrep sobre al menos 10 repositorios seleccionados.
  * Mínimo de 300 alertas etiquetadas manualmente como vulnerabilidad real o falso positivo, garantizando al menos un $30\%$ de casos reales.
  * Partición estricta **por repositorio**: $70\%$ entrenamiento, $15\%$ validación y $15\%$ verificación manual (*holdout* de al menos 40 alertas). Inclusión de un script de verificación automatizado que falle si un repositorio aparece en más de una partición.
  * Doble etiquetado en el $20\%$ de las muestras, con índice de acuerdo inter-evaluador ($\kappa$ de Fleiss/Cohen) $\ge 0.6$.
  * Redacción de explicaciones de referencia escritas por humanos para el conjunto de verificación (base para $BERTScore$).
* **Preguntas a resolver:** ¿Existe código duplicado (forks o librerías copiadas) entre repositorios de distintas particiones? ¿La distribución de vulnerabilidades reales refleja un escenario realista de uso?
* **Documento:** Redacción de la sección de Metodología de Datos y Etiquetado.
* **Resultado / Conclusión:** Dataset v1 construido, partición por repositorio validada e inspeccionada con el stakeholder.

---

### Sprint 3: Flujo base y pipeline local (20–22 oct)
* **Período:** 20–22 de octubre | **Cierre interno:** 22 de octubre
* **Estado:** Completado.
* **Problema:** Los componentes de análisis (SAST), la capa de inferencia y la generación de informes operan como elementos aislados; se requiere construir y orquestar el flujo automatizado desde el código fuente hasta el reporte final.
* **Criterios de aceptación:**
  * Flujo CLI funcional que ejecuta el SAST y normaliza los hallazgos a formato SARIF de forma transparente.
  * Lógica de deduplicación compuesta (combinando $CWE$, ruta de archivo y función/línea) para evitar la fusión de hallazgos independientes.
  * Extracción automática del contexto del código (bloque o función afectada).
  * Invocación del modelo base vía HTTP a Ollama con reporte estructurado de salida, asignando un ID único que enlaza la alerta del SAST con el veredicto.
* **Preguntas a resolver:** ¿El modelo de datos conserva la trazabilidad completa entre la alerta SAST, el fragmento de código y la decisión del agente? ¿Dónde se ubica el cuello de botella de latencia durante el análisis?
* **Documento:** Consolidación de la sección de Arquitectura y Modelo de Datos.
* **Resultado / Conclusión:** CLI ejecutable de extremo a extremo que procesa repositorios con el modelo sin ajustar de forma secuencial.

---

### Sprint 4: Línea base y preparación Avance 4 (23–26 oct)
* **Período:** 23–26 de octubre | **Cierre interno:** 25 de octubre (Entrega oficial: 26 oct)
* **Estado:** En curso (documento entregado; corridas B y C pendientes).
* **Problema:** Para atribuir valor al *fine-tuning* se requiere medir primero el desempeño del modelo sin ajustar. Asimismo, el Avance 4 exige software funcional demostrable en vivo.
* **Criterios de aceptación:**
  * Evaluación cuantitativa de las Configuraciones A, B y C sobre el conjunto de validación ($FPRR$, $FOR$, Exactitud $CWE$), tabulada formalmente.
  * Ensayos de la demostración en vivo completados el 25 de octubre sobre un flujo completo de extremo a extremo.
  * Paquete del **Avance 4** listo: documento con arquitectura, modelo de datos y evidencias de integración.
* **Preguntas a resolver:** ¿Qué nivel de $FPRR$ y $FOR$ registra el modelo base sin entrenamiento especializado? ¿Cuánto aporta la inclusión del contexto técnico dentro del prompt?
* **Documento:** Sección de Metodología Experimental y Resultados de la Línea Base.
* **Resultado / Conclusión:** **Avance 4 entregado** el 26 de octubre con software en vivo, arquitectura consolidada y métricas base establecidas.

---

### Sprint 5: Fine-tuning del modelo (27–29 oct)
* **Período:** 27–29 de octubre | **Cierre interno:** 29 de octubre
* **Estado:** Pendiente.
* **Problema:** El modelo genérico debe especializarse en el triage de la familia de vulnerabilidades seleccionada utilizando el dataset v1 de forma reproducible.
* **Criterios de aceptación:**
  * Entrenamiento $QLoRA$ ejecutado en Colab/Kaggle reutilizando la infraestructura validada, guardando *checkpoints* en Google Drive ante interrupciones.
  * Registro riguroso de hiperparámetros: semillas, *learning rate*, tamaño de lote, épocas y curvas de pérdida (*loss*) de entrenamiento vs. validación.
  * Exportación, fusión de pesos (*merge*) y conversión a binario $GGUF$ cuantizado (`Q4_K_M`), cargado en Ollama y probado con 3 alertas de control.
  * Verificación cualitativa simple de retención de capacidades generales (10 a 20 preguntas fuera de dominio).
* **Preguntas a resolver:** ¿La curva de pérdida en validación muestra señales de sobreajuste (*overfitting*)? ¿Se requiere un ajuste en los hiperparámetros o tamaño de lote?
* **Documento:** Sección de Entrenamiento del Modelo: Hiperparámetros, Entorno y Curvas de Aprendizaje.
* **Resultado / Conclusión:** Adaptador LoRA fusionado y modelo $GGUF$ operativo localmente en Ollama con bitácora de entrenamiento replicable.

---

### Sprint 6: Integración de IA y Avance 5 (30 oct–2 nov)
* **Período:** 30 de octubre–2 de noviembre | **Cierre interno:** 1 de noviembre (Entrega oficial: 2 nov)
* **Estado:** Pendiente.
* **Problema:** El modelo afinado debe integrarse al CLI local implementando mecanismos de resiliencia que eviten descartar alertas reales ante fallos en la generación de la IA.
* **Criterios de aceptación:**
  * Modelo afinado integrado al flujo de la CLI en sustitución del modelo base.
  * Política de seguridad implementada: si el modelo genera una respuesta malformada, ambigua o fuera de esquema JSON, la alerta **se conserva obligatoriamente** y se marca como `SOSPECHOSA`.
  * Cálculo de métricas de la Configuración D sobre el conjunto de validación y comparación contra A, B y C.
  * **Punto de decisión (1 de noviembre):** Si D no supera a C en la métrica $FPRR$ (manteniendo $FOR \le 5\%$), el equipo decide entre ejecutar un reentrenamiento en el Sprint 7 o reportar el resultado con análisis de causas.
  * Paquete del **Avance 5** consolidado.
* **Preguntas a resolver:** ¿La Configuración D reduce los falsos positivos sin incrementar la tasa de omisión de hallazgos reales ($FOR$)? ¿La latencia en consola se mantiene dentro de rangos operativos?
* **Documento:** Sección de Integración de Componentes Inteligentes y Mecanismos de Resiliencia.
* **Resultado / Conclusión:** **Avance 5 entregado** el 2 de noviembre con el componente de IA integrado, resiliencia probada y primera evaluación comparativa formal.

---

### Sprint 7: Evaluación cuantitativa y pruebas funcionales (3–5 nov)
* **Período:** 3–5 de noviembre | **Cierre interno:** 5 de noviembre
* **Estado:** Pendiente.
* **Problema:** Se requiere medir el rendimiento real del agente sobre el conjunto de datos no visto (*holdout*) y validar la estabilidad de la CLI ante escenarios límite.
* **Criterios de aceptación:**
  * Generación de la matriz de evaluación sobre el conjunto de verificación (evaluado una sola vez): $FPRR$, $FOR$, Exactitud $CWE$ y $BERTScore$ para A, B, C y D.
  * Auditoría manual cruzada sobre una muestra de las explicaciones generadas.
  * Ejecución de batería de pruebas funcionales: archivos vacíos, repositorios de gran tamaño, servicio de Ollama detenido, formato JSON inválido y código en otros lenguajes.
  * Contraste empírico de los resultados frente a las metas propuestas en la Sección 3.
* **Preguntas a resolver:** ¿El modelo afinado logra un equilibrio superior entre descarte de ruido y retención de vulnerabilidades reales frente al SAST aislado? ¿Las explicaciones generadas son claras para un perfil desarrollador?
* **Documento:** Sección de Resultados, Análisis Discursivo y Evaluación de Hipótesis.
* **Resultado / Conclusión:** Matriz de evaluación cuantitativa formalizada, hipótesis evaluada con datos reales y batería de pruebas del software completada.

---

### Sprint 8: Congelamiento y Avance 6 (6–9 nov)
* **Período:** 6–9 de noviembre | **Cierre interno:** 8 de noviembre (Entrega oficial: 9 nov)
* **Estado:** Pendiente.
* **Problema:** El código del software debe congelarse para concentrar el esfuerzo en la consolidación del documento académico, asegurando la coherencia entre las cifras reportadas y la ejecución del programa.
* **Criterios de aceptación:**
  * **Congelamiento de código (*Code Freeze*)** activo desde el 6 de noviembre: solo se permiten parches para errores bloqueantes, registrando cada cambio.
  * Borrador completo del documento: Introducción, Estado del Arte, Requisitos, Arquitectura, Entrenamiento, Experimentos, Resultados, Conclusiones y Referencias.
  * Verificación de reproducibilidad: confirmación de que los números de las tablas coinciden exactamente con la ejecución del software congelado.
  * Diagramación del boceto del pendón con espacio reservado para métricas finales.
* **Preguntas a resolver:** ¿El documento responde directamente a la pregunta de investigación y evalúa objetivamente la hipótesis? ¿Existen discrepancias entre el texto y el comportamiento de la CLI?
* **Documento:** Borrador integral finalizado y revisado.
* **Resultado / Conclusión:** **Avance 6 entregado** el 9 de noviembre con el producto congelado, evaluación completa y borrador del documento finalizado.

---

### Sprint 9: Preparación para la feria y pendón (10–12 nov)
* **Período:** 10–12 de noviembre | **Cierre interno:** 11 de noviembre (Entregable congelado el 11; Ensayo general: 12 nov)
* **Estado:** Pendiente.
* **Problema:** El proyecto debe sintetizarse visualmente para la Feria de Proyectos y la demostración técnica debe funcionar de forma autónoma sin depender de conexión a internet.
* **Criterios de aceptación:**
  * Pendón diseñado y enviado a impresión, incluyendo: Problema, Objetivo, Solución, Arquitectura, Componente de IA, Resultados clave, Conclusiones y Código QR a evidencias.
  * Diapositivas de presentación preparadas siguiendo la estructura: Problema $\rightarrow$ Solución $\rightarrow$ Funcionamiento $\rightarrow$ Demo $\rightarrow$ Componente Investigativo $\rightarrow$ Resultados.
  * Ensayo general de la demostración *offline* utilizando Ollama local en la máquina de presentación.
  * Aplicación de correcciones de fondo y forma derivadas de la revisión del Avance 6.
* **Preguntas a resolver:** ¿La demostración en consola es fluida y resistente ante fallos de red durante la feria? ¿El pendón comunica el aporte investigativo a un público no especialista?
* **Documento:** Incorporación de correcciones finales en el documento.
* **Resultado / Conclusión:** Pendón impreso, presentación lista y demostración técnica ensayada con éxito el 12 de noviembre.

---

### Sprint 10: Cierre, coherencia y entrega final (13–15 nov)
* **Período:** 13–15 de noviembre | **Cierre interno:** 14 de noviembre (Carga final: 14 nov; 15 nov como margen de seguridad)
* **Estado:** Pendiente.
* **Problema:** Todos los artefactos del proyecto (código, documento, dataset, pesas, pendón y diapositivas) deben integrarse sin contradicciones y cumpliendo la totalidad de los requisitos institucionales.
* **Criterios de aceptación:**
  * Auditoría de coherencia cruzada: verificación punto por punto de datos, métricas y afirmaciones entre el documento, la CLI, el pendón y la presentación.
  * Repositorio final etiquetado con versión estable (`tag v1.0`), incluyendo archivo `README.md` detallado con instrucciones de instalación y reproducción de experimentos.
  * Publicación de hiperparámetros, semillas, dataset particionado y scripts para replicación de resultados.
  * Carga del paquete final en la plataforma institucional el 14 de noviembre (dejando el 15 como margen de seguridad).
* **Preguntas a resolver:** ¿Un tercero puede clonar el repositorio y reproducir las métricas de evaluación siguiendo únicamente la documentación? ¿Se resolvieron todas las observaciones docentes?
* **Documento:** Versión final definitiva del Documento de Proyecto.
* **Resultado / Conclusión:** **Entrega Final completada** el 14 de noviembre (con el 15 como margen de seguridad) con todos los componentes aprobados y empaquetados.

---

## 6. Riesgos y plan B

| Riesgo | Probabilidad / Impacto | Plan B (Acción de Mitigación) |
| :--- | :--- | :--- |
| **El dataset v1 no alcanza las 300 alertas el 19 de octubre** | Media / Alto | Reducir el tamaño objetivo a 270 alertas (15% de holdout = 40 alertas, conservando el mínimo del Sprint 2) concentradas en 2 $CWE$, extendiendo la recolección de forma paralela durante el Sprint 3 y documentando la limitación en la metodología. |
| **Agotamiento de cuota de GPU en Colab/Kaggle** | Alta / Medio | Migrar el proceso a Kaggle Notebooks (30h/semana de T4/P100), guardar *checkpoints* intermedios en Google Drive y programar los entrenamientos con holgura al inicio del Sprint 5. |
| **El modelo afinado (D) no supera a la línea base (C)** | Media / Alto | Ejecutar una segunda corrida rápida de entrenamiento variando hiperparámetros (*learning rate*, *rank* LoRA); si no supera, reportar el resultado empírico analizando causas (tamaño de dataset, arquitectura del SLM). |
| **Incompatibilidad o lentitud del modelo en la laptop de la demo** | Media / Alto | Probar la ejecución en el equipo de la demo desde el Sprint 6; optimizar la cuantización a $Q4\_K\_M$ y disponer de un vídeo grabado en alta definición como respaldo de seguridad. |
| **Retraso acumulado en la redacción del documento final** | Media / Medio | Aplicar estrictamente la regla de "una sección redactada por sprint", utilizando las revisiones de cada avance para validar el texto progresivamente. |
| **Sobrecarga por entregas simultáneas en otras asignaturas** | Alta / Medio | Identificar los picos de carga académica al inicio de cada sprint en la reunión de planificación y redistribuir temporalmente las tareas entre el Responsable y el Revisor. |

---

## 7. Frentes de trabajo sugeridos

Para garantizar un avance equilibrado entre los 4 integrantes del equipo, las responsabilidades se estructuran en cuatro frentes principales. Cada sprint designa a un **Responsable Principal** y a un **Revisor** por frente:

1. **Frente 1: Datos y Etiquetado**  
   * Selección y licencias de los repositorios fuente del dataset.  
   * Ejecución de Bandit/Semgrep y recolección de alertas.  
   * Etiquetado manual, doble evaluación y cálculo del índice de acuerdo.  
   * Redacción de explicaciones de referencia para el conjunto de verificación.

2. **Frente 2: Modelo e IA**  
   * Investigación y validación del modelo base (`Qwen2.5-Coder-1.5B-Instruct`).  
   * Ingeniería de prompts (Configuraciones B y C).  
   * Entrenamiento $QLoRA$, fusión de pesos y conversión a $GGUF$.  
   * Carga y pruebas del modelo en Ollama local.

3. **Frente 3: Software y CLI**  
   * Ejecución del SAST y normalización a $SARIF$.  
   * Deduplicación, extracción de contexto e integración con Ollama por HTTP.  
   * Interfaz de línea de comandos, reportes y mecanismos de resiliencia.  
   * Pruebas funcionales, rendimiento y empaquetado del producto.

4. **Frente 4: Documentación y Difusión**  
   * Redacción y actualización continua del documento académico por sprint.  
   * Bitácora de decisiones y control de versiones del repositorio.  
   * Diagramas de arquitectura y material de sustentación.  
   * Pendón, diapositivas y preparación de la demostración en feria.

#### Designación de roles por sprint

| Sprint | Responsable Principal | Revisor |
| :--- | :--- | :--- |
| **1** | | |
| **2** | | |
| **3** | | |
| **4** | | |
| **5** | | |
| **6** | | |
| **7** | | |
| **8** | | |
| **9** | | |
| **10** | | |

> *Cada celda debe asignarse a un integrante distinto por sprint, procurando que ningún integrante acumule consecutivemente el rol de Responsable Principal en dos sprints seguidos y que el Revisor sea siempre alguien distinto del Responsable.*