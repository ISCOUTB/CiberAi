"""Servidor web ligero para el dashboard de CiberAi.

Sirve el frontend construido en ``frontend/dist`` y expone una API para
ejecutar escaneos y consultar el último reporte.

Uso:
    python agente/server.py

O con uvicorn:
    uvicorn agente.server:app --reload

Desarrollo del frontend (puerto 5173):
    cd frontend && npm run dev

El servidor espera estar lanzado desde la raíz del proyecto.
"""

import asyncio
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = ROOT / "reportes" / "web_dashboard"
RUN_PY = ROOT / "agente" / "run.py"
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
if not PYTHON.exists():
    PYTHON = Path(sys.executable)

app = FastAPI(title="CiberAi Dashboard API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ScanRequest(BaseModel):
    target: str = Field(default="agente/examples/sample_repo")
    scanner: str = Field(default="both")
    model: str = Field(default="qwen2.5-coder:1.5b")
    no_llm: bool = Field(default=False)
    max_alerts: int = Field(default=0, ge=0)
    audit_max_chunks: int = Field(default=0, ge=0)

    @field_validator("scanner")
    @classmethod
    def _scanner(cls, v: str) -> str:
        if v not in {"both", "bandit", "owasp", "llm", "all"}:
            raise ValueError("scanner debe ser both, bandit, owasp, llm o all")
        return v


class ScanJob(BaseModel):
    job_id: str
    status: str  # pending, running, done, error
    output_dir: str
    error: Optional[str] = None
    command: str = ""


_jobs: Dict[str, Dict[str, Any]] = {}


def _report_path() -> Path:
    return REPORT_DIR / "reporte.json"


def _build_args(req: ScanRequest) -> list:
    target = ROOT / req.target if not Path(req.target).is_absolute() else Path(req.target)
    args = [
        str(PYTHON), str(RUN_PY), "scan", str(target),
        "--scanner", req.scanner,
        "--out", str(REPORT_DIR),
        "--no-color",
    ]
    if req.scanner not in ("llm",):
        if not req.no_llm:
            args += ["--model", req.model]
    else:
        args += ["--model", req.model]
    if req.no_llm:
        args.append("--no-llm")
    if req.max_alerts:
        args += ["--max-alerts", str(req.max_alerts)]
    if req.audit_max_chunks:
        args += ["--audit-max-chunks", str(req.audit_max_chunks)]
    return args


async def _run_scan(job_id: str, req: ScanRequest) -> None:
    job = _jobs[job_id]
    job["status"] = "running"
    args = _build_args(req)
    job["command"] = " ".join(args)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    try:
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            job["status"] = "error"
            job["error"] = stderr.decode("utf-8", errors="replace").strip() or "El escaneo falló"
        else:
            job["status"] = "done"
            job["stdout"] = stdout.decode("utf-8", errors="replace")
    except Exception as exc:
        job["status"] = "error"
        job["error"] = str(exc)


@app.get("/api/health")
async def health() -> dict:
    return {"ok": True, "python": str(PYTHON), "model": "qwen2.5-coder:1.5b"}


@app.get("/api/report")
async def get_report(job_id: Optional[str] = Query(default=None)):
    path = _report_path()
    if not path.is_file():
        raise HTTPException(status_code=404, detail="No hay reporte todavía. Ejecuta un escaneo.")
    try:
        content = path.read_text(encoding="utf-8")
        data = json.loads(content)
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=500, detail=f"No se pudo leer el reporte: {exc}")
    return data


@app.post("/api/scan")
async def start_scan(req: ScanRequest) -> ScanJob:
    job_id = uuid.uuid4().hex[:12]
    _jobs[job_id] = {"status": "pending", "output_dir": str(REPORT_DIR), "command": ""}
    args = _build_args(req)
    _jobs[job_id]["command"] = " ".join(args)
    asyncio.create_task(_run_scan(job_id, req))
    return ScanJob(job_id=job_id, status="pending", output_dir=str(REPORT_DIR), command=_jobs[job_id]["command"])


@app.get("/api/scan/{job_id}")
async def scan_status(job_id: str) -> ScanJob:
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Trabajo no encontrado")
    return ScanJob(
        job_id=job_id,
        status=job["status"],
        output_dir=job["output_dir"],
        error=job.get("error"),
        command=job.get("command", ""),
    )


# Sirve /reporte.json desde el directorio del dashboard para compatibilidad con el frontend.
@app.get("/reporte.json")
async def reporte_json():
    path = _report_path()
    if not path.is_file():
        raise HTTPException(status_code=404, detail="No hay reporte todavía")
    return FileResponse(path, media_type="application/json")


# Frontend estático. Las rutas de la API deben ir antes que esta montura.
FRONTEND_DIST = ROOT / "frontend" / "dist"
if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)
