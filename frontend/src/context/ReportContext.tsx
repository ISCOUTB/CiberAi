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

interface ScanRequest {
  target: string;
  scanner: string;
  model: string;
  no_llm?: boolean;
  max_alerts?: number;
  audit_max_chunks?: number;
}

interface ReportContextType {
  summary: ReportSummary;
  findings: DetailedFinding[];
  discarded: DiscardedAlert[];
  selectedFinding: DetailedFinding | null;
  selectFinding: (id: string) => void;
  loadReportFromFile: (file: File) => Promise<boolean>;
  loadReportFromJson: (content: string, filename?: string) => void;
  resetToDemo: () => void;
  runScan: (req: ScanRequest) => Promise<string>;
  pollScan: (jobId: string) => Promise<boolean>;
  refreshReport: () => Promise<void>;
  loading: boolean;
  loadingScan: boolean;
  error: string | null;
  scanError: string | null;
}

const ReportContext = createContext<ReportContextType | undefined>(undefined);

async function fetchReportFromEndpoint(endpoint: string): Promise<string | null> {
  try {
    const res = await fetch(endpoint);
    if (!res.ok) return null;
    return await res.text();
  } catch {
    return null;
  }
}

export function ReportProvider({ children }: { children: React.ReactNode }) {
  const [summary, setSummary] = useState<ReportSummary>(DEFAULT_SUMMARY);
  const [findings, setFindings] = useState<DetailedFinding[]>(FINDINGS as DetailedFinding[]);
  const [discarded, setDiscarded] = useState<DiscardedAlert[]>(INITIAL_DISCARDED);
  const [selectedFindingId, setSelectedFindingId] = useState<string>('SEC-024-003');
  const [loading, setLoading] = useState(false);
  const [loadingScan, setLoadingScan] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [scanError, setScanError] = useState<string | null>(null);

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

  const refreshReport = async () => {
    setLoading(true);
    setError(null);
    try {
      const text = await fetchReportFromEndpoint('/api/report');
      if (text) {
        loadReportFromJson(text, 'reporte.json (servidor)');
      }
    } catch (err: any) {
      setError(err.message || 'Error al recargar el reporte');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let active = true;
    async function loadInitial() {
      try {
        const text = await fetchReportFromEndpoint('/api/report');
        if (!text && active) {
          // Fallback al archivo estático si el backend aún no sirve /api/report
          const fallback = await fetchReportFromEndpoint('/reporte.json');
          if (fallback && active) {
            loadReportFromJson(fallback, 'reporte.json (automático)');
          }
          return;
        }
        if (text && active) {
          loadReportFromJson(text, 'reporte.json (servidor)');
        }
      } catch (err) {
        // Si no hay reporte disponible, se mantienen los datos demo
      }
    }
    loadInitial();
    return () => {
      active = false;
    };
  }, []);

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
    setScanError(null);
  };

  const runScan = async (req: ScanRequest): Promise<string> => {
    setLoadingScan(true);
    setScanError(null);
    try {
      const res = await fetch('/api/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Error al iniciar el escaneo');
      }
      return data.job_id as string;
    } catch (err: any) {
      setScanError(err.message || 'Error al iniciar el escaneo');
      setLoadingScan(false);
      throw err;
    }
  };

  const pollScan = async (jobId: string): Promise<boolean> => {
    try {
      const res = await fetch(`/api/scan/${jobId}`);
      const data = await res.json();
      if (!res.ok) {
        setScanError(data.detail || 'Error consultando el escaneo');
        setLoadingScan(false);
        return true;
      }
      if (data.status === 'done') {
        setLoadingScan(false);
        await refreshReport();
        return true;
      }
      if (data.status === 'error') {
        setScanError(data.error || 'El escaneo falló');
        setLoadingScan(false);
        return true;
      }
      return false;
    } catch (err: any) {
      setScanError(err.message || 'Error consultando el escaneo');
      setLoadingScan(false);
      return true;
    }
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
        runScan,
        pollScan,
        refreshReport,
        loading,
        loadingScan,
        error,
        scanError,
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
