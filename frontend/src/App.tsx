import type { ReactElement } from 'react';
import { Layout } from './components/Layout';
import { ReportProvider } from './context/ReportContext';
import { useHashRoute } from './hooks/useHashRoute';
import { ToastProvider } from './hooks/useToast';
import type { ViewId } from './types';
import { Dashboard } from './views/Dashboard';
import { Detail } from './views/Detail';
import { Discarded } from './views/Discarded';
import { Findings } from './views/Findings';
import { Progress } from './views/Progress';
import { Report } from './views/Report';

const SCREENS: Record<ViewId, () => ReactElement> = {
  dashboard: Dashboard,
  progreso: Progress,
  hallazgos: Findings,
  detalle: Detail,
  descartadas: Discarded,
  informe: Report,
};

export default function App() {
  const view = useHashRoute();
  const Screen = SCREENS[view];

  return (
    <ToastProvider>
      <ReportProvider>
        <Layout view={view}>
          <Screen />
        </Layout>
      </ReportProvider>
    </ToastProvider>
  );
}
