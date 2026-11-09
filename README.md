# Agente de IA para la revisión de seguridad de código

Herramienta local que combina un analizador estático (Bandit) con un modelo de
lenguaje afinado (Qwen2.5-Coder-1.5B + QLoRA) para hacer *triage* de alertas:
decide si una alerta es una vulnerabilidad real o un falso positivo. El CWE y el
contexto provienen del SAST; el modelo aporta el veredicto y una justificación
breve, que en esta versión es genérica y no reemplaza la revisión humana.

Todo corre en la máquina del usuario: no se envía código a ninguna API externa.

## Estado

- Sprint 5: entrenamiento QLoRA completado (1 época, 1 h 50 min en RTX 4070 Super).
- Sprint 6: modelo fusionado, exportado a GGUF Q4_K_M (940 MB) y registrado en
  Ollama como `qwen2.5-coder-triage`; evaluaciones C y D sobre 141 alertas,
  integración con la CLI y batería funcional completadas.
- Sprint 7: evaluación única sobre el conjunto de verificación reservado
  completada (111 alertas, 65 reales); política B403 implementada y validada
  parcialmente. El holdout confirmó que el FNR de D supera la meta y que el modo
  asesor debe mantenerse.
- Sprint 8: comparación pareada con Qwen base (C0 vs. D), cobertura OWASP
  calculada por el CWE del SAST, arquitectura arc42 con vistas C4 y smoke test
  sobre tres repositorios reales. Ninguna de las tres piezas cambia el modo
  asesor.
- Auditoría de falsos negativos: de las 11 alertas reales que C0 y D descartan,
  6 son ruido de etiqueta (la línea señalada no es el defecto). El FNR de D baja
  de 5,5 % a 3,3 % en desarrollo y de 9,2 % a 3,1 % en el holdout, y la
  diferencia frente a C0 deja de ser significativa. Se reporta como análisis de
  sensibilidad; el resultado pre-registrado del holdout no cambia.

El producto funciona en **modo asesor**: una recomendación `SAFE` marca la
alerta para descarte, pero **nunca la elimina** del reporte. Ante una respuesta
dudosa, inválida o un servicio caído, la alerta se conserva como `SOSPECHOSA`.

## Arquitectura

```
repositorio
   │
   ├─ Bandit (SAST) ──> alertas normalizadas
   │                        │
   │                        ├─ deduplicación por archivo/línea/regla
   │                        ├─ extracción de la función afectada
   │                        └─ contexto para el modelo
   │
   ├─ Ollama + qwen2.5-coder-triage ──> veredicto JSON
   │
   └─ reporte JSON + SARIF (todas las alertas, con o sin descarte recomendado)
```

## Requisitos

- Python 3.9 o superior para la CLI (probado con 3.14).
- Python 3.11 para entrenar (bitsandbytes y PyTorch CUDA).
- [Ollama](https://ollama.com) para ejecutar el modelo.
- GPU NVIDIA para entrenar; para inferencia alcanza CPU, aunque es más lento.

## Inicio rápido

```powershell
# 1. Dependencias de la CLI
pip install bandit requests

# 2. Modelo (una sola vez, ~1 GB)
ollama create qwen2.5-coder-triage -f Modelfile

# 3. Escanear un repositorio
python agente\run.py scan agente\examples\sample_repo --model qwen2.5-coder-triage
```

Salidas en `reportes/reporte.json` y `reportes/hallazgos.sarif`.

Opciones útiles:

```powershell
# Solo SAST, sin modelo
python agente\run.py scan ruta\al\repo --no-llm

# Limitar la cantidad de alertas (útil para pruebas)
python agente\run.py scan ruta\al\repo --max-alerts 20

# Simular Ollama caído (debe conservar todo como SOSPECHOSA)
python agente\run.py scan ruta\al\repo --ollama-url http://localhost:9
```

## Modelo afinado

Artefactos en `training/out/`:

| Artefacto | Tamaño |
|---|---|
| Adaptador LoRA (`qwen-coder-1.5b-lora/`) | 70,5 MB |
| Modelo fusionado (`qwen-coder-1.5b-merged/`) | — |
| GGUF f16 | 2.950 MB |
| GGUF Q4_K_M (`gguf/qwen-coder-1.5b-q4_k_m.gguf`) | 940 MB |

Hashes SHA-256 en `training/out/SHA256SUMS.txt`.

En inferencia, el Q4_K_M ocupa 1.115 MB de VRAM (contexto de 4.096 tokens) y
unos 700 MB de RAM del proceso `llama-server`. La corrida de integración sobre
`examples/sample_repo` tarda 4,8 s por alerta en una GTX 1650.

## Entrenamiento

En Windows nativo, con una GPU de 12 GB o más:

```powershell
# Verificar entorno (instala Python 3.11, PyTorch CUDA y dependencias)
VERIFICAR.bat

# Entrenar, fusionar, exportar a GGUF y registrar en Ollama
ENTRENAR.bat
```

También se puede ejecutar por partes:

```powershell
# Pipeline anterior (alertas sinteticas; corrida registrada de 11.510 ejemplos)
python training\prepare_sft.py
python training\train_qlora.py --quant 4bit --epochs 1

# Pipeline nuevo: alertas reales de Bandit, formato de produccion y perdida
# centrada en la decision (requiere GPU; el adaptador anterior no se toca)
python training\build_bandit_sft.py
python training\train_qlora.py --quant 4bit --epochs 1 --decision-weight 3.0 `
    --train training\data\train_sft_real.jsonl --val training\data\val_sft_real.jsonl `
    --out training\out\qwen-coder-1.5b-lora-v2

python training\export_gguf.py
ollama create qwen2.5-coder-triage -f Modelfile
```

El pipeline nuevo genera 554 ejemplos de entrenamiento y 286 de validación a
partir de 554 y 286 alertas reales de Bandit (todas con alerta, sin
`finding_id`), y aplica el criterio de patrón de `docs/AUDITORIA_FN.md`. La
política de no descarte está pre-registrada en `docs/POLITICA_REGLAS.md`.

Hiperparámetros de la corrida registrada: LoRA r=16, alpha=32, dropout=0,05,
4 bits, lote efectivo 8, 1 época, 1.439 pasos, 11.510 ejemplos de
entrenamiento y 1.000 de validación. Instrucciones detalladas en
`training/LEEME_WINDOWS.md`.

## Evaluación

Conjunto de desarrollo: 141 alertas de Bandit sobre funciones Python del split
de validación (91 reales, 50 falsos positivos). El split de test (17.542
muestras, 300 de ellas Python) se evaluó **una sola vez** en el Sprint 7; produjo
111 alertas (65 reales, 46 falsos positivos). Los resultados completos y las
limitaciones están en `docs/ANALISIS_HOLDOUT.md` y el registro en
`docs/PROTOCOLO_HOLDOUT.md`.

```powershell
python eval\run_eval.py --config A
python eval\run_eval.py --config B --model qwen2.5-coder:1.5b
python eval\run_eval.py --config C --model qwen2.5-coder:1.5b
python eval\run_eval.py --config C0 --model qwen2.5-coder:1.5b
python eval\run_eval.py --config D --model qwen2.5-coder-triage
```

Métricas: FPRR (falsos positivos recomendados para descarte), FNR (alertas
reales recomendadas para descarte), FOR (falsos positivos entre las
recomendadas para descarte), precisión y exactitud CWE. La meta principal es **FNR ≤ 5 %**; FPRR mide el ahorro de
revisión.

Resultados sobre las 141 alertas:

| Configuración | FPRR | FNR | FOR | Precisión | CWE |
|---|---|---|---|---|---|
| A. Solo SAST | 0,0 % | 0,0 % | 0,0 % | 64,5 % | 45,1 % |
| B. Cero-shot (piloto 10) | 75,0 % | 0,0 % | 0,0 % | 85,7 % | 0,0 % |
| C. Contexto + few-shot | 2,0 % | 0,0 % | 0,0 % | 65,0 % | 37,4 % |
| C0. Contexto sin few-shot | 22,0 % | 2,2 % | 15,4 % | 69,5 % | 44,9 % |
| D. Modelo afinado | 48,0 % | 5,5 % | 17,2 % | 76,8 % | 43,0 % |

C y D **no** comparten prompt: C antepone dos ejemplos resueltos y D no. Para
aislar el efecto del ajuste se agregó C0 (modelo base con el mismo formato de
alerta que D, sin few-shot). En desarrollo, D frente a C0 sube el FPRR de 22,0 %
a 48,0 %, pero también el FNR de 2,2 % a 5,5 %. Frente a C, la diferencia es
mayor, pero mezcla modelo y prompt. Como el FNR de D supera la meta de 5 %, el
producto se queda en modo asesor. La auditoría de falsos negativos reduce ese
FNR a 3,3 % (sección «Auditoría de falsos negativos»).

### Holdout (Sprint 7)

Resultados sobre las 111 alertas del test, con el mismo protocolo:

| Configuración | FPRR | FNR | FOR | Precisión | CWE |
|---|---:|---:|---:|---:|---:|
| A. Solo SAST | 0,0 % | 0,0 % | 0,0 % | 58,6 % | 35,4 % |
| C0. Base sin few-shot | 10,9 % | 0,0 % | 0,0 % | 61,3 % | 33,8 % |
| D. Afinado (crudo) | 30,4 % | **9,2 %** | 30,0 % | 64,8 % | 32,2 % |
| D + política B403 | 19,6 % | 3,1 % | 18,2 % | 63,0 % | 30,2 % |

El holdout **no confirma** la meta de FNR: D omite 6 de 65 alertas reales
(9,2 %, IC95 4,3–18,7 %; bootstrap por archivo 1,9–17,9 %). La política B403
rescata 4 casos, pero deja 2 B311 y el IC95 sigue por encima del 5 %. El FPRR
también baja respecto de desarrollo (30,4 % crudo, 19,6 % con la política). Con
65 alertas reales, incluso 0 fallos deja el límite superior del IC95 en 5,6 %:
el diseño no alcanza para demostrar la meta. La conclusión es mantener el modo
asesor, hacer obligatoria la política B403 y **no** agregar B311 después de ver
el holdout. El detalle está en `docs/ANALISIS_HOLDOUT.md`.

### Comparación con Qwen base (C0 vs. D)

C0 y D comparten prompt, conjunto, temperatura y `num_predict`; la única
diferencia es la etiqueta del modelo. Por eso el par C0/D aísla el efecto del
ajuste fino. El análisis empareja las alertas por `id`, aplica McNemar sobre las
discordancias y estima la diferencia con bootstrap agrupado por archivo.

| Conjunto | Configuración | FPRR | FNR | McNemar p |
|---|---|---:|---:|---:|
| Desarrollo | C0 (base) | 22,0 % | 2,2 % | — |
| Desarrollo | D (afinado) | 48,0 % | 5,5 % | 0,0004 |
| Holdout | C0 (base) | 10,9 % | 0,0 % | — |
| Holdout | D (afinado) | 30,4 % | 9,2 % | 0,0015 |

El resultado es un intercambio, no una derrota en ambas métricas: D gana en FPRR
(descarta más ruido) y C0 gana en FNR (omite menos alertas reales). En el
holdout, Δ FPRR = +19,6 puntos (IC95 0,0–38,5) y Δ FNR = +9,2 puntos (IC95
1,8–17,5). El aporte del ajuste es ahorro de revisión, no superioridad sobre el
modelo base. El detalle está en `docs/ANALISIS_C0_VS_D.md`; se reproduce con
`python eval/analisis_c0_vs_d.py`.

### Auditoría de falsos negativos

La etiqueta del conjunto es a nivel de fragmento: si el fragmento es vulnerable,
cualquier alerta de Bandit sobre él cuenta como real, aunque la línea señalada
sea otra. Se auditaron los 12 falsos negativos de C0 y D con un criterio de
patrón (B403 real si hay `pickle.load`/`pickle.loads`; B404 real si acompaña a
`shell=True`); **6 de las 11 omisiones de D son ruido de etiqueta**.

| Conjunto | Modelo | FN brutos | FN reales | Ruido | FNR bruto | FNR ajustado | FPRR ajustado |
|---|---|---:|---:|---:|---:|---:|---:|
| Desarrollo | C0 | 2 | 2 | 0 | 2,2 % | 2,2 % | 22,0 % |
| Desarrollo | D | 5 | 3 | 2 | 5,5 % | 3,3 % | 52,0 % |
| Holdout | C0 | 0 | 0 | 0 | 0,0 % | 0,0 % | 10,9 % |
| Holdout | D | 6 | 2 | 4 | 9,2 % | 3,1 % | 39,1 % |

La diferencia real frente a C0 queda en 1 alerta (desarrollo) y 2 (holdout), y
McNemar sobre alertas reales deja de ser significativo (p = 1,00 y p = 0,50). La
precisión de las recomendaciones de descarte de D sube a 89,7 % y 90,0 %. Es un
análisis de sensibilidad manual y no a ciegas: no reetiqueta el holdout ni
sustituye el resultado pre-registrado. Se reproduce con `python eval/auditar_fn.py`
y se detalla en `docs/AUDITORIA_FN.md`.

## Cobertura OWASP

La cobertura se calcula con el CWE que reporta Bandit, no con la columna `owasp`
del dataset. Se usa el OWASP Top 10 2021 y se reportan como `sin_categoria` los
CWE que no pertenecen a ninguna lista oficial.

| Categoría | Desarrollo (141) | Holdout (111) |
|---|---:|---:|
| A01 Broken Access Control | 3 | 1 |
| A02 Cryptographic Failures | 1 | 3 |
| A03 Injection | 83 | 76 |
| A08 Software and Data Integrity Failures | 53 | 30 |
| Fuera del Top 10 2021 | 1 | 1 |

A03 y A08 concentran más del 95 % de las alertas. A04–A07, A09 y A10 no tienen
alertas medidas porque requieren diseño, configuración de despliegue, inventario
de dependencias, credenciales, telemetría o seguimiento de red. El producto es un
triage de Bandit organizado por OWASP, no un escáner del Top 10 completo. El
modelo de amenaza del agente (OWASP LLM Top 10 2025 y ASVS 5.0.0) y las
discrepancias del mapeo del dataset están en `docs/OWASP.md`; la matriz se
regenera con `python eval/cobertura_owasp.py`.

OWASP también viaja con cada alerta en el producto: `Finding.owasp` guarda la
categoría derivada del CWE del SAST; `reporte.json` incluye `resumen.por_owasp` y
`owasp_nombres`; SARIF añade `properties.owasp` y los tags `OWASP-Axx` y `CWE-xx`;
y la consola muestra el resumen por categoría y una columna por hallazgo. El
mapeo vive en `agente/src/agente_seguridad/owasp.py` y se cubre con pruebas en
`agente/tests/test_agente.py`.

## Arquitectura arc42/C4

La arquitectura está documentada en `docs/ARQUITECTURA_ARC42.md` con la plantilla
arc42 9.1 y vistas C4 de contexto y contenedores. Los diagramas se escriben en
`docs/diagramas/*.mmd` y se renderizan con Mermaid CLI; el `.mmd` es la fuente.
El contrato de decisión —un `SAFE` solo recomienda, nunca elimina— forma parte de
la arquitectura, no es un detalle de implementación.

## Pruebas con repositorios reales y banco sintético

### Repositorios pinneados

Se ejecutó el producto sobre tres repositorios fijados por etiqueta y commit:
`pallets/itsdangerous` 2.2.0, `jpadilla/pyjwt` 2.10.1 y `httpie/cli` 3.2.4. Se
escaneó solo el paquete fuente: 38 alertas por modelo y 0 alertas eliminadas. En
la corrida reproducible del 8 de noviembre, el modelo base recomendó descartar 4
(2 respuestas inválidas quedaron como `SOSPECHOSA`) y D recomendó descartar 34,
sin errores. Una corrida anterior del base había dado 3 `SAFE` y 0 errores; la
diferencia es no determinismo del servidor, no un cambio de política. La
auditoría manual de las 34 recomendaciones de D no encontró descartes
incorrectos. D conservó una alerta real de HTTPie (`requests.get(...,
verify=False)`). No es una evaluación etiquetada y no produce FPRR/FNR; el
detalle está en `docs/SMOKE_REPOS.md`, la repetición en
`docs/CORRIDA_REPOS_REALES.md` y el resumen en `eval/corrida_repos_reales.json`.

La repetición confirma un patrón: D recomienda descartar 34 de 34 alertas de
severidad baja y 0 de las 4 de severidad media o alta. El banco sintético mide
esa hipótesis de forma directa.

### Banco sintético etiquetado

`eval/sinteticas/casos.jsonl` contiene 26 alertas nuevas con etiqueta a nivel de
alerta: 14 reales y 12 falsos positivos, repartidas en 13 reglas de Bandit. Cada
regla tiene casos reales y falsos para romper la correlación regla→veredicto. No
se usa el holdout.

| Métrica | Base | D | IC95 de D |
|---|---:|---:|---:|
| FPRR (FP recomendados para descarte) | 0,0 % | 58,3 % | 32,0–80,7 % |
| FNR (reales recomendados para descarte) | 0,0 % | 35,7 % | 16,3–61,2 % |
| Exactitud de decisión | 53,8 % | 61,5 % | 42,5–77,6 % |
| Precisión de los descartes | n/a | 58,3 % | 32,0–80,7 % |

El base no descarta nada y su FPRR de 0 % no es un mérito. D acierta 7 de 12
falsos positivos, pero descarta 5 de 14 alertas reales. Con n tan pequeño, sus
intervalos son amplios: el FNR de D supera la meta de 5 % incluso en su límite
inferior (16,3 %), pero la mejora de exactitud frente al base (+7,7 puntos) no es
estadísticamente demostrable. Su decisión se reproduce al 100 % con la regla «`SAFE` si la severidad
del SAST es baja», y sus explicaciones son plantillas idénticas: en este banco no
usa el contexto del código. El resultado respalda el modo asesor y desaconseja el
descarte automático. Detalle en `docs/BANCO_SINTETICO.md`, interpretación en
`docs/ANALISIS_BANCO_SINTETICO.md`; se reproduce con
`python eval/banco_sintetico.py`.

## Estructura del proyecto

```
agente/            CLI, SAST, cliente de Ollama, reportes y pruebas unitarias
dataset/           dataset base y particiones (train/val/test)
eval/              conjunto de evaluación, script de métricas y resultados
training/          preparación SFT, QLoRA, exportación GGUF y scripts de Windows
scripts/           generadores de los documentos (Avances 1–5)
reportes/          salidas JSON/SARIF y figuras
```

## Pruebas

```powershell
python -m unittest discover -s agente\tests -v
```

Batería funcional y de robustez: `eval/pruebas/LEEME.md` (repo vacío, archivo
vacío, sintaxis inválida, otro lenguaje, repositorio grande, Ollama caído y
prompt injection).

## Limitaciones conocidas

- La partición es aleatoria por función, no por repositorio; el dataset no tiene
  identificador de proyecto. El holdout se evaluó sin reagrupar. La comparación
  exacta de hashes normalizados contra train y validación dio 0 coincidencias,
  pero no se midieron casi-duplicados.
- El CWE que devuelve el modelo copia el CWE reportado por el SAST: 59 de 59
  alertas reales conservadas en el holdout. No se debe usar como clasificador
  independiente; el producto conserva el CWE del SAST.
- El FNR de D en desarrollo fue 5,5 % (5/91, todas B403). En el holdout subió a
  **9,2 % (6/65)**: 4 B403 y 2 B311. La política B403 lo baja a 3,1 % (IC95
  0,8–10,5 %), pero no alcanza para afirmar ≤ 5 %. El modo asesor se mantiene y
  no se agrega B311 después de ver el holdout.
- Con 65 alertas reales, el holdout no tiene potencia para demostrar un FNR
  ≤ 5 %: incluso 0 fallos deja el IC95 en 5,6 %.
- Las explicaciones de D colapsaron a plantillas: 11 explicaciones, 8 vectores y
  2 correcciones para 111 alertas; 91 de 91 `VULNERABLE` comparten la misma
  corrección. D sirve para triage, no como generador de explicaciones técnicas.
- La pérdida de validación de la corrida original quedó en `nan` por
  truncamiento de ejemplos largos; ya corregido en `training/train_qlora.py`.
- Una alerta B102 de 1.818 caracteres hizo entrar en bucle al modelo base y
  agotó el timeout de 180 s. El cliente del producto y el arnés de evaluación
  ahora usan `num_predict: 512`; con el límite, la misma alerta responde en
  8,2 s y el runner no sigue generando tras el timeout.
- El prompt de evaluación (`eval/run_eval.py`) coincide con el de entrenamiento,
  pero no es idéntico al prompt de producto (`agente/src/agente_seguridad/triage.py`).
  C0 y D comparten prompt, así que la comparación no se ve afectada; el FPRR y el
  FNR reportados no describen exactamente la CLI. Alinear ambos prompts exige un
  conjunto nuevo, no el holdout cerrado.
- El smoke test con repositorios usa 38 alertas por modelo, tres repos y una
  auditoría de una sola persona. Los 34 `SAFE` de D fueron correctos en esa
  muestra, pero no demuestran que el descarte automático sea seguro.

## Documentación

- `docs/PLAN_DOCUMENTO_FINAL.md`: mapa de la memoria del Sprint 8.
- `docs/BORRADOR_INTRODUCCION.md`: problema, pregunta, hipótesis y objetivos.
- `docs/BORRADOR_METODOLOGIA.md`: dataset, ajuste, exportación y protocolo de evaluación.
- `docs/BORRADOR_ESTADO_ARTE.md`: estado del arte con referencias verificadas.
- `docs/BORRADOR_DISCUSION.md`: discusión de resultados y amenazas a la validez.
- `docs/BORRADOR_CONCLUSIONES.md`: respuesta a la hipótesis, aportes y trabajo futuro.
- `docs/BORRADOR_ANEXOS.md`: reproducción, artefactos, hashes y prompts.
- `docs/ANALISIS_C.md`, `docs/ANALISIS_C0.md` y `docs/ANALISIS_D.md`: lectura
  detallada de las corridas de desarrollo.
- `docs/ANALISIS_HOLDOUT.md`: resultados, intervalos, falsos negativos y límites
  de la evaluación única.
- `docs/ANALISIS_C0_VS_D.md`: comparación pareada con Qwen base, McNemar e
  intervalos por bootstrap.
- `docs/OWASP.md`: cobertura del Top 10 2021, discrepancias del dataset, LLM Top
  10 2025 y ASVS 5.0.0 como checklist parcial.
- `docs/ARQUITECTURA_ARC42.md`: arquitectura arc42 9.1 con vistas C4; diagramas
  en `docs/diagramas/`.
- `docs/SMOKE_REPOS.md`: smoke test sobre tres repositorios reales y auditoría
  manual de las recomendaciones de descarte.
- `docs/CORRIDA_REPOS_REALES.md`: repetición reproducible del smoke con los dos
  modelos, desglose OWASP y decisión por severidad.
- `docs/BANCO_SINTETICO.md`: resultados del banco de 26 casos etiquetados.
- `docs/ANALISIS_BANCO_SINTETICO.md`: interpretación del banco, atajo de
  severidad y límites.
- `docs/PROTOCOLO_HOLDOUT.md`: reglas, comandos y checklist de la evaluación.
- `AVANCE5_PENDIENTES.md`: estado del Sprint 8 y pendientes.
- `scripts/check_consistencia.py`: valida las tablas del Avance 5 y de los
  documentos contra los JSON de resultados.

## Licencia

Uso académico. El dataset base conserva su licencia original (Apache 2.0).
