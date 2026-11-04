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
| 6. Experimentos y resultados | Entrenamiento, D, C, comparativa, latencia, pruebas | Avance 5 §6–§7 + D/C | Falta holdout |
| 7. Discusión | FPRR vs. FNR, CWE copiado, B403, límites de la partición, validez | `docs/BORRADOR_DISCUSION.md` | Borrador listo |
| 8. Conclusiones | Respuesta a la hipótesis, aportes, trabajo futuro | `docs/BORRADOR_CONCLUSIONES.md` | Borrador listo |
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
  en la mayoría de las alertas conservadas; la exactitud CWE no debe
  interpretarse como capacidad de clasificación. El producto conserva el CWE
  del SAST.
- **El FNR de D se concentra en B403.** Las cinco alertas reales descartadas
  son `import pickle`; dos de esos casos solo serializan. El error es de una
  regla, no sistémico. Excluir B403 del descarte lleva el FNR a 0 % con FPRR
  38 %.
- **La comparación que aísla el ajuste es D contra C0**, porque comparten el
  formato de alerta; C agrega few-shot y D no. La comparación D contra C mide el
  resultado práctico frente a un prompt cuidado, pero mezcla modelo y prompt.
- **La partición es de desarrollo.** `val_total` alimentó la validación del
  ajuste; el test de 17.542 sigue intacto. La partición aleatoria por función
  no garantiza independencia por repositorio.
- **La pérdida baja no prueba buen triage.** La pérdida de entrenamiento cayó
  a 0,36 y se estancó; la evidencia de calidad es la matriz de evaluación, no
  la curva.

### 8. Conclusiones

Responder explícitamente:

1. ¿El modelo afinado reduce falsos positivos sin perder vulnerabilidades
   reales? (FPRR de D vs. C y FNR con intervalo de confianza).
2. ¿Sirve para descarte automático? (No con FNR > 5 %; modo asesor).
3. ¿Aporta en CWE? (No; conservar el del SAST).
4. ¿Qué falta para producción? (partición por proyecto, holdout, auditoría
   humana, regla B403).

## Cifras que deben coincidir

- 141 alertas: 91 reales, 50 falsos positivos.
- D: FPRR 48,0 %, FNR 5,5 %, FOR 17,2 %, precisión 76,8 %, CWE 43,0 %.
- A: FPRR 0 %, FNR 0 %, CWE 45,1 %, precisión 64,5 %.
- B (piloto 10): FPRR 75 %, FNR 0 %, CWE 0 %.
- C: FPRR 2,0 %, FNR 0,0 %, FOR 0,0 %, precisión 65,0 %, CWE 37,4 %,
  1 respuesta inválida.
- Entrenamiento: 1.439 pasos, 1 h 50 min 56 s, pérdida 1,11 → 0,36,
  18.464.768 parámetros (1,18 %), 11.510/1.000 ejemplos.
- Integración: 9 alertas, 9 conservadas, 4 recomendadas, 0 errores, 43,1 s.

## Riesgos de la escritura

- **No presentar CWE como clasificación independiente.** El prompt incluye el
  CWE del SAST y el modelo lo copia.
- **No presentar el piloto B como resultado definitivo.** n=10.
- **No afirmar resistencia a prompt injection** sin el resultado de la batería.
- **No afirmar que el test está limpio** sin la partición agrupada por proyecto.
- **No usar BERTScore sin referencias humanas.** Si no hay referencias,
  declararlo como limitación.

## Orden de trabajo sugerido

1. Cerrar cifras de C y holdout.
2. Escribir 6, 7 y 8 (dependen de datos).
3. Escribir 2 (independiente).
4. Revisar 1, 3, 4 y 5 sobre los Avances.
5. Unificar referencias y numeración.
6. Auditoría de coherencia contra `eval/` y `reportes/`.
