import { Fragment, useEffect, useMemo, useState } from 'react';
import { Notice, PageHead, Pager, Stats } from '../components/ui';
import { useReport } from '../context/ReportContext';
import { useToast } from '../hooks/useToast';
import { download } from '../lib/utils';
import type { DiscardedAlert } from '../types';

export function Discarded() {
  const toast = useToast();
  const { discarded, summary } = useReport();
  const [items, setItems] = useState<DiscardedAlert[]>(discarded);
  const [restored, setRestored] = useState(0);
  const [query, setQuery] = useState('');
  const [reason, setReason] = useState<string>('');

  useEffect(() => {
    setItems(discarded);
    setRestored(0);
  }, [discarded]);

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return items.filter(
      (d) =>
        (!q || `${d.title} ${d.sub} ${d.loc}`.toLowerCase().includes(q)) &&
        (!reason || d.why === reason),
    );
  }, [items, query, reason]);

  const total = items.length;

  const restore = (id: string) => {
    setItems((prev) => prev.filter((d) => d.id !== id));
    setRestored((n) => n + 1);
    toast('Alerta devuelta a revisión prioritaria');
  };

  const exportTraces = () => {
    const payload = items.map(({ id, title, loc, why, detail }) => ({
      id,
      title,
      loc,
      motivo: why,
      detalle: detail?.text,
      trazas: detail?.trace,
    }));
    download(`trazas-descarte-${summary.scanId}.json`, JSON.stringify(payload, null, 2), 'application/json');
  };

  const pad = (n: number) => (n < 10 ? `0${n}` : `${n}`);

  return (
    <section className="view on" id="descartadas">
      <PageHead
        crumb={`05 / ${summary.target} · ${summary.scanId}`}
        title="Descartar no es borrar."
        action={
          <button className="btn" type="button" onClick={exportTraces}>
            Exportar trazas <span>↓</span>
          </button>
        }
      />
      <p className="lede">
        {summary.discardedAlerts} alertas recomendadas para descarte por el modelo según su contexto sintáctico.
        En modo asesor, ninguna alerta se elimina del reporte final (SARIF/JSON).
      </p>

      <Stats
        items={[
          { value: String(total), label: 'Recomendadas para descarte' },
          { value: pad(summary.conservedAlerts + restored), label: 'Conservadas' },
          { value: pad(restored), label: 'Restauradas manualmente' },
        ]}
      />

      <div className="filters">
        <input
          type="search"
          placeholder="Buscar alerta, regla o ubicación"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <select value={reason} onChange={(e) => setReason(e.target.value)}>
          <option value="">Motivo: todos</option>
          <option>Recomendación LLM (SAFE)</option>
          <option>Datos de prueba</option>
          <option>Uso no sensible</option>
          <option>Ejemplo aislado</option>
        </select>
        <span className="cnt">Total recomendadas: {rows.length}</span>
      </div>

      <table>
        <thead>
          <tr>
            <th>Alerta / origen</th>
            <th>Ubicación</th>
            <th>Motivo de descarte</th>
            <th>Acción</th>
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td colSpan={4} className="empty">
                {items.length === 0
                  ? 'No hay alertas recomendadas para descarte en este reporte.'
                  : 'Ninguna alerta coincide con los filtros aplicados.'}
              </td>
            </tr>
          ) : (
            rows.map((d) => (
              <Fragment key={d.id}>
                <tr>
                  <td>
                    <span className="t1">{d.title}</span>
                    <span className="t2">{d.sub}</span>
                  </td>
                  <td>
                    <span className="loc">{d.loc}</span>
                  </td>
                  <td>
                    <span className="badge plain">{d.why}</span>
                  </td>
                  <td>
                    <button className="btn sm" type="button" onClick={() => restore(d.id)}>
                      Restaurar ↻
                    </button>
                  </td>
                </tr>
                {d.detail && (
                  <tr>
                    <td colSpan={4} className="trace-td">
                      <div className="trace">
                        <div>
                          <b className="t">Justificación del modelo · evaluación local</b>
                          {d.detail.text}
                          {d.detail.correction && d.detail.correction !== 'N/A' && (
                            <div style={{ marginTop: 8, fontSize: 11, color: 'var(--ink-2)' }}>
                              <b>Sugerencia:</b> {d.detail.correction}
                            </div>
                          )}
                        </div>
                        <div className="m">
                          <span className="eyebrow">Traza {d.id}</span>
                          {d.detail.trace.map((line) => (
                            <Fragment key={line}>
                              <br />
                              {line}
                            </Fragment>
                          ))}
                        </div>
                      </div>
                    </td>
                  </tr>
                )}
              </Fragment>
            ))
          )}
        </tbody>
      </table>

      <Pager
        label={`Mostrando ${rows.length} de ${total} recomendadas para descarte · ${summary.scanId}`}
        pages={['1']}
      />

      <Notice plain title="Garantía de Modo Asesor">
        Una recomendación SAFE marca la alerta como descarte sugerido para el revisor humano, pero se preserva íntegra en
        los informes JSON y SARIF generados por el agente.
      </Notice>
    </section>
  );
}
