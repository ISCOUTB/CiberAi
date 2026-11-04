# Estado Sprint 2 — dataset construido (20 oct 2026)

## Hecho
- Dataset auditado: `dataset/data/*.parquet` (175.419 filas; 140.335 / 17.542 / 17.542).
- Fuga detectada por hash SHA-256 de código normalizado:
  - train vs test: 2.025 hashes compartidos
  - train vs val: 2.088
  - val vs test: 292
  - etiquetas contradictorias: 433 hashes
- Dataset reconstruido (`dataset/scripts/build_splits.py`):
  - Se retiraron de train/val los hashes presentes en test o en otra partición.
  - Test intacto: 17.542 muestras (holdout final).
  - Train único tras filtros: 127.348.
  - Split 80/20 (semilla 42): **101.878 train** / **25.470 val**.
  - Validación total (val 80/20 + val original depurada 17.066): **42.536**.
  - Vulnerables: 6.178 en train (6,1 %) → desbalanceo fuerte.
  - Lenguajes train: C 94,1 %, Python 1,4 %, C++ 1,2 %, Java 0,9 %, JS 0,7 %, PHP/Go/C#/Swift/etc. resto.
- Salidas en `dataset/splits/`: `train_80.jsonl`, `val_20.jsonl`, `val_total.jsonl`, `stats.json`.
  - Formato por línea: `{"prompt": ..., "target": "{...}", "meta": {...}}`.
  - `target` usa el esquema del Avance 3: veredicto, cwe, severidad, explicacion, vector_ataque, correccion.
- `Avance 3.docx` actualizado (respaldo en `respaldo/Avance 3 (original).docx`):
  - Nueva sección 5.4.1 con el dataset real y la auditoría de fuga.
  - Limitaciones marcadas como resueltas/pendientes.
  - Próximos pasos: pasos 1–2 completados.
  - Conclusión actualizada. Script: `scripts/update_avance3.py`.

## Pendiente Sprint 2 (equipo)
- Etiquetado manual / verificación de muestra y explicaciones de referencia del holdout.
- Actualizar la sección "Metodología de Datos y Etiquetado" del documento final.
- Entrada en bitácora de decisiones.

## Siguiente: Sprint 3 (software)
CLI: Bandit + normalización SARIF + deduplicación (CWE+ruta+función/línea) + extracción de contexto + llamada HTTP a Ollama con ID único.
Proyecto de código aún no existe en esta carpeta: hay que crearlo.
