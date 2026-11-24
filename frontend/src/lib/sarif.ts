import type { DetailedFinding } from '../types';

export function buildSarif(findings: DetailedFinding[]): string {
  const results = findings.map((f) => ({
    ruleId: f.rule,
    level: f.sev === 'Crítica' || f.sev === 'Alta' ? 'error' : f.sev === 'Media' ? 'warning' : 'note',
    message: { text: f.title },
    locations: [
      {
        physicalLocation: {
          artifactLocation: { uri: f.loc.split(':')[0] || f.loc },
          region: {
            startLine: f.lineNum || 1,
          },
        },
      },
    ],
    properties: {
      cwe: f.cwe,
      owasp: f.src,
      confidence: f.confidence,
      state: f.state,
      verdict: f.triageVerdict,
    },
  }));

  const sarif = {
    $schema: 'https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json',
    version: '2.1.0',
    runs: [
      {
        tool: { driver: { name: 'ciberai-web', version: '0.8.0' } },
        results,
      },
    ],
  };

  return JSON.stringify(sarif, null, 2);
}
