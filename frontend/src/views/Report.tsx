import { Badge, Notice, PageHead, Stats } from '../components/ui';
import { useReport } from '../context/ReportContext';
import { buildSarif } from '../lib/sarif';
import { download } from '../lib/utils';

export function Report() {
  const { summary, findings } = useReport();

  const pad = (n: number) => (n < 10 ? `0${n}` : `${n}`);

  const severityStats = [
    { value: pad(summary.severityCounts.critica), label: 'Críticas' },
    { value: pad(summary.severityCounts.alta), label: 'Altas' },
    { value: pad(summary.severityCounts.media), label: 'Medias' },
    { value: pad(summary.severityCounts.baja), label: 'Bajas' },
  ];

  const formattedDate = new Date(summary.created).toLocaleString('es-ES', {
    dateStyle: 'medium',
    timeStyle: 'short',
  });

  return (
    <section className="view on" id="informe">
      <PageHead
        crumb={`06 / ${summary.target} · ${summary.scanId}`}
        title="Una lectura para actuar."
        action={<Badge variant={summary.isRealReport ? 'alta' : ''}>Análisis finalizado</Badge>}
      />
      <p className="lede">
        Informe de seguridad · {summary.target} · {summary.scanId} · {formattedDate} · Herramienta: {summary.tool}
      </p>

      <div className="rep-grid">
        <div>
          <div className="sec-n" style={{ marginTop: 0 }}>
            01 / Resumen ejecutivo
          </div>
          <div className="rep-head">
            {summary.conservedAlerts} alertas para revisar.
            <br />
            La prioridad es mitigar vulnerabilidades reales.
          </div>
          <p className="rep-text">
            El analizador SAST generó {summary.totalAlerts} alertas originales. El modelo de triage local afinado
            recomienda descartar {summary.discardedAlerts} por considerar que corresponden a falsos positivos según
            el contexto sintáctico, conservando {summary.conservedAlerts} en el reporte en modo asesor.
          </p>
          <Stats line items={severityStats} style={{ marginTop: 18, maxWidth: 420 }} />

          <div className="sec-n">02 / Desglose por Vulnerabilidad (CWE)</div>
          <table className="small-table">
            <thead>
              <tr>
                <th>CWE</th>
                <th>Descripción / Familia</th>
                <th>Alertas</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(summary.cweCounts).length === 0 ? (
                <tr>
                  <td colSpan={3}>Sin clasificación CWE específica.</td>
                </tr>
              ) : (
                Object.entries(summary.cweCounts).map(([cwe, count]) => (
                  <tr key={cwe}>
                    <td><b>{cwe}</b></td>
                    <td>Clasificación SAST Bandit</td>
                    <td>{count}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
          <p className="note">
            Triage efectuado mediante modelo SLM (Qwen2.5-Coder-1.5B) ajustado con QLoRA y cuantizado a GGUF Q4_K_M
            ejecutándose en local mediante Ollama. En modo asesor, las sugerencias SAFE son informativas y no borran
            la señal del reporte.
          </p>

          <div className="sec-n">03 / Recomendaciones clave de ingeniería</div>
          <div className="reco">
            <span className="n">01</span>
            <div>
              <b>Revisar alertas críticas y altas de inmediato</b>
              <p>Priorizar sinks de ejecución de comandos (`B602`/`B605`), inyección SQL (`B608`) y deserialización insegura (`B301`/`B403`).</p>
            </div>
            <span className="tag now">Inmediato</span>
          </div>

          <div className="reco">
            <span className="n">02</span>
            <div>
              <b>Validar alertas marcadas como SOSPECHOSA</b>
              <p>
                {summary.suspiciousAlerts} alerta(s) conservada(s) por política de seguridad o falta de certeza.
                Requieren revisión manual obligatoria.
              </p>
            </div>
            <span className="tag">Revisión humana</span>
          </div>

          <Notice title="Siguiente paso: parchear y re-escanear">
            Las {summary.conservedAlerts} alertas conservadas están listas para ser atendidas en el código.
            Vuelve a escanear el repositorio para verificar que los parches eliminaron las vulnerabilidades.
          </Notice>
        </div>

        <div>
          <div className="aside">
            <div className="eyebrow">Artefactos del escaneo</div>
            <h2>La evidencia se queda contigo.</h2>
            <p>
              Exporta el informe en PDF o descarga el archivo SARIF normalizado generado a partir de este análisis.
            </p>
            <button className="btn primary" type="button" onClick={() => window.print()}>
              Exportar informe PDF <span>↓</span>
            </button>
            <button
              className="btn"
              type="button"
              onClick={() =>
                download(`resultados-${summary.scanId}.sarif`, buildSarif(findings), 'application/json')
              }
            >
              Exportar SARIF <span>↓</span>
            </button>
            <div className="path">
              reportes/{summary.scanId}/
              <br />
              reporte.json · hallazgos.sarif
            </div>
            <div className="how">
              <div className="eyebrow">Privacidad y Seguridad</div>
              <h3>100% Local · Sin Telemetría</h3>
              <p>
                El modelo se ejecuta en tu GPU/CPU mediante Ollama. Ninguna línea de código sale de tu equipo.
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
