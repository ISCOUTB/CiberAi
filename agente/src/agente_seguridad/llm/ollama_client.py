import json
from typing import Optional

import requests


class OllamaError(RuntimeError):
    pass


class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "qwen2.5-coder:1.5b",
                 timeout: int = 180):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def is_available(self) -> bool:
        try:
            resp = requests.get(self.base_url + "/api/tags", timeout=5)
            return resp.status_code == 200
        except requests.RequestException:
            return False

    def generate(self, prompt: str, system: Optional[str] = None) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            # Acota la generacion: una alerta patologica puede hacer que el
            # modelo entre en bucle. Sin limite, el cliente espera hasta el
            # timeout y el runner sigue consumiendo CPU. 512 tokens alcanzan
            # para el JSON esperado (veredicto, CWE, explicacion, vector y
            # correccion) y convierten un bucle en una respuesta invalida que
            # la politica conservadora absorbe.
            "options": {"temperature": 0, "num_predict": 512},
        }
        if system:
            payload["system"] = system
        try:
            resp = requests.post(self.base_url + "/api/generate", json=payload, timeout=self.timeout)
        except requests.RequestException as exc:
            raise OllamaError("No se pudo conectar con Ollama: {}".format(exc))
        if resp.status_code != 200:
            raise OllamaError("Ollama respondio {}: {}".format(resp.status_code, resp.text[:300]))
        try:
            data = resp.json()
        except json.JSONDecodeError as exc:
            raise OllamaError("Respuesta no JSON de Ollama: {}".format(exc))
        if "response" not in data:
            raise OllamaError("Respuesta de Ollama sin campo 'response'")
        return str(data["response"])
