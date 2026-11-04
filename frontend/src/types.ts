export type ViewId =
  | 'dashboard'
  | 'progreso'
  | 'hallazgos'
  | 'detalle'
  | 'descartadas'
  | 'informe';

export type Severity = 'Crítica' | 'Alta' | 'Media' | 'Baja';
export type Scanner = 'Gitleaks' | 'Bandit' | 'osv-scanner' | 'SAST';
export type FindingState = 'Conservada' | 'Evaluación inválida' | 'Sospechosa';
export type DiscardReason =
  | 'Datos de prueba'
  | 'Uso no sensible'
  | 'Ejemplo aislado'
  | 'Recomendación LLM (SAFE)'
  | 'Patrón no vulnerable';

export interface Finding {
  id: string;
  sev: Severity;
  title: string;
  sub: string;
  src: Scanner;
  rule: string;
  loc: string;
  state: FindingState;
  focus?: boolean;
}

export interface DetailedFinding extends Finding {
  cwe?: string;
  functionName?: string;
  codeContext?: string;
  lineNum?: number;
  triageVerdict?: 'VULNERABLE' | 'SAFE' | 'SOSPECHOSA';
  explanation?: string;
  attackVector?: string;
  correction?: string;
  triageOrigin?: string;
  confidence?: string;
}

export interface DiscardedAlert {
  id: string;
  title: string;
  sub: string;
  loc: string;
  why: DiscardReason | string;
  detail?: {
    text: string;
    trace: string[];
    vector?: string;
    correction?: string;
    code?: string;
  };
}

export interface ReportSummary {
  scanId: string;
  target: string;
  created: string;
  tool: string;
  toolVersion: string;
  totalAlerts: number;
  conservedAlerts: number;
  discardedAlerts: number;
  suspiciousAlerts: number;
  severityCounts: {
    critica: number;
    alta: number;
    media: number;
    baja: number;
  };
  cweCounts: Record<string, number>;
  isRealReport: boolean;
  filename?: string;
}
