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

# 6. Cobertura OWASP y análisis pareado C0/D
python eval\cobertura_owasp.py
python eval\analisis_c0_vs_d.py

# 7. Pruebas y consistencia de cifras
python -m unittest discover -s agente\tests -v
python scripts\check_consistencia.py

# 8. Validaciones out-of-distribution
python eval\banco_sintetico.py --validar
python eval\banco_sintetico.py
python eval\corrida_repos_reales.py
python eval\auditoria_repos.py --preparar
# editar eval\auditoria_repos.jsonl
python eval\auditoria_repos.py --calcular
python eval\casi_duplicados.py
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

**Sistema (idéntico en entrenamiento y evaluación):**

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

**Diferencia con el prompt del producto.** `agente/src/agente_seguridad/triage.py`
usa un `SYSTEM` y un `TEMPLATE` más detallados: agrega archivo, línea y una
descripción campo por campo de la salida. Las métricas del proyecto se midieron
con el prompt de evaluación, no con el del producto. La comparación C0/D no se
ve afectada —ambas usan el mismo prompt—, pero el FPRR y el FNR reportados no
describen exactamente el comportamiento de la CLI. Alinear ambos prompts y medir
el efecto sobre `examples/sample_repo` queda como trabajo futuro; no se hizo en
este sprint porque el holdout ya está cerrado y el cambio no está medido.

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
parseo de la respuesta, política conservadora, modo asesor, ejecución de Bandit,
mapeo OWASP y el límite de generación del cliente: **22 pruebas**, todas
correctas. La batería funcional y de robustez está en `eval/pruebas/LEEME.md`:
repositorio vacío, archivo vacío, sintaxis inválida, otro lenguaje, repositorio
grande, Ollama caído, JSON inválido y prompt injection.

## Anexo F. Tablas por regla

Las tablas de resultados por regla de Bandit viven en `docs/ANALISIS_C.md`,
`docs/ANALISIS_D.md` y `docs/ANALISIS_HOLDOUT.md`. La tabla comparativa del
documento se genera desde `scripts/build_avance5.py` y se valida contra los JSON
con `scripts/check_consistencia.py`. El análisis del holdout se reproduce con
`python eval/analisis_holdout.py`.

## Anexo G. Cobertura OWASP

La matriz se calcula con `python eval/cobertura_owasp.py`, que escribe
`eval/cobertura_owasp.json`. Se usa el CWE que reporta Bandit (`cwe_sast`) y no
la columna `owasp` del dataset. Las tablas siguientes se regeneran desde ese JSON.

**Cobertura del OWASP Top 10 2021**

| Categoría | Nombre | Desarrollo (141) | Holdout (111) |
|---|---|---:|---:|
| A01 | Broken Access Control | 3 | 1 |
| A02 | Cryptographic Failures | 1 | 3 |
| A03 | Injection | 83 | 76 |
| A04 | Insecure Design | 0 | 0 |
| A05 | Security Misconfiguration | 0 | 0 |
| A06 | Vulnerable and Outdated Components | 0 | 0 |
| A07 | Identification and Authentication Failures | 0 | 0 |
| A08 | Software and Data Integrity Failures | 53 | 30 |
| A09 | Security Logging and Monitoring Failures | 0 | 0 |
| A10 | Server Side Request Forgery (SSRF) | 0 | 0 |
| — | Fuera del Top 10 2021 | 1 | 1 |

**Regla, CWE del SAST y categoría**

| Regla | CWE | Categoría | Desarrollo | Holdout |
|---|---|---|---:|---:|
| B102 | CWE-78 | A03 | 7 | 7 |
| B201 | CWE-94 | A03 | 10 | 9 |
| B307 | CWE-78 | A03 | 21 | 27 |
| B404 | CWE-78 | A03 | 16 | 11 |
| B602 | CWE-78 | A03 | 5 | 2 |
| B603 | CWE-78 | A03 | 7 | 3 |
| B605 | CWE-78 | A03 | 11 | 9 |
| B608 | CWE-89 | A03 | 6 | 8 |
| B301 | CWE-502 | A08 | 25 | 15 |
| B403 | CWE-502 | A08 | 28 | 15 |
| B310 | CWE-22 | A01 | 1 | 0 |
| B311 | CWE-330 | A02 | 1 | 3 |
| B104 | CWE-605 | sin categoría | 1 | 0 |
| B108 | CWE-377 | A01 | 2 | 1 |
| B110 | CWE-703 | sin categoría | 0 | 1 |

**Discrepancias entre el mapeo del dataset y las listas oficiales**

El dataset asigna categoría OWASP a 30 CWE; 10 no coinciden con la lista oficial
y 7 de esas 10 están forzadas a A03.

| CWE | Dataset | Oficial | Observación |
|---|---|---|---|
| CWE-119 | A03 | sin categoría | Desbordamiento de búfer; el Top 10 2021 no cubre memoria. |
| CWE-125 | A03 | sin categoría | Lectura fuera de límites; ídem. |
| CWE-190 | A03 | sin categoría | Desbordamiento de entero; ídem. |
| CWE-401 | A03 | sin categoría | Fuga de memoria; ídem. |
| CWE-416 | A03 | sin categoría | Uso después de liberar; ídem. |
| CWE-476 | A03 | sin categoría | Desreferencia de puntero nulo; ídem. |
| CWE-787 | A03 | sin categoría | Escritura fuera de límites; ídem. |
| CWE-362 | A04 | sin categoría | Condición de carrera; no está en A04. |
| CWE-399 | A04 | sin categoría | Gestión de recursos; no está en A04. |
| CWE-269 | A01 | A04 | Gestión de privilegios; A04 la incluye explícitamente. |

**Categorías no medidas y motivo**

| Categoría | Motivo |
|---|---|
| A04 | Requiere diseño y flujo; Bandit no distingue intención. |
| A05 | Depende de la configuración de despliegue, no del código fuente. |
| A06 | Requiere inventario y versiones de dependencias. |
| A07 | Solo credenciales embebidas (B105–B107), fuera del corpus evaluado. |
| A09 | Requiere observar el runtime y los registros. |
| A10 | Bandit no sigue destinos de red. |

El detalle del modelo de amenaza del agente (OWASP Top 10 for LLM Applications
2025 y ASVS 5.0.0) está en `docs/OWASP.md`.
