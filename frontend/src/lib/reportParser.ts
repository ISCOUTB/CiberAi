import type { DetailedFinding, DiscardedAlert, ReportSummary, Severity, Scanner, FindingState } from '../types';

const SEVERITY_MAP: Record<string, Severity> = {
  critica: 'Crítica',
  alta: 'Alta',
  media: 'Media',
  baja: 'Baja',
};

const SCANNER_MAP: Record<string, Scanner> = {
  bandit: 'Bandit',
  owasp: 'SAST',
  'llm-audit': 'SAST',
};

function toSeverity(raw: string): Severity {
  return SEVERITY_MAP[raw.toLowerCase()] || 'Media';
}

function toScanner(raw: string): Scanner {
  return SCANNER_MAP[raw.toLowerCase()] || 'SAST';
}

function toState(verdict: string, valid: boolean): FindingState {
  const v = (verdict || '').toUpperCase();
  if (!valid) return 'Evaluación inválida';
  if (v === 'SOSPECHOSA') return 'Sospechosa';
  return 'Conservada';
}

function toFinding(raw: any, toolName: string): DetailedFinding {
  const triage = raw.triage || {};
  const verdict = (triage.veredicto || 'SIN_TRIAGE').toUpperCase();
  const id = raw.finding_id || raw.id || `SEC-${raw.rule_id || 'UNK'}`;
  const loc = `${raw.file || '?'}:${raw.line || 0}`;
  const state = toState(verdict, triage.valido !== false);
  const title = raw.message || 'Alerta SAST';

  return {
    id,
    sev: toSeverity(raw.severity || 'media'),
    title,
    sub: `${raw.rule_id || ''} · ${raw.cwe || ''}`.replace(/^[ ·]+|[ ·]+$/g, ''),
    src: toScanner(toolName),
    rule: raw.rule_id || '',
    loc,
    state,
    cwe: raw.cwe || undefined,
    functionName: raw.function || undefined,
    codeContext: raw.context || undefined,
    lineNum: typeof raw.line === 'number' ? raw.line : undefined,
    triageVerdict: verdict as any,
    explanation: triage.explicacion || undefined,
    attackVector: triage.vector_ataque || undefined,
    correction: triage.correccion || undefined,
    triageOrigin: triage.origen || undefined,
    confidence: raw.confidence || undefined,
  };
}

function toDiscarded(raw: any, toolName: string): DiscardedAlert {
  const finding = toFinding(raw, toolName);
  return {
    id: finding.id,
    title: finding.title,
    sub: `${finding.src} · ${finding.rule} · ${finding.id}`,
    loc: finding.loc,
    why: 'Recomendación LLM (SAFE)',
    detail: {
      text: finding.explanation || 'El modelo recomendó descartar esta alerta.',
      trace: [
        `Origen: ${finding.src} → ${finding.rule}`,
        `Decisión: SAFE · ${finding.triageOrigin || 'triage'}`,
        `CWE: ${finding.cwe || 'N/A'}`,
      ],
      vector: finding.attackVector,
      correction: finding.correction,
      code: finding.codeContext,
    },
  };
}

export function parseReport(content: string, filename?: string): {
  summary: ReportSummary;
  findings: DetailedFinding[];
  discarded: DiscardedAlert[];
} {
  let data: any;
  try {
    data = JSON.parse(content);
  } catch {
    throw new Error('El archivo no es JSON válido');
  }

  const scan = data.scan || {};
  const summary = data.resumen || data.summary || {};

  const findings: DetailedFinding[] = [];
  const discarded: DiscardedAlert[] = [];
  const toolRuns = scan.tool_runs || [];

  toolRuns.forEach((run: any) => {
    const toolName = run.tool || 'sast';
    (run.findings || []).forEach((raw: any) => {
      const verdict = ((raw.triage || {}).veredicto || '').toUpperCase();
      if (verdict === 'SAFE') {
        discarded.push(toDiscarded(raw, toolName));
      } else {
        findings.push(toFinding(raw, toolName));
      }
    });
  });

  const severityRaw = summary.por_severidad || {};
  const severityCounts = {
    critica: severityRaw.critica || severityRaw.Crítica || 0,
    alta: severityRaw.alta || severityRaw.Alta || 0,
    media: severityRaw.media || severityRaw.Media || 0,
    baja: severityRaw.baja || severityRaw.Baja || 0,
  };

  return {
    summary: {
      scanId: scan.scan_id || 'N/A',
      target: scan.target || filename || 'desconocido',
      created: scan.created || new Date().toISOString(),
      tool: Object.keys(summary.por_herramienta || {}).join(' · ') || 'SAST',
      toolVersion: 'v0.8.0',
      totalAlerts: summary.total ?? findings.length + discarded.length,
      conservedAlerts: summary.conservadas ?? findings.length,
      discardedAlerts: summary.recomendadas_descarte ?? discarded.length,
      suspiciousAlerts: summary.sospechosas ?? 0,
      severityCounts,
      cweCounts: summary.por_cwe || {},
      isRealReport: true,
      filename,
    },
    findings,
    discarded,
  };
}
