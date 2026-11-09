# Corrida sobre repositorios reales

Generado por `eval/corrida_repos_reales.py` el 2026-11-08.

Prueba de humo reproducible, no una evaluación etiquetada: no hay verdad de referencia por línea, así que **no produce FPRR ni FNR**. Mide cuántas alertas recomienda descartar cada modelo y cuánto coinciden.

## 1. Repositorios

| Repo | Etiqueta | Commit | Subdirectorio | Alertas |
|---|---|---|---|---:|
| `itsdangerous` | 2.2.0 | `096c8d42545d3b68ea21a4f890fb2b2d8979c0bd` | `src` | 2 |
| `pyjwt` | 2.10.1 | `3ebbb22f30f2b1b41727b269a08b427e9a85d6bb` | `jwt` | 1 |
| `httpie` | 3.2.4 | `2105caa49bae87c5809c274e407619a0de2639d1` | `httpie` | 35 |

## 2. Resultados

| Modelo | Alertas | SAFE | Conservadas | SOSPECHOSA | Errores | % SAFE |
|---|---:|---:|---:|---:|---:|---:|
| Base | 38 | 4 | 38 | 2 | 2 | 10,5 % |
| D | 38 | 34 | 38 | 0 | 0 | 89,5 % |

| Repo | Alertas | SAFE base | SAFE D | Acuerdo |
|---|---:|---:|---:|---:|
| `itsdangerous` | 2 | 0 | 1 | 1/2 |
| `pyjwt` | 1 | 0 | 0 | 1/1 |
| `httpie` | 35 | 4 | 33 | 6/35 |

## 3. Cobertura OWASP

| Categoría | Alertas | SAFE base | SAFE D |
|---|---:|---:|---:|
| A01 | 1 | 0 | 0 |
| A02 | 1 | 0 | 0 |
| A03 | 10 | 1 | 10 |
| A07 | 2 | 0 | 2 |
| sin_categoria | 24 | 3 | 22 |

## 4. Decisión de D por severidad del SAST

| Severidad | Alertas | SAFE base | SAFE D | % SAFE D |
|---|---:|---:|---:|---:|
| alta | 2 | 0 | 0 | 0,0 % |
| baja | 34 | 4 | 34 | 100,0 % |
| media | 2 | 0 | 0 | 0,0 % |

## 5. Discrepancias entre modelos

| Repo | Regla | Severidad | Archivo:Línea | Base | D |
|---|---|---|---|---|---|
| `itsdangerous` | B110 | baja | `itsdangerous/timed.py:114` | VULNERABLE | SAFE |
| `httpie` | B101 | baja | `cli/argparser.py:416` | VULNERABLE | SAFE |
| `httpie` | B101 | baja | `cli/dicts.py:65` | VULNERABLE | SAFE |
| `httpie` | B101 | baja | `cli/nested_json/interpret.py:115` | VULNERABLE | SAFE |
| `httpie` | B101 | baja | `cli/nested_json/parse.py:48` | VULNERABLE | SAFE |
| `httpie` | B101 | baja | `cli/utils.py:53` | VULNERABLE | SAFE |
| `httpie` | B101 | baja | `downloads.py:263` | VULNERABLE | SAFE |
| `httpie` | B101 | baja | `downloads.py:319` | VULNERABLE | SAFE |
| `httpie` | B101 | baja | `downloads.py:350` | VULNERABLE | SAFE |
| `httpie` | B101 | baja | `downloads.py:369` | VULNERABLE | SAFE |
| `httpie` | B101 | baja | `downloads.py:370` | VULNERABLE | SAFE |
| `httpie` | B101 | baja | `internal/daemon_runner.py:44` | VULNERABLE | SAFE |
| `httpie` | B101 | baja | `internal/daemon_runner.py:45` | SOSPECHOSA | SAFE |
| `httpie` | B603 | baja | `internal/daemons.py:29` | VULNERABLE | SAFE |
| `httpie` | B404 | baja | `internal/daemons.py:33` | SOSPECHOSA | SAFE |
| `httpie` | B101 | baja | `manager/cli.py:100` | VULNERABLE | SAFE |
| `httpie` | B404 | baja | `manager/compat.py:3` | VULNERABLE | SAFE |
| `httpie` | B603 | baja | `manager/compat.py:30` | VULNERABLE | SAFE |
| `httpie` | B603 | baja | `manager/compat.py:52` | VULNERABLE | SAFE |
| `httpie` | B408 | baja | `output/formatters/xml.py:7` | VULNERABLE | SAFE |
| `httpie` | B101 | baja | `output/streams.py:45` | VULNERABLE | SAFE |
| `httpie` | B101 | baja | `output/streams.py:212` | VULNERABLE | SAFE |
| `httpie` | B404 | baja | `output/ui/man_pages.py:3` | VULNERABLE | SAFE |
| `httpie` | B603 | baja | `output/ui/man_pages.py:26` | VULNERABLE | SAFE |
| `httpie` | B603 | baja | `output/ui/man_pages.py:44` | VULNERABLE | SAFE |
| `httpie` | B101 | baja | `output/ui/palette.py:97` | VULNERABLE | SAFE |
| `httpie` | B101 | baja | `output/ui/rich_progress.py:109` | VULNERABLE | SAFE |
| `httpie` | B105 | baja | `sessions.py:144` | VULNERABLE | SAFE |
| `httpie` | B105 | baja | `sessions.py:280` | VULNERABLE | SAFE |
| `httpie` | B101 | baja | `sessions.py:303` | VULNERABLE | SAFE |

## 6. Lectura

- Ninguna alerta se elimina: `conservadas == alertas` en los dos modelos. Un `SAFE` es una recomendación para revisión humana.
- La corrida no etiqueta aciertos. Los porcentajes de SAFE miden ahorro potencial de revisión, no corrección. Para corrección está el banco sintético etiquetado y la auditoría manual de `docs/SMOKE_REPOS.md`.
- Si D recomienda descartar casi todas las alertas de severidad baja y ninguna de severidad media o alta, la decisión puede explicarse por la severidad que reporta Bandit y no por el contexto del código. El banco sintético mide esa hipótesis de forma directa.
- Los repos están pinneados por commit. El escaneo se limita al paquete fuente para no mezclar pruebas, documentación ni entornos virtuales.
