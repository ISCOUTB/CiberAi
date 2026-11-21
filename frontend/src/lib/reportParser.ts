import type {
  DetailedFinding,
  DiscardedAlert,
  FindingState,
  ReportSummary,
} from '../types';

type Obj = Record<string, unknown>;
type TriageVerdict = NonNullable<DetailedFinding['triageVerdict']>;

export interface ParsedReport {
  summary: ReportSummary;
  findings: DetailedFinding[];
  discarded: DiscardedAlert[];
}

function obj(value: unknown): Obj {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Obj)
    : {};
}

function arr(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function text(value: unknown, fallback = ''): string {
  if (value === undefined || value === null) return fallback;
  return typeof value === 'string' ? value : String(value);
}

function count(value: unknown): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function mapSeverity(value: unknown): DetailedFinding['sev'] {
  const raw = text(value).toLowerCase();
  if (raw.includes('crít') || raw.includes('crit') || raw === 'error') return 'Crítica';
  if (raw.includes('alta') || raw === 'high') return 'Alta';
  if (raw.includes('media') || raw === 'medium' || raw === 'warning') return 'Media';
  return 'Baja';
}

function mapSource(value: unknown): DetailedFinding['src'] {
  const raw = text(value).toLowerCase();
  if (raw.includes('gitleaks')) return 'Gitleaks';
  if (raw.includes('osv') || raw.includes('dependen') || raw.includes('npm') || raw.includes('pip')) {
    return 'osv-scanner';
  }
  return 'SAST';
}

function mapVerdict(value: unknown): TriageVerdict | undefined {
  const raw = text(value).toUpperCase();
  if (raw === 'SAFE' || raw === 'VULNERABLE' || raw === 'SOSPECHOSA') {
    return raw;
  }
  return undefined;
}

function mapState(verdict: TriageVerdict | undefined, invalid: boolean): FindingState {
  if (invalid) return 'Evaluación inválida';
  if (verdict === 'SOSPECHOSA') return 'Sospechosa';
  return 'Conservada';
}

function makeDiscarded(
  finding: DetailedFinding,
  meta: Obj,
  toolName: string,
): DiscardedAlert {
  const origin = text(meta.origen) || text(meta.triageOrigin);
  const why = origin === 'politica'
    ? 'Política de seguridad: la regla no se descarta automáticamente'
    : 'Recomendación LLM (SAFE)';
  const detail = [
    text(meta.explicacion) || finding.explanation,
    text(meta.cwe) && text(meta.cwe) !== 'Ninguno'
      ? `CWE propuesto: ${text(meta.cwe)}`
      : '',
  ]
    .filter(Boolean)
    .join('\n\n');
  const trace = [
    `${toolName || finding.src} → ${finding.rule} → ${finding.loc}`,
    `Veredicto: ${text(meta.veredicto) || finding.triageVerdict || 'SAFE'}`,
    `Origen: ${origin || finding.triageOrigin || 'llm'}`,
  ];

  return {
    id: finding.id,
    title: finding.title,
    sub: finding.sub,
    loc: finding.loc,
    why,
    detail: {
      text: detail,
      trace,
      vector: finding.attackVector,
      correction: finding.correction || text(meta.correccion),
      code: finding.codeContext,
    },
  };
}

function buildSummary(
  findings: DetailedFinding[],
  discarded: DiscardedAlert[],
  scan: Obj,
  resumen: Obj,
  filename: string,
  fallbackTools: string[] = [],
): ReportSummary {
  const rawSeverity = obj(resumen.por_severidad);
  let severityCounts = {
    critica: count(rawSeverity.critica) + count(rawSeverity['crítica']),
    alta: count(rawSeverity.alta),
    media: count(rawSeverity.media),
    baja: count(rawSeverity.baja),
  };

  if (severityCounts.critica + severityCounts.alta + severityCounts.media + severityCounts.baja === 0) {
    severityCounts = {
      critica: findings.filter((finding) => finding.sev === 'Crítica').length,
      alta: findings.filter((finding) => finding.sev === 'Alta').length,
      media: findings.filter((finding) => finding.sev === 'Media').length,
      baja: findings.filter((finding) => finding.sev === 'Baja').length,
    };
  }

  const rawCwe = obj(resumen.por_cwe);
  const cweCounts: Record<string, number> = Object.keys(rawCwe).length
    ? Object.fromEntries(Object.entries(rawCwe).map(([key, value]) => [key, count(value)]))
    : findings.reduce<Record<string, number>>((acc, finding) => {
        if (!finding.cwe) return acc;
        acc[finding.cwe] = (acc[finding.cwe] || 0) + 1;
        return acc;
      }, {});

  const scanTools = arr(scan.tool_runs)
    .map((run) => text(obj(run).tool))
    .filter(Boolean);
  const tools = Array.from(new Set(fallbackTools.length ? fallbackTools : scanTools));
  const toolVersion = arr(scan.tool_runs)
    .map((run) => text(obj(run).version))
    .find(Boolean);

  return {
    scanId: text(scan.scan_id) || text(resumen.scan_id) || 'local',
    target: text(scan.target) || 'objetivo desconocido',
    created: text(scan.created) || new Date().toISOString(),
    tool: tools.join(' · '),
    toolVersion: toolVersion || 'v0.8.0',
    totalAlerts: count(resumen.total) || findings.length,
    conservedAlerts: count(resumen.conservadas)
      || findings.filter((finding) => finding.state === 'Conservada').length,
    discardedAlerts: count(resumen.recomendadas_descarte) || discarded.length,
    suspiciousAlerts: count(resumen.sospechosas)
      || findings.filter((finding) => finding.state === 'Sospechosa').length,
    severityCounts,
    cweCounts,
    filename,
    isRealReport: true,
  };
}

function parseProductReport(data: Obj, filename: string): ParsedReport {
  const scan = obj(data.scan);
  const resumen = obj(data.resumen);
  const findings: DetailedFinding[] = [];
  const discarded: DiscardedAlert[] = [];

  for (const rawRun of arr(scan.tool_runs)) {
    const run = obj(rawRun);
    const toolName = text(run.tool);

    for (const raw of arr(run.findings)) {
      const item = obj(raw);
      const triage = obj(item.triage);
      const verdict = mapVerdict(triage.veredicto);
      const invalid = triage.valido === false;
      const rule = text(item.rule_id);
      const cwe = text(item.cwe);
      const lineNum = count(item.line);
      const file = text(item.file);
      const analysis = text(triage.explicacion) || text(item.message);
      const finding: DetailedFinding = {
        id: text(item.finding_id) || text(item.fingerprint) || `${rule}:${file}:${lineNum}`,
        title: text(item.message) || 'Hallazgo sin descripción',
        sub: [rule, cwe].filter(Boolean).join(' · '),
        sev: mapSeverity(item.severity),
        src: mapSource(toolName),
        state: mapState(verdict, invalid),
        confidence: text(item.confidence) || 'HIGH',
        rule,
        cwe,
        loc: `${file}:${lineNum}`,
        lineNum,
        codeContext: text(item.context) || text(item.code),
        explanation: analysis,
        correction: text(triage.correccion),
        attackVector: text(triage.vector_ataque),
        functionName: text(item.function),
        triageVerdict: verdict,
        triageOrigin: text(triage.origen),
      };

      findings.push(finding);
      if (verdict === 'SAFE') discarded.push(makeDiscarded(finding, triage, toolName));
    }
  }

  return {
    summary: buildSummary(findings, discarded, scan, resumen, filename),
    findings,
    discarded,
  };
}

function parseSarifReport(data: Obj, filename: string): ParsedReport {
  const findings: DetailedFinding[] = [];
  const discarded: DiscardedAlert[] = [];
  const tools: string[] = [];

  for (const rawRun of arr(data.runs)) {
    const run = obj(rawRun);
    const driver = obj(obj(run.tool).driver);
    const toolName = text(driver.name) || 'SARIF';
    tools.push(toolName);

    for (const rawResult of arr(run.results)) {
      const result = obj(rawResult);
      const properties = obj(result.properties);
      const triage = obj(properties.triage);
      const meta: Obj = { ...properties, ...triage };
      const message = obj(result.message);
      const firstLocation = obj(arr(result.locations)[0]);
      const physical = obj(firstLocation.physicalLocation);
      const artifact = obj(physical.artifactLocation);
      const region = obj(physical.region);
      const snippet = obj(region.snippet);
      const file = text(artifact.uri) || 'archivo';
      const lineNum = count(region.startLine);
      const rule = text(result.ruleId) || text(properties.rule_id);
      const cwe = text(properties.cwe) || text(triage.cwe);
      const title = text(message.text) || 'Hallazgo SARIF';
      const verdict = mapVerdict(text(properties.veredicto) || text(triage.veredicto));
      const invalid = properties.valido === false || triage.valido === false;
      const analysis = text(properties.explicacion) || text(triage.explicacion) || title;
      const finding: DetailedFinding = {
        id: text(properties.finding_id) || text(result.id) || `${rule}:${file}:${lineNum}`,
        title,
        sub: [rule, cwe].filter(Boolean).join(' · '),
        sev: mapSeverity(text(result.level) || text(properties.severity)),
        src: mapSource(text(properties.source) || toolName),
        state: mapState(verdict, invalid),
        confidence: text(properties.confidence) || 'HIGH',
        rule,
        cwe,
        loc: `${file}:${lineNum}`,
        lineNum,
        codeContext: text(snippet.text) || text(properties.code),
        explanation: analysis,
        correction: text(properties.correccion) || text(triage.correccion),
        attackVector: text(properties.vector_ataque) || text(triage.vector_ataque),
        functionName: text(properties.function) || text(properties.functionName),
        triageVerdict: verdict,
        triageOrigin: text(properties.origen) || text(triage.origen),
      };

      findings.push(finding);
      if (verdict === 'SAFE') discarded.push(makeDiscarded(finding, meta, toolName));
    }
  }

  return {
    summary: buildSummary(findings, discarded, {}, {}, filename, tools),
    findings,
    discarded,
  };
}

export function parseReport(content: string, filename = 'reporte.json'): ParsedReport {
  const data: unknown = JSON.parse(content);
  if (!data || typeof data !== 'object' || Array.isArray(data)) {
    throw new Error('El archivo no contiene un reporte válido');
  }

  const root = data as Obj;
  if (text(root.version).startsWith('2.') && Array.isArray(root.runs)) {
    return parseSarifReport(root, filename);
  }
  return parseProductReport(root, filename);
}
