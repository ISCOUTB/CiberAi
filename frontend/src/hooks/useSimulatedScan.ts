import { useEffect, useState } from 'react';

export interface ScanSimulationState {
  running: boolean;
  completed: boolean;
  percent: number;
  seconds: number;
  evaluated: number;
  total: number;
  kept: number;
  discarded: number;
  pending: number;
  currentStep: number;
  logs: [string, string][];
}

// Estado persistente fuera del componente para que cambiar de pestaña no lo reinicie
let persistentState: ScanSimulationState = {
  running: false,
  completed: true,
  percent: 100,
  seconds: 43,
  evaluated: 9,
  total: 9,
  kept: 5,
  discarded: 4,
  pending: 0,
  currentStep: 5,
  logs: [
    ['00:00:01', 'Iniciando escaneo local sobre target'],
    ['00:00:03', 'Bandit SAST: 9 alertas encontradas'],
    ['00:00:04', 'Deduplicación completada: 9 alertas únicas'],
    ['00:00:05', 'Conectando con Ollama (qwen2.5-coder-triage)...'],
    ['00:00:15', 'Triage alerta 1/9: SAFE (B403, import pickle)'],
    ['00:00:22', 'Triage alerta 2/9: SAFE (B404, import subprocess)'],
    ['00:00:30', 'Triage alerta 5/9: VULNERABLE (B608, SQL Injection)'],
    ['00:00:38', 'Triage alerta 8/9: VULNERABLE (B602, shell=True)'],
    ['00:00:43', 'Escaneo finalizado: JSON y SARIF generados en reportes/'],
  ],
};

const listeners = new Set<(state: ScanSimulationState) => void>();

function notify() {
  listeners.forEach((listener) => listener({ ...persistentState }));
}

let intervalId: number | null = null;

export function startLiveSimulation(totalAlerts: number = 9, conserved: number = 5, discarded: number = 4) {
  if (intervalId !== null) {
    window.clearInterval(intervalId);
    intervalId = null;
  }

  persistentState = {
    running: true,
    completed: false,
    percent: 5,
    seconds: 0,
    evaluated: 0,
    total: totalAlerts,
    kept: 0,
    discarded: 0,
    pending: totalAlerts,
    currentStep: 1,
    logs: [
      ['00:00:00', 'Iniciando pipeline de análisis local...'],
      ['00:00:01', 'Ejecutando Bandit sobre el código fuente...'],
    ],
  };
  notify();

  intervalId = window.setInterval(() => {
    if (!persistentState.running) return;

    persistentState.seconds += 1;
    const s = persistentState.seconds;

    if (s === 2) {
      persistentState.currentStep = 2;
      persistentState.percent = 25;
      persistentState.logs.push(['00:00:02', `Bandit SAST: ${totalAlerts} alertas detectadas`]);
    } else if (s === 4) {
      persistentState.currentStep = 3;
      persistentState.percent = 40;
      persistentState.logs.push(['00:00:04', 'Normalización SARIF y deduplicación por archivo/línea/regla']);
    } else if (s === 6) {
      persistentState.currentStep = 4;
      persistentState.percent = 50;
      persistentState.logs.push(['00:00:06', 'Ollama activo: evaluando alertas con qwen2.5-coder-triage...']);
    } else if (s >= 7 && s < 18) {
      const stepIdx = s - 6;
      const evalCount = Math.min(totalAlerts, Math.round((stepIdx / 11) * totalAlerts));
      persistentState.evaluated = evalCount;
      persistentState.pending = totalAlerts - evalCount;
      persistentState.discarded = Math.round((evalCount / totalAlerts) * discarded);
      persistentState.kept = evalCount - persistentState.discarded;
      persistentState.percent = Math.min(95, 50 + Math.round((evalCount / totalAlerts) * 45));

      if (s % 3 === 0) {
        persistentState.logs.push([
          `00:00:${s < 10 ? '0' + s : s}`,
          `Evaluando alerta ${evalCount}/${totalAlerts}... contexto sintáctico analizado`,
        ]);
      }
    } else if (s >= 18) {
      persistentState.currentStep = 5;
      persistentState.percent = 100;
      persistentState.evaluated = totalAlerts;
      persistentState.pending = 0;
      persistentState.kept = conserved;
      persistentState.discarded = discarded;
      persistentState.running = false;
      persistentState.completed = true;
      persistentState.logs.push(['00:00:18', 'Evaluación completada. Reportes escritos en reportes/reporte.json']);

      if (intervalId !== null) {
        window.clearInterval(intervalId);
        intervalId = null;
      }
    }

    notify();
  }, 1000);
}

export function stopSimulation() {
  if (intervalId !== null) {
    window.clearInterval(intervalId);
    intervalId = null;
  }
  persistentState.running = false;
  notify();
}

export function useSimulatedScan() {
  const [state, setState] = useState<ScanSimulationState>({ ...persistentState });

  useEffect(() => {
    listeners.add(setState);
    return () => {
      listeners.delete(setState);
    };
  }, []);

  return {
    ...state,
    start: (total?: number, conserved?: number, discarded?: number) =>
      startLiveSimulation(total, conserved, discarded),
    stop: stopSimulation,
  };
}
