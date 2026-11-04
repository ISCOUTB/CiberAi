import { useRef, type ReactNode } from 'react';
import { useReport } from '../context/ReportContext';
import { VIEWS } from '../data';
import { useToast } from '../hooks/useToast';
import type { ViewId } from '../types';

export function Layout({
  view,
  children,
}: {
  view: ViewId;
  children: ReactNode;
}) {
  const { summary, loadReportFromFile, resetToDemo } = useReport();
  const toast = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const ok = await loadReportFromFile(file);
    if (ok) {
      toast(`Reporte cargado: ${file.name}`);
    } else {
      toast(`Error al cargar ${file.name}`);
    }
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const shortTarget = summary.target.length > 35
    ? '...' + summary.target.slice(-32)
    : summary.target;

  return (
    <div className="wrap">
      <header className="top">
        <div className="brand">
          <b>ciberAi.</b>
          <small>SEGURIDAD CON CONTEXTO</small>
        </div>
        <div className="meta-top" style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <span className="local">
            <i className="dot" />
            100% local · sin nube
          </span>

          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            accept=".json,.sarif"
            style={{ display: 'none' }}
          />

          <button
            type="button"
            className="btn sm"
            onClick={() => fileInputRef.current?.click()}
            style={{ fontSize: 11, padding: '4px 10px', height: 'auto', cursor: 'pointer' }}
          >
            📂 Cargar reporte JSON / SARIF
          </button>

          {summary.isRealReport && (
            <button
              type="button"
              className="btn sm"
              onClick={() => {
                resetToDemo();
                toast('Restaurado a datos de demostración');
              }}
              style={{ fontSize: 11, padding: '4px 8px', height: 'auto', color: 'var(--ink-3)' }}
              title="Volver a los datos de ejemplo iniciales"
            >
              Reiniciar demo
            </button>
          )}

          <span className="ver">CLI v0.8.0</span>
        </div>
      </header>

      <nav>
        {VIEWS.map((v) => (
          <a
            key={v.id}
            href={`#${v.id}`}
            className={v.id === view ? 'on' : ''}
            aria-current={v.id === view ? 'page' : undefined}
          >
            <i>{v.n}</i>
            {v.label}
          </a>
        ))}
        <span className="path" title={summary.target}>
          {summary.isRealReport ? `⚡ ${shortTarget}` : summary.target}
        </span>
      </nav>

      {children}

      <footer>
        <span>
          {summary.isRealReport
            ? `Reporte activo: ${summary.filename || 'reporte.json'} · Escaneo ${summary.scanId}`
            : 'Análisis de ejemplo · Datos ilustrativos'}
        </span>
        <span>CLI → SAST (Bandit) → deduplicación → Ollama (qwen2.5-coder-triage)</span>
      </footer>
    </div>
  );
}
