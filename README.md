# CiberAi — Agente local de triage de seguridad para Python

CiberAi es un agente local que analiza código Python con escáneres SAST (Bandit y un motor OWASP propio) y un modelo de lenguaje ejecutado en [Ollama](https://ollama.com). Su objetivo es reducir el ruido de las alertas: para cada hallazgo decide si es una vulnerabilidad real (`VULNERABLE`) o un falso positivo recomendado para descarte (`SAFE`).

> **Modo asesor obligatorio:** un veredicto `SAFE` solo **recomienda** descartar la alerta; **nunca la elimina** del reporte. Si el modelo no responde o la respuesta es dudosa, la alerta se conserva como `SOSPECHOSA`.

Todo corre en tu máquina: no se envía código a APIs externas.

---

## Flujo de trabajo

![Flujo de trabajo de CiberAi](assets/workflow.png)

1. **Entrada:** le das una carpeta con código Python (`agente\run.py scan <ruta>`).
2. **Detección:** Bandit y/o el escáner OWASP propio encuentran patrones de riesgo.
3. **Normalización:** cada alerta se convierte a un objeto común, se le asigna un ID, se deduplica y se extrae su contexto (función y líneas cercanas).
4. **Triage:** el modelo local en Ollama analiza cada alerta y emite un veredicto JSON.
5. **Salida:** se generan `reporte.json` y `hallazgos.sarif` con todas las alertas y sus recomendaciones.
6. **Visualización:** puedes consultar los resultados en consola, en el dashboard web o en el TUI de pantalla completa.

---

## Estructura del proyecto

```text
CiberAi/
├── agente/                         # Producto: CLI, SAST, LLM, reportes y tests
│   ├── run.py                      # Punto de entrada principal
│   ├── chat.py                     # Interfaz interactiva de terminal (REPL)
│   ├── server.py                   # Servidor web del dashboard
│   ├── tui.py                      # TUI de pantalla completa
│   └── src/agente_seguridad/
│       ├── cli.py                  # Argumentos y orquestación del escaneo
│       ├── triage.py               # Prompt, veredicto y validación
│       ├── report.py               # Salida JSON/SARIF y resumen de consola
│       ├── llm/                    # Cliente de Ollama y auditoría LLM-first
│       ├── sast/                   # Bandit, escáner OWASP, SARIF, cargador de reportes
│       └── tests/                  # Pruebas unitarias
├── frontend/                       # Dashboard web (React + Vite)
│   └── src/...
├── dataset/                        # Dataset y splits (no versionados)
├── eval/                           # Evaluaciones, resultados y bancos de prueba
├── training/                       # Entrenamiento QLoRA y exportación GGUF
├── scripts/                        # Generadores de documentación y gráficas
├── docs/                           # Documentación del TFG
├── reportes/                       # Salidas JSON/SARIF (no versionadas)
└── Modelfile                       # Definición del modelo para Ollama
```

---

## Instalación

### 1. Requisitos

- **Python 3.10+** (probado con 3.11).
- **Ollama** instalado y corriendo en `http://localhost:11434`.
- (Opcional) GPU NVIDIA para entrenar; para inferencia basta CPU.

### 2. Crear el entorno virtual e instalar dependencias

```powershell
cd C:\Users\samsam\Documents\CiberAi

# Crear entorno virtual
python -m venv .venv

# Activar entorno
.venv\Scripts\activate

# Instalar la CLI y dependencias base
python -m pip install -e agente

# Para el dashboard web
python -m pip install -e agente[server]

# Para el TUI
python -m pip install -e agente[tui]
```

### 3. Descargar el modelo en Ollama

El modelo por defecto es `qwen2.5-coder:1.5b` (~1 GB). Si tienes el GGUF afinado, usa el `Modelfile`; si no, el base ya funciona:

```powershell
ollama pull qwen2.5-coder:1.5b
```

Verifica que esté disponible:

```powershell
ollama list
```

---

## Cómo usar el proyecto

### Escanear un repositorio

El argumento `target` es la carpeta que quieres analizar.

```powershell
# Análisis completo: Bandit + OWASP + triage con modelo
python agente\run.py scan agente\examples\sample_repo

# Con modelo explícito
python agente\run.py scan agente\examples\sample_repo --model qwen2.5-coder:1.5b

# Sin modelo (solo SAST)
python agente\run.py scan agente\examples\sample_repo --no-llm
```

### Elegir escáner

```powershell
# Bandit + OWASP (por defecto)
python agente\run.py scan agente\examples\sample_repo --scanner both

# Solo Bandit
python agente\run.py scan agente\examples\sample_repo --scanner bandit --no-llm

# Solo escáner OWASP propio (sin Bandit)
python agente\run.py scan agente\examples\sample_repo --scanner owasp --no-llm

# Modelo primero: el LLM lee el código y detecta por sí mismo
python agente\run.py scan agente\examples\sample_repo --scanner llm --model qwen2.5-coder:1.5b

# Todo: LLM primero + Bandit + OWASP
python agente\run.py scan agente\examples\sample_repo --scanner all --model qwen2.5-coder:1.5b
```

### Escanear cualquier carpeta

```powershell
python agente\run.py scan C:\Users\samsam\Documents\mi_proyecto
python agente\run.py scan C:\Users\samsam\Documents\mi_proyecto\src --scanner owasp --no-llm
```

### Opciones útiles

```powershell
# Limitar alertas (útil para pruebas)
python agente\run.py scan agente\examples\sample_repo --max-alerts 10

# Cambiar directorio de salida
python agente\run.py scan agente\examples\sample_repo --out reportes\mi_scan

# Desactivar colores en consola
python agente\run.py scan agente\examples\sample_repo --no-color

# Simular Ollama caído (conserva todo como SOSPECHOSA)
python agente\run.py scan agente\examples\sample_repo --ollama-url http://localhost:9
```

### Reutilizar un reporte existente

```powershell
# Cargar hallazgos de un reporte previo sin volver a ejecutar el SAST
python agente\run.py scan agente\examples\sample_repo `
  --from-report reportes\reporte.json --no-llm

# Con triage por modelo
python agente\run.py scan agente\examples\sample_repo `
  --from-report reportes\reporte.json --model qwen2.5-coder:1.5b
```

Acepta:
- `reporte.json` generado por esta CLI.
- `hallazgos.sarif` generado por esta CLI.
- Salida JSON cruda de Bandit (`{"results": [...]}`).
- Una lista plana de hallazgos.

---

## Interfaces adicionales

### Interfaz interactiva (REPL)

```powershell
python agente\chat.py
```

Ejemplo de sesión:

```text
agente> help
agente> scan agente/examples/sample_repo --scanner owasp --no-llm
agente> report
agente> rescan
agente> exit
```

### Dashboard web

1. Construye el frontend (solo la primera vez, o tras cambiarlo):

```powershell
cd frontend
npm install
npm run build
cd ..
```

2. Levanta el servidor:

```powershell
python agente\server.py
```

3. Abre en el navegador:

```text
http://127.0.0.1:8000
```

Desde el dashboard puedes escanear, ver el resumen, filtrar hallazgos y descargar el SARIF.

### TUI de pantalla completa

```powershell
python agente\tui.py
python agente\tui.py reportes\reporte.json
```

Teclas:

| Tecla | Acción |
|---|---|
| `↑` / `↓` | Moverse entre hallazgos |
| `Enter` | Ver detalle |
| `r` | Recargar reporte |
| `q` / `Esc` | Salir |

---

## Tests

```powershell
python -m unittest discover -s agente\tests -v
```

Actualmente pasan **44 tests**.

---

## Modo asesor

CiberAi nunca elimina una alerta del reporte. Sus veredictos son:

- `VULNERABLE` → alerta real, se conserva.
- `SAFE` → recomendación de descarte, pero la alerta sigue en JSON/SARIF.
- `SOSPECHOSA` → respuesta inválida o modelo no disponible; se conserva para revisión humana.

---

## Documentación adicional

El resto de la documentación del TFG vive en `docs/`:

- `docs/PLAN_DOCUMENTO_FINAL.md`: mapa de la memoria.
- `docs/BORRADOR_INTRODUCCION.md`: problema, hipótesis y objetivos.
- `docs/BORRADOR_METODOLOGIA.md`: dataset, entrenamiento y evaluación.
- `docs/ANALISIS_HOLDOUT.md`: resultados del holdout y modo asesor.
- `docs/OWASP.md`: cobertura OWASP Top 10 2021.
- `docs/ARQUITECTURA_ARC42.md`: arquitectura con vistas C4.

---

## Licencia

Uso académico. El dataset base conserva su licencia original (Apache 2.0).
