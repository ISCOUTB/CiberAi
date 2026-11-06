# Análisis de la evaluación holdout (Sprint 7)

Corrida del **3 de noviembre de 2026** sobre el split `test`, reservado hasta ese
momento. El conjunto tiene **111 alertas de Bandit** extraídas de **300 funciones
Python** del test de 17.542 filas: **65 alertas reales y 46 falsos positivos**.
Se evaluaron A (solo SAST), C0 (modelo base sin few-shot) y D (modelo afinado
`qwen2.5-coder-triage` en Q4_K_M), con temperatura 0 y `num_predict: 512`.
C0 y D comparten el mismo formato de alerta; C no se corrió en el holdout.

> Este documento se escribió **después** de la corrida. No es un preregistro y
> no pretende demostrar que el holdout se abrió una sola vez: registra lo que se
> ejecutó, con qué archivos y qué se puede concluir. Las cifras se reproducen
> con `python eval/analisis_holdout.py`.

## 1. Resultados globales

| Configuración | Alertas | FPRR | FNR | FOR | Precisión | CWE | Inválidas |
|---|---:|---:|---:|---:|---:|---:|---:|
| A. Solo SAST | 111 | 0,0 % | 0,0 % | 0,0 % | 58,6 % | 35,4 % | 0 |
| C0. Base sin few-shot | 111 | 10,9 % | 0,0 % | 0,0 % | 61,3 % | 33,8 % | 1 |
| D. Afinado (crudo) | 111 | 30,4 % | 9,2 % | 30,0 % | 64,8 % | 32,2 % | 0 |
| D + política B403 | 111 | 19,6 % | 3,1 % | 18,2 % | 63,0 % | 30,2 % | 0 |
| D + B403 y B311 | 111 | 19,6 % | 0,0 % | 0,0 % | 63,7 % | 29,2 % | 0 |

- **D crudo:** descarta 14 de 46 falsos positivos y 6 de 65 alertas reales.
- **D con la política de producto:** la política B403 convierte en `SOSPECHOSA`
  las recomendaciones SAFE de esa regla. Rescata 4 de los 6 falsos negativos,
  pero deja 2 B311 y reduce el FPRR de 30,4 % a 19,6 % porque también conserva
  5 falsos positivos B403.
- **B403 y B311:** proteger también B311 lleva el FNR a 0 %, pero **no es una
  decisión válida**: B311 se agregaría después de ver el holdout. Se reporta
  como escenario, no como política adoptada.

La política B403 ya estaba definida antes de esta corrida y está implementada en
`agente/src/agente_seguridad/triage.py` (`DEFAULT_NEVER_DISCARD`). Las métricas
con política se derivan de los mismos resultados, sin volver a ejecutar el
modelo.

## 2. Intervalos de confianza y unidad de análisis

| Métrica | Valor | IC95 Wilson | IC95 bootstrap por archivo |
|---|---:|---|---|
| FPRR de D crudo | 30,4 % | 19,1–44,8 % | 15,2–45,7 % |
| FNR de D crudo | 9,2 % | 4,3–18,7 % | 1,9–17,9 % |
| FPRR de D + B403 | 19,6 % | 10,7–33,2 % | 9,4–31,2 % |
| FNR de D + B403 | 3,1 % | 0,8–10,5 % | 0,0–10,2 % |
| FNR de C0 | 0,0 % | 0,0–5,6 % | — |

El bootstrap remuestrea **archivos**, no alertas, porque las 111 alertas salen de
71 archivos y 98 funciones y hay 40 filas que repiten exactamente el mismo
código. Las observaciones no son independientes y los intervalos de Wilson son
demasiado angostos.

Con **65 alertas reales**, incluso un resultado de 0 falsos negativos deja el
límite superior del IC95 en **5,6 %**. En otras palabras: este holdout **no
alcanza para demostrar estadísticamente que el FNR sea ≤ 5 %**; solo permite
descartar tasas mucho peores. Esa limitación debe quedar escrita en la memoria.

## 3. D frente a C0

La comparación que aísla el ajuste fino es D contra C0, porque comparten prompt,
conjunto y temperatura.

- D descarta **18 alertas que C0 conserva**: 6 reales y 12 falsos positivos.
- C0 descarta **3 alertas que D conserva**: 0 reales y 3 falsos positivos.
- En términos netos, D recomienda **15 descartes más** que C0, pero paga con
  **6 alertas reales adicionales**.

El intercambio marginal es claro: por cada 12 falsos positivos adicionales que D
elimina, omite 6 alertas reales. No es un cambio de “inteligencia”; es un cambio
de umbral de decisión aprendido.

Frente a C0, el FPRR de D crudo sube **+19,6 puntos**; con la política B403 sube
**+8,7 puntos**. Los “+46 puntos” que se reportaban en desarrollo comparaban D
contra C, no contra C0, y no se sostienen en el holdout.

## 4. Falsos negativos de D

| ID | Regla | CWE SAST / dataset | Qué hace el código | Lectura |
|---|---|---|---|---|
| `f11445.py:1` | B403 | CWE-502 / CWE-502 | `pickle.dump` + `pickle.load` + `pickle.loads` de un objeto con `__reduce__` que ejecuta `/bin/sh` | **Omisión genuina:** hay deserialización de un objeto explotable |
| `f1878.py:1` | B403 | CWE-502 / CWE-502 | `pickle.dump` + `pickle.load` de `EvilPickle` con `os.system` | **Omisión genuina:** hay deserialización |
| `f15804.py:1` | B403 | CWE-502 / CWE-502 | Solo `pickle.dump` de un objeto con `__reduce__`; no deserializa | Discutible: serializar no ejecuta el payload; el riesgo está en el `load` ausente |
| `f2231.py:1` | B403 | CWE-502 / CWE-502 | Solo `pickle.dump`; no deserializa | Discutible, igual que el anterior |
| `f16317.py:7` | B311 | CWE-330 / CWE-94 | `random.randint(0, 10)` para una división de ejemplo | Etiqueta ruidosa: no hay uso criptográfico ni de seguridad; el dataset lo marca CWE-94, que no corresponde a B311 |
| `f16317.py:8` | B311 | CWE-330 / CWE-94 | Igual que la anterior, segunda línea del mismo ejemplo | Etiqueta ruidosa, mismo caso |

**Lectura honesta:** el FNR crudo es **9,2 % (6/65)** y es la cifra que debe
reportarse. De esos 6 casos, 2 son omisiones claras y 4 son discutibles por
etiquetas del dataset o por tratarse de serialización sin deserialización. Una
auditoría de sensibilidad que solo cuente las omisiones claras daría **3,1 %
(2/65)**, pero **no se puede reetiquetar el holdout después de verlo**. La
auditoría se reporta aparte, con el criterio explícito, y la métrica principal
sigue siendo la cruda.

## 5. La política B403 no alcanza

La hipótesis de desarrollo era: “todo el error está en B403; excluir B403 lleva
el FNR a 0 %”. El holdout la refuta parcialmente:

- B403 explica 4 de los 6 falsos negativos; los otros 2 son B311.
- Con B403 protegido, el FNR baja a **3,1 %**, pero su IC95 llega a **10,5 %**
  (bootstrap: 0,0–10,2 %). El valor puntual cumple la meta; la evidencia no.
- El FPRR cae a **19,6 %**, porque se conservan 5 falsos positivos B403.
- Proteger B311 después de ver el holdout sería sobreajustar la política al
  conjunto de prueba. No se adopta.

**Consecuencia de producto:** si se usa D, la política B403 debe ser obligatoria
y el modo asesor se mantiene. No hay base para habilitar descarte automático ni
para afirmar que el FNR es 0 %.

## 6. CWE

D copia el CWE del SAST en **59 de 59** alertas reales conservadas. Su exactitud
CWE de 32,2 % no mide clasificación independiente: mide la coincidencia entre la
etiqueta del SAST y la del dataset, sobre el subconjunto que D conservó. A
obtiene 35,4 % y C0 33,8 % con denominadores distintos. El producto debe seguir
mostrando el CWE del SAST y no presentar el CWE del modelo como una clasificación
propia.

## 7. Las explicaciones de D colapsaron

| Salida | D: valores únicos | C0: valores únicos |
|---|---:|---:|
| Explicaciones | **11** | 109 |
| Vectores de ataque | **8** | 103 |
| Correcciones | **2** | 106 |

- 91 de 91 alertas `VULNERABLE` de D comparten la misma corrección:
  “Aplicar validación de entradas y sanitización.”
- 47 alertas comparten la misma explicación de CWE-78.
- En los datos de entrenamiento, **5.489 de 5.755** respuestas SAFE tienen
  exactamente la misma explicación; solo hay 28 vectores distintos. El modelo
  aprendió la plantilla, no un análisis específico del código.

D sirve como **clasificador de triage**, no como generador de explicaciones
técnicas. La rúbrica de explicaciones sigue pendiente y, si se aplica sobre D,
va a confirmar esta falta de diversidad. La memoria no debe presentar las
explicaciones de D como un aporte de calidad sin ese resultado.

## 8. Limitaciones

1. **Partición por función, no por proyecto.** El dataset no tiene identificador
   de repositorio, así que no se puede agrupar de verdad. La comparación exacta
   de hashes normalizados contra `train_80` y `val_total` dio **0 coincidencias**,
   pero no se midieron casi-duplicados.
2. **Dependencia interna del holdout.** 111 alertas, 71 códigos únicos y 98
   funciones: 40 filas repiten código. El tamaño efectivo es menor que 111 y los
   IC de Wilson no lo reflejan; por eso se agrega el bootstrap por archivo.
3. **Etiquetas ruidosas.** Los dos B311 son un ejemplo de división con
   `random.randint`, etiquetado CWE-94; los dos B403 de solo serialización no
   ejecutan el payload. No se reetiqueta: se audita.
4. **Una sola corrida, sin preregistro formal.** Los archivos y sus hashes
   permiten auditar qué se evaluó, pero no demuestran por sí solos que el
   holdout no se reutilizó. El protocolo se registra en
   `docs/PROTOCOLO_HOLDOUT.md`.
5. **C no se midió en el holdout.** La comparación con C sigue siendo de
   desarrollo; en el holdout la referencia correcta es C0.
6. **Potencia insuficiente para la meta.** Con 65 reales, el IC95 de 0/65 llega
   a 5,6 %. La meta de FNR ≤ 5 % no se puede demostrar con este tamaño.

## 9. Conclusiones

1. **D no cumple la meta de omisión en el holdout:** FNR crudo 9,2 % (IC95
   4,3–18,7 %; bootstrap 1,9–17,9 %). El modo asesor se mantiene sin excepciones.
2. **La política B403 mejora el resultado, pero no lo vuelve seguro:** FNR 3,1 %
   con IC95 0,8–10,5 % y FPRR 19,6 %. Es obligatoria si se usa D, no opcional.
3. **Aparece un riesgo nuevo en B311.** No se puede convertir en regla después de
   ver el holdout; se reporta como hallazgo y como trabajo futuro.
4. **El ahorro real es menor que el de desarrollo:** +8,7 puntos de FPRR sobre C0
   con la política, no +46. La conclusión de “D reduce el ruido” sigue siendo
   cierta en dirección, pero mucho más modesta en magnitud.
5. **D no explica:** 11 explicaciones y 2 correcciones para 111 alertas. El
   producto debe separar triage de explicación y usar el CWE y el contexto del
   SAST para el reporte.
6. **El holdout hizo su trabajo:** mostró que el resultado de desarrollo no se
   generaliza tal cual. Esa es la conclusión metodológica más valiosa del Sprint.

## 10. Reproducibilidad

| Archivo | SHA256 |
|---|---|
| `eval/holdout_set.jsonl` | `D9A91DC4B41170E0E2427D202E05F44E777A61C2F9DD4D4196D7EC752EAB1E81` |
| `eval/resultados_holdout_A.json` | `26C6B4F752BF7EAA328239D487100B8BF40344CC967D943BA49FD799EB711D5F` |
| `eval/resultados_holdout_C0.json` | `5DEC71D371D202A543AD9B8D36C94BE788C899D23506ED5D33D38D6C4529698E` |
| `eval/resultados_holdout_D.json` | `9FDAA511C0E7A48E19D4E047E2EE78C5FFD5BB84872D0FCBA2A7E63C9DC84C0F` |

Comandos registrados (no volver a ejecutar la generación del holdout; se
incluyen para auditoría):

```powershell
python eval\build_eval_set.py --split test --confirm-holdout
python eval\run_eval.py --config A --eval-set eval\holdout_set.jsonl
python eval\run_eval.py --config C0 --model qwen2.5-coder:1.5b --eval-set eval\holdout_set.jsonl
python eval\run_eval.py --config D --model qwen2.5-coder-triage --eval-set eval\holdout_set.jsonl
python eval\analisis_holdout.py
```

El resumen derivado se guarda en `eval/analisis_holdout.json`. La corrida usó
Bandit 1.8.6 para la configuración A, `qwen2.5-coder:1.5b` para C0 y
`qwen2.5-coder-triage` (Q4_K_M) para D, con Ollama 0.40.13.
