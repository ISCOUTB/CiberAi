# Avance 5 — estado y pendientes

Estado: Sprint 6 cerrado. `Avance 5.docx` regenerado con
`scripts/build_avance5.py` (131 párrafos, 14 tablas, ~5.850 palabras) con las
corridas A/B/C/D, la batería funcional, la prueba de prompt injection, la
simulación de Ollama caído y la memoria del modelo. Lo que resta para el
Sprint 7 es la evaluación única del holdout, la rúbrica de explicaciones y la
partición por proyecto.

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
- `agente/tests/test_agente.py`: **12 de 12 pruebas OK**, incluida
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
  FPRR 38 %). La decisión se valida con el holdout en el Sprint 7.

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
  como medida descriptiva (requiere referencias humanas).

- [ ] **Partición por proyecto/archivo** antes del test final. El dataset no
  tiene identificador de proyecto; la partición actual es aleatoria por
  función y no garantiza ausencia de filtraciones entre repositorios.

- [x] **Generador del holdout preparado, sin ejecutar.** `eval/build_eval_set.py`
  ahora acepta `--split validation|test`; el split test exige
  `--confirm-holdout` y escribe `eval/holdout_set.jsonl` en un directorio
  temporal distinto, sin pisar el conjunto de desarrollo. El test sigue
  intacto.

## 3. Pendientes del documento

- [x] `COMPARATIVA` y `EVIDENCIAS` actualizadas en
  `scripts/build_avance5.py` con A/B/C/D, latencia, memoria, batería funcional,
  prompt injection y Ollama caído. Documento regenerado con
  `python scripts/build_avance5.py`. Análisis de C en `docs/ANALISIS_C.md`.
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
  Conclusiones y Referencias. Avance parcial: `docs/BORRADOR_ESTADO_ARTE.md`
  (sección 2) y `docs/BORRADOR_DISCUSION.md` (sección 7); el resto se reutiliza
  del Avance 5 según `docs/PLAN_DOCUMENTO_FINAL.md`.

## 4. Criterios de la entrega

- Producto prácticamente terminado.
- Resultados de pruebas funcionales.
- Evaluación del componente inteligente con D medida.
- Borrador completo del documento del proyecto.

## 5. Después del Avance 5 (Sprint 7, 3–9 nov)

- Evaluación única sobre el test intacto (17.542 muestras), sin reutilizarlo.
- Auditoría manual cruzada de explicaciones generadas (rúbrica + kappa).
- Partición agrupada por proyecto/archivo antes de abrir el holdout.
- Contraste con las metas: FNR ≤ 5 %, FPRR ≥ +15 puntos sobre C, exactitud
  CWE ≥ C. D ya cumple la mejora de FPRR (+46 puntos) pero no la meta de FNR
  (5,5 %); el holdout debe confirmar si el exceso se mantiene.
- Validar la política de exclusión de B403 y medir el timeout real de Ollama.
- Preparar insumos del Avance 6: congelamiento de código y borrador integral.
