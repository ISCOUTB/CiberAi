import { useEffect, useRef, useState } from 'react';
import { Badge, PageHead } from '../components/ui';
import { useReport } from '../context/ReportContext';
import { useToast } from '../hooks/useToast';

const CLI_COMMAND = 'python agente/run.py scan agente/examples/sample_repo --model qwen2.5-coder-triage';
const SCANNERS = ['both', 'bandit', 'owasp', 'llm', 'all'];

const TOOLS = [
  { name: 'Bandit', desc: 'SAST · código Python', state: 'Disponible' },
  { name: 'Ollama', desc: 'qwen2.5-coder-triage (Q4_K_M)', state: 'Modelo registrado' },
  { name: 'SARIF 2.1.0', desc: 'Normalización de hallazgos', state: 'Exportación lista' },
  { name: 'Modo Asesor', desc: 'Conservación defensiva (SAFE nunca borra)', state: 'Activo' },
];

export function Dashboard() {
  const toast = useToast();
  const { summary, loadReportFromFile, runScan, pollScan, loadingScan, scanError } = useReport();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [target, setTarget] = useState('agente/examples/sample_repo');
  const [scanner, setScanner] = useState('both');
  const [model, setModel] = useState('qwen2.5-coder:1.5b');
  const [useLlm, setUseLlm] = useState(true);
  const [jobId, setJobId] = useState<string | null>(null);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(CLI_COMMAND);
      toast('Comando de escaneo copiado');
    } catch {
      toast('No se pudo copiar el comando');
    }
  };

  const handleFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const ok = await loadReportFromFile(file);
    if (ok) toast(`Reporte cargado: ${file.name}`);
    else toast(`Error al procesar ${file.name}`);
  };

  const startScan = async () => {
    try {
      const id = await runScan({ target, scanner, model, no_llm: !useLlm });
      setJobId(id);
      toast(`Escaneo iniciado: ${id}`);
    } catch {
      toast(scanError || 'Error al iniciar el escaneo');
    }
  };

  useEffect(() => {
    if (!jobId) return;
    const interval = setInterval(async () => {
      const finished = await pollScan(jobId);
      if (finished) {
        clearInterval(interval);
        setJobId(null);
        toast('Escaneo completado');
      }
    }, 1500);
    return () => clearInterval(interval);
  }, [jobId, pollScan, toast]);

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
    <section className="view on" id="dashboard">
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFile}
        accept=".json,.sarif"
        style={{ display: 'none' }}
      />

      <PageHead
        crumb={`01 / ${summary.target} · ${summary.scanId}`}
        title="Menos ruido. Más criterio."
        action={
          <button
            className="btn primary"
            type="button"
            onClick={() => fileInputRef.current?.click()}
          >
            Cargar reporte JSON <span>↗</span>
          </button>
        }
      />
      <p className="lede">
        Tu código no sale de tu equipo. ciberAi combina Bandit con un modelo local
        ajustado (QLoRA) para hacer triage de vulnerabilidades.
      </p>

      <div className="grid2">
        <div className="l">
          <div className="eyebrow">
            Último análisis / {summary.scanId} &nbsp;
            <Badge variant={summary.isRealReport ? 'alta' : ''}>
              {summary.isRealReport ? 'Reporte Real Cargado' : 'Datos Demostrativos'}
            </Badge>
          </div>
          <div className="big">
            <b>{summary.conservedAlerts}</b>
            <span>Hallazgos conservados para atención.</span>
          </div>
          <div className="sub">
            {summary.totalAlerts} alertas detectadas por el SAST. {summary.discardedAlerts} recomendadas
            para descarte con justificación del modelo.
          </div>
          <div className="stats line">
            {severityStats.map((s) => (
              <div className="stat" key={s.label}>
                <b>{s.value}</b>
                <span>{s.label}</span>
              </div>
            ))}
            <div style={{ marginLeft: 'auto', alignSelf: 'flex-end' }}>
              <a className="btn" href="#hallazgos">
                Ver hallazgos <span>↗</span>
              </a>
            </div>
          </div>
          <div
            className="kv mono"
            style={{ marginTop: 14, fontSize: 11, color: 'var(--ink-3)' }}
          >
            {formattedDate} · Escaneo {summary.scanId} · {summary.tool}
          </div>
          <div className="note">
            {summary.suspiciousAlerts > 0
              ? `${summary.suspiciousAlerts} alertas conservadas como SOSPECHOSA (por resiliencia o política de seguridad).`
              : 'Modo asesor activo: las recomendaciones SAFE no eliminan la alerta del reporte.'}
          </div>
        </div>

        <div className="r">
          <div className="eyebrow">Directorio analizado</div>
          <h2 style={{ margin: '8px 0 2px', wordBreak: 'break-all' }}>
            {summary.target.split(/[\\/]/).pop() || summary.target}{' '}
            <small className="mono" style={{ fontSize: 11, color: 'var(--ink-3)' }}>
              / local
            </small>
          </h2>
          <div className="kv mono" style={{ wordBreak: 'break-all' }}>
            {summary.target}
          </div>
          <div className="kv">Python · Analizador {summary.tool} {summary.toolVersion}</div>

          <div className="eyebrow" style={{ marginTop: 18 }}>
            Ejecutar nuevo análisis desde el navegador
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 8 }}>
            <input
              className="mono"
              type="text"
              value={target}
              onChange={(e) => setTarget(e.target.value)}
              placeholder="Ruta del directorio"
              style={{ padding: '6px 8px', fontSize: 12 }}
            />
            <select
              value={scanner}
              onChange={(e) => setScanner(e.target.value)}
              style={{ padding: '6px 8px', fontSize: 12 }}
            >
              {SCANNERS.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
            {scanner !== 'llm' && (
              <label style={{ fontSize: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
                <input type="checkbox" checked={useLlm} onChange={(e) => setUseLlm(e.target.checked)} />
                Usar modelo para triage
              </label>
            )}
            {(useLlm || scanner === 'llm') && (
              <input
                className="mono"
                type="text"
                value={model}
                onChange={(e) => setModel(e.target.value)}
                placeholder="Modelo Ollama"
                style={{ padding: '6px 8px', fontSize: 12 }}
              />
            )}
            <button
              type="button"
              className="btn primary"
              onClick={startScan}
              disabled={loadingScan || !target.trim()}
              style={{ marginTop: 4 }}
            >
              {loadingScan ? 'Escaneando...' : 'Escanear ahora'}
            </button>
            {scanError && (
              <div style={{ color: 'var(--red)', fontSize: 12 }}>{scanError}</div>
            )}
          </div>

          <div className="eyebrow" style={{ marginTop: 18 }}>
            O desde la consola
          </div>
          <div className="cli">
            <span>$ {CLI_COMMAND}</span>
            <button type="button" title="Copiar" onClick={copy}>
              ⧉
            </button>
          </div>
          <div className="note">
            El reporte del dashboard se guarda en <code>reportes/web_dashboard/reporte.json</code>.
          </div>
        </div>
      </div>

      <div className="sec-head">
        <h2>Todo listo, en tu equipo local.</h2>
        <span className="eyebrow">Entorno verificado</span>
      </div>
      <div className="tools">
        {TOOLS.map((t) => (
          <div key={t.name}>
            <b>{t.name}</b>
            <span>{t.desc}</span>
            <em>{t.state}</em>
          </div>
        ))}
      </div>

      <p className="quote">
        La duda se conserva.{' '}
        <small>
          El modelo prioriza y explica; no sustituye a los escáneres ni
          elimina hallazgos sin supervisión humana.
        </small>
      </p>
    </section>
  );
}
