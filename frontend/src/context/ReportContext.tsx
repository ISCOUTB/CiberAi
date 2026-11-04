import React, { createContext, useContext, useEffect, useState } from 'react';
import { FINDINGS, INITIAL_DISCARDED, TOTAL_DISCARDED } from '../data';
import { parseReport } from '../lib/reportParser';
import type { DetailedFinding, DiscardedAlert, ReportSummary } from '../types';

const DEFAULT_SUMMARY: ReportSummary = {
  scanId: 'SEC-024',
  target: 'pagos-api / main',
  created: '2026-10-27T10:42:00.000Z',
  tool: 'Bandit · Gitleaks · osv-scanner',
  toolVersion: 'v0.8.0',
  totalAlerts: 48,
  conservedAlerts: FINDINGS.length,
  discardedAlerts: TOTAL_DISCARDED,
  suspiciousAlerts: 3,
  severityCounts: {
    critica: 2,
    alta: 5,
    media: 8,
    baja: 3,
  },
  cweCounts: {
    'CWE-89': 4,
    'CWE-78': 3,
    'CWE-502': 2,
    'CWE-259': 2,
  },
  isRealReport: false,
};

interface ReportContextType {
  summary: ReportSummary;
  findings: DetailedFinding[];
  discarded: DiscardedAlert[];
  selectedFinding: DetailedFinding | null;
  selectFinding: (id: string) => void;
  loadReportFromFile: (file: File) => Promise<boolean>;
  loadReportFromJson: (content: string, filename?: string) => void;
  resetToDemo: () => void;
  loading: boolean;
  error: string | null;
}

const ReportContext = createContext<ReportContextType | undefined>(undefined);

export function ReportProvider({ children }: { children: React.ReactNode }) {
  const [summary, setSummary] = useState<ReportSummary>(DEFAULT_SUMMARY);
  const [findings, setFindings] = useState<DetailedFinding[]>(FINDINGS as DetailedFinding[]);
  const [discarded, setDiscarded] = useState<DiscardedAlert[]>(INITIAL_DISCARDED);
  const [selectedFindingId, setSelectedFindingId] = useState<string>('SEC-024-003');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Intentar cargar automáticamente /reporte.json al inicio
  useEffect(() => {
    let active = true;
    async function loadInitial() {
      try {
        const res = await fetch('/reporte.json');
        if (res.ok && active) {
          const text = await res.text();
          const parsed = parseReport(text, 'reporte.json (automático)');
          setSummary(parsed.summary);
          setFindings(parsed.findings);
          setDiscarded(parsed.discarded);
          if (parsed.findings.length > 0) {
            setSelectedFindingId(parsed.findings[0].id);
          }
        }
      } catch (err) {
        // Si no está disponible reporte.json, se mantiene los datos demo por defecto
      }
    }
    loadInitial();
    return () => {
      active = false;
    };
  }, []);

  const loadReportFromJson = (content: string, filename: string = 'reporte.json') => {
    setError(null);
    try {
      const parsed = parseReport(content, filename);
      setSummary(parsed.summary);
      setFindings(parsed.findings);
      setDiscarded(parsed.discarded);
      if (parsed.findings.length > 0) {
        setSelectedFindingId(parsed.findings[0].id);
      }
    } catch (err: any) {
      setError(err.message || 'Error al procesar el reporte');
      throw err;
    }
  };

  const loadReportFromFile = async (file: File): Promise<boolean> => {
    setLoading(true);
    setError(null);
    try {
      const text = await file.text();
      loadReportFromJson(text, file.name);
      setLoading(false);
      return true;
    } catch (err: any) {
      setError(err.message || 'Error al leer el archivo');
      setLoading(false);
      return false;
    }
  };

  const resetToDemo = () => {
    setSummary(DEFAULT_SUMMARY);
    setFindings(FINDINGS as DetailedFinding[]);
    setDiscarded(INITIAL_DISCARDED);
    setSelectedFindingId('SEC-024-003');
    setError(null);
  };

  const selectFinding = (id: string) => {
    setSelectedFindingId(id);
    window.location.hash = '#detalle';
  };

  const selectedFinding =
    findings.find((f) => f.id === selectedFindingId) ||
    findings[0] ||
    null;

  return (
    <ReportContext.Provider
      value={{
        summary,
        findings,
        discarded,
        selectedFinding,
        selectFinding,
        loadReportFromFile,
        loadReportFromJson,
        resetToDemo,
        loading,
        error,
      }}
    >
      {children}
    </ReportContext.Provider>
  );
}

export function useReport() {
  const ctx = useContext(ReportContext);
  if (!ctx) {
    throw new Error('useReport debe usarse dentro de un ReportProvider');
  }
  return ctx;
}
