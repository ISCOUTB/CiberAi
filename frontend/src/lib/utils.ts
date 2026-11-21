export function sevClass(sev: string): string {
  const value = sev.toLowerCase();
  if (value.includes('crít') || value.includes('crit') || value === 'error') return 'crit';
  if (value.includes('alta') || value === 'high') return 'alta';
  if (value.includes('media') || value === 'medium' || value === 'warning') return 'media';
  if (value.includes('baja') || value === 'low' || value === 'note') return 'baja';
  return 'plain';
}

export function mmss(seconds: number): string {
  const safe = Math.max(0, Math.floor(seconds));
  const minutes = Math.floor(safe / 60);
  const rest = safe % 60;
  return `${String(minutes).padStart(2, '0')}:${String(rest).padStart(2, '0')}`;
}

export function download(filename: string, content: string, mime = 'text/plain'): void {
  const blob = new Blob([content], { type: `${mime};charset=utf-8` });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}
