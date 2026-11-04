import { Badge, Notice, PageHead, Stats } from '../components/ui';
import { useReport } from '../context/ReportContext';
import { useSimulatedScan } from '../hooks/useSimulatedScan';
import { mmss } from '../lib/utils';

const PIPELINE_STEPS = [
  { n: 1, title: 'Preparar repositorio', sub: 'Extracción de archivos .py' },
  { n: 2, title: 'Ejecutar Bandit SAST', sub: 'Identificación de reglas y AST' },
  { n: 3, title: 'Normalizar y deduplicar', sub: 'Formato estándar y extracción de función' },
  { n: 4, title: 'Triage con Ollama', sub: 'qwen2.5-coder-triage local (QLoRA)' },
  { n: 5, title: 'Generar reporte JSON / SARIF', sub: 'reportes/reporte.json y hallazgos.sarif' },
];

export function Progress() {
  const { summary } = useReport();
  const sim = useSimulatedScan();

  const handleToggle = () => {
    if (sim.running) {
      sim.stop();
    } else {
      sim.start(summary.totalAlerts, summary.conservedAlerts, summary.discardedAlerts);
    }
  };

  const stateLabel = sim.running
    ? 'En ejecución'
    : sim.completed
      ? 'Completado'
      : 'Detenido';

  return (
    <section className="view on" id="progreso">
      <PageHead
        crumb={`02 / ${summary.target} · ${summary.scanId}`}
        title="De la señal al contexto."
        action={
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn" type="button" onClick={handleToggle}>
              {sim.running ? 'Detener simulación' : '▶ Reanudar / Simular en vivo'}
            </button>
            <a className="btn primary" href="#hallazgos">
              Ver hallazgos <span>↗</span>
            </a>
          </div>
        }
      />
      <p className="lede">
        {sim.running
          ? `Análisis en curso sobre ${summary.target}. El triage local consulta a Ollama tras la fase de SAST.`
          : `Escaneo ${summary.scanId} finalizado. Las alertas del SAST fueron procesadas localmente en modo asesor.`}
      </p>

      <div className="progress-card">
        <div className="progress-row">
          <div>
            <span className="pct">{sim.percent}%</span>
            {sim.running ? 'Evaluación contextual en curso' : 'Pipeline de análisis completado'}
          </div>
          <div>
            <span className="mono" style={{ color: 'var(--ink-2)' }}>
              {mmss(sim.seconds)} transcurridos
            </span>{' '}
            &nbsp;
            <Badge variant={sim.completed ? 'alta' : sim.running ? '' : 'warn'}>
              {stateLabel}
            </Badge>
          </div>
        </div>
        <div className="bar">
          <i style={{ width: `${sim.percent}%` }} />
        </div>
      </div>

      <div className="prog-cols">
        <div>
          <div className="eyebrow" style={{ marginBottom: 6 }}>
            Pipeline secuencial
          </div>
          {PIPELINE_STEPS.map((s) => {
            const isDone = sim.currentStep > s.n || sim.completed;
            const isCurrent = sim.currentStep === s.n && !sim.completed;
            return (
              <div
                className={`step ${isDone ? 'done' : isCurrent ? 'run' : ''}`}
                key={s.n}
              >
                <span className="n">{isDone ? '✓' : `0${s.n}`}</span>
                <div>
                  <b>{s.title}</b>
                  <small>{s.sub}</small>
                </div>
                <span className="t">
                  {isDone ? 'Listo' : isCurrent ? 'En curso' : 'En espera'}
                </span>
              </div>
            );
          })}
        </div>

        <div>
          <div className="pane-head">
            <span className="eyebrow">Consola de ejecución</span>
            <span className="eyebrow">Salida CLI en vivo</span>
          </div>
          <div className="term">
            <div className="cmd">
              $ python agente/run.py scan {summary.target} --model qwen2.5-coder-triage
            </div>
            {sim.logs.map(([ts, msg], idx) => (
              <div key={ts + idx}>
                <span className="ts">{ts}</span>
                {msg}
              </div>
            ))}
            {sim.running && (
              <div>
                <span className="ts">{mmss(sim.seconds)}</span>
                Evaluando alertas en local… <span className="cursor" />
              </div>
            )}
          </div>
          <p className="note">
            Sin conexión externa. Los pesos del modelo corren localmente en la GPU/CPU mediante Ollama.
          </p>
        </div>
      </div>

      <div className="partial">
        <h2>
          {sim.completed ? 'Resultados del escaneo' : 'Avance parcial del triage'}
          <small>
            {sim.evaluated} de {sim.total} alertas evaluadas
          </small>
        </h2>
        <Stats
          items={[
            { value: String(sim.kept), label: 'Conservadas (revisión prioritaria)' },
            { value: String(sim.discarded), label: 'Recomendadas para descarte' },
            { value: String(sim.pending), label: 'Pendientes' },
          ]}
        />
      </div>

      <Notice title="Política de Seguridad y Modo Asesor">
        En este agente, las recomendaciones SAFE nunca borran la alerta del informe (JSON ni SARIF). Si Ollama no
        está disponible o se detecta una regla protegida (como B403), la alerta se conserva obligatoriamente como
        SOSPECHOSA.
      </Notice>
    </section>
  );
}
