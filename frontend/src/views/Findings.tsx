import { useMemo, useState } from 'react';
import { Notice, PageHead, Pager } from '../components/ui';
import { useReport } from '../context/ReportContext';
import { sevClass } from '../lib/utils';
import type { FindingState, Scanner, Severity } from '../types';

export function Findings() {
  const { findings, summary, selectFinding } = useReport();
  const [query, setQuery] = useState('');
  const [severity, setSeverity] = useState<Severity | ''>('');
  const [source, setSource] = useState<Scanner | ''>('');
  const [state, setState] = useState<FindingState | ''>('');

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return findings.filter(
      (f) =>
        (!q || `${f.title} ${f.sub} ${f.loc} ${f.rule}`.toLowerCase().includes(q)) &&
        (!severity || f.sev === severity) &&
        (!source || f.src === source) &&
        (!state || f.state === state),
    );
  }, [findings, query, severity, source, state]);

  const pad = (n: number) => (n < 10 ? `0${n}` : `${n}`);

  return (
    <section className="view on" id="hallazgos">
      <PageHead
        crumb={`03 / ${summary.target} · ${summary.scanId}`}
        title="Lo que importa revisar."
        action={
          <a className="btn" href="#informe">
            Abrir informe <span>↗</span>
          </a>
        }
      />
      <p className="lede">
        {summary.conservedAlerts} alertas conservadas de {summary.totalAlerts} originales.
        Revisión priorizada por modelo local de IA según el contexto de la función.
      </p>

      <div className="stats">
        <div className="stat">
          <b>{summary.conservedAlerts}</b>
          <span>conservadas · {summary.discardedAlerts} recomendadas para descarte</span>
        </div>
        <div className="stat">
          <b>{pad(summary.severityCounts.critica)}</b>
          <span>Críticas</span>
        </div>
        <div className="stat">
          <b>{pad(summary.severityCounts.alta)}</b>
          <span>Altas</span>
        </div>
        <div className="stat">
          <b>{pad(summary.severityCounts.media)}</b>
          <span>Medias</span>
        </div>
        <div className="stat">
          <b>{pad(summary.severityCounts.baja)}</b>
          <span>Bajas</span>
        </div>
      </div>

      <div className="filters">
        <input
          type="search"
          placeholder="Buscar por regla, CWE, archivo o descripción"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <select value={severity} onChange={(e) => setSeverity(e.target.value as Severity | '')}>
          <option value="">Prioridad: todas</option>
          <option>Crítica</option>
          <option>Alta</option>
          <option>Media</option>
          <option>Baja</option>
        </select>
        <select value={source} onChange={(e) => setSource(e.target.value as Scanner | '')}>
          <option value="">Origen: todos</option>
          <option>Bandit</option>
          <option>Gitleaks</option>
          <option>osv-scanner</option>
        </select>
        <select value={state} onChange={(e) => setState(e.target.value as FindingState | '')}>
          <option value="">Estado: todos</option>
          <option>Conservada</option>
          <option>Evaluación inválida</option>
        </select>
        <span className="cnt">Total: {rows.length}</span>
      </div>

      <table>
        <thead>
          <tr>
            <th>Prioridad</th>
            <th>Hallazgo / regla</th>
            <th>Origen</th>
            <th>Ubicación</th>
            <th>Estado</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td colSpan={6} className="empty">
                Ninguna alerta coincide con los filtros aplicados.
              </td>
            </tr>
          ) : (
            rows.map((f) => (
              <tr
                key={f.id}
                className={`row${f.focus ? ' focus' : ''}`}
                onClick={() => selectFinding(f.id)}
                style={{ cursor: 'pointer' }}
                title="Haz clic para ver el análisis detallado del modelo"
              >
                <td>
                  <span className={`badge ${sevClass(f.sev)}`}>{f.sev}</span>
                </td>
                <td>
                  <span className="t1">{f.title}</span>
                  <span className="t2">{f.sub}</span>
                </td>
                <td>{f.src}</td>
                <td>
                  <span className="loc">{f.loc}</span>
                </td>
                <td>
                  <span className={`badge ${f.state === 'Conservada' ? '' : 'warn'}`}>
                    {f.state}
                  </span>
                </td>
                <td style={{ color: 'var(--ink-3)' }}>↗</td>
              </tr>
            ))
          )}
        </tbody>
      </table>

      <Pager
        label={`Mostrando ${rows.length} alertas · ${summary.scanId}`}
        pages={['1']}
      />

      {summary.suspiciousAlerts > 0 && (
        <Notice plain title={`${summary.suspiciousAlerts} alerta(s) conservada(s) por política defensiva`}>
          Ante respuestas dudosas o reglas protegidas (como B403), el sistema aplica el principio de menor privilegio
          y conserva obligatoriamente la alerta para inspección de un analista.
        </Notice>
      )}
    </section>
  );
}
