import type { CSSProperties, ReactNode } from 'react';

export function Badge({
  variant = '',
  children,
}: {
  variant?: string;
  children: ReactNode;
}) {
  return <span className={`badge ${variant}`.trim()}>{children}</span>;
}

export interface StatItem {
  value: string;
  label: ReactNode;
}

export function Stats({
  items,
  line = false,
  style,
}: {
  items: StatItem[];
  line?: boolean;
  style?: CSSProperties;
}) {
  return (
    <div className={`stats${line ? ' line' : ''}`} style={style}>
      {items.map((s, i) => (
        <div className="stat" key={i}>
          <b>{s.value}</b>
          <span>{s.label}</span>
        </div>
      ))}
    </div>
  );
}

export const SEVERITY_STATS: StatItem[] = [
  { value: '02', label: 'Críticas' },
  { value: '05', label: 'Altas' },
  { value: '08', label: 'Medias' },
  { value: '03', label: 'Bajas' },
];

export function Notice({
  title,
  children,
  plain = false,
}: {
  title: string;
  children: ReactNode;
  plain?: boolean;
}) {
  return (
    <div className={`notice${plain ? ' plain' : ''}`}>
      <span className="ico">◈</span>
      <div>
        <b>{title}</b>
        {children}
      </div>
    </div>
  );
}

export function PageHead({
  crumb,
  title,
  action,
}: {
  crumb: string;
  title: string;
  action?: ReactNode;
}) {
  return (
    <>
      <div className="crumb">{crumb}</div>
      <div className="head">
        <h1>{title}</h1>
        {action}
      </div>
    </>
  );
}

export function Pager({ label, pages }: { label: string; pages: string[] }) {
  return (
    <div className="pager">
      <span>{label}</span>
      <div>
        {pages.map((p, i) => (
          <button key={p + i} className={i === 0 ? 'on' : ''} type="button">
            {p}
          </button>
        ))}
      </div>
    </div>
  );
}
