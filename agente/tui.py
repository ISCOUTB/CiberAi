"""TUI de pantalla completa para visualizar reportes de CiberAi.

Requiere:
    pip install textual

Uso:
    python agente/tui.py [ruta/reporte.json]

Teclas:
    ↑ / ↓      moverse entre hallazgos
    Enter      ver detalle del hallazgo seleccionado
    r          recargar reporte
    q / Esc    salir
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Footer, Header, Static

ROOT = Path(__file__).resolve().parent.parent


def _load_report(path: Path) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    return json.loads(text)


def _severity_order(sev: str) -> int:
    return {"critica": 0, "alta": 1, "media": 2, "baja": 3}.get(sev.lower(), 9)


class CiberAiTui(App):
    CSS = """
    Screen { align: center middle; }
    #summary {
        height: 8;
        padding: 1 2;
        border: solid $primary;
    }
    #detail {
        width: 45%;
        padding: 1 2;
        border-left: solid $primary;
    }
    #detail-title { text-style: bold; color: $warning; margin-bottom: 1; }
    #detail-body { color: $text; }
    DataTable { height: 1fr; }
    Static { color: $text-muted; }
    """

    BINDINGS = [
        Binding("q,escape", "quit", "Salir"),
        Binding("r", "reload", "Recargar"),
        Binding("enter", "detail", "Detalle"),
        Binding("up", "cursor_up", "Arriba"),
        Binding("down", "cursor_down", "Abajo"),
    ]

    def __init__(self, report_path: Path, **kwargs):
        super().__init__(**kwargs)
        self.report_path = report_path
        self.report: Dict[str, Any] = {}
        self.findings: List[Dict[str, Any]] = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static(id="summary")
        with Horizontal():
            table = DataTable(id="findings")
            table.cursor_type = "row"
            table.add_columns("#", "Veredicto", "CWE", "OWASP", "Archivo", "Línea", "Severidad", "Regla")
            yield table
            with Vertical(id="detail"):
                yield Static("Selecciona un hallazgo para ver el detalle", id="detail-title")
                yield Static("", id="detail-body")
        yield Footer()

    def on_mount(self) -> None:
        self.title = "CiberAi - Reporte de seguridad"
        self._load()

    def action_reload(self) -> None:
        self._load()
        self.notify("Reporte recargado", severity="information")

    def action_detail(self) -> None:
        self._show_detail()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self._show_detail()

    def _load(self) -> None:
        try:
            self.report = _load_report(self.report_path)
        except Exception as exc:
            self.notify(f"No se pudo cargar {self.report_path}: {exc}", severity="error")
            return

        scan = self.report.get("scan", {})
        summary = self.report.get("resumen", {})

        summary_text = (
            f"Escaneo: {scan.get('scan_id', '?')}  →  {scan.get('target', '?')}\n"
            f"Total: {summary.get('total', 0)} | Conservadas: {summary.get('conservadas', 0)} | "
            f"Recomendadas descarte: {summary.get('recomendadas_descarte', 0)} | "
            f"Sospechosas: {summary.get('sospechosas', 0)} | Errores modelo: {summary.get('errores_modelo', 0)}\n"
            f"Herramientas: {self._format_counts(summary.get('por_herramienta', {}))} | "
            f"OWASP: {self._format_counts(summary.get('por_owasp', {}))}"
        )
        self.query_one("#summary", Static).update(summary_text)

        self.findings = []
        for run in scan.get("tool_runs", []):
            for f in run.get("findings", []):
                self.findings.append(f)

        # Ordenar: primero severidad alta, luego archivo/línea
        self.findings.sort(key=lambda f: (_severity_order(f.get("severity", "")), f.get("file", ""), f.get("line", 0)))

        table = self.query_one("#findings", DataTable)
        table.clear()
        for i, f in enumerate(self.findings, 1):
            triage = f.get("triage", {})
            table.add_row(
                str(i),
                str(triage.get("veredicto", "SIN_TRIAGE")),
                str(f.get("cwe", "")),
                str(f.get("owasp", "")),
                str(f.get("file", "")),
                str(f.get("line", "")),
                str(f.get("severity", "")),
                str(f.get("rule_id", "")),
                key=f.get("finding_id", str(i)),
            )

        if self.findings:
            table.move_cursor(row=0)

    def _show_detail(self) -> None:
        table = self.query_one("#findings", DataTable)
        if table.cursor_row is None or not self.findings:
            return
        idx = table.cursor_row
        if idx < 0 or idx >= len(self.findings):
            return
        f = self.findings[idx]
        triage = f.get("triage", {})
        title = self.query_one("#detail-title", Static)
        body = self.query_one("#detail-body", Static)
        title.update(f"{f.get('rule_id', '?')} · {f.get('cwe', '?')} · {f.get('file')}:{f.get('line')}")
        detail_text = (
            f"[b]Veredicto:[/b] {triage.get('veredicto', 'SIN_TRIAGE')}\n"
            f"[b]Severidad:[/b] {f.get('severity', 'N/A')}\n"
            f"[b]Función:[/b] {f.get('function', '<módulo>')}\n"
            f"[b]Confianza:[/b] {f.get('confidence', 'N/A')}\n\n"
            f"[b]Mensaje:[/b]\n{f.get('message', 'Sin mensaje')}\n\n"
            f"[b]Explicación del modelo:[/b]\n{triage.get('explicacion', 'No disponible')}\n\n"
            f"[b]Vector de ataque:[/b] {triage.get('vector_ataque', 'N/A')}\n\n"
            f"[b]Corrección:[/b] {triage.get('correccion', 'Revisar manualmente.')}\n\n"
            f"[b]Contexto:[/b]\n{f.get('context', 'No disponible')[:800]}"
        )
        body.update(detail_text)

    @staticmethod
    def _format_counts(counts: Dict[str, int]) -> str:
        return ", ".join(f"{k}={v}" for k, v in counts.items()) or "N/A"


def main(argv=None) -> int:
    path = Path(argv[1]) if argv and len(argv) > 1 else ROOT / "reportes" / "reporte.json"
    if not path.is_file():
        print(f"No se encontró el reporte: {path}", file=sys.stderr)
        return 1
    app = CiberAiTui(path)
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
