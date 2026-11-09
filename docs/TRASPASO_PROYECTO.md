# Traspaso del proyecto — estado al 8 de noviembre de 2026

Documento de traspaso para continuar el trabajo en un chat nuevo. Resume qué se
hizo, qué está en curso, qué falta y qué recomiendo hacer primero. Las cifras
están sacadas de los JSON del repositorio, no de memoria; si algo cambia, deben
regenerarse con los comandos de la sección 10.

Rama de trabajo: `feature/sprint-7`. Último commit: `1200f57`.

---

## 1. Qué es el proyecto

Herramienta **local** que combina Bandit (SAST) con un modelo de lenguaje
afinado (Qwen2.5-Coder-1.5B + QLoRA → fusión → GGUF Q4_K_M → Ollama) para hacer
*triage* de alertas: decidir si una alerta es una vulnerabilidad real
(`VULNERABLE`) o un falso positivo (`SAFE`).

- **Modo asesor**: un `SAFE` solo *recomienda* descarte; la alerta nunca se
  elimina del reporte. Ante duda, respuesta inválida u Ollama caído, se conserva
  como `SOSPECHOSA`.
- **Todo local**: no se envía código a ninguna API externa.
- **Objetivo de la memoria**: medir el aporte del ajuste fino frente a Qwen base
  con un control correcto (C0 vs. D), integrar OWASP como eje, documentar la
  arquitectura con arc42/C4 y probar con repositorios reales.

## 2. Reglas que no se deben romper

1. **El holdout está cerrado.** `eval/holdout_set.jsonl` se ejecutó una sola vez
   en el Sprint 7. No se usa para ajustar prompts, hiperparámetros, reglas ni
   umbrales. Cualquier cambio se valida en desarrollo y, después, en un conjunto
   nuevo.
2. **No reentrenar ni rehacer el split** sin un conjunto de evaluación nuevo.
3. **No adoptar reglas post hoc**: B311 no se añade a la política porque se vio
   en el holdout. B403 sí está justificada y ya está pre-registrada
   (`docs/POLITICA_REGLAS.md`).
4. **El resultado pre-registrado es el de etiqueta de fragmento.** La auditoría a
   nivel de alerta es un análisis de sensibilidad, no un reetiquetado.
5. **Modo asesor siempre**: ninguna mejora habilita descarte automático.
6. **Nada de API externa** en el flujo del producto.

## 3. Entorno

| Elemento | Estado |
|---|---|
| Python | 3.14 en esta máquina (el proyecto se entrenó con 3.11) |
| PyTorch | `2.15.0+cpu`, `torch.cuda.is_available() == False` |
| GPU | GTX 1650 4 GB; **el entrenamiento no se puede ejecutar aquí** |
| Ollama | activo, con `qwen2.5-coder:1.5b` y `qwen2.5-coder-triage` |
| Bandit | 1.9.4 vía `python -m bandit` (no hay CLI en PATH) |
| transformers / datasets / peft | 5.22.0 / 5.1.0 / 0.21.2 |
| Tokenizer local | `training/out/qwen-coder-1.5b-merged` |

El entrenamiento registrado se hizo en una RTX 4070 Super (~1 h 50 min por
época). El pipeline nuevo tiene 554 ejemplos, así que debería ser mucho más
rápido, pero sigue necesitando GPU.

## 4. Dónde estamos

### Commits relevantes

| Commit | Contenido |
|---|---|
| `aa4cd0a` | Sprint 8: OWASP, arc42/C4, C0 vs. D y smoke test |
| `ccd19de` | Auditoría de falsos negativos + corrección de la lectura C0/D + memoria |
| `e649a7f` | Hoja ciega y kappa para la segunda revisión |
| `1200f57` | SFT con alertas reales de Bandit y pérdida centrada en la decisión |

### Semáforo

| Bloque | Estado |
|---|---|
| Producto (CLI, reportes, SARIF, frontend) | Terminado y probado |
| Evaluación A/B/C/C0/D en desarrollo | Cerrada |
| Holdout (A, C0, D) | Cerrado, ejecutado una sola vez |
| Comparación C0 vs. D | Cerrada y documentada |
| Auditoría de falsos negativos | Hecha; falta segunda revisión a ciegas |
| OWASP / arc42 / C4 / smoke test | Cerrados |
| Memoria `Avance 5.docx` | Regenerada y validada (190 párrafos, 23 tablas) |
| Pipeline de reentrenamiento v2 | Construido y probado en CPU; **sin entrenar** |
| Rúbrica de explicaciones | Planillas generadas, sin calificar |
| Casi-duplicados train/holdout | Solo verificado el solapamiento exacto (0) |

## 5. Resultados cerrados

### 5.1 Conjuntos

| Conjunto | Alertas | Reales | Falsos positivos | Origen |
|---|---:|---:|---:|---|
| Desarrollo | 141 | 91 | 50 | `val_total`, 298 funciones Python |
| Holdout | 111 | 65 | 46 | `test`, 300 funciones Python; 71 archivos, 98 funciones, 40 filas duplicadas |

La etiqueta es **a nivel de fragmento** (`is_vulnerable`), no de línea.

### 5.2 Desarrollo (141 alertas)

| Config | FPRR | FNR | FOR | Precisión | CWE |
|---|---:|---:|---:|---:|---:|
| A. Solo SAST | 0,0 % | 0,0 % | 0,0 % | 64,5 % | 45,1 % |
| B. Cero-shot (piloto 10) | 75,0 % | 0,0 % | 0,0 % | 85,7 % | 0,0 % |
| C. Contexto + few-shot | 2,0 % | 0,0 % | 0,0 % | 65,0 % | 37,4 % |
| C0. Base sin few-shot | 22,0 % | 2,2 % | 15,4 % | 69,5 % | 44,9 % |
| D. Afinado | 48,0 % | 5,5 % | 17,2 % | 76,8 % | 43,0 % |

### 5.3 Holdout (111 alertas)

| Config | FPRR | FNR | FOR | Precisión | CWE |
|---|---:|---:|---:|---:|---:|
| A. Solo SAST | 0,0 % | 0,0 % | 0,0 % | 58,6 % | 35,4 % |
| C0. Base sin few-shot | 10,9 % | 0,0 % | 0,0 % | 61,3 % | 33,8 % |
| D. Afinado (crudo) | 30,4 % | 9,2 % | 30,0 % | 64,8 % | 32,2 % |
| D + política B403 | 19,6 % | 3,1 % | 18,2 % | 63,0 % | 30,2 % |

Lectura honesta: D **no** alcanza FNR ≤ 5 % con la etiqueta de fragmento. La
política B403 lo baja a 3,1 %, pero su IC95 (0,8–10,5 %) sigue por encima de la
meta y es post hoc. Con 65 alertas reales, incluso 0 fallos deja el límite
superior del IC95 en 5,6 %: el diseño no alcanza para demostrar la meta.

### 5.4 C0 vs. D (la comparación que aísla el ajuste)

Mismo prompt (`prompt_d`), mismo SYSTEM, temperatura 0, mismo `num_predict`; la
única diferencia es el modelo.

| Conjunto | Δ FPRR (D−C0) | IC95 | Δ FNR (D−C0) | IC95 | McNemar |
|---|---:|---|---:|---|---:|
| Desarrollo | +26,0 pts | 9,4 a 43,6 | +3,3 pts | −1,2 a 8,2 | p = 0,0004 |
| Holdout | +19,6 pts | 0,0 a 38,5 | +9,2 pts | 1,8 a 17,5 | p = 0,0015 |

Es un **intercambio**: D descarta más ruido (mejor FPRR) y C0 omite menos
alertas reales (mejor FNR). Ninguno domina ambas métricas. El aporte del ajuste
es ahorro de revisión, no superioridad.

### 5.5 Auditoría de falsos negativos (análisis de sensibilidad)

Se auditaron los 12 FN de C0 y D a **nivel de alerta**. **6 de las 11 omisiones
de D son ruido de etiqueta** (B403 solo `pickle.dump`, B311 de `randint` en una
división).

| Conjunto | Modelo | FN brutos | FN reales | Ruido | FNR bruto | FNR ajustado | FPRR ajustado | Precisión descarte |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Desarrollo | C0 | 2 | 2 | 0 | 2,2 % | 2,2 % | 22,0 % | 84,6 % |
| Desarrollo | D | 5 | 3 | 2 | 5,5 % | 3,3 % | 52,0 % | 89,7 % |
| Holdout | C0 | 0 | 0 | 0 | 0,0 % | 0,0 % | 10,9 % | 100,0 % |
| Holdout | D | 6 | 2 | 4 | 9,2 % | 3,1 % | 39,1 % | 90,0 % |

Con alertas reales, McNemar deja de ser significativo (p = 1,00 en desarrollo y
p = 0,50 en holdout). La ventaja de C0 en FNR queda en 1 y 2 alertas. Sigue
siendo un análisis **manual y no a ciegas**; el criterio es de patrón
(presencia/ausencia del sink), no de flujo de datos.

Con la política B403 aplicada, D queda en FNR 0,0 % y FPRR 38,0 % (desarrollo)
y 23,9 % (holdout) **a nivel de alerta**; en etiqueta de fragmento, 3,1 % y
19,6 %. Es post hoc.

### 5.6 OWASP

Cobertura calculada con el CWE del SAST (`cwe_sast`), no con la columna `owasp`
del dataset. Se usan TOP 10 2021, LLM TOP 10 2025 y ASVS 5.0.0 como checklist
parcial con exclusiones.

| Conjunto | A01 | A02 | A03 | A08 | Sin categoría |
|---|---:|---:|---:|---:|---:|
| Desarrollo (141) | 3 | 1 | 83 | 53 | 1 |
| Holdout (111) | 1 | 3 | 76 | 30 | 1 |

Se documentan 10 discrepancias de 30 etiquetas del dataset. Detalle en
`docs/OWASP.md`. El mapeo también está en el producto
(`agente/src/agente_seguridad/owasp.py`): cada hallazgo lleva `owasp`, el reporte
incluye `resumen.por_owasp`, SARIF añade propiedades y tags, y la consola muestra
la categoría por alerta.

### 5.7 Smoke test con repositorios reales

`pallets/itsdangerous` 2.2.0, `jpadilla/pyjwt` 2.10.1 y `httpie/cli` 3.2.4,
fijados por commit y limitados al paquete fuente.

- 38 alertas: base recomienda descartar 3; D recomienda descartar 34.
- 0 alertas eliminadas, 0 respuestas inválidas, 0 errores.
- Auditoría manual: 0 descartes incorrectos y 0 dudosos.
- D conservó una alerta real (`requests.get(..., verify=False)`).

### 5.8 Rendimiento y robustez

- Integración: 43,1 s para 9 alertas (≈4,8 s/alerta) en GTX 1650.
- Banco de 10 alertas: 4,9 s de media, 4,1 s de mediana.
- Q4_K_M: 1.115 MB de VRAM con contexto 4.096; `llama-server` ≈700 MB de RAM.
- `num_predict: 512` evita bucles patológicos (una alerta pasó de 180 s a 8,2 s).
- Probados: cliente nulo, JSON malformado, veredicto inválido, SAFE sin
  justificación, Ollama caído, repo vacío, archivo vacío, sintaxis inválida,
  otro lenguaje, repo de 40 archivos/360 alertas y prompt injection.
- `agente/tests`: 22/22 pruebas OK (requiere Bandit instalado).

## 6. Lo que está hecho pero **no ejecutado**

### Pipeline de SFT v2 con alertas reales

`training/build_bandit_sft.py` ejecuta Bandit de verdad sobre los fragmentos
Python de `train_80` y `val_total` y genera el SFT en el formato de producción:

- Prompt `prompt_d` (alerta primero, código después), idéntico al del arnés.
- **Todas** las filas tienen alerta; no hay ejemplos sin alerta.
- Target sin `finding_id`; el CWE usa el del dataset si es compatible con el
  del SAST y, si no, el del SAST.
- Explicaciones variadas (plantillas con regla/CWE/mensaje).
- Criterio de patrón de `docs/AUDITORIA_FN.md`: B403 sin `pickle.load/loads`,
  B404 sin `shell=True` y B311 sin contexto de seguridad se etiquetan `SAFE`.
- Verificación por hash: 0 fugas con el holdout.

Resultado (`training/data/bandit_sft_stats.json`):

| Split | Filas Python | Alertas reales | Ejemplos | VULN | SAFE | Reclasificadas a SAFE | Explicaciones únicas |
|---|---:|---:|---:|---:|---:|---:|---:|
| Train | 1.464 | 554 | 554 | 217 | 337 | 12 | 111 |
| Val | 649 | 286 | 286 | 135 | 151 | 3 | 93 |

Comparación con el SFT anterior: 11.510 ejemplos con solo 164 explicaciones
únicas y 50 % sin alerta. El nuevo es más pequeño pero consistente con el
formato de producción.

### Pérdida centrada en la decisión

`training/train_qlora.py` acepta `--decision-weight`. Con 3.0, los tokens de
`veredicto` y `cwe` pesan el triple; con 1.0 se comporta como la pérdida
estándar. `training/verificar_ponderacion.py` lo prueba en CPU con un Qwen2
diminuto: 42 tokens ponderados, pérdida finita y 2 pasos correctos. También se
corrigió `remove_unused_columns=False`, necesario para que el Trainer no
descarte la columna de pesos.

### Política pre-registrada

`docs/POLITICA_REGLAS.md` fija el criterio derivado **solo de desarrollo**:
«ninguna regla donde el modelo haya descartado una alerta real puede producir
`SAFE`». En desarrollo eso selecciona B403 y excluye B311. Coincide con
`DEFAULT_NEVER_DISCARD = {"B403"}` de `triage.py`, pero ahora con justificación
pre-registrada.

## 7. Lo que falta, priorizado

### P0 — Entrenar y evaluar el modelo v2 (bloquea el resto)

En la máquina con GPU:

```powershell
python training\train_qlora.py --quant 4bit --epochs 1 --decision-weight 3.0 `
    --train training\data\train_sft_real.jsonl `
    --val training\data\val_sft_real.jsonl `
    --out training\out\qwen-coder-1.5b-lora-v2

python training\export_gguf.py `
    --adapter training\out\qwen-coder-1.5b-lora-v2 `
    --out training\out\qwen-coder-1.5b-merged-v2 `
    --f16-out training\out\gguf\qwen-coder-1.5b-v2-f16.gguf `
    --gguf-out training\out\gguf\qwen-coder-1.5b-v2-q4_k_m.gguf
```

Después, crear el modelo en Ollama con un nombre distinto
(`qwen2.5-coder-triage-v2`) para no pisar el modelo de la corrida registrada, y
evaluar **solo en desarrollo**:

```powershell
python eval\run_eval.py --config D --model qwen2.5-coder-triage-v2 `
    --out eval\resultados_D_v2.json
python eval\run_eval.py --config D --model qwen2.5-coder-triage-v2 `
    --never-discard B403 --out eval\resultados_D_v2_politica.json
```

Criterio de éxito: FNR ajustado ≤ 5 % en desarrollo sin perder el ahorro de
revisión (FPRR comparable o mejor que D). Si no se cumple, no se toca el
holdout: se itera en desarrollo.

### P1 — Cerrar la evidencia pendiente

1. **Segunda revisión a ciegas de los 12 casos de la auditoría.** La hoja está
   en `eval/rubrica/auditoria_fn_ciega.csv`; otra persona la completa sin ver el
   veredicto del modelo y se ejecuta `python eval/acuerdo_auditoria.py` para
   obtener kappa. Hoy la auditoría es de un solo revisor.
2. **Rúbrica de explicaciones.** `eval/rubrica/evaluador_1.csv` y
   `evaluador_2.csv` están generadas (25 alertas cada una) pero sin calificar.
   Dos revisores independientes; reportar kappa y diversidad, no solo calidad.
3. **Casi-duplicados train/holdout.** Solo se comprobó hash normalizado exacto
   (0 coincidencias). Falta una medida de similitud (p. ej. MinHash o
   embeddings) y declararlo como amenaza a la validez.

### P2 — Memoria y entrega

1. Integrar las secciones en `Documento_Proyecto_Seguridad_Ia.docx`.
2. Completar el borrador: faltan requisitos; hay borradores de introducción,
   estado del arte, metodología, discusión, conclusiones, anexos y arquitectura.
3. Ensayo de demostración y verificación final de cifras
   (`python scripts/check_consistencia.py`).

### P3 — Mejoras futuras (no bloquean la entrega)

- Conjunto de oro **a nivel de alerta** para dejar de medir con etiqueta de
  fragmento.
- Evaluación en un conjunto nuevo (nunca el holdout actual).
- Ampliar el corpus Python (hoy el 94,1 % del dataset es C) para que el SFT v2
  no dependa de 1.464 fragmentos.
- Presupuesto de contexto y latencia en una GPU de 4 GB.

## 8. Recomendaciones

1. **No tocar el holdout.** Cualquier intento de «mejorar» mirando esas 111
   alertas destruye la validez de la única medición independiente que hay.
2. **Entrenar v2 cueste lo que cueste antes de escribir más texto.** La memoria
   ya cuenta la historia correcta; lo que falta es evidencia de que el
   diagnóstico (formato + alertas reales + pérdida centrada) funciona.
3. **Comparar v2 contra D y contra C0 en desarrollo**, no contra el mejor número
   histórico aislado. La métrica que manda es FNR ajustado, con FPRR como
   contrapeso; no mezclar etiqueta de fragmento y de alerta en la misma tabla
   sin decirlo.
4. **Mantener la política B403** y no ampliarla a B311. Si v2 la necesita, que
   salga de desarrollo y se pre-registre.
5. **No prometer FNR ≤ 5 % con el holdout actual.** Con 65 reales, el IC95 no
   permite demostrarlo ni con 0 fallos. La afirmación correcta es «no se
   observaron omisiones reales en el holdout tras la auditoría, con IC95 ancho».
6. **Cuidar la rúbrica de explicaciones**: D genera muy pocas explicaciones
   únicas. Es una limitación real del producto y el tribunal puede preguntarla.
7. **La segunda revisión a ciegas es barata y sube mucho la calidad de la
   evidencia.** Hacerla antes de la entrega si hay otra persona disponible.
8. **Evitar el reentrenamiento con el conjunto de validación.** El SFT v2 usa
   `train_80`; `val_total` solo para validación. No mezclar.

## 9. Mapa de archivos

### Producto

| Ruta | Función |
|---|---|
| `agente/src/agente_seguridad/cli.py` | CLI: SAST → triage → reporte |
| `agente/src/agente_seguridad/triage.py` | Prompt de producción, SYSTEM, política B403 |
| `agente/src/agente_seguridad/sast/bandit_runner.py` | Ejecuta Bandit y normaliza alertas |
| `agente/src/agente_seguridad/context.py` | Extrae la función afectada |
| `agente/src/agente_seguridad/dedup.py` | Deduplicación por archivo/línea/regla/contexto |
| `agente/src/agente_seguridad/report.py` | Reporte en modo asesor (JSON/consola) |
| `agente/src/agente_seguridad/sast/sarif.py` | Exportación SARIF |
| `agente/src/agente_seguridad/llm/ollama_client.py` | Cliente Ollama con timeouts |
| `agente/tests/test_agente.py` | 13 pruebas, incluida la de modo asesor |
| `frontend/` | Visor de reportes (build con npm) |

### Evaluación

| Ruta | Función |
|---|---|
| `eval/build_eval_set.py` | Construye dev/holdout desde parquet + Bandit |
| `eval/run_eval.py` | Arnés de evaluación A/B/C/C0/D |
| `eval/analisis_c0_vs_d.py` | McNemar + bootstrap agrupado por archivo |
| `eval/analisis_holdout.py` | Análisis del holdout y política |
| `eval/auditar_fn.py` | Auditoría de FN a nivel de alerta |
| `eval/preparar_auditoria_ciega.py` | Hoja ciega para el segundo revisor |
| `eval/acuerdo_auditoria.py` | Kappa de Cohen entre revisores |
| `eval/cobertura_owasp.py` | Cobertura OWASP por CWE del SAST |
| `eval/run_smoke.py` | Smoke test con repos reales |
| `eval/rubrica_explicaciones.py` | Genera planillas de rúbrica |
| `eval/bench_latency.py` | Latencia del modelo |

### Entrenamiento

| Ruta | Función |
|---|---|
| `training/build_bandit_sft.py` | **Nuevo**: SFT con alertas reales de Bandit |
| `training/train_qlora.py` | QLoRA + pérdida ponderada (`--decision-weight`) |
| `training/prepare_sft.py` | Pipeline anterior con alertas sintéticas |
| `training/export_gguf.py` | Fusión → GGUF → Q4_K_M |
| `training/verificar_ponderacion.py` | Prueba de humo de la pérdida en CPU |
| `training/data/train_sft_real.jsonl` | 554 ejemplos v2 |
| `training/data/val_sft_real.jsonl` | 286 ejemplos v2 |
| `training/data/bandit_sft_stats.json` | Estadísticas del SFT v2 |

### Documentación

| Ruta | Función |
|---|---|
| `Avance 5.docx` | Memoria del avance (190 párrafos, 23 tablas) |
| `AVANCE5_PENDIENTES.md` | Estado y pendientes |
| `README.md` | Visión general, resultados, comandos |
| `docs/ANALISIS_HOLDOUT.md` | Lectura del holdout |
| `docs/PROTOCOLO_HOLDOUT.md` | Registro del uso único |
| `docs/ANALISIS_C0_VS_D.md` | Comparación con el base + sensibilidad |
| `docs/AUDITORIA_FN.md` | Auditoría de falsos negativos |
| `docs/POLITICA_REGLAS.md` | Pre-registro de `NEVER_DISCARD` |
| `docs/OWASP.md` | Cobertura y mapeo |
| `docs/ARQUITECTURA_ARC42.md` | arc42 9.1 + C4 |
| `docs/SMOKE_REPOS.md` | Repos reales y auditoría manual |
| `docs/BORRADOR_*.md` | Borradores de la memoria |
| `docs/PLAN_DOCUMENTO_FINAL.md` | Plan de integración |

## 10. Verificación y reproducción

```powershell
# Consistencia docx/README/Markdown contra los JSON (debe dar "Consistencia OK")
python scripts\check_consistencia.py

# Regenerar la memoria
python scripts\build_avance5.py

# Análisis
python eval\analisis_c0_vs_d.py
python eval\analisis_holdout.py
python eval\auditar_fn.py
python eval\cobertura_owasp.py
python eval\preparar_auditoria_ciega.py

# SFT v2 (Bandit real; tarda unos minutos)
python training\build_bandit_sft.py

# Prueba de la pérdida ponderada en CPU
python training\verificar_ponderacion.py
```

`check_consistencia.py` valida las tablas del docx, README, `ANALISIS_C0_VS_D`,
`AUDITORIA_FN`, `OWASP`, `BORRADOR_ANEXOS` y `SMOKE_REPOS` contra los JSON, y
falla si reaparecen cifras obsoletas.

## 11. Decisiones tomadas y porqué

**¿Por qué C0 es el control y no C?**
C añade few-shot; C0 y D comparten prompt, SYSTEM, temperatura y `num_predict`.
La única diferencia entre C0 y D es el modelo, así que el par C0/D aísla el
efecto del ajuste.

**¿Por qué se dice que el ajuste «no es una mejora automática»?**
D gana FPRR y C0 gana FNR. Ninguno domina. Tras la auditoría, la ventaja de C0
en FNR queda en 1 y 2 alertas y pierde significación, pero D tampoco demuestra
mejor detección.

**¿Por qué se auditó a nivel de alerta?**
La etiqueta de fragmento convierte en «real» cualquier alerta sobre una función
vulnerable, aunque la línea señalada sea otra. La auditoría mide cuánto pesa ese
efecto; no reetiqueta el holdout.

**¿Por qué B403 sí y B311 no?**
B403 es la única regla con omisiones reales en desarrollo y ya estaba
implementada. B311 apareció solo en el holdout y la auditoría la clasificó como
ruido; añadirla sería ajustar con el holdout.

**¿Por qué no se busca FNR ≤ 5 % en el holdout?**
Con 65 alertas reales, el IC95 de 0 fallos llega a 5,6 %. El diseño no permite
demostrar la meta; la conclusión correcta es mantener el modo asesor y reportar
el intervalo.

**¿Por qué el SFT v2 usa solo Python?**
Bandit solo analiza Python. El SFT anterior mezclaba 94 % de C con alertas
sintéticas; eso enseñaba un formato que no era el de producción. El nuevo usa
alertas reales, aunque el conjunto sea más pequeño.

## 12. Riesgos y limitaciones

- **Muestra pequeña**: 141 alertas en desarrollo y 111 en holdout; 12 casos en la
  auditoría. No permite afirmar equivalencia, solo descartar diferencias
  grandes.
- **Etiqueta de fragmento**: no hay línea ni alcanzabilidad; el SAST se ve
  favorecido.
- **Auditoría no ciega**: un solo revisor que conocía el veredicto del modelo.
- **Criterio de patrón, no de flujo**: si se exigiera origen no confiable, los
  casos de pickle con `load` también serían discutibles.
- **Partición aleatoria por función**: sin identificador de proyecto; solo se
  verificó solapamiento exacto, no casi-duplicados.
- **Explicaciones pobres**: D produce muy pocas respuestas únicas; sirve como
  clasificador de triage, no como generador de explicaciones.
- **CWE**: la exactitud de D es menor que la de A y C0 por el denominador; el
  modelo copia el CWE del SAST en 59/59.
- **Entorno**: esta máquina no puede entrenar; el pipeline v2 está probado en
  CPU con un modelo diminuto, no con el modelo real.

## 13. Glosario

- **FPRR**: falsos positivos descartados / total de falsos positivos. Más alto
  es mejor.
- **FNR**: alertas reales descartadas / total de reales. Más bajo es mejor.
- **FOR**: falsos positivos entre los descartes. Más bajo es mejor.
- **Precisión del descarte**: descartes correctos / descartes recomendados.
- **FNR ajustado**: FNR tras adjudicar a nivel de alerta (auditoría).
- **C0**: Qwen2.5-Coder-1.5B sin entrenar, con el prompt de D.
- **D**: modelo afinado (LoRA + fusión + Q4_K_M) registrado como
  `qwen2.5-coder-triage`.
- **SAFE / SOSPECHOSA**: recomendación de descarte / alerta conservada por duda.
  En modo asesor, nunca se elimina.

## 14. Bitácora de commits

```
1200f57 training: SFT con alertas reales de Bandit y perdida centrada en la decision
e649a7f eval: preparar revision ciega de la auditoria de falsos negativos
ccd19de docs: auditar falsos negativos y corregir lectura C0 vs D
aa4cd0a docs: cerrar Sprint 8 con OWASP, arc42/C4, C0 vs D y smoke test
3111a4e docs: cerrar Sprint 7 con analisis del holdout y memoria coherente
90c2c30 feat: add dataset splits with LFS tracking
34837f5 Sprint 7: Evaluacion holdout, politica de proteccion B403, frontend con reportes reales y rubrica inter-evaluador
```

## 15. Prompt sugerido para el chat nuevo

> Trabajo en un TFG de triage local de alertas de Bandit con Qwen2.5-Coder-1.5B
> + LoRA, en `C:\Users\flopx\Documents\proyecto ing`. Lee
> `docs/TRASPASO_PROYECTO.md` y `AVANCE5_PENDIENTES.md`. El holdout está cerrado:
> no se reutiliza. La prioridad es ejecutar el entrenamiento v2 en la GPU,
> evaluarlo solo en desarrollo y cerrar la segunda revisión a ciegas de la
> auditoría de falsos negativos. Responde en español y no cambies el modo asesor.
