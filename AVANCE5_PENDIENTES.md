# Avance 5 — estado y pendientes

Estado: Sprint 7 cerrado. El Sprint 8 se ejecutó el 5 de noviembre de 2026 con
las observaciones del director de programa: comparación explícita con Qwen base,
OWASP como eje, arquitectura arc42/C4 y smoke test con repositorios reales. El 7
de noviembre se añadió la auditoría de falsos negativos a nivel de alerta.
`Avance 5.docx` se regeneró con A/B/C/C0/D, holdout, C0 vs. D, auditoría de
falsos negativos, cobertura OWASP y smoke test (190 párrafos, 23 tablas). El
holdout se mantiene cerrado: no se reentrenó ni se rehizo el split, y ninguna
pieza nueva cambia el modo asesor.
Resultados del holdout en `docs/ANALISIS_HOLDOUT.md`; comparación con el modelo
base en `docs/ANALISIS_C0_VS_D.md`; auditoría en `docs/AUDITORIA_FN.md`;
cobertura en `docs/OWASP.md`; arquitectura en `docs/ARQUITECTURA_ARC42.md`;
smoke test en `docs/SMOKE_REPOS.md`. Lo que resta es la segunda revisión a
ciegas de la auditoría, la rúbrica de explicaciones, el análisis de
casi-duplicados, el reentrenamiento con alertas reales y la integración final de
la memoria.

## 1. Ya resuelto en esta revisión

### Documento

- Estilo visual de Avance 2/3: portada con acentos, H1 `#0F1633`, H2
  `#2864E8`, cuerpo `#1F2A44`, tablas sin bordes con cabecera azul marino,
  cajas de hallazgo `#EEF3FF` y pie de página real (sin pie en portada).
- 9 páginas: se compactaron referencias y espaciados para eliminar la página
  final casi vacía. Las tablas largas repiten cabecera al partirse.
- Nuevas secciones:
  - **1.1 Ajustes derivados de la revisión** (modo asesor, fórmulas, dedup,
    alcance, rúbrica, prompt injection).
  - **1.2 Correcciones conceptuales y bibliográficas** (tabla de afirmaciones
    corregidas).
  - **4.1.1 Alcance real del ajuste** (el ajuste no restringe conocimiento; la
    cuantización no especializa; la pérdida solo en la respuesta no evita
    memorizar).
  - **5.3 Matriz de confusión y fórmulas** (VP/FP/FN/VN, FNR, FOR, FPRR,
    precisión, FPR).
  - **5.4 Rúbrica de explicaciones** (CWE, vector, corrección, claridad;
    kappa de Cohen; BERTScore solo como apoyo).
  - **11 Referencias** corregidas (SecurityEval = MSR4P&S 2022; Tencent
    328/433 ≈ 75,8 %; IRIS no es solo un filtro posterior).
- La tabla comparativa usa FPRR, FNR, FOR y exactitud CWE por separado.

### Código

- `agente/src/agente_seguridad/report.py`: resumen en modo asesor con
  `conservadas` = total y `recomendadas_descarte`; la consola ya no dice
  «descartadas».
- `agente/src/agente_seguridad/dedup.py`: la huella incluye `rule_id` y el
  contexto normalizado; no deduplica solo por CWE.
- `eval/run_eval.py`: configuración **D** (`prompt_d`), métricas `FNR`, `FOR`,
  `FPRR`, `precision`, exactitud CWE sobre alertas reales conservadas y
  decisión `recomendada_descarte`.
- `training/export_gguf.py`: docstring corregido (`Modelfile` +
  `ollama create qwen2.5-coder-triage -f Modelfile`).
- `agente/tests/test_agente.py`: **13 de 13 pruebas OK**, incluida
  `test_safe_is_kept_and_only_recommended` (modo asesor). Requiere
  `bandit` instalado.
- `python -m py_compile` pasa en `run_eval.py`, `report.py`, `dedup.py` y
  `export_gguf.py`.

## 2. Pendientes técnicos (bloquean las cifras)

- [x] **Entrenamiento QLoRA.** Completado en la RTX 4070 Super: 1.439 pasos,
  1 h 50 min 56 s, pérdida de 1,11 a 0,36, 18.464.768 parámetros entrenables
  (1,18 %). Salidas en `training/out/`:
  `qwen-coder-1.5b-lora/` (adaptador, 70,5 MB), `checkpoint-1000/`,
  `checkpoint-1439/` y `train.log`.

  Incidencia resuelta: las evaluaciones intermedias dieron `eval_loss = nan`
  porque la truncación a 2.048 tokens dejaba algunos ejemplos de validación sin
  tokens de respuesta. `train_qlora.py` ahora descarta esos ejemplos
  (`encode_rows`), de modo que una futura corrida produce pérdida de
  validación válida. La calidad del modelo se mide con la corrida D.

- [x] **Fusión + GGUF + Ollama.** Completado: `qwen-coder-1.5b-merged/`,
  `qwen-coder-1.5b-f16.gguf` (2.950 MB) y `qwen-coder-1.5b-q4_k_m.gguf`
  (940 MB). Modelo registrado como `qwen2.5-coder-triage` en Ollama 0.40.13.
  Prueba de control con 3 alertas reales: 3/3 respuestas válidas, 3/3
  conservadas, CWE correcto en 2/3.

- [x] **Corrida de integración con el modelo afinado** sobre
  `agente/examples/sample_repo`: 9 alertas, 9 conservadas, 4 recomendadas para
  descarte, 0 respuestas inválidas y 0 errores del modelo. Tiempo total 43,1 s
  (≈4,8 s por alerta) en la GTX 1650. JSON y SARIF generados en `reportes/`.

- [x] **Corrida D completa** sobre las 141 alertas con
  `qwen2.5-coder-triage`: FPRR 48,0 %, FNR 5,5 % (5 de 91 reales), FOR 17,2 %,
  precisión 76,8 %, exactitud CWE 43,0 %, 0 respuestas inválidas. Las 5 alertas
  reales descartadas son todas B403 (`import pickle`, CWE-502). Resultado en
  `eval/resultados_D.json`.

- [x] **Corrida C completa** sobre las 141 alertas con
  `qwen2.5-coder:1.5b`: FPRR 2,0 % (1 de 50 falsos positivos), FNR 0,0 %,
  FOR 0,0 %, precisión 65,0 %, exactitud CWE 37,4 %, 1 respuesta inválida
  (B102 conservada como `SOSPECHOSA`). C descartó una sola alerta (B404) y
  conservó las 91 reales. Resultado en `eval/resultados_C.json`. Se corrigió
  antes un bug del prompt few-shot: las llaves del JSON de ejemplo se
  interpretaban como campos de `str.format` y la corrida abortaba con
  `KeyError: '"veredicto"'`. El prompt D no cambió.

  ```
  python eval/run_eval.py --config C --model qwen2.5-coder:1.5b
  ```

  B completa no se corre: el piloto de 10 alertas ya mostró que el modelo base
  no acierta el CWE y no es la comparación justa.

- [x] **Punto de decisión del 1 de noviembre.** D mejora el FPRR frente a C
  (48,0 % vs. 2,0 %) a costa de 5 falsos negativos (FNR 5,5 % vs. 0,0 %). Como
  el FNR de D supera la meta de 5 %, **no se habilita el descarte automático**:
  se mantiene el modo asesor y se propone excluir B403 del descarte (FNR 0 %,
  FPRR 38 % en desarrollo).

  **Actualización del 3 de noviembre (holdout):** la propuesta no se confirma
  tal cual. D obtiene FNR 9,2 % (6/65; 4 B403 y 2 B311) y FPRR 30,4 %. Con la
  política B403 queda FNR 3,1 % (IC95 0,8–10,5 %) y FPRR 19,6 %. B403 es
  obligatoria si se usa D, pero no alcanza para afirmar ≤ 5 %; B311 se reporta
  como riesgo nuevo y no se agrega post hoc. Detalle en
  `docs/ANALISIS_HOLDOUT.md`.

- [x] **Resiliencia en vivo.** Las pruebas unitarias cubren cliente nulo, JSON
  malformado, veredicto inválido y SAFE sin justificación. Batería funcional
  `--no-llm` completada: repo vacío, archivo vacío, sintaxis inválida, otro
  lenguaje y repo de 40 archivos/360 alertas, todos con código 0 y reportes
  válidos. Ollama caído simulado con `--ollama-url http://localhost:9`: 9
  alertas, 9 conservadas como `SOSPECHOSA`, 9 errores de modelo, exit 0 y
  reportes válidos. Falta medir el timeout real con un servidor que no responde.

- [x] **Latencia y memoria** del modelo afinado: 43,1 s para 9 alertas (4,8 s
  por alerta) en la integración; banco de 10 alertas con 4,9 s de media y 4,1 s
  de mediana (`eval/bench_latency.py`). C promedia ~4,3 s por alerta. El Q4_K_M
  ocupa 1.115 MB de VRAM con contexto de 4.096 tokens y el proceso
  `llama-server` unos 700 MB de RAM (medido con `/api/ps` y `Get-Process`).

- [x] **Bucle de generación acotado.** Una alerta B102 de 1.818 caracteres hizo
  que el modelo base agotara el timeout de 180 s en C y dejara el runner de
  Ollama consumiendo CPU. Se agregó `num_predict: 512` al cliente del producto
  y al arnés de evaluación; con el límite, la misma alerta responde en 8,2 s.
  La corrida C se repitió con el arnés corregido.

- [x] **Batería de prompt injection** con instrucciones maliciosas dentro del
  código. Con `qwen2.5-coder-triage`, las 4 alertas de `inyeccion.py` se
  conservaron; las dos vulnerabilidades reales (B602 y B301) se clasificaron
  como `VULNERABLE` pese al comentario. Los dos `SAFE` corresponden a las
  advertencias de importación B404 y B403, no a la inyección. 0 respuestas
  inválidas, 23,6 s.

- [ ] **Rúbrica de explicaciones** con dos revisores y kappa; BERTScore solo
  como medida descriptiva (requiere referencias humanas). Las planillas de 25
  alertas por revisor están generadas en `eval/rubrica/evaluador_1.csv` y
  `evaluador_2.csv`, pero **sin calificar**. El holdout mostró un problema
  previo: D produce 11 explicaciones, 8 vectores y 2 correcciones únicas en 111
  alertas. La rúbrica debe reportar también esa diversidad, no solo el kappa.

- [ ] **Partición por proyecto/archivo.** El dataset no tiene identificador de
  proyecto; la partición es aleatoria por función. El holdout se evaluó sin
  reagrupar. La comparación exacta de hashes normalizados contra train y
  validación dio 0 coincidencias, pero falta medir casi-duplicados. Se declara
  como amenaza a la validez; no se rehace el split.

- [x] **Holdout ejecutado una sola vez.** `eval/build_eval_set.py --split test
  --confirm-holdout` generó 111 alertas (65 reales, 46 falsos positivos) a
  partir de 300 funciones Python del test de 17.542 filas. Se evaluaron A, C0 y
  D. Resultados en `eval/resultados_holdout_*.json`, análisis en
  `docs/ANALISIS_HOLDOUT.md` y registro en `docs/PROTOCOLO_HOLDOUT.md`. El set
  no se vuelve a usar para ajustar prompts, hiperparámetros ni reglas.

## 3. Pendientes del documento

- [x] `COMPARATIVA` y `EVIDENCIAS` actualizadas en
  `scripts/build_avance5.py` con A/B/C/C0/D, holdout, latencia, memoria, batería
  funcional, prompt injection y Ollama caído. Documento regenerado con
  `python scripts/build_avance5.py`. Análisis de C en `docs/ANALISIS_C.md` y del
  holdout en `docs/ANALISIS_HOLDOUT.md`.
- [x] Figura de pérdida de entrenamiento agregada con `scripts/plot_loss.py`
  (`reportes/curva_perdida.png`) e insertada en la sección 6. La curva de
  validación queda pendiente de una corrida futura: las evaluaciones
  intermedias dieron NaN por el truncamiento ya corregido.
- [x] **Inconsistencia de B resuelta:** `eval/resultados_B.json` conserva las
  10 alertas del piloto (6 reales, 4 FP, FPRR 75 %). El Avance 5 ahora aclara
  que el piloto se amplió de 5 a 10 alertas respecto del Avance 4, con el
  mismo protocolo y orden. El archivo se regeneró con el esquema nuevo
  (`FNR`, `recomendadas_descarte` y `precision`).
- [ ] Integrar estas secciones en `Documento_Proyecto_Seguridad_Ia.docx`.
- [ ] Borrador completo (requisito del Avance 5): Introducción, Estado del
  Arte, Requisitos, Arquitectura, Entrenamiento, Experimentos, Resultados,
  Conclusiones y Referencias. Hay borradores de introducción, estado del arte,
  metodología, discusión, conclusiones, anexos y arquitectura; faltan requisitos
  y la integración en `Documento_Proyecto_Seguridad_Ia.docx`.

## 4. Criterios de la entrega

- Producto prácticamente terminado.
- Resultados de pruebas funcionales.
- Evaluación del componente inteligente con D medida.
- Borrador completo del documento del proyecto.

## 5. Sprint 7 (3–9 nov): estado

- [x] Evaluación única sobre el split test: 111 alertas, 65 reales, 46 falsos
  positivos. A, C0 y D medidos; resultados crudos y con política B403.
- [x] Política B403 implementada y probada. El holdout la confirma como
  necesaria, pero no suficiente: FNR 3,1 % (IC95 0,8–10,5 %) y FPRR 19,6 %.
- [x] Frontend conectado a reportes reales; `npm run build` pasa.
- [x] Planillas de rúbrica generadas (25 alertas × 2 revisores), sin calificar.
- [ ] Rúbrica aplicada y kappa calculado.
- [ ] Análisis de casi-duplicados train/holdout.
- [ ] Integración final de la memoria y ensayo de demostración.

**Contraste con las metas:** D no cumple FNR ≤ 5 % en el holdout (9,2 % crudo;
3,1 % con B403, pero IC95 hasta 10,5 %). El ahorro real con política es +8,7
puntos sobre C0, no +46. La exactitud CWE de D (32,2 %) es menor que A (35,4 %)
y C0 (33,8 %), aunque el modelo copia el CWE del SAST en 59/59: la diferencia es
de denominador, no de clasificación. La conclusión es mantener el modo asesor,
hacer obligatoria B403 y no agregar B311 después de ver el holdout.

## 6. Sprint 8 (5 nov): estado

- [x] **Comparación explícita con Qwen base.** `eval/analisis_c0_vs_d.py`
  empareja C0 y D por alerta, calcula McNemar y un IC95 por bootstrap agrupado
  por archivo. Desarrollo: FPRR 22,0 → 48,0 y FNR 2,2 → 5,5 (p = 0,0004).
  Holdout: FPRR 10,9 → 30,4 y FNR 0,0 → 9,2 (p = 0,0015). Es un intercambio: D
  gana en reducción de ruido y C0 gana en conservación de alertas reales; se
  publica completo. Datos en `eval/analisis_c0_vs_d.json` y lectura en
  `docs/ANALISIS_C0_VS_D.md`.
- [x] **OWASP como eje.** `eval/cobertura_owasp.py` mide la cobertura por el CWE
  del SAST. Desarrollo: A01 3, A02 1, A03 83, A08 53, sin categoría 1. Holdout:
  A01 1, A02 3, A03 76, A08 30, sin categoría 1. Se documentan 10 discrepancias de 30
  etiquetas del dataset, el LLM Top 10 2025 del agente y ASVS 5.0.0 como
  checklist parcial con exclusiones. Datos en `eval/cobertura_owasp.json` y
  lectura en `docs/OWASP.md`. El mapeo también está en el producto: campo `owasp`
  por hallazgo, `resumen.por_owasp` en JSON, propiedades y tags en SARIF, y
  columna/resumen en consola, con 22/22 pruebas en `agente/tests`.
- [x] **Arquitectura arc42/C4.** `docs/ARQUITECTURA_ARC42.md` cubre las 12
  secciones de arc42 9.1; las vistas C4 de contexto y contenedores se
  renderizan desde `docs/diagramas/*.mmd` con Mermaid CLI 12.2.0.
- [x] **Smoke test con repositorios reales.** `pallets/itsdangerous` 2.2.0,
  `jpadilla/pyjwt` 2.10.1 y `httpie/cli` 3.2.4, fijados por commit y limitados
  al paquete fuente. Base: 3 SAFE de 38; D: 34 SAFE de 38; 0 alertas eliminadas
  y 0 errores. Auditoría manual: 0 descartes incorrectos y 0 dudosos; D
  conservó una alerta real (`requests.get(..., verify=False)`). Resumen en
  `eval/auditoria_smoke_repos.json` y `docs/SMOKE_REPOS.md`. Repetición del 8 de
  noviembre: base 4 SAFE, 2 SOSPECHOSA y 2 respuestas inválidas; D 34 SAFE y 0
  errores; D descarta 34/34 alertas de severidad baja y 0/4 de media o alta
  (`docs/CORRIDA_REPOS_REALES.md`).
- [x] **Banco sintético etiquetado.** 26 alertas nuevas fuera del holdout (14
  reales, 12 falsos positivos, 13 reglas). Base: FPRR 0,0 %, FNR 0,0 %, exactitud
  53,8 %, 2 respuestas inválidas. D: FPRR 58,3 %, FNR 35,7 %, exactitud 61,5 %.
  La decisión de D se reproduce al 100 % con «SAFE si la severidad del SAST es
  baja», señal de atajo y no de lectura del contexto. `eval/banco_sintetico.py`,
  `docs/BANCO_SINTETICO.md` y `docs/ANALISIS_BANCO_SINTETICO.md`.
- [x] **Documento regenerado y validado.** `python scripts/build_avance5.py`
  produce 190 párrafos y 23 tablas. `python scripts/check_consistencia.py`
  valida las tablas del docx, README, `docs/ANALISIS_C0_VS_D.md`,
  `docs/AUDITORIA_FN.md`, `docs/OWASP.md`, `docs/BORRADOR_ANEXOS.md` y
  `docs/SMOKE_REPOS.md` contra los JSON.
- [x] **Auditoría de falsos negativos.** `eval/auditar_fn.py` cruza los 12
  falsos negativos de C0 y D con la adjudicación manual de
  `eval/auditoria_fn.json` y escribe `eval/analisis_fn.json`. 6 de 11 omisiones
  brutas son ruido de etiqueta. FNR ajustado: desarrollo C0 2,2 % vs. D 3,3 %;
  holdout C0 0,0 % vs. D 3,1 %. FPRR ajustado de D: 52,0 % y 39,1 %. McNemar
  sobre alertas reales deja de ser significativo (p = 1,00 y p = 0,50). Con la
  política B403, D queda en FNR 0,0 % y FPRR 38,0 %/23,9 %, pero es post hoc.
  Lectura en `docs/AUDITORIA_FN.md` y sección 11 de `docs/ANALISIS_C0_VS_D.md`.
- [ ] **Segunda revisión a ciegas de la auditoría de falsos negativos.** La
  adjudicación actual conoce el veredicto del modelo. La hoja ciega está en
  `eval/rubrica/auditoria_fn_ciega.csv` (12 casos mezclados, sin veredicto ni
  etiqueta) y se regenera con `python eval/preparar_auditoria_ciega.py`. Falta
  que otro revisor la complete; el acuerdo se calcula con
  `python eval/acuerdo_auditoria.py` (kappa de Cohen y discrepancias).
- [ ] Rúbrica aplicada y kappa calculado (requiere dos revisores).
- [ ] Análisis de casi-duplicados train/holdout.
- [ ] Integración final de la memoria y ensayo de demostración.

## 7. Plan de mejora del modelo (siguiente iteración)

La auditoría confirma que el problema no es de prompt ni de umbral: es de
entrenamiento. El modelo nunca vio B403 en el ajuste, la alerta de entrenamiento
es sintética y va al final del prompt, y la mitad de los ejemplos no tienen
alerta. Orden propuesto:

1. [x] Auditar los falsos negativos y separar omisión real de ruido de etiqueta.
2. [x] Derivar la política por regla **solo de desarrollo** y pre-registrarla.
   `docs/POLITICA_REGLAS.md` fija el criterio («ninguna regla con un descarte
   real en desarrollo puede producir SAFE»), que selecciona B403 y excluye B311.
3. [x] Construir el SFT con alertas reales de Bandit en formato de producción.
   `training/build_bandit_sft.py` ejecuta Bandit sobre los fragmentos Python de
   train_80 y val_total, usa el prompt de `prompt_d`, no incluye ejemplos sin
   alerta, quita `finding_id`, aplica el criterio de patrón de la auditoría y
   balancea las clases. Resultado: 554 ejemplos de entrenamiento (217
   VULNERABLE / 337 SAFE) y 286 de validación, con verificación por hash de que
   no hay fuga con el holdout. **Falta ejecutar el entrenamiento en la GPU.**
4. [x] Pérdida centrada en la decisión. `training/train_qlora.py` acepta
   `--decision-weight` (1.0 = pérdida estándar; 3.0 = los tokens de `veredicto`
   y `cwe` pesan el triple). `training/verificar_ponderacion.py` lo prueba en
   CPU con un modelo diminuto: 42 tokens ponderados, pérdida finita y dos pasos
   de entrenamiento correctos.
5. [ ] Entrenar, fusionar, exportar y evaluar **solo en desarrollo**. Después,
   construir un conjunto de oro **a nivel de alerta** y validar en un conjunto
   nuevo; el holdout actual queda cerrado.
