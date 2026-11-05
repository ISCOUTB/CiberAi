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
python training\prepare_sft.py
python training\train_qlora.py --quant 4bit --epochs 1
python training\export_gguf.py
ollama create qwen2.5-coder-triage -f Modelfile
```

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

Métricas: FPRR (falsos positivos descartados), FNR (alertas reales
descartadas), FOR (falsos positivos entre los descartes), precisión y
exactitud CWE. La meta principal es **FNR ≤ 5 %**; FPRR mide el ahorro de
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
producto se queda en modo asesor.

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
- `docs/PROTOCOLO_HOLDOUT.md`: reglas, comandos y checklist de la evaluación.
- `AVANCE5_PENDIENTES.md`: estado del Sprint 6 y pendientes del Sprint 7.

## Licencia

Uso académico. El dataset base conserva su licencia original (Apache 2.0).
