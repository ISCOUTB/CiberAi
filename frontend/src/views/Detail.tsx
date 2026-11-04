import { useState } from 'react';
import { Badge, PageHead } from '../components/ui';
import { useReport } from '../context/ReportContext';
import { useToast } from '../hooks/useToast';
import { sevClass } from '../lib/utils';

export function Detail() {
  const toast = useToast();
  const { selectedFinding, summary } = useReport();
  const [reviewed, setReviewed] = useState(false);

  if (!selectedFinding) {
    return (
      <section className="view on" id="detalle">
        <PageHead
          crumb={`04 / ${summary.target}`}
          title="Detalle del hallazgo"
          action={
            <a className="btn" href="#hallazgos">
              Ver hallazgos <span>↗</span>
            </a>
          }
        />
        <p className="lede">No hay ningún hallazgo seleccionado. Selecciona una alerta en la tabla de hallazgos.</p>
      </section>
    );
  }

  const f = selectedFinding;
  const lines = (f.codeContext || 'No hay contexto de código disponible')
    .split('\n')
    .map((code, idx) => ({
      n: (f.lineNum || 1) + idx,
      code,
      hit: idx === 0 || code.includes(f.rule || ''),
    }));

  return (
    <section className="view on" id="detalle">
      <PageHead
        crumb={`04 / ${summary.target} · ${f.id}`}
        title={f.title}
        action={
          <a className="btn" href="#hallazgos">
            Ver hallazgos <span>↗</span>
          </a>
        }
      />
      <div
        className="crumb"
        style={{ textTransform: 'none', letterSpacing: 0, margin: '2px 0 0' }}
      >
        Hallazgos / {f.id} · {f.cwe || f.rule} en {f.loc} ({f.functionName || '<módulo>'})
      </div>

      <div className="d-meta" style={{ justifyContent: 'space-between', marginTop: 12 }}>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <Badge variant={sevClass(f.sev)}>Prioridad {f.sev}</Badge>
          <Badge variant={f.state === 'Conservada' ? '' : 'warn'}>{f.state}</Badge>
          <span className="mono" style={{ color: 'var(--ink-3)' }}>
            {f.src} · {f.rule} · {f.cwe || ''} · {f.id}
          </span>
        </div>
        <button
          className="btn sm"
          type="button"
          disabled={reviewed}
          onClick={() => {
            setReviewed(true);
            toast(`${f.id} marcado como revisado`);
          }}
        >
          {reviewed ? 'Revisado ✓' : 'Marcar revisado ✓'}
        </button>
      </div>

      <div className="d-grid" style={{ marginTop: 20 }}>
        <div>
          <div className="sech">
            <h2>Lo que detecta el escáner SAST.</h2>
            <span className="eyebrow">01 / Evidencia</span>
          </div>
          <p style={{ fontSize: 13, color: 'var(--ink-2)', lineHeight: 1.6 }}>
            {f.title}
          </p>
          <div className="chips">
            <span>Severidad: <b>{f.sev}</b></span>
            <span>Confianza: <b>{f.confidence || 'HIGH'}</b></span>
            <span>Regla: <b>{f.rule}</b></span>
            <span>Función: <b>{f.functionName || '<módulo>'}</b></span>
          </div>

          <div className="code">
            <div className="ch">
              <span>{f.loc}</span>
              <span>PYTHON</span>
            </div>
            {lines.slice(0, 15).map((l) => (
              <div className={`ln${l.hit ? ' hit' : ''}`} key={l.n}>
                <span>{l.n}</span>
                <code>{l.code}</code>
              </div>
            ))}
          </div>

          <div className="sech" style={{ marginTop: 24 }}>
            <h2>Corrección recomendada por el modelo.</h2>
            <span className="eyebrow">02 / Mitigación</span>
          </div>
          <p style={{ fontSize: 13, color: 'var(--ink-2)', lineHeight: 1.6 }}>
            Propuesta generada localmente para subsanar la regla {f.rule} preservando el comportamiento funcional.
          </p>
          <div className="code" style={{ marginTop: 12, padding: '12px 16px' }}>
            <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: 12 }}>
              {f.correction || 'Revisar manualmente el patrón en el código fuente.'}
            </pre>
          </div>
          <div className="cli" style={{ marginTop: 14 }}>
            <span>$ python agente/run.py scan {summary.target} --model qwen2.5-coder-triage</span>
            <span style={{ color: 'var(--ink-3)', fontSize: 11 }}>
              # volver a escanear tras aplicar el parche
            </span>
          </div>
        </div>

        <aside className="ctx">
          <div className="eyebrow">03 / Evaluación local del modelo</div>
          <h2>{f.triageVerdict === 'VULNERABLE' ? 'Vulnerabilidad confirmada' : 'Alerta conservada por política'}</h2>
          <p style={{ lineHeight: 1.6 }}>
            {f.explanation || 'El modelo analizó el contexto sintáctico de la función y emitió este veredicto.'}
          </p>

          <div className="eyebrow lab">Vector de ataque inferido</div>
          <div className="flow" style={{ fontSize: 12 }}>
            {f.attackVector || 'No especificado.'}
          </div>

          <div className="eyebrow lab">Decisión de Triage</div>
          <p>
            <b style={{ color: 'var(--ink)' }}>
              {f.triageVerdict === 'SAFE' ? 'Descarte recomendado' : 'Conservar en reporte'}.
            </b>{' '}
            {f.triageOrigin === 'politica_seguridad'
              ? 'Protegida por política de seguridad: alto riesgo de omisión.'
              : 'El agente mantiene la alerta en modo asesor para revisión humana prioritaria.'}
          </p>

          <div className="warnbox">
            <span className="ico">◈</span>
            <div>
              <b>Modo Asesor Activo</b>
              Las sugerencias del modelo aportan contexto semántico pero no reemplazan la auditoría de un desarrollador.
            </div>
          </div>

          <div className="eyebrow lab">Motor de Inferencia</div>
          <div
            className="mono"
            style={{ fontSize: 11.5, color: 'var(--ink-2)', lineHeight: 1.8 }}
          >
            qwen2.5-coder-triage (QLoRA)
            <br />
            Cuantización GGUF Q4_K_M · Ollama
          </div>
        </aside>
      </div>
    </section>
  );
}
