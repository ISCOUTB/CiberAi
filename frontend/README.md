# ciberAi · interfaz (React + TypeScript)

Interfaz de las 6 pantallas de ciberAi: Dashboard, Progreso, Hallazgos, Detalle, Descartadas e Informe.

## Uso

```bash
npm install
npm run dev        # servidor de desarrollo
npm run build      # comprueba tipos y genera dist/
npm run preview    # sirve dist/
```

Requiere Node 18 o superior.

## Estructura

```
src/
  App.tsx                 mapa de pantallas y layout
  data.ts / types.ts      datos de ejemplo y tipos
  hooks/
    useHashRoute.ts       router por hash (#hallazgos…)
    useToast.tsx          avisos breves
    useSimulatedScan.ts   simulación del análisis en curso
  components/             Layout y piezas de UI reutilizables
  views/                  una pantalla por archivo
  lib/                    utilidades (descargas, SARIF)
  styles.css              estilos globales con variables CSS
```

## Notas

- Todos los datos son de ejemplo (ver `src/data.ts`). Para conectarlo a la CLI, sustituye `FINDINGS`, `INITIAL_DISCARDED` y el hook `useSimulatedScan` por lecturas del SARIF real.
- La paginación de las tablas es solo visual.
- "Exportar informe PDF" usa el diálogo de impresión del navegador.
