import { useEffect, useState } from 'react';
import { VIEWS } from '../data';
import type { ViewId } from '../types';

function readHash(): ViewId {
  const h = window.location.hash.slice(1);
  const found = VIEWS.find((v) => v.id === h);
  return found ? found.id : 'dashboard';
}

/** Router mínimo basado en el hash de la URL (#dashboard, #hallazgos…). */
export function useHashRoute(): ViewId {
  const [view, setView] = useState<ViewId>(readHash);

  useEffect(() => {
    const onChange = () => {
      setView(readHash());
      window.scrollTo(0, 0);
    };
    window.addEventListener('hashchange', onChange);
    return () => window.removeEventListener('hashchange', onChange);
  }, []);

  return view;
}

export function goTo(view: ViewId): void {
  window.location.hash = `#${view}`;
}
