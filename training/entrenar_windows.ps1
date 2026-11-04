#Requires -Version 5.1
<#
.SYNOPSIS
    Instala dependencias, genera los datos SFT y entrena Qwen2.5-Coder-1.5B con QLoRA en Windows.

.DESCRIPTION
    Pensado para que una sola persona ejecute el script en la PC con GPU NVIDIA.
    Hace todo el flujo: Python 3.11, entorno virtual, PyTorch CUDA, datos SFT,
    entrenamiento, fusion del adaptador, exportacion a GGUF y registro en Ollama.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File training\entrenar_windows.ps1

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File training\entrenar_windows.ps1 -SkipExport
#>
[CmdletBinding()]
param(
    [int]$Epochs = 1,
    [int]$MaxSeq = 2048,
    [int]$BatchSize = 1,
    [int]$GradAccum = 8,
    [switch]$SkipSetup,
    [switch]$SkipExport,
    [switch]$ForceData,
    [switch]$NoOllama,
    [switch]$CheckOnly
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Write-Step([string]$Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Fail([string]$Message) {
    Write-Host ""
    Write-Host "ERROR: $Message" -ForegroundColor Red
    exit 1
}

# Ejecuta un comando nativo sin que su salida de error (stderr) aborte el script.
# Con $ErrorActionPreference = "Stop", PowerShell 5.1 convierte cualquier linea de
# stderr en un error terminante cuando se redirige, incluso con 2>$null. Por eso
# se baja la preferencia solo durante la llamada y se devuelve la salida junto con
# el codigo de salida.
function Invoke-Native {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments
    )
    if (-not (Get-Command $FilePath -ErrorAction SilentlyContinue)) {
        return [pscustomobject]@{ Output = @(); Code = 127 }
    }
    $previous = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $output = & $FilePath @Arguments 2>&1
        $code = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previous
    }
    [pscustomobject]@{ Output = $output; Code = $code }
}

function Find-Python311 {
    $pyCmd = Get-Command py -ErrorAction SilentlyContinue
    if ($pyCmd) {
        # Primero se listan los runtimes instalados: asi no se invoca -3.11
        # cuando no existe (el lanzador nuevo imprime un error en stderr).
        $listed = Invoke-Native "py" "-0p"
        $has311 = ($listed.Code -eq 0) -and ($listed.Output -match "3\.11")
        if ($has311) {
            $probe = Invoke-Native "py" "-3.11" "-c" "import sys; print(sys.executable)"
            $path = ($probe.Output | Where-Object { $_ -and $_.ToString().Trim() -ne "" } | Select-Object -Last 1)
            if ($probe.Code -eq 0 -and $path) {
                return $path.ToString().Trim()
            }
        }
    }
    $candidates = @(
        (Join-Path $env:LOCALAPPDATA "Programs\Python\Python311\python.exe"),
        "C:\Program Files\Python311\python.exe",
        "C:\Python311\python.exe"
    )
    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) { return $candidate }
    }
    $found = Get-ChildItem (Join-Path $env:LOCALAPPDATA "Programs\Python") -Filter python.exe -Recurse -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -match "Python311" } |
        Select-Object -First 1
    if ($found) { return $found.FullName }
    return $null
}

Write-Host "============================================================" -ForegroundColor Green
Write-Host " Entrenamiento Qwen2.5-Coder-1.5B + QLoRA (Windows)" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host "Repositorio: $Root"

$drive = (Get-Item $Root).PSDrive
if ($drive) {
    $freeGB = [math]::Round((Get-PSDrive $drive.Name).Free / 1GB, 1)
    Write-Host "Espacio libre en $($drive.Name): $freeGB GB"
    if ($freeGB -lt 35) {
        Write-Host "ADVERTENCIA: se recomiendan al menos 35 GB libres para modelos y checkpoints." -ForegroundColor Yellow
    }
}

# ---------------------------------------------------------------------------
# 1. Python 3.11
# ---------------------------------------------------------------------------
Write-Step "Buscando Python 3.11"
$python = Find-Python311
if (-not $python) {
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if ($winget) {
        Write-Host "Python 3.11 no esta instalado. Instalando con winget..." -ForegroundColor Yellow
        Invoke-Native "winget" "install" "-e" "--id" "Python.Python.3.11" "--accept-source-agreements" "--accept-package-agreements" | Out-Null
        $python = Find-Python311
    }
    if (-not $python) {
        $pyCmd = Get-Command py -ErrorAction SilentlyContinue
        if ($pyCmd) {
            Write-Host "Intentando instalar Python 3.11 con el lanzador py..." -ForegroundColor Yellow
            Invoke-Native "py" "install" "3.11" | Out-Null
            $python = Find-Python311
        }
    }
    if (-not $python) {
        Fail "No se pudo instalar Python 3.11. Instalalo manualmente desde https://www.python.org/downloads/ (marcar 'Add python.exe to PATH') y vuelve a ejecutar."
    }
}
Write-Host "Python: $python"

$Venv = Join-Path $Root ".venv"
$VenvPy = Join-Path $Venv "Scripts\python.exe"
if (-not (Test-Path $VenvPy)) {
    Write-Step "Creando entorno virtual .venv"
    $venv = Invoke-Native $python "-m" "venv" $Venv
    if ($venv.Code -ne 0) { Fail "No se pudo crear el entorno virtual." }
}

# ---------------------------------------------------------------------------
# 2. Dependencias
# ---------------------------------------------------------------------------
if (-not $SkipSetup) {
    Write-Step "Actualizando pip"
    & $VenvPy -m pip install --upgrade pip wheel
    if ($LASTEXITCODE -ne 0) { Fail "No se pudo actualizar pip." }

    $cudaCheck = Invoke-Native $VenvPy "-c" "import torch; print('1' if torch.cuda.is_available() else '0')"
    $cudaOk = ($cudaCheck.Code -eq 0) -and ($cudaCheck.Output | Where-Object { "$_".Trim() -eq "1" })
    if (-not $cudaOk) {
        Write-Step "Instalando PyTorch con CUDA (puede tardar varios minutos)"
        & $VenvPy -m pip install torch --index-url https://download.pytorch.org/whl/cu124
        if ($LASTEXITCODE -ne 0) {
            Write-Host "No se pudo instalar cu124; probando cu121..." -ForegroundColor Yellow
            & $VenvPy -m pip install torch --index-url https://download.pytorch.org/whl/cu121
            if ($LASTEXITCODE -ne 0) { Fail "No se pudo instalar PyTorch con CUDA." }
        }
    } else {
        Write-Host "PyTorch con CUDA ya esta instalado."
    }

    Write-Step "Instalando dependencias de training"
    & $VenvPy -m pip install -r (Join-Path $Root "training\requirements.txt")
    if ($LASTEXITCODE -ne 0) { Fail "No se pudieron instalar las dependencias de training." }
}

# ---------------------------------------------------------------------------
# 3. Verificacion de GPU
# ---------------------------------------------------------------------------
Write-Step "Verificando GPU"
$gpuCheck = Invoke-Native $VenvPy "-c" "import torch; ok=torch.cuda.is_available(); print('torch', torch.__version__); print('cuda', ok); print('gpu', torch.cuda.get_device_name(0) if ok else 'NO DISPONIBLE'); raise SystemExit(0 if ok else 1)"
$gpuCheck.Output | ForEach-Object { Write-Host "$_" }
if ($gpuCheck.Code -ne 0) {
    Fail "PyTorch no detecta la GPU. Actualiza el driver NVIDIA y verifica que la GPU sea compatible con CUDA."
}

# ---------------------------------------------------------------------------
# 4. Datos SFT
# ---------------------------------------------------------------------------
$Train = Join-Path $Root "training\data\train_sft.jsonl"
$Val = Join-Path $Root "training\data\val_sft.jsonl"
$TrainCount = if (Test-Path $Train) { (Get-Content $Train | Measure-Object -Line).Lines } else { 0 }
$ValCount = if (Test-Path $Val) { (Get-Content $Val | Measure-Object -Line).Lines } else { 0 }

if ($ForceData -or $TrainCount -lt 10000 -or $ValCount -lt 800) {
    Write-Step "Generando datos SFT (11.510 train / 1.000 val)"
    & $VenvPy (Join-Path $Root "training\prepare_sft.py")
    if ($LASTEXITCODE -ne 0) { Fail "prepare_sft.py fallo." }
    $TrainCount = (Get-Content $Train | Measure-Object -Line).Lines
    $ValCount = (Get-Content $Val | Measure-Object -Line).Lines
}
Write-Host "Datos: $TrainCount train | $ValCount val"
if ($TrainCount -lt 10000) {
    Fail "Muy pocos ejemplos de entrenamiento ($TrainCount). Revisa dataset\splits y vuelve a ejecutar con -ForceData."
}

if ($CheckOnly) {
    Write-Host ""
    Write-Host "Chequeo completado: Python, CUDA y datos estan listos." -ForegroundColor Green
    Write-Host "Para entrenar, ejecuta el script sin -CheckOnly."
    exit 0
}

# ---------------------------------------------------------------------------
# 5. Entrenamiento
# ---------------------------------------------------------------------------
Write-Step "Desactivando suspension de la PC"
Invoke-Native "powercfg" "/change" "standby-timeout-ac" "0" | Out-Null
Invoke-Native "powercfg" "/change" "hibernate-timeout-ac" "0" | Out-Null

$OutDir = Join-Path $Root "training\out"
New-Item -ItemType Directory -Force $OutDir | Out-Null
$Log = Join-Path $OutDir "train.log"
$Adapter = Join-Path $OutDir "qwen-coder-1.5b-lora"

Write-Step "Entrenando QLoRA"
Write-Host "Log: $Log"
$env:PYTHONUNBUFFERED = "1"
$trainArgs = @(
    (Join-Path $Root "training\train_qlora.py"),
    "--quant", "4bit",
    "--epochs", "$Epochs",
    "--max-seq", "$MaxSeq",
    "--batch-size", "$BatchSize",
    "--grad-accum", "$GradAccum",
    "--out", $Adapter
)
$previousPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
try {
    & $VenvPy @trainArgs 2>&1 | Tee-Object -FilePath $Log
    $trainCode = $LASTEXITCODE
} finally {
    $ErrorActionPreference = $previousPreference
}
if ($trainCode -ne 0) { Fail "El entrenamiento fallo. Revisa $Log" }

if (-not (Test-Path (Join-Path $Adapter "adapter_config.json"))) {
    Fail "No se encontro el adaptador en $Adapter"
}
Write-Host ""
Write-Host "Adaptador guardado en: $Adapter" -ForegroundColor Green

# ---------------------------------------------------------------------------
# 6. Exportacion a GGUF y Ollama
# ---------------------------------------------------------------------------
if (-not $SkipExport) {
    Write-Step "Preparando llama.cpp"
    $LlamaCpp = Join-Path $Root "training\llama.cpp"
    $LlamaTag = "v0.8.0"
    $Converter = Join-Path $LlamaCpp "convert_hf_to_gguf.py"
    if (-not (Test-Path $Converter)) {
        if (Test-Path $LlamaCpp) { Remove-Item -Recurse -Force $LlamaCpp }
        $git = Get-Command git -ErrorAction SilentlyContinue
        $cloned = $false
        if ($git) {
            & git clone --depth 1 --branch $LlamaTag https://github.com/ggml-org/llama.cpp $LlamaCpp
            if ($LASTEXITCODE -eq 0) { $cloned = $true }
        }
        if (-not $cloned) {
            Write-Host "Descargando llama.cpp en ZIP..." -ForegroundColor Yellow
            $Zip = Join-Path $OutDir "llama.cpp.zip"
            Invoke-WebRequest -Uri "https://github.com/ggml-org/llama.cpp/archive/refs/tags/$LlamaTag.zip" -OutFile $Zip
            Expand-Archive -Path $Zip -DestinationPath $OutDir -Force
            $Extracted = Join-Path $OutDir "llama.cpp-0.8.0"
            if (Test-Path $LlamaCpp) { Remove-Item -Recurse -Force $LlamaCpp }
            Move-Item $Extracted $LlamaCpp
            Remove-Item $Zip -Force
        }
    }

    $Gguf = Join-Path $OutDir "gguf\qwen-coder-1.5b-q4_k_m.gguf"
    $GgufF16 = Join-Path $OutDir "gguf\qwen-coder-1.5b-f16.gguf"
    $QuantTools = Join-Path $Root "training\llama-bin"
    Write-Step "Fusionando adaptador, convirtiendo a GGUF y cuantizando a Q4_K_M"
    Write-Host "El primer intento descarga llama-quantize (unos 25 MB)."
    & $VenvPy (Join-Path $Root "training\export_gguf.py") `
        --adapter $Adapter `
        --out (Join-Path $OutDir "qwen-coder-1.5b-merged") `
        --f16-out $GgufF16 `
        --gguf-out $Gguf `
        --quant Q4_K_M `
        --llama-cpp $LlamaCpp `
        --tools-dir $QuantTools
    if ($LASTEXITCODE -ne 0) { Fail "La exportacion a GGUF fallo." }
    Write-Host "GGUF: $Gguf" -ForegroundColor Green

    $Modelfile = Join-Path $Root "Modelfile"
    "FROM ./training/out/gguf/qwen-coder-1.5b-q4_k_m.gguf" | Set-Content -Encoding ASCII $Modelfile
    if (-not $NoOllama) {
        $ollama = Get-Command ollama -ErrorAction SilentlyContinue
        if ($ollama) {
            Write-Step "Registrando el modelo en Ollama"
            & ollama create qwen2.5-coder-triage -f $Modelfile
            if ($LASTEXITCODE -ne 0) {
                Write-Host "No se pudo registrar en Ollama. Abre Ollama y ejecuta:" -ForegroundColor Yellow
                Write-Host "  ollama create qwen2.5-coder-triage -f `"$Modelfile`"" -ForegroundColor Yellow
            } else {
                Write-Host "Modelo registrado: qwen2.5-coder-triage" -ForegroundColor Green
            }
        } else {
            Write-Host "Ollama no esta instalado. Instalalo desde https://ollama.com y ejecuta:" -ForegroundColor Yellow
            Write-Host "  ollama create qwen2.5-coder-triage -f `"$Modelfile`"" -ForegroundColor Yellow
        }
    }
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host " Proceso terminado" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host "Log:       $Log"
Write-Host "Adaptador: $Adapter"
if (-not $SkipExport) {
    Write-Host "GGUF:      $(Join-Path $OutDir 'gguf\qwen-coder-1.5b-q4_k_m.gguf')"
}
Write-Host ""
Write-Host "Para usar el modelo en el agente:"
Write-Host "  python agente\run.py scan agente\examples\sample_repo --model qwen2.5-coder-triage"
