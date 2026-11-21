# Avance extra

## Auditoría LLM-first: detección directa de vulnerabilidades antes del SAST

**Documento de integración para la memoria «Agente inteligente para la revisión de seguridad de código fuente»**

**Fecha:** 11 de noviembre de 2026  
**Rama:** `feature/sprint-7`  
**Alcance:** cambios de implementación, datos, evaluación y documentación del modo modelo primero.

> Este archivo contiene el avance adicional y las modificaciones que deben incorporarse a la memoria. No se regeneró el PDF ni el `.docx`; la entrega de este avance se hace únicamente en Markdown, como se solicitó.

---

## Resumen ejecutivo

La versión anterior del producto era un **triage de alertas SAST**: Bandit encontraba una posible vulnerabilidad y el modelo decidía si era real o un falso positivo. Esa arquitectura hereda el límite del SAST: si Bandit no genera la alerta, el modelo nunca ve el fragmento y no puede detectar la vulnerabilidad.

En esta iteración se añadió un modo **LLM-first** o **modelo primero**. El modelo recibe directamente fragmentos de código Python y emite por sí mismo un veredicto, un CWE, una severidad y una explicación. Solo las respuestas `VULNERABLE` se convierten en hallazgos. El modo se integró en la CLI como `--scanner llm` y `--scanner all`, sin eliminar el triage existente ni cambiar el modo asesor.

También se construyó el pipeline necesario para que este modo sea medible:

- generador de SFT directo código → JSON (`training/build_audit_sft.py`);
- conjunto de evaluación sin alertas SAST (`eval/audit_eval_set.jsonl`);
- runner de métricas de detección directa (`eval/run_audit_eval.py`);
- pruebas unitarias e integración con la CLI;
- documentación de la regla OWASP específica para este modo.

El pipeline quedó funcional, pero **todavía no se entrenó un modelo especializado para auditoría directa**. La primera línea base, con `qwen2.5-coder:1.5b` y 40 fragmentos, muestra el comportamiento esperado de un modelo no ajustado para esta tarea: recall alto, pero muchos falsos positivos y muy baja exactitud de CWE.

| Métrica | Línea base |
|---|---:|
| Fragmentos evaluados | 40 (20 vulnerables / 20 seguros) |
| Precisión | 55,2 % |
| Recall | 80,0 % |
| F1 | 65,3 % |
| FPR | 65,0 % |
| FNR | 20,0 % |
| Exactitud CWE | 12,5 % |
| Respuestas inválidas | 5/40 |

**Conclusión:** el modo LLM-first ya es ejecutable y medible, pero el modelo base no es confiable como detector independiente. La siguiente iteración debe entrenar el adaptador con el SFT nuevo y evaluarlo sobre los 214 fragmentos de desarrollo antes de considerar cualquier uso fuera del modo asesor.

---

## 1. Motivación y cambio de enfoque

### 1.1 El límite del triage

El flujo anterior era:

```text
repositorio → Bandit → alerta normalizada → modelo → veredicto
```

El modelo solo podía actuar sobre lo que Bandit ya había señalado. Esto tiene dos consecuencias:

1. **Dependencia de la cobertura del SAST.** Una vulnerabilidad que Bandit no detecta no llega al modelo.
2. **Sesgo de la alerta.** El modelo ve la regla, el CWE y la línea señalada; puede apoyarse en esa pista en lugar de analizar el código de forma independiente.

El proyecto ya había documentado que el CWE del modelo en modo triage copia el CWE del SAST. Eso es deseable para el triage, pero impide saber si el modelo puede detectar por sí mismo.

### 1.2 La pregunta complementaria

La pregunta principal de la memoria sigue siendo la misma: si el ajuste fino mejora el triage sin aumentar la omisión de vulnerabilidades reales. Este avance añade una pregunta complementaria, no la sustituye:

> ¿Puede el mismo modelo, sin una alerta SAST, detectar vulnerabilidades directamente en el código y emitir un CWE útil?

La pregunta es deliberadamente acotada:

- solo Python, porque es el lenguaje que analiza Bandit y el que se filtró en el corpus;
- solo fragmentos de código, sin flujo entre archivos ni dependencias;
- solo una evaluación de desarrollo, sin tocar el holdout;
- solo una línea base con el modelo base, no una afirmación sobre el modelo afinado.

### 1.3 Por qué no se reemplaza el triage

El modo LLM-first no invalida el trabajo anterior. Las alertas SAST siguen siendo evidencia barata y reproducible; el modelo puede aportar contexto y detectar casos que el SAST no marca. Por eso la CLI permite tres combinaciones:

- solo SAST;
- solo LLM;
- LLM primero y SAST después (`all`).

El modo asesor se mantiene: una recomendación `SAFE` del triage nunca elimina la alerta. Los hallazgos positivos del modo LLM-first son hallazgos del detector y no se vuelven a triagear.

---

## 2. Diseño implementado

### 2.1 Flujo del modo LLM-first

```text
archivo .py
   │
   ├─ ast.parse
   │    ├─ funciones externas → fragmentos
   │    └─ código de módulo → fragmentos
   │
   ├─ ventanas de máximo 6.000 caracteres
   │
   ├─ prompt de auditoría (solo código)
   │
   ├─ Ollama
   │
   ├─ JSON: VULNERABLE / SAFE + CWE + explicación
   │
   └─ solo VULNERABLE → Finding
```

El módulo principal es `agente/src/agente_seguridad/llm/code_audit.py`.

### 2.2 Fragmentación

La fragmentación busca que el prompt se parezca al corpus de entrenamiento, no a una alerta de Bandit.

- Se procesan únicamente archivos `.py`.
- Se omiten directorios como `.git`, `node_modules`, `__pycache__`, `.venv`, `build`, `dist`, `reportes` y similares.
- Se usa `ast.parse` para localizar funciones.
- Se seleccionan las funciones externas; las funciones anidadas dentro de una función seleccionada no se emiten por separado.
- El código de módulo que no queda cubierto por una función se emite como fragmento `<modulo>` si contiene algo distinto de clases, funciones, decoradores o líneas vacías.
- Los fragmentos largos se dividen en ventanas de máximo `6.000` caracteres, con un solapamiento de hasta 5 líneas.
- Si el archivo no parsea, se emite un único fragmento `<sin_ast>` con los primeros 6.000 caracteres, para no perder el archivo silenciosamente.

Cada fragmento conserva archivo, línea inicial, línea final, función y lenguaje.

### 2.3 Prompt

El prompt de sistema es:

```text
Eres un analista de seguridad de software. Analizas un fragmento de codigo y decides
si contiene una vulnerabilidad real (VULNERABLE) o si es seguro (SAFE). Responde SOLO
con un objeto JSON con las claves: veredicto, cwe, severidad, explicacion, vector_ataque, correccion.
```

El prompt de usuario es:

```text
Analiza el siguiente fragmento de codigo en {language}.

<code_snippet>
{code}
</code_snippet>
```

No se incluye la alerta de Bandit, ni la regla, ni el CWE del dataset. La única entrada es el código y el lenguaje.

### 2.4 Contrato de salida y validación

El modelo debe devolver un JSON con:

| Campo | Uso |
|---|---|
| `veredicto` | `VULNERABLE` o `SAFE`; cualquier otro valor invalida la respuesta |
| `cwe` | Obligatorio y numérico cuando el veredicto es `VULNERABLE` |
| `severidad` | `Alta`, `Media`, `Baja` o `Info`; si falta o no es válida, se usa `Media` |
| `explicacion` | Justificación breve |
| `vector_ataque` | Cómo se explotaría |
| `correccion` | Mitigación sugerida |

Reglas de aceptación:

- `SAFE` no crea hallazgo.
- `VULNERABLE` con CWE normalizable crea un `Finding`.
- `VULNERABLE` sin CWE numérico se considera respuesta inválida y no crea hallazgo.
- JSON malformado, veredicto desconocido o error de Ollama se cuentan como respuesta inválida.
- Una respuesta inválida no inventa un hallazgo ni cambia una alerta SAST existente.

El parser tolera bloques Markdown y texto alrededor del JSON: elimina las cercas ```` ``` ```` y recorta desde la primera `{` hasta la última `}`. No intenta “arreglar” un JSON roto.

### 2.5 Cómo se construye el `Finding`

Los hallazgos del modelo usan:

| Campo | Valor |
|---|---|
| `rule_id` | `LLM-CWE-xx` |
| `cwe` | CWE normalizado del modelo |
| `severity` | Severidad del modelo en minúsculas |
| `confidence` | `MEDIUM` |
| `message` | `El modelo detecta CWE-xx: ...` |
| `file`, `line`, `end_line` | Ubicación del fragmento |
| `code` | Primeros 500 caracteres del fragmento |
| `function` | Nombre de la función o `<modulo>` |
| `owasp` | `owasp.etiqueta(cwe)` |
| `context` | Fragmento completo |
| `triage.origen` | `llm_audit` |
| `triage.veredicto` | `VULNERABLE` |

La herramienta se reporta como `llm-audit` en el `ToolRun` y en el resumen por herramienta.

### 2.6 Regla OWASP en este modo

La regla general del proyecto sigue siendo: **OWASP se deriva del CWE del detector que originó el hallazgo**.

- En triage, el detector es Bandit o el escáner OWASP propio; se usa el CWE del SAST.
- En LLM-first, el detector es el modelo; se usa el CWE que el modelo declara.
- Nunca se usa la columna `owasp` del dataset.
- El modelo no puede imponer una categoría OWASP: solo puede aportar un CWE; la categoría se calcula con `owasp.etiqueta`.

Esta es la única excepción a la fórmula “CWE del SAST”, y está documentada en `docs/OWASP.md`.

### 2.7 Integración en la CLI

La CLI incorpora estos valores en `--scanner`:

| Valor | Comportamiento |
|---|---|
| `both` | Bandit + escáner OWASP; triage del modelo sobre las alertas. Es el valor por defecto. |
| `bandit` | Solo Bandit. |
| `owasp` | Solo escáner OWASP propio. |
| `llm` | Solo auditoría LLM-first; no ejecuta Bandit ni OWASP. |
| `all` | Auditoría LLM-first primero y después Bandit + OWASP. |

Opciones relacionadas:

- `--audit-max-chars`: tamaño máximo de cada fragmento; por defecto `6000`.
- `--audit-max-chunks`: límite de fragmentos analizados; `0` significa todos.
- `--max-alerts`: límite de alertas SAST que pasan a triage; no limita la auditoría LLM.
- `--no-llm`: solo SAST. Es incompatible con `--scanner llm` y `--scanner all`; la CLI devuelve error de uso (exit 2).
- Si Ollama no responde y el modo requiere auditoría, la CLI termina con exit 4.

El modo `all` ejecuta la auditoría LLM **antes** de Bandit y OWASP. Los hallazgos del modelo se agregan al mismo reporte, pero no se re-triagean: su veredicto y explicación ya son la respuesta del detector.

### 2.8 Triage y deduplicación

- Los hallazgos con `triage["origen"] == "llm_audit"` se omiten en el triage posterior.
- `dedup.with_ids` actualiza también `triage["finding_id"]`, para que la trazabilidad del reporte siga siendo consistente.
- El modo asesor no cambia para las alertas SAST: `SAFE` solo recomienda descarte y la alerta permanece visible.

---

## 3. Datos y construcción del SFT

### 3.1 Fuente y particiones

Se usó el dataset público `ayshajavd/code-security-vulnerability-dataset`, ya descargado en `dataset/data/*.parquet`, y los splits generados por `dataset/scripts/build_splits.py`:

- `train_80.jsonl` para entrenamiento;
- `val_total.jsonl` para validación y para el conjunto de evaluación de desarrollo;
- el test/holdout no se usó.

El dataset tiene etiquetas de lenguaje ruidosas: hay fragmentos Go, Ruby, Swift y otros marcados como Python. Por eso el generador valida cada fragmento Python con `ast.parse(textwrap.dedent(...))`.

### 3.2 Filtros aplicados

Configuración por defecto de `training/build_audit_sft.py`:

| Filtro | Valor |
|---|---|
| Lenguaje | `Python` |
| Longitud mínima | 40 caracteres |
| Longitud máxima | 8.000 caracteres |
| Duplicados | Eliminados por hash del código normalizado |
| Fuga de evaluación | Se prohíben hashes de `eval/eval_set.jsonl` y `eval/holdout_set.jsonl` |
| Validación sintáctica | `ast.parse` obligatorio para Python |
| Balance | `ratio = 2.0` |
| Mezcla de triage | `triage_frac = 0.5`, solo si existen los archivos de triage reales |

### 3.3 Resultado del SFT

| Partición | Filas leídas | Descartes por lenguaje | Descartes por sintaxis | Vulnerables | Seguros | Total |
|---|---:|---:|---:|---:|---:|---:|
| Entrenamiento (`train_80`) | 101.878 | 100.414 | 1.054 | 195 | 215 | **410** |
| Validación (`val_total`) | 42.536 | 41.887 | 435 | 108 | 106 | **214** |

El filtro de sintaxis es el que más reduce el corpus: de 1.464 fragmentos marcados como Python en `train_80`, solo 410 parsean y pasan los demás filtros. Esto confirma que la etiqueta de lenguaje del dataset no es confiable.

CWEs más frecuentes:

| CWE | Train | Validación |
|---|---:|---:|
| CWE-94 | 77 | 42 |
| CWE-502 | 40 | 27 |
| CWE-787 | 23 | 11 |
| CWE-119 | 18 | 8 |
| CWE-20 | 14 | 7 |

### 3.4 Formato del ejemplo

Cada ejemplo tiene tres mensajes:

```json
{
  "messages": [
    {"role": "system", "content": "Eres un analista de seguridad..."},
    {"role": "user", "content": "Analiza el siguiente fragmento... <code_snippet>...</code_snippet>"},
    {"role": "assistant", "content": "{\"veredicto\":\"VULNERABLE\",\"cwe\":\"CWE-94\",...}"}
  ],
  "meta": {
    "language": "Python",
    "vulnerable": true,
    "cwe": "CWE-94",
    "hash": "...",
    "source": "...",
    "task": "audit"
  }
}
```

El objetivo se genera con el CWE del dataset y plantillas variadas de explicación, vector y corrección. No se incluye `finding_id`, porque no hay alerta SAST.

### 3.5 Estado del entrenamiento

El SFT está generado, pero **no se entrenó un adaptador nuevo en esta iteración**. El entorno local actual no tiene `torch`, `transformers`, `peft` ni `datasets`, y no dispone de GPU/CUDA. El adaptador existente `qwen-coder-1.5b-lora` fue entrenado para triage con alertas, no para auditoría directa.

El comando previsto para una máquina con GPU es:

```powershell
python training\build_audit_sft.py
python training\train_qlora.py --quant 4bit --epochs 1 --decision-weight 3.0 `
    --train training\data\train_audit.jsonl `
    --val training\data\val_audit.jsonl `
    --out training\out\qwen-coder-1.5b-lora-v3
```

Los archivos generados son:

- `training/data/train_audit.jsonl` (410 ejemplos);
- `training/data/val_audit.jsonl` (214 ejemplos);
- `training/data/audit_sft_stats.json` (trazabilidad de filtros).

---

## 4. Evaluación de la detección directa

### 4.1 Construcción del conjunto

`eval/build_audit_eval_set.py` construye un conjunto sin alertas SAST a partir de `val_total.jsonl`.

- Rechaza explícitamente un archivo cuyo nombre contenga `holdout`.
- Extrae solo el código del prompt.
- Exige Python parseable y entre 40 y 8.000 caracteres.
- Elimina duplicados por hash.
- Guarda `truth`, `cwe_dataset`, `severity`, `source` y un `id` estable.
- Baraja con semilla 42.

Resultado: `eval/audit_eval_set.jsonl` con **214 fragmentos** (108 vulnerables / 106 seguros). El límite `--per-class 300` no se alcanza porque el corpus Python parseable de validación es pequeño.

### 4.2 Métricas

`eval/run_audit_eval.py` mide un detector binario:

- TP: vulnerables clasificadas como `VULNERABLE`;
- FN: vulnerables no clasificadas como `VULNERABLE`;
- FP: seguras clasificadas como `VULNERABLE`;
- TN: seguras no clasificadas como `VULNERABLE`;
- precisión, recall, F1, FPR y FNR;
- exactitud de CWE solo sobre los verdaderos positivos;
- respuestas inválidas, contadas como negativas y reportadas aparte.

La comparación de CWE usa familias de equivalencia para no castigar sinónimos razonables, por ejemplo `CWE-259`/`798`/`257`, `CWE-327`/`328`/`326`/`310`/`916`, `CWE-89`/`564`/`943` o `CWE-78`/`77`/`88`. La lista está en `EQUIV` dentro del runner.

### 4.3 Línea base

Se ejecutó con el modelo base disponible en Ollama:

```powershell
python eval\run_audit_eval.py --model qwen2.5-coder:1.5b --limit 40 --timeout 180
```

Resultado sobre los primeros 40 fragmentos del conjunto barajado (20 vulnerables / 20 seguros):

| Métrica | Valor |
|---|---:|
| TP | 16 |
| FN | 4 |
| FP | 13 |
| TN | 7 |
| Precisión | 55,2 % |
| Recall | 80,0 % |
| F1 | 65,3 % |
| FPR | 65,0 % |
| FNR | 20,0 % |
| Exactitud CWE | 12,5 % (2/16) |
| Respuestas inválidas | 5/40 |

Las cinco respuestas inválidas fueron dos vulnerables y tres seguras. Al contar como negativas, dos se contabilizan como FN y tres como TN; no se creó ningún hallazgo para ellas.

Lectura:

- El recall alto es esperable porque el modelo tiende a declarar `VULNERABLE` ante código con patrones sospechosos.
- El FPR del 65 % muestra el problema opuesto: el modelo no distingue bien el contexto seguro.
- La exactitud CWE del 12,5 % indica que el CWE del modelo base no es utilizable como clasificación independiente.
- El 12,5 % de respuestas inválidas obliga a mejorar el formato de salida o el prompt antes de usar el modo en producción.
- La muestra es pequeña y no es el holdout; no permite afirmaciones estadísticas.

El resultado completo está en `eval/resultados_audit_qwen2.5-coder_1.5b.json`.

### 4.4 Comparación con el triage

No se debe comparar directamente esta línea base con el FPRR/FNR del triage:

- el triage parte de alertas de Bandit y mide recomendaciones de descarte;
- la auditoría LLM-first parte de código crudo y mide detección;
- las clases, el denominador y el coste de error son distintos.

La comparación válida será contra el modelo afinado para auditoría y, si se quiere, contra Bandit como detector de referencia, usando el mismo conjunto de 214 fragmentos.

---

## 5. Pruebas y validación

### 5.1 Pruebas unitarias

```powershell
python -m unittest discover -s agente\tests
```

Resultado: **36 pruebas OK**. Incluyen:

- parsing de respuestas `VULNERABLE`, `SAFE`, inválidas y con Markdown;
- creación de `Finding` solo para `VULNERABLE`;
- mapeo OWASP desde el CWE del modelo;
- omisión del re-triage de hallazgos `llm_audit`;
- sincronización de `finding_id` en deduplicación;
- validación de `--scanner llm|all` y de `--no-llm`.

### 5.2 Compilación y consistencia

```powershell
python -m py_compile agente\src\agente_seguridad\llm\code_audit.py `
    training\build_audit_sft.py eval\build_audit_eval_set.py eval\run_audit_eval.py
python scripts\check_consistencia.py
```

Resultado: compilación sin errores y `Consistencia OK`.

### 5.3 Prueba de integración con la CLI

```powershell
python agente\run.py scan agente\examples\sample_repo --scanner all `
    --model qwen2.5-coder:1.5b --audit-max-chunks 3 --max-alerts 3 `
    --out reportes\test_llmfirst_all --quiet
```

Resultado:

- auditoría LLM: 3 fragmentos, 0 hallazgos, 1 respuesta inválida;
- Bandit: 9 alertas;
- OWASP: 6 alertas;
- reporte JSON y SARIF generados correctamente;
- exit code 0.

La prueba demuestra que el pipeline completo funciona. No demuestra calidad de detección: con 3 fragmentos y una respuesta inválida no hay base para evaluar el modelo.

### 5.4 Comportamiento de error

Las pruebas y la CLI cubren:

- `--scanner llm --no-llm` → exit 2 con mensaje de uso;
- `--scanner all --no-llm` → exit 2 con mensaje de uso;
- Ollama caído en un modo que requiere LLM → exit 4;
- Ollama caído en modo SAST → se conserva la política conservadora y no se pierden alertas.

---

## 6. Limitaciones y amenazas a la validez

1. **El modelo evaluado no es el modelo afinado.** `qwen2.5-coder:1.5b` es el modelo base. `qwen2.5-coder-triage` no está instalado en este entorno y, además, fue entrenado para triage, no para auditoría directa.
2. **No se entrenó el adaptador nuevo.** El SFT está listo, pero la corrida QLoRA requiere GPU y dependencias que no están disponibles localmente.
3. **Muestra pequeña.** La línea base usa 40 fragmentos. No es el conjunto completo de 214 ni el holdout.
4. **Etiquetas ruidosas.** El dataset mezcla lenguajes y tiene CWEs discutibles; el filtro `ast.parse` reduce el ruido, pero no lo elimina. Por ejemplo, quedan patrones de CWE-787 o CWE-119 en Python que pueden estar mal etiquetados.
5. **Solo análisis local.** El modelo ve una función o una ventana de 6.000 caracteres; no sigue flujos entre archivos, no resuelve imports y no conoce el despliegue.
6. **CWE débil.** El modelo base acierta el CWE en 2 de 16 verdaderos positivos. No se puede usar como clasificador independiente.
7. **Respuestas inválidas.** Un 12,5 % de la línea base no produjo JSON válido. El parser es deliberadamente estricto: no inventa hallazgos.
8. **Sin evaluación de prompt injection en este modo.** La batería existente se hizo sobre el triage; no se debe extrapolar a la auditoría directa.
9. **Sin análisis de coste/latencia completo.** La corrida de 40 fragmentos no se usó para medir latencia por fragmento ni consumo de VRAM en este modo.

Ninguna de estas limitaciones cambia el modo asesor ni autoriza el descarte automático.

---

## 7. Qué debe cambiar en la memoria final

Las cifras del triage y del holdout **no cambian**. Este avance agrega una sección y ajusta la redacción para no presentar el producto como si solo fuera un triage.

| Sección de la memoria | Cambio sugerido |
|---|---|
| Resumen | Añadir que el producto también incluye auditoría LLM-first y la línea base; aclarar que el modelo afinado de auditoría aún no se entrenó. |
| 1.3 Pregunta e hipótesis | Añadir la pregunta complementaria sobre detección directa, sin sustituir la pregunta principal. |
| 1.4 Objetivos | Añadir el objetivo específico de construir y medir el modo LLM-first. |
| 1.5 Contribuciones | Añadir el pipeline SFT/evaluación y el resultado negativo de la línea base como evidencia de que el modo aún no es confiable. |
| 2.2 LLM para detección y triage | Distinguir detección directa de triage y explicar por qué el CWE del modelo solo es válido como detector en LLM-first. |
| 3.2 Construcción de los ejemplos | Añadir `training/build_audit_sft.py`, sus filtros y las cifras 410/214. |
| 3.3 Ajuste QLoRA | Aclarar que el adaptador de auditoría está pendiente; no atribuirle resultados. |
| 3.5 Protocolo de evaluación | Añadir una subsección 3.5.4 para `eval/audit_eval_set.jsonl` y `eval/run_audit_eval.py`. |
| 3.6 Métricas | Añadir TP/FN/FP/TN, precisión, recall, F1, FPR, FNR, exactitud CWE y respuestas inválidas. |
| 3.7 Pruebas | Actualizar el conteo a 36 pruebas y mencionar las pruebas del modo LLM. |
| 3.9 Marco OWASP | Añadir la excepción: en LLM-first el CWE del modelo es el CWE del detector; nunca se usa la columna `owasp` del dataset. |
| 4. Resultados | Añadir una sección 4.13 «Auditoría LLM-first: línea base» con la tabla de 40 fragmentos y sus límites. |
| 5.5 Trabajo futuro | Incluir entrenamiento del adaptador de auditoría, evaluación de los 214 fragmentos y comparación contra Bandit; el holdout sigue cerrado. |
| Anexo C. Prompts | Añadir el prompt de sistema y el template `<code_snippet>`. |
| Anexo D. Conjuntos | Añadir la construcción y el tamaño de `audit_eval_set.jsonl`. |
| Anexo E. Pruebas | Actualizar el conteo y los casos nuevos. |
| Anexo G. Cobertura OWASP | Añadir la nota de que la auditoría LLM puede emitir categorías fuera de A01–A03/A08, pero no se ha medido cobertura completa. |

Redacción sugerida para el resumen:

> Además del triage, el producto incorpora un modo de auditoría LLM-first en el que el modelo lee fragmentos de código Python y emite por sí mismo el veredicto y el CWE. El pipeline de SFT y evaluación quedó construido, pero el adaptador específico aún no se entrenó. Una línea base de 40 fragmentos con el modelo base obtuvo recall 80,0 %, precisión 55,2 %, FPR 65,0 % y exactitud CWE 12,5 %, lo que confirma que el modo es ejecutable pero todavía no confiable.

Redacción sugerida para la sección 4.13:

> La auditoría LLM-first se evaluó sobre 40 fragmentos de desarrollo (20 vulnerables y 20 seguros) con `qwen2.5-coder:1.5b`. El modelo obtuvo TP=16, FN=4, FP=13 y TN=7; precisión 55,2 %, recall 80,0 %, F1 65,3 %, FPR 65,0 % y FNR 20,0 %. La exactitud CWE fue 12,5 % y cinco respuestas fueron inválidas. El resultado no mide el modelo afinado ni el holdout: mide la línea base de un modelo no especializado y justifica entrenar un adaptador nuevo antes de usar este modo como detector.

---

## 8. Reproducibilidad

### 8.1 Requisitos

- Python 3.9+ para la CLI y los scripts de evaluación.
- `pandas` y `pyarrow` para los parquet y splits.
- `bandit` para el SAST.
- Ollama para la auditoría LLM.
- Para entrenar: `torch`, `transformers`, `peft`, `datasets` y GPU NVIDIA.

### 8.2 Comandos de evaluación

```powershell
# 1. Verificar el servidor y los modelos
ollama list

# 2. Construir el conjunto de auditoría (solo desarrollo)
python eval\build_audit_eval_set.py --per-class 300

# 3. Línea base de 40 fragmentos
python eval\run_audit_eval.py --model qwen2.5-coder:1.5b --limit 40 --timeout 180

# 4. Prueba de integración de la CLI
python agente\run.py scan agente\examples\sample_repo --scanner all `
    --model qwen2.5-coder:1.5b --audit-max-chunks 3 --max-alerts 3 `
    --out reportes\test_llmfirst_all --quiet

# 5. Pruebas y consistencia
python -m unittest discover -s agente\tests
python scripts\check_consistencia.py
```

### 8.3 Comandos de SFT

```powershell
python training\build_audit_sft.py
```

Salidas esperadas:

```text
training/data/train_audit.jsonl
training/data/val_audit.jsonl
training/data/audit_sft_stats.json
```

### 8.4 Comandos de entrenamiento (pendientes de GPU)

```powershell
python training\train_qlora.py --quant 4bit --epochs 1 --decision-weight 3.0 `
    --train training\data\train_audit.jsonl `
    --val training\data\val_audit.jsonl `
    --out training\out\qwen-coder-1.5b-lora-v3
```

Después del entrenamiento:

```powershell
python training\export_gguf.py --adapter training\out\qwen-coder-1.5b-lora-v3
ollama create qwen2.5-coder-triage -f Modelfile
python eval\run_audit_eval.py --model qwen2.5-coder-triage
```

---

## 9. Artefactos

| Archivo | Contenido |
|---|---|
| `agente/src/agente_seguridad/llm/code_audit.py` | Chunking, prompt, parseo y ejecución de la auditoría LLM-first |
| `agente/src/agente_seguridad/cli.py` | `--scanner llm|all`, límites y manejo de errores |
| `agente/src/agente_seguridad/triage.py` | Omisión de re-triage de hallazgos LLM |
| `agente/src/agente_seguridad/dedup.py` | Sincronización de `finding_id` |
| `agente/tests/test_agente.py` | 36 pruebas, incluidas las del modo LLM |
| `training/build_audit_sft.py` | Generador del SFT directo |
| `training/data/train_audit.jsonl` | 410 ejemplos de entrenamiento |
| `training/data/val_audit.jsonl` | 214 ejemplos de validación |
| `training/data/audit_sft_stats.json` | Estadísticas y filtros del SFT |
| `eval/build_audit_eval_set.py` | Constructor del conjunto de auditoría |
| `eval/audit_eval_set.jsonl` | 214 fragmentos de evaluación |
| `eval/run_audit_eval.py` | Runner de métricas de detección directa |
| `eval/resultados_audit_qwen2.5-coder_1.5b.json` | Resultado de la línea base |
| `docs/OWASP.md` | Regla OWASP para LLM-first |
| `README.md` | Documentación de uso y línea base |
| `AGENTS.md` | Contexto y comandos para agentes |

---

## 10. Conclusión y siguiente iteración

El avance deja tres resultados concretos:

1. **El producto ya tiene un modo de detección directa.** No depende de que Bandit genere una alerta y conserva el triage existente como segunda capa.
2. **El pipeline de datos y evaluación está completo.** Hay 410 ejemplos de SFT, 214 de validación y 214 de evaluación, con filtros de fuga y sintaxis.
3. **La línea base es negativa para usar el modo como detector.** El modelo base tiene buen recall pero FPR alto, CWE débil y respuestas inválidas. Eso no invalida el modo; indica que el adaptador debe entrenarse para esta tarea.

La siguiente iteración debe:

- entrenar `qwen-coder-1.5b-lora-v3` con `train_audit.jsonl`;
- evaluar los 214 fragmentos completos, no solo 40;
- comparar el modelo afinado contra el base y contra Bandit;
- mantener el holdout cerrado y no usarlo para ajustar el prompt;
- conservar el modo asesor hasta que exista evidencia suficiente.

No se modificó el PDF ni `Avance 5.docx`. Este Markdown es el insumo para integrar el avance en la memoria y regenerar el PDF en una etapa posterior.

---

## Anexo A. Prompt exacto

**Sistema:**

```text
Eres un analista de seguridad de software. Analizas un fragmento de codigo y decides
si contiene una vulnerabilidad real (VULNERABLE) o si es seguro (SAFE). Responde SOLO
con un objeto JSON con las claves: veredicto, cwe, severidad, explicacion, vector_ataque, correccion.
```

**Usuario:**

```text
Analiza el siguiente fragmento de codigo en {language}.

<code_snippet>
{code}
</code_snippet>
```

**Respuesta vulnerable esperada:**

```json
{
  "veredicto": "VULNERABLE",
  "cwe": "CWE-94",
  "severidad": "Alta",
  "explicacion": "El fragmento evalúa entrada no confiable.",
  "vector_ataque": "Un atacante controla la cadena y ejecuta código arbitrario.",
  "correccion": "Evitar eval y usar una API segura con validación de entrada."
}
```

**Respuesta segura esperada:**

```json
{
  "veredicto": "SAFE",
  "cwe": "Ninguno",
  "severidad": "Info",
  "explicacion": "El fragmento no presenta un patrón vulnerable en este contexto.",
  "vector_ataque": "N/A",
  "correccion": "N/A"
}
```
