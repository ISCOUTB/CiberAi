# Borrador — Anexos (Sprint 8)

> Documento de trabajo. Los anexos remiten a archivos del repositorio; no
> duplican tablas que ya viven en `eval/` para evitar que se desincronicen.

## Anexo A. Reproducción

Requisitos de inferencia: Python 3.10 o superior, Bandit 1.9, Ollama y un modelo
registrado. En la máquina de desarrollo se usó Python 3.14.7, Bandit 1.9.4,
Ollama 0.40.14, `requests` 2.34.2 y `python-docx` 1.2.0.

```powershell
# 1. Dependencias del agente
pip install -r agente\requirements.txt

# 2. Modelo en Ollama (ya registrado como qwen2.5-coder-triage)
ollama list

# 3. Escaneo de un repositorio en modo asesor
python agente\run.py scan examples\sample_repo --model qwen2.5-coder-triage `
    --out reportes\sample

# 4. Escaneo sin modelo (solo SAST)
python agente\run.py scan examples\sample_repo --no-llm --out reportes\sample_sast

# 5. Evaluación A/B/C/C0/D
python eval\run_eval.py --config A
python eval\run_eval.py --config B  --model qwen2.5-coder:1.5b
python eval\run_eval.py --config C  --model qwen2.5-coder:1.5b
python eval\run_eval.py --config C0 --model qwen2.5-coder:1.5b
python eval\run_eval.py --config D  --model qwen2.5-coder-triage

# 6. Pruebas y consistencia de cifras
python -m unittest discover -s agente\tests -v
python scripts\check_consistencia.py
```

El entrenamiento se ejecutó en una RTX 4070 Super con `training\entrenar_windows.ps1`.
El adaptador se exportó con `training\export_gguf.py`; el registro en Ollama y la
prueba de tres alertas de control están descritos en `README.md`.

## Anexo B. Artefactos y hashes

| Artefacto | Ruta | Tamaño |
|---|---|---|
| Adaptador LoRA | `training/out/qwen-coder-1.5b-lora/` | 70,5 MB |
| Modelo fusionado f16 | `training/out/qwen-coder-1.5b-merged/` | 2.950 MB |
| GGUF f16 | `training/out/gguf/qwen-coder-1.5b-f16.gguf` | — |
| GGUF Q4_K_M | `training/out/gguf/qwen-coder-1.5b-q4_k_m.gguf` | 940,4 MB |
| Registro de hashes | `training/out/SHA256SUMS.txt` | — |
| Log de entrenamiento | `training/out/train.log` (UTF-16) | 414 KB |

Hashes SHA-256:

```
561F877723465779DC049D2B5C3AA2501982931FF01473B227A57ACE924B6D4E  qwen-coder-1.5b-q4_k_m.gguf
B2990C07C3B0FA788B052E879FDF05C8B82180A13E10F5688B144696823A93D5  adapter_model.safetensors
ED23ABB0F677473486977A22F58D4A4D90105336797EB082DB08A232E9FFA9AD  qwen-coder-1.5b-f16.gguf
```

## Anexo C. Prompts

**Sistema (idéntico en entrenamiento, evaluación y producto):**

> Eres un analista de seguridad de software. Analizas un fragmento de código y
> decides si contiene una vulnerabilidad real (VULNERABLE) o si es seguro
> (SAFE). Responde SOLO con un objeto JSON con las claves: veredicto, cwe,
> severidad, explicacion, vector_ataque, correccion.

**Plantilla de alerta (D y C0):**

```
Alerta del SAST (triage):
- Regla: {rule_id}
- CWE reportado: {cwe_sast}
- Severidad: {severity}
- Confianza: {confidence}
- Funcion: {function}
- Mensaje: {message}

Codigo fuente:
<code>
{code}
</code>

Devuelve el JSON.
```

**C** antepone dos ejemplos resueltos (una inyección SQL y un `assert` de
prueba) al mismo bloque de alerta. **B** envía solo el código, sin alerta ni
ejemplos. El texto completo está en `eval/run_eval.py` (`SYSTEM`, `FEW_SHOT`,
`TEMPLATE_ALERTA`).

El delimitador `<code>` separa el código de las instrucciones. No es una defensa
completa contra prompt injection: reduce el riesgo de que el modelo confunda
datos con órdenes, pero la validación de la salida y la política conservadora son
las que impiden que una inyección convierta una alerta en un descarte silencioso.

## Anexo D. Conjuntos de evaluación

`eval/eval_set.jsonl` contiene 141 alertas de Bandit sobre funciones Python de
`val_total`: 91 reales y 50 falsos positivos. Cada línea incluye `id`, `rule_id`,
`cwe_sast`, `cwe_dataset`, `truth`, `severity`, `confidence`, `function`,
`message` y `code`. El conjunto se regenera con `eval/build_eval_set.py`.

`eval/holdout_set.jsonl` contiene las 111 alertas del test reservado (65 reales,
46 falsos positivos) sobre 300 funciones Python. Se generó una sola vez con
`--split test --confirm-holdout`, se evaluó con A, C0 y D, y no se reutiliza para
ajustar nada. Su SHA256 es
`D9A91DC4B41170E0E2427D202E05F44E777A61C2F9DD4D4196D7EC752EAB1E81`; los hashes
de los resultados y las reglas de lectura están en `docs/ANALISIS_HOLDOUT.md` y
`docs/PROTOCOLO_HOLDOUT.md`.

## Anexo E. Pruebas

`agente/tests/test_agente.py` cubre contexto por AST, deduplicación, SARIF,
parseo de la respuesta, política conservadora, modo asesor, ejecución de Bandit
y el límite de generación del cliente: 13 pruebas, todas correctas. La batería
funcional y de robustez está en `eval/pruebas/LEEME.md`: repositorio vacío,
archivo vacío, sintaxis inválida, otro lenguaje, repositorio grande, Ollama
caído, JSON inválido y prompt injection.

## Anexo F. Tablas por regla

Las tablas de resultados por regla de Bandit viven en `docs/ANALISIS_C.md`,
`docs/ANALISIS_D.md` y `docs/ANALISIS_HOLDOUT.md`. La tabla comparativa del
documento se genera desde `scripts/build_avance5.py` y se valida contra los JSON
con `scripts/check_consistencia.py`. El análisis del holdout se reproduce con
`python eval/analisis_holdout.py`.
