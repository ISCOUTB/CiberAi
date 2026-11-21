# Guía para agentes de IA — Agente de seguridad de código fuente

> Este archivo es para ti, agente de IA, y para cualquier colaborador humano que entre al proyecto. Resume el contexto, las convenciones y los comandos que más se usan.

## 1. Qué es este proyecto

Trabajo de Fin de Grado que implementa un **agente local de triage** para alertas SAST sobre código Python. Usa un Qwen2.5-Coder-1.5B afinado con QLoRA, cuantizado a Q4_K_M y servido con Ollama. Además de Bandit, el producto incluye un **escaner propio de reglas OWASP Top 10 2021** y un modo **LLM-first** (`--scanner llm`) en el que el modelo lee el código y detecta vulnerabilidades por sí mismo, antes de ejecutar cualquier herramienta SAST.

**Decisión clave de diseño:** el agente opera en **modo asesor**. Recomienda descartar alertas (`SAFE`), pero **nunca elimina la alerta del reporte**. La decisión final es del revisor humano.

**Meta de investigación:** reducir el FPRR sin superar un FNR del 5 %. El holdout mostró FNR 9,2 % crudo y 3,1 % con política B403, pero el IC95 superior es 10,5 %, así que el descarte automático queda fuera de alcance.

## 2. Estructura del repositorio

```text
agente/                 # Código del producto (CLI, parsing, SARIF, política, tests)
  run.py                # Punto de entrada de la CLI
  triage.py             # Prompt, veredicto, validación
  src/agente_seguridad/sast/bandit_runner.py   # Runner de Bandit
  src/agente_seguridad/sast/owasp_runner.py    # Escaner propio OWASP
  src/agente_seguridad/sast/owasp_rules.py     # Catalogo de reglas OWASP
  src/agente_seguridad/llm/code_audit.py       # Auditoria LLM-first (modelo primero)
  tests/                # Pruebas unitarias

dataset/                # Dataset y splits
  scripts/build_splits.py
  scripts/download_dataset.py   # Descarga el dataset de HuggingFace
  data/                 # *.parquet descargables (ignorados por git)
  splits/               # *.jsonl regenerables (ignorados por git)

eval/                   # Evaluaciones, resultados JSON, bancos y auditorías
  resultados_*.json     # Resultados A/B/C/C0/D, holdout y auditoria LLM
  build_audit_eval_set.py  # Conjunto de codigo crudo para --scanner llm
  run_audit_eval.py        # Precision/recall/F1/FPR/FNR de deteccion directa
  banco_sintetico.json
  auditoria_repos_metricas.json
  casi_duplicados.json
  holdout_set.jsonl     # Conjunto reservado: NO usar para ajustar nada
  repos_reales/         # Repos clonados para smoke test (ignorado)

training/               # Entrenamiento QLoRA y exportación GGUF
  train_qlora.py
  prepare_sft.py
  build_audit_sft.py    # SFT para deteccion directa (codigo -> JSON)
  export_gguf.py
  data/                 # *.jsonl regenerables (ignorado)
  llama-bin/            # Binarios descargables (ignorado)
  out/                  # Modelos, checkpoints, logs (ignorado)

scripts/                # Scripts de documentación y gráficas
  build_avance5.py      # Genera Avance 5.docx
  build_informe_final.py
  build_informe_html.py
  graficas_avance.py
  check_consistencia.py

docs/                   # Borradores y documentos Markdown
  INFORME_FINAL.md      # Generado con build_informe_final.py
  BORRADOR_*.md
  OWASP.md
  AUDITORIA_REPOS.md
  BANCO_SINTETICO.md

reportes/               # Salida de escaneos, gráficas, PDFs (ignorado)
```

## 3. Reglas de oro

1. **NO tocar el holdout** (`eval/holdout_set.jsonl`). No se usa para entrenar, ajustar prompts, hiperparámetros ni reglas.
2. **NO adoptar reglas post hoc**. B311 apareció como problema, pero no se añade a la política porque se descubrió después del holdout.
3. **El modo asesor es obligatorio**. Un `SAFE` solo recomienda descarte; la alerta permanece visible.
4. **OWASP se deriva del CWE del detector que originó el hallazgo**: del SAST en el triage y del CWE que emite el modelo en `--scanner llm`. Nunca se usa la columna `owasp` del dataset ni una categoría OWASP inventada por el modelo.
5. **Mantener `DEFAULT_NEVER_DISCARD = {"B403"}`** en `triage.py`.
6. **Las cifras del Avance 5 / informe deben coincidir** con `eval/resultados_*.json`. Antes de entregar, ejecutar `check_consistencia.py`.
7. **El escaner OWASP es propio y heuristico.** Sus reglas viven en `sast/owasp_rules.py` y no llaman a Bandit. La categoria OWASP se sigue derivando del CWE con `owasp.py`.

## 4. Comandos esenciales

### Verificar que todo funciona
```powershell
python -m unittest discover -s agente\tests
python scripts\check_consistencia.py
```

### Regenerar documentos
```powershell
python scripts\graficas_avance.py        # reportes/grafica_*.png
python scripts\build_avance5.py          # Avance 5.docx
python scripts\build_informe_final.py    # docs/INFORME_FINAL.md
python scripts\build_informe_html.py     # docs/INFORME_FINAL.html
```

### Descargar dataset y regenerar splits
```powershell
pip install datasets
python dataset\scripts\download_dataset.py
python dataset\scripts\build_splits.py
```

### Entrenar (requiere GPU y `training/requirements.txt`)
```powershell
python training\prepare_sft.py
python training\build_audit_sft.py          # modo modelo primero
python training\train_qlora.py --train training\data\train_audit.jsonl --val training\data\val_audit.jsonl
python training\export_gguf.py --adapter training\out\qwen-coder-1.5b-lora --out training\out\qwen-coder-1.5b-merged --gguf-out training\out\gguf\qwen-coder-1.5b-q4_k_m.gguf
ollama create qwen2.5-coder-triage -f Modelfile
```

### Evaluar la deteccion directa (sin alertas SAST)
```powershell
python eval\build_audit_eval_set.py --per-class 300
python eval\run_audit_eval.py --model qwen2.5-coder-triage
```

### Escanear un repositorio
```powershell
python agente\run.py scan agente\examples\sample_repo --model qwen2.5-coder-triage --out reportes\sample
python agente\run.py scan agente\examples\sample_repo --scanner llm --model qwen2.5-coder-triage --out reportes\sample_llm
python agente\run.py scan agente\examples\sample_repo --scanner all --model qwen2.5-coder-triage --out reportes\sample_all
python agente\run.py scan agente\examples\sample_repo --no-llm --out reportes\sample_sast
python agente\run.py scan agente\examples\sample_repo --scanner owasp --no-llm --out reportes\sample_owasp
python agente\run.py scan agente\examples\sample_repo --scanner bandit --no-llm --out reportes\sample_bandit
```

`--scanner` acepta `both` (por defecto: Bandit + escaner OWASP), `bandit`, `owasp`, `llm` (solo auditoria del modelo) o `all` (LLM primero y despues Bandit + OWASP).

## 5. Convenciones de código

- Python 3.10+.
- Codificación UTF-8. En Windows, los scripts usan `sys.stdout.reconfigure(encoding="utf-8")`.
- Preferir `pathlib.Path` sobre cadenas de ruta.
- Los scripts escriben en UTF-8 (`open(..., encoding="utf-8")`).
- Tests con `unittest`. Ejecutar con `python -m unittest discover -s agente\tests`.
- Nombres de funciones y variables en español o inglés según el módulo; seguir el estilo existente.
- **No usar `git commit`, `git push`, `git reset`, `git rebase` salvo que el usuario lo pida explícitamente.**

## 6. Cómo se miden las cosas

- **FPRR:** falsos positivos recomendados para descarte / total de falsos positivos.
- **FNR:** alertas reales recomendadas para descarte / total de alertas reales.
- **FOR:** falsos positivos entre las recomendaciones de descarte.
- **Holdout:** `eval/holdout_set.jsonl`, evaluado una sola vez.
- **Auditoría LLM-first:** `eval/audit_eval_set.jsonl` (solo desarrollo). Se miden TP/FN/FP/TN, precisión, recall, F1, FPR, FNR y exactitud del CWE. Una respuesta inválida cuenta como negativa y se reporta aparte.
- **Línea base LLM-first (11/11/2026):** `qwen2.5-coder:1.5b`, primeros 40 fragmentos (20 vulnerables / 20 seguros): precisión 55,2 %, recall 80,0 %, F1 65,3 %, FPR 65,0 %, FNR 20,0 %, CWE 12,5 %, 5 respuestas inválidas. Es el modelo base, no el afinado; `qwen2.5-coder-triage` no está instalado en este entorno.
- **Banco sintético:** 26 alertas, prompt del producto (`triage.build_prompt`), no comparable con C0/D del arnés.
- **Auditoría de repos reales:** 38 alertas de `itsdangerous`, `pyjwt`, `httpie`.

## 7. Cómo ampliar la evaluación

- Si quieres probar una nueva configuración, créala como `eval/config_X.py` y ejecuta `python eval\run_eval.py --config X`.
- Si descubres un nuevo caso interesante, añádelo al banco sintético en `eval/sinteticas/` y ejecuta `eval/banco_sintetico.py`.
- **Nunca** uses el holdout para iterar.

## 8. Documentos clave para leer

- `docs/BORRADOR_INTRODUCCION.md` — pregunta, hipótesis, objetivos.
- `docs/BORRADOR_METODOLOGIA.md` — dataset, entrenamiento, evaluación.
- `docs/BORRADOR_DISCUSION.md` — interpretación de resultados.
- `docs/BORRADOR_CONCLUSIONES.md` — respuestas y trabajo futuro.
- `docs/OWASP.md` — mapeo OWASP del agente.
- `docs/PLAN_DOCUMENTO_FINAL.md` — mapa de la memoria.

## 9. Contacto y contexto

- Rama activa: `feature/sprint-7`.
- Fecha límite aproximada: 15 de noviembre de 2026.
- Entregable principal: memoria del TFG + `Avance 5.docx`.
- Si algo no está claro, pregunta antes de cambiar reglas, prompts o umbrales.
