# Borrador — Estado del arte (Sprint 8)

> Documento de trabajo. Las referencias de esta sección están verificadas contra
> arXiv, Crossref o el sitio del proyecto al 3 de noviembre de 2026. Falta
> integrarlo al formato institucional y ampliar la discusión de trabajos
> relacionados con SAST comercial.

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

## 2.6 Síntesis y vacío que cubre el proyecto

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

## Referencias de esta sección

- Bhandari, G., Naseer, A., y Moonen, L. (2021). CVEfixes: automated collection
  of vulnerabilities and their fixes from open-source software. PROMISE 2021.
  https://doi.org/10.1145/3475960.3475985
- Chen, Y. et al. (2023). DiverseVul: A New Vulnerable Source Code Dataset for
  Deep Learning Based Vulnerability Detection. RAID 2023.
  https://arxiv.org/abs/2304.00409
- Dettmers, T. et al. (2023). QLoRA: Efficient Finetuning of Quantized LLMs.
  https://arxiv.org/abs/2305.14314
- Ding, Y. et al. (2025). Vulnerability Detection with Code Language Models: How
  Far Are We? ICSE 2025. https://arxiv.org/abs/2403.18624
- Du, X. et al. (2026). Reducing False Positives in Static Bug Detection with
  LLMs: An Empirical Study in Industry. ICSE 2026 SEIP.
  https://arxiv.org/abs/2601.18844
- Hu, E. J. et al. (2021). LoRA: Low-Rank Adaptation of Large Language Models.
  https://arxiv.org/abs/2106.09685
- Hui, B. et al. (2024). Qwen2.5-Coder Technical Report.
  https://arxiv.org/abs/2409.12186
- Li, H. et al. (2025). IRIS: LLM-Assisted Static Analysis for Detecting Security
  Vulnerabilities. ICLR 2025. https://arxiv.org/abs/2405.17238
- Siddiq, M. L., y Santos, J. C. (2022). SecurityEval dataset: mining
  vulnerability examples to evaluate machine learning-based code generation
  techniques. MSR4P&S 2022. https://doi.org/10.1145/3549035.3561184
- Zhang, T. et al. (2020). BERTScore: Evaluating Text Generation with BERT.
  ICLR 2020. https://arxiv.org/abs/1904.09675
