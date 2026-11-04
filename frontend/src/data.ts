import type { DiscardedAlert, Finding } from './types';

export const TOTAL_DISCARDED = 30;

export const VIEWS = [
  { id: 'dashboard', n: '01', label: 'Dashboard' },
  { id: 'progreso', n: '02', label: 'Progreso' },
  { id: 'hallazgos', n: '03', label: 'Hallazgos' },
  { id: 'detalle', n: '04', label: 'Detalle' },
  { id: 'descartadas', n: '05', label: 'Descartadas' },
  { id: 'informe', n: '06', label: 'Informe' },
] as const;

export const FINDINGS: Finding[] = [
  { id: 'SEC-024-001', sev: 'Crítica', title: 'Credencial versionada', sub: 'Valor enmascarado: ••••••••', src: 'Gitleaks', rule: 'generic-api-key', loc: 'config/production.env:8', state: 'Conservada' },
  { id: 'SEC-024-002', sev: 'Crítica', title: 'Comando con entrada externa', sub: 'B602 · shell=True', src: 'Bandit', rule: 'B602', loc: 'app/jobs/export.py:61', state: 'Conservada' },
  { id: 'SEC-024-003', sev: 'Alta', title: 'Consulta SQL construida dinámicamente', sub: 'B608 · construcción de consulta', src: 'Bandit', rule: 'B608', loc: 'app/api/payments.py:87', state: 'Conservada', focus: true },
  { id: 'SEC-024-004', sev: 'Alta', title: 'Carga YAML sin modo seguro', sub: 'B506 · yaml.load', src: 'Bandit', rule: 'B506', loc: 'app/core/config.py:34', state: 'Conservada' },
  { id: 'SEC-024-005', sev: 'Alta', title: 'Deserialización de datos no confiables', sub: 'B301 · pickle', src: 'Bandit', rule: 'B301', loc: 'app/cache/store.py:52', state: 'Conservada' },
  { id: 'SEC-024-006', sev: 'Media', title: 'Alerta SCA pendiente de validar', sub: 'Revisar evidencia local del escáner', src: 'osv-scanner', rule: 'OSV', loc: 'requirements.txt:18', state: 'Evaluación inválida' },
];

export const INITIAL_DISCARDED: DiscardedAlert[] = [
  {
    id: 'SEC-024-019',
    title: 'Credencial de prueba en fixture',
    sub: 'Gitleaks · SEC-024-019',
    loc: 'tests/fixtures/auth.env:4',
    why: 'Datos de prueba',
    detail: {
      text: 'El valor coincide con el marcador ficticio del fixture y solo se referencia desde pruebas. No se encontró uso en la configuración de ejecución dentro del alcance revisado.',
      trace: [
        'Origen: Gitleaks → SARIF → contexto de tests',
        'Decisión: descarte contextual · 27 oct, 10:41',
        'Modelo: Qwen2.5-Coder-7B · Q4_K_M',
        'Valor: •••••••• · original en SARIF local',
      ],
    },
  },
  { id: 'SEC-024-020', title: 'Assert en prueba unitaria', sub: 'Bandit · B101 · SEC-024-020', loc: 'tests/test_payments.py:42', why: 'Datos de prueba' },
  { id: 'SEC-024-021', title: 'Aleatoriedad para color de gráfico', sub: 'Bandit · B311 · SEC-024-021', loc: 'tools/chart_colors.py:19', why: 'Uso no sensible' },
  { id: 'SEC-024-022', title: 'Cadena de contraseña de ejemplo', sub: 'Bandit · B105 · SEC-024-022', loc: 'tests/fixtures/users.py:12', why: 'Datos de prueba' },
  { id: 'SEC-024-023', title: 'Consulta en ejemplo aislado', sub: 'Bandit · B608 · SEC-024-023', loc: 'examples/sql_demo.py:23', why: 'Ejemplo aislado' },
];
