# Borrador — Metodología (Sprint 8)

> Documento de trabajo. Consolida el dataset, el ajuste, la exportación y el
> protocolo de evaluación del Sprint 6, el holdout del Sprint 7 y las pruebas
> posteriores con banco sintético y repositorios reales. Las cifras de resultados
> viven en `docs/ANALISIS_C.md`, `docs/ANALISIS_D.md`,
> `docs/ANALISIS_HOLDOUT.md` y `eval/*.json`.

## 5.1 Dataset y verdad de referencia

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
contra `train_80` y `val_total` dio 0 coincidencias, pero los casi-duplicados
quedan pendientes.

## 5.2 Construcción de los ejemplos de ajuste

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

## 5.3 Ajuste QLoRA

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

## 5.4 Fusión, exportación y registro

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

## 5.5 Protocolo de evaluación

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

### 5.5.1 Holdout

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

### 5.5.2 Banco sintético etiquetado

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

Dos diferencias impiden comparar sus cifras con C0/D del holdout. Primero, el
banco es adversarial: busca el contraejemplo de cada regla, no la prevalencia del
corpus. Segundo, usa el prompt del producto y no `prompt_d`, el formato con el
que se entrenó y evaluó D. El banco mide el producto, no el arnés de evaluación.
Con 26 casos y un solo anotador tampoco produce una estimación poblacional: sirve
para detectar regresiones y para probar una hipótesis mecánica.

### 5.5.3 Repositorios reales pinneados

`eval/corrida_repos_reales.py` clona tres repositorios en un commit fijo y
escanea solo el paquete fuente: `itsdangerous` 2.2.0 (`096c8d4`), `pyjwt` 2.10.1
(`3ebbb22`) y `httpie` 3.2.4 (`2105caa`). Bandit produce **38 alertas** (2, 1 y
35). Los dos modelos se ejecutan con el mismo prompt del producto y la misma
política; ninguna alerta se elimina.

La corrida es una prueba de humo, no una evaluación etiquetada: no hay verdad de
referencia por línea y por eso no produce FPRR ni FNR. Mide cuántas alertas
recomienda descartar cada modelo y en qué coincide. Sus resultados están en
`eval/corrida_repos_reales.json` y `docs/CORRIDA_REPOS_REALES.md`. La ausencia de
etiquetas es deliberada: la corrección se mide en el banco sintético y en la
auditoría manual de `docs/SMOKE_REPOS.md`.

## 5.6 Métricas

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

## 5.7 Pruebas funcionales y de robustez

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

## 5.8 Reproducibilidad

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
python scripts\check_consistencia.py                           # auditoría de cifras
python -m unittest discover -s agente\tests                    # pruebas del producto
```

El holdout no se reejecuta: `eval/resultados_holdout_*.json` es el registro de la
corrida única del Sprint 7 y sus comandos están en `docs/PROTOCOLO_HOLDOUT.md`.
El banco y los repositorios se añadieron después y no participaron en el ajuste
ni en la elección de reglas. `eval/corrida_repos_reales.py --refrescar` vuelve a
clonar los commits fijados si hace falta reconstruir el entorno.

## 5.9 Marco OWASP y cobertura declarada

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
