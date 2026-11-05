# Protocolo y registro de la evaluación holdout

> **Naturaleza del documento.** Se redactó después de ejecutar la corrida del
> 3 de noviembre de 2026. No es un preregistro y no puede demostrar por sí solo
> que el holdout se abrió una sola vez. Su función es dejar fijadas las reglas,
> los archivos y los comandos para la defensa del trabajo y para una réplica
> futura. El análisis de resultados está en `docs/ANALISIS_HOLDOUT.md`.

## 1. Decisión evaluada

La pregunta del Sprint 7 es si el modelo afinado D generaliza el intercambio
observado en desarrollo: reducir el FPRR sin superar un FNR del 5 %. La
comparación que aísla el ajuste fino es **D contra C0**, porque comparten
formato de alerta, conjunto y temperatura. C usa few-shot y no comparte prompt
con D; por eso no se usa como control principal.

## 2. Qué se congeló antes de mirar el holdout

| Elemento | Decisión |
|---|---|
| Split | `test` del dataset, 17.542 filas; 300 funciones Python |
| Conjunto de alertas | 111 alertas de Bandit (65 reales, 46 falsos positivos) |
| Reentrenamiento | Prohibido durante la evaluación |
| Rehacer el split | Prohibido; el dataset no tiene identificador de repositorio |
| Modelo D | `qwen2.5-coder-triage` (Q4_K_M) ya fusionado y registrado en Ollama |
| Modelo C0 | `qwen2.5-coder:1.5b`, mismo formato de alerta que D, sin few-shot |
| Prompt | El mismo de la corrida de desarrollo; sin cambios por alerta |
| Temperatura | 0 |
| Límite de generación | `num_predict: 512` |
| Política B403 | `DEFAULT_NEVER_DISCARD = {"B403"}` en el producto |
| Política B311 | **No** definida antes; no se agrega después de ver el holdout |
| Métrica principal | FNR sobre alertas reales, meta ≤ 5 % |
| Métricas secundarias | FPRR, FOR, precisión, exactitud CWE |
| Decisión de producto | Modo asesor; nunca descarte automático |

## 3. Reglas de lectura acordadas

1. El FNR se calcula sobre las 65 alertas reales; el FOR no lo reemplaza.
2. El FPRR se calcula sobre las 46 alertas falsas.
3. El CWE del modelo no se evalúa como clasificador independiente: se reporta
   cuántas veces copia el CWE del SAST.
4. Se reportan intervalos de confianza Wilson y bootstrap agrupado por archivo,
   porque las alertas de un mismo archivo no son independientes.
5. Un FNR puntual ≤ 5 % no basta si el límite superior del IC95 lo supera.
6. Los falsos negativos se auditan uno por uno, pero **no se reetiqueta** el
   holdout ni se recalcula la métrica principal con las etiquetas auditadas.
7. Cualquier regla de protección nueva (por ejemplo B311) se reporta como
   hallazgo, no se adopta con los mismos datos que la sugirieron.
8. El holdout no se reutiliza para ajustar prompts, hiperparámetros ni reglas.
   Si se cambia algo, hace falta un conjunto nuevo, no otra corrida sobre este.

## 4. Ejecución registrada

| Paso | Comando | Resultado |
|---|---|---|
| Generar el conjunto | `python eval\build_eval_set.py --split test --confirm-holdout` | `eval/holdout_set.jsonl`, 111 alertas |
| Línea base SAST | `python eval\run_eval.py --config A --eval-set eval\holdout_set.jsonl` | `eval/resultados_holdout_A.json` |
| Control sin few-shot | `python eval\run_eval.py --config C0 --model qwen2.5-coder:1.5b --eval-set eval\holdout_set.jsonl` | `eval/resultados_holdout_C0.json` |
| Modelo afinado | `python eval\run_eval.py --config D --model qwen2.5-coder-triage --eval-set eval\holdout_set.jsonl` | `eval/resultados_holdout_D.json` |
| Análisis derivado | `python eval\analisis_holdout.py` | `eval/analisis_holdout.json` |

No se volvió a ejecutar el modelo para aplicar la política B403: las métricas de
producto se derivan de los mismos resultados, cambiando solo la decisión de las
alertas B403 que el modelo marcó como SAFE.

## 5. Resultado y decisión

- D crudo: FPRR 30,4 %, FNR 9,2 % (6/65), FOR 30,0 %, CWE 32,2 %.
- D + política B403: FPRR 19,6 %, FNR 3,1 % (2/65), IC95 0,8–10,5 %.
- D + B403 y B311: FNR 0 %, pero **no se adopta** por ser una decisión post hoc.
- El FNR crudo supera la meta y el intervalo de la política B403 también la
  supera en su límite superior.

**Decisión:** se mantiene el modo asesor; la política B403 queda obligatoria si
se usa D; B311 se registra como riesgo nuevo; no se habilita descarte
automático. El holdout queda consumido y no se vuelve a usar para ajustar nada.

## 6. Checklist de la defensa

- [x] Set generado con `--confirm-holdout` y guardado aparte de desarrollo.
- [x] A, C0 y D evaluados sobre las mismas 111 alertas.
- [x] Prompt, temperatura y `num_predict` congelados.
- [x] Sin reentrenamiento ni cambio de split.
- [x] Métricas crudas y con política separadas.
- [x] Intervalos Wilson y bootstrap por archivo.
- [x] Falsos negativos auditados sin reetiquetar.
- [x] B403 aplicado; B311 reportado y no adoptado.
- [x] SHA256 de set y resultados registrados en `docs/ANALISIS_HOLDOUT.md`.
- [ ] Rúbrica de explicaciones completada por dos revisores (pendiente).
- [ ] Análisis de casi-duplicados entre train y holdout (pendiente).
