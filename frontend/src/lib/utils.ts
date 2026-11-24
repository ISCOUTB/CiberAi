import type { Severity } from '../types';

export function sevClass(sev: Severity): string {
  switch (sev) {
    case 'Crítica':
      return 'crit';
    case 'Alta':
      return 'alta';
    case 'Media':
      return 'media';
    case 'Baja':
      return 'baja';
    default:
      return '';
  }
}

export function mmss(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
}

export function download(filename: string, content: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
