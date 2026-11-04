# Entrenamiento en Windows (para la PC con RTX 4070 Super)

Esta carpeta queda lista para que tu compañero **solo copie el proyecto, ejecute un
script y espere**. No hace falta API ni subir el código a ningún servicio.

## Qué hace el script

`training/entrenar_windows.ps1` ejecuta el flujo completo:

1. Detecta o instala **Python 3.11**.
2. Crea el entorno virtual `.venv`.
3. Instala **PyTorch con CUDA** y las dependencias de `training/requirements.txt`.
4. Verifica que la GPU NVIDIA esté disponible.
5. Genera los datos SFT si faltan (`training/prepare_sft.py`).
6. Entrena **Qwen2.5-Coder-1.5B-Instruct con QLoRA 4-bit**.
7. Fusiona el adaptador LoRA con el modelo base.
8. Convierte el modelo fusionado a GGUF f16 con el conversor oficial de
   `llama.cpp` y lo cuantiza a **GGUF Q4_K_M** con `llama-quantize`.
9. Si Ollama está instalado, registra el modelo como `qwen2.5-coder-triage`.

## Requisitos en la PC

- Windows 10 u 11.
- GPU NVIDIA con driver actualizado (RTX 4070 Super de 12 GB es suficiente).
- 32 GB de RAM recomendados.
- **35–50 GB libres** en disco.
- Conexión a internet para descargar Python, PyTorch, el modelo base y
  `llama.cpp` (código fuente y un binario de `llama-quantize` de ~25 MB).

No se necesita cuenta de Hugging Face ni clave de API. El modelo
`Qwen/Qwen2.5-Coder-1.5B-Instruct` es público.

## Cómo ejecutarlo

La forma más simple es hacer doble clic en los archivos de la raíz del proyecto:

- **`VERIFICAR.bat`**: comprueba Python, CUDA y los datos (no entrena).
- **`ENTRENAR.bat`**: hace todo el proceso y deja el modelo en Ollama.

También se puede ejecutar desde PowerShell:

1. Copiar la carpeta completa del proyecto a la PC, por ejemplo:
   `C:\proyecto-ing`.
   Alcanza con incluir `training/data/` (ya trae los 11.510 + 1.000 ejemplos).
   Si se quiere regenerar, incluir también `dataset/splits/`.
2. Abrir **PowerShell** en esa carpeta.
3. Verificar el entorno antes de entrenar:

   ```powershell
   powershell -ExecutionPolicy Bypass -File training\entrenar_windows.ps1 -CheckOnly
   ```

   La primera vez también instala Python, PyTorch y las dependencias (15–30
   minutos); después el chequeo tarda segundos. Debe terminar con
   `Chequeo completado`.
4. Ejecutar el entrenamiento:

   ```powershell
   powershell -ExecutionPolicy Bypass -File training\entrenar_windows.ps1
   ```

   La primera vez instala todo y puede tardar 15–30 minutos antes de empezar a
   entrenar.
5. Dejar la PC conectada y sin suspensión. El script ya desactiva la suspensión.
6. El entrenamiento tarda aproximadamente **2–4 horas** con esta GPU.

## Salidas

| Archivo | Contenido |
|---|---|
| `training/out/qwen-coder-1.5b-lora/` | Adaptador LoRA (liviano) |
| `training/out/qwen-coder-1.5b-merged/` | Modelo fusionado en safetensors |
| `training/out/gguf/qwen-coder-1.5b-f16.gguf` | GGUF intermedio sin cuantizar (~3 GB) |
| `training/out/gguf/qwen-coder-1.5b-q4_k_m.gguf` | Modelo listo para Ollama (~1 GB) |
| `training/llama-bin/` | Binario de `llama-quantize` descargado automáticamente |
| `training/out/train.log` | Log completo del entrenamiento |
| `Modelfile` (raíz del proyecto) | Archivo para registrar el modelo en Ollama |

Para llevarlo de vuelta alcanza con copiar el `.gguf` (o el adaptador si se
quiere reexportar en la otra PC).

## Opciones útiles

Entrenar sin exportar todavía:

```powershell
powershell -ExecutionPolicy Bypass -File training\entrenar_windows.ps1 -SkipExport
```

Si se queda sin VRAM:

```powershell
powershell -ExecutionPolicy Bypass -File training\entrenar_windows.ps1 -MaxSeq 1024
```

Forzar la regeneración de los datos SFT:

```powershell
powershell -ExecutionPolicy Bypass -File training\entrenar_windows.ps1 -ForceData
```

No registrar automáticamente en Ollama:

```powershell
powershell -ExecutionPolicy Bypass -File training\entrenar_windows.ps1 -NoOllama
```

## Notas importantes

- Los datos SFT actuales tienen **11.510 ejemplos de entrenamiento y 1.000 de
  validación**, no 12.000: el generador mantiene el balance 50/50 y solo hay
  5.755 funciones vulnerables después de filtrar prompts largos. Es la cifra
  real que debe figurar en el documento.
- Si `bitsandbytes` falla en Windows nativo, el plan B es WSL2 con Ubuntu. El
  script actual está pensado para Windows nativo.
- El conversor oficial solo genera GGUF f16/bf16/q8_0. Por eso el script
  convierte a f16 y después usa `llama-quantize` para obtener Q4_K_M. Si la
  descarga automática falla, se puede compilar `llama.cpp` o bajar un binario
  de <https://github.com/ggml-org/llama.cpp/releases> y pasarlo con
  `--quantize-bin`. La ruta del binario también se puede fijar en la variable
  de entorno `LLAMA_QUANTIZE`.
- Si Ollama no está instalado, el script igual exporta el GGUF. Después se
  instala Ollama y se ejecuta:

  ```powershell
  ollama create qwen2.5-coder-triage -f Modelfile
  ```

- Para probar el modelo con el agente:

  ```powershell
  python agente\run.py scan agente\examples\sample_repo --model qwen2.5-coder-triage
  ```

## Problemas frecuentes

- **`py.exe : [ERROR] No runtime installed that matches 3.11`**: aparecía
  cuando solo estaba instalado Python 3.14. Ya está corregido: el script
  consulta los runtimes con `py -0p` y, si falta 3.11, lo instala con `winget`
  o con `py install 3.11`. Si ninguna de las dos vías funciona, instalar
  Python 3.11 desde <https://www.python.org/downloads/> marcando
  **Add python.exe to PATH** y repetir.
- **`winget` no está disponible**: el script prueba el lanzador `py`; si
  tampoco sirve, muestra el enlace de descarga manual.
- **La verificación termina con error de GPU**: revisar el driver NVIDIA con
  `nvidia-smi`. Sin GPU visible no se puede entrenar; el resto del chequeo
  (Python y datos) igual queda hecho.
