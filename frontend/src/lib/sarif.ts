import type { DetailedFinding } from '../types';

function levelFor(sev: string): string {
  const value = sev.toLowerCase();
  if (value.includes('crít') || value.includes('crit') || value.includes('alta')) return 'error';
  if (value.includes('media')) return 'warning';
  return 'note';
}

function splitLoc(loc: string): { file: string; line: number } {
  const parts = loc.split(':');
  const rawLine = parts.pop() ?? '0';
  const line = Number.parseInt(rawLine, 10);
  return {
    file: parts.join(':') || 'archivo',
    line: Number.isFinite(line) ? line : 0,
  };
}

export function buildSarif(findings: DetailedFinding[]): string {
  const rules = Array.from(
    new Map(
      findings.map((finding) => {
        const ruleId = finding.rule || finding.id;
        return [
          ruleId,
          {
            id: ruleId,
            name: ruleId,
            shortDescription: { text: finding.title },
            properties: { cwe: finding.cwe || '' },
          },
        ];
      }),
    ).values(),
  );

  const results = findings.map((finding) => {
    const loc = splitLoc(finding.loc);
    return {
      ruleId: finding.rule || finding.id,
      level: levelFor(finding.sev),
      message: { text: finding.title },
      locations: [
        {
          physicalLocation: {
            artifactLocation: { uri: loc.file },
            region: {
              startLine: finding.lineNum || loc.line || 1,
              snippet: { text: finding.codeContext || '' },
            },
          },
        },
      ],
      partialFingerprints: { findingId: finding.id },
      properties: {
        source: finding.src,
        severity: finding.sev,
        cwe: finding.cwe || '',
        state: finding.state,
        confidence: finding.confidence || '',
        function: finding.functionName || '',
        verdict: finding.triageVerdict || '',
        triageOrigin: finding.triageOrigin || '',
        explanation: finding.explanation || '',
        correction: finding.correction || '',
        attackVector: finding.attackVector || '',
      },
    };
  });

  return JSON.stringify(
    {
      $schema: 'https://json.schemastore.org/sarif-2.1.0.json',
      version: '2.1.0',
      runs: [
        {
          tool: {
            driver: {
              name: 'ciberAi',
              version: '0.8.0',
              rules,
            },
          },
          results,
        },
      ],
    },
    null,
    2,
  );
}
