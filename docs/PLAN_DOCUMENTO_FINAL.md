# Plan del documento final (Sprint 8)

Objetivo: convertir los Avances 1–5 en la memoria del proyecto, sin reescribir lo
que ya está validado. Este archivo es un mapa de trabajo, no el documento.

## Formato y extensión

- Formato institucional: portada, resumen, índice, cuerpo, referencias y anexos.
- Extensión objetivo: 25–35 páginas (8.000–12.000 palabras), sin contar anexos.
- Tablas y figuras numeradas por sección; las métricas deben coincidir con
  `eval/resultados_*.json` y con `reportes/`.

## Estructura y fuente de cada sección

| Sección | Contenido | Fuente principal | Estado |
|---|---|---|---|
| Portada | Título, integrantes, asignatura, fecha | Avance 5 | Reutilizable |
| Resumen | Problema, método, resultados, conclusión (250–300 palabras) | Avance 5 §1 + D/C | Revisar con C |
| 1. Introducción | Contexto, problema, pregunta de investigación, hipótesis, objetivos, contribuciones | `docs/BORRADOR_INTRODUCCION.md` | Borrador listo |
| 2. Estado del arte | SAST, LLM para seguridad, fine-tuning, QLoRA, trabajos relacionados | Avance 5 §11 + `docs/BORRADOR_ESTADO_ARTE.md` | Borrador listo (~2.000 palabras) |
| 3. Requisitos y alcance | Funcionales, no funcionales, recorte Python/Bandit/CWE, modo asesor | Avance 5 §1.1 y §5 | Reutilizable |
| 4. Arquitectura | Pipeline, modelo de datos, CLI, resiliencia, contrato de decisión | Avance 5 §2–§4 | Reutilizable |
| 5. Metodología | Dataset, particiones, SFT, QLoRA, exportación, evaluación A/B/C/D, métricas | `docs/BORRADOR_METODOLOGIA.md` | Borrador listo |
| 6. Experimentos y resultados | Entrenamiento, D, C, comparativa, holdout, latencia, pruebas | Avance 5 §6–§7 + D/C + `docs/ANALISIS_HOLDOUT.md` | Borrador listo con holdout |
| 7. Discusión | FPRR vs. FNR, CWE copiado, B403/B311, límites de la partición, explicaciones, validez | `docs/BORRADOR_DISCUSION.md` | Borrador actualizado |
| 8. Conclusiones | Respuesta a la hipótesis, aportes, trabajo futuro | `docs/BORRADOR_CONCLUSIONES.md` | Borrador actualizado |
| 9. Referencias | 15–20 fuentes verificables | Avance 5 §11 | Ampliar |
| Anexos | Reproducción, artefactos, hashes, prompts, tabla por regla | `docs/BORRADOR_ANEXOS.md` + README + training/ | Borrador listo |

## Secciones que faltan y cómo resolverlas

### 2. Estado del arte

Borrador desarrollado en `docs/BORRADOR_ESTADO_ARTE.md`, con referencias
verificadas contra arXiv y Crossref. Bloques mínimos:

1. **SAST clásico y su límite**: Bandit, Semgrep, reglas sintácticas, alta tasa
   de falsos positivos, ausencia de alcanzabilidad.
2. **LLM para detección y triage**: IRIS (Li et al., 2025), reducción de falsos
   positivos con LLM (Du et al., 2026), límites de los benchmarks (Ding et al.,
   2025; PrimeVul).
3. **Datos**: SecurityEval (Siddiq & Santos, 2022), DiverseVul (Chen et al.,
   2023), CVEfixes (Bhandari et al., 2021), riesgo de fuga de datos.
4. **Ajuste eficiente**: LoRA (Hu et al., 2021), QLoRA (Dettmers et al., 2023),
   cuantización GGUF/llama.cpp, Qwen2.5-Coder (Hui et al., 2024).
5. **Métricas**: FPRR, FNR, FOR, precisión, exactitud CWE, kappa de Cohen,
   BERTScore (Zhang et al., 2020) como medida descriptiva.

Cada bloque debe cerrar con una frase que conecte con la decisión del proyecto
(por qué se eligió Qwen 1.5B, por qué modo asesor, por qué Bandit).

### 7. Discusión

Puntos que la evidencia ya permite argumentar:

- **D reduce el ruido, no clasifica el CWE.** El modelo copia el CWE del SAST
  en 86 de 86 alertas reales conservadas en desarrollo y 59 de 59 en el holdout;
  la exactitud CWE no debe interpretarse como capacidad de clasificación. El
  producto conserva el CWE del SAST.
- **El FNR se concentra en reglas de importación, pero no solo en B403.** En
  desarrollo las 5 alertas reales descartadas eran `import pickle`; en el
  holdout son 4 B403 y 2 B311. B403 es obligatoria como política, pero no
  suficiente: el FNR baja a 3,1 % (IC95 0,8–10,5 %), no a 0 %.
- **La comparación que aísla el ajuste es D contra C0**, porque comparten el
  formato de alerta; C agrega few-shot y D no. La comparación D contra C mide el
  resultado práctico frente a un prompt cuidado, pero mezcla modelo y prompt.
- **La partición es de desarrollo y el holdout también es por función.**
  `val_total` alimentó la validación del ajuste; el test se evaluó una sola vez
  en el Sprint 7. La partición aleatoria por función no garantiza independencia
  por repositorio; los hashes exactos dieron 0 coincidencias, pero faltan los
  casi-duplicados.
- **La pérdida baja no prueba buen triage.** La pérdida de entrenamiento cayó
  a 0,36 y se estancó; la evidencia de calidad es la matriz de evaluación, no
  la curva.
- **D no explica: repite plantillas.** En el holdout produjo 11 explicaciones, 8
  vectores y 2 correcciones para 111 alertas; 91 de 91 `VULNERABLE` comparten la
  misma corrección. La rúbrica debe reportar diversidad, no solo kappa.
- **El holdout no tiene potencia para demostrar FNR ≤ 5 %.** Con 65 alertas
  reales, incluso 0 fallos deja el IC95 superior en 5,6 %.

### 8. Conclusiones

Responder explícitamente:

1. ¿El modelo afinado reduce falsos positivos sin perder vulnerabilidades
   reales? (FPRR y FNR de D frente a C0, con intervalo de confianza y holdout).
2. ¿Sirve para descarte automático? (No: FNR crudo 9,2 %; con B403, 3,1 % pero
   IC95 hasta 10,5 %; modo asesor).
3. ¿Aporta en CWE? (No; conservar el del SAST).
4. ¿Qué falta para producción? (casi-duplicados, rúbrica de explicaciones,
   auditoría humana, regla B311 validada en un conjunto nuevo).

## Cifras que deben coincidir

**Desarrollo (141 alertas):**

- D: FPRR 48,0 %, FNR 5,5 %, FOR 17,2 %, precisión 76,8 %, CWE 43,0 %.
- A: FPRR 0 %, FNR 0 %, CWE 45,1 %, precisión 64,5 %.
- B (piloto 10): FPRR 75 %, FNR 0 %, CWE 0 %.
- C: FPRR 2,0 %, FNR 0,0 %, FOR 0,0 %, precisión 65,0 %, CWE 37,4 %,
  1 respuesta inválida.
- C0: FPRR 22,0 %, FNR 2,2 %, FOR 15,4 %, CWE 44,9 %.
- Entrenamiento: 1.439 pasos, 1 h 50 min 56 s, pérdida 1,11 → 0,36,
  18.464.768 parámetros (1,18 %), 11.510/1.000 ejemplos.
- Integración: 9 alertas, 9 conservadas, 4 recomendadas, 0 errores, 43,1 s.

**Holdout (111 alertas: 65 reales, 46 falsos positivos):**

- A: FPRR 0,0 %, FNR 0,0 %, precisión 58,6 %, CWE 35,4 %.
- C0: FPRR 10,9 %, FNR 0,0 %, FOR 0,0 %, precisión 61,3 %, CWE 33,8 %,
  1 inválida.
- D crudo: FPRR 30,4 %, FNR 9,2 %, FOR 30,0 %, precisión 64,8 %, CWE 32,2 %,
  0 inválidas.
- D + B403: FPRR 19,6 %, FNR 3,1 % (IC95 0,8–10,5 %), FOR 18,2 %,
  precisión 63,0 %.
- D + B403 + B311: FNR 0 %, FPRR 19,6 %, **no adoptado** por ser post hoc.
- Bootstrap por archivo: D crudo FNR 1,9–17,9 %, FPRR 15,2–45,7 %; D + B403
  FNR 0,0–10,2 %, FPRR 9,4–31,2 %.
- Explicaciones de D: 11 / 8 / 2 valores únicos (explicación, vector,
  corrección). C0: 109 / 103 / 106.

## Riesgos de la escritura

- **No presentar CWE como clasificación independiente.** El prompt incluye el
  CWE del SAST y el modelo lo copia (59/59 en el holdout).
- **No presentar el piloto B como resultado definitivo.** n=10.
- **No afirmar resistencia a prompt injection** sin la batería completa.
- **No afirmar que el test está limpio** sin medir casi-duplicados; la partición
  agrupada no es posible porque el dataset no tiene identificador de repositorio.
- **No usar BERTScore sin referencias humanas.** Si no hay referencias,
  declararlo como limitación.
- **No citar solo el valor puntual del FNR.** Con 65 reales, el IC95 de 0/65 ya
  llega a 5,6 %.
- **No presentar B311 como política adoptada.** Se eligió después de ver el
  holdout; es un hallazgo y trabajo futuro.
- **No presentar las explicaciones de D como aporte de calidad.** Son plantillas
  repetidas; la diversidad debe reportarse.

## Orden de trabajo sugerido

1. Cerrar la rúbrica de explicaciones o declararla pendiente con la evidencia de
   diversidad.
2. Medir casi-duplicados entre train y holdout y documentar el resultado.
3. Integrar 6, 7 y 8 en la memoria con las cifras del holdout.
4. Revisar 1, 3, 4 y 5 sobre los Avances.
5. Unificar referencias y numeración.
6. Auditoría de coherencia contra `eval/`, `reportes/` y `scripts/check_consistencia.py`.
