# Smoke test con repositorios reales

Prueba de humo del producto, no una evaluación etiquetada. Sirve para verificar
que el agente funciona sobre código que no se escribió para el proyecto, que las
recomendaciones de descarte se pueden auditar a mano y que el modo asesor se
mantiene. No produce FPRR ni FNR: no hay verdad de referencia por línea.

Fecha: 5 de noviembre de 2026.

## 1. Repositorios

Se eligieron tres proyectos Python pequeños, con licencia permisiva y actividad
real. Se fijó la etiqueta y el commit; el escaneo se limitó al paquete fuente
para no mezclar pruebas, documentación ni entornos virtuales.

| Repo | Etiqueta | Commit | Subdirectorio | Alertas |
|---|---|---|---|---:|
| `pallets/itsdangerous` | 2.2.0 | `096c8d42545d3b68ea21a4f890fb2b2d8979c0bd` | `src/` | 2 |
| `jpadilla/pyjwt` | 2.10.1 | `3ebbb22f30f2b1b41727b269a08b427e9a85d6bb` | `jwt/` | 1 |
| `httpie/cli` | 3.2.4 | `2105caa49bae87c5809c274e407619a0de2639d1` | `httpie/` | 35 |

```powershell
git clone --depth 1 --branch 2.2.0  https://github.com/pallets/itsdangerous
git clone --depth 1 --branch 2.10.1 https://github.com/jpadilla/pyjwt
git clone --depth 1 --branch 3.2.4  https://github.com/httpie/cli
```

El escaneo completo de cada repositorio produce muchas más alertas (68, 344 y
811) porque Bandit también analiza pruebas y utilidades. Para el smoke test se
usa el paquete fuente, que es lo que se distribuye.

## 2. Ejecución

```powershell
python agente\run.py scan <repo>\src --model qwen2.5-coder:1.5b      --out out_base_<repo> --quiet
python agente\run.py scan <repo>\src --model qwen2.5-coder-triage   --out out_d_<repo>    --quiet
python eval\auditar_smoke_repos.py --root <carpeta> --json eval\auditoria_smoke_repos.json
```

Los dos modelos se ejecutaron en modo asesor, con la política por defecto
(`B403` nunca se recomienda para descarte). No se usó `--max-alerts`: se
procesaron todas las alertas del subdirectorio.

## 3. Resultados

| Repo | Modelo | Alertas | Conservadas | SAFE | SOSPECHOSA | Errores |
|---|---|---:|---:|---:|---:|---:|
| itsdangerous | base | 2 | 2 | 0 | 0 | 0 |
| itsdangerous | D | 2 | 2 | 1 | 0 | 0 |
| pyjwt | base | 1 | 1 | 0 | 0 | 0 |
| pyjwt | D | 1 | 1 | 0 | 0 | 0 |
| httpie | base | 35 | 35 | 3 | 0 | 0 |
| httpie | D | 35 | 35 | 33 | 0 | 0 |

En los 38 escaneos por modelo, `conservadas == total`: ninguna alerta se eliminó.
No hubo respuestas inválidas ni errores de modelo.

D recomienda descartar 34 de 38 alertas (89,5 %); el modelo base, 3 de 38
(7,9 %). La diferencia es consistente con lo observado en el conjunto de
evaluación: el ajuste aumenta el ahorro de revisión. El smoke test no permite
afirmar que esos descartes sean correctos en general; para eso está la auditoría
manual de la sección siguiente.

## 4. Auditoría manual de los descartes

Se revisó el código de cada alerta recomendada como `SAFE`. La clasificación es
del autor del proyecto, no de un revisor independiente.

| Regla | Alertas SAFE | Qué es | Veredicto |
|---|---:|---|---|
| B101 | 21 | `assert` internos que verifican invariantes, no validación de entrada | Falso positivo correcto |
| B404 | 4 | Aviso de importación de `subprocess` | Falso positivo correcto |
| B603 | 5 | `subprocess` con lista constante y `shell=False` | Falso positivo correcto |
| B408 | 1 | Import de `xml.dom.minidom` bajo `TYPE_CHECKING`; en runtime se usa `defusedxml` | Falso positivo correcto |
| B105 | 2 | `password: None` como valor por defecto de la sesión | Falso positivo correcto |
| B110 | 1 | `try/except/pass` deliberado al parsear el timestamp; el flujo sigue y falla más adelante | Falso positivo correcto |

Detalle de los casos que no son `assert`:

- `httpie/internal/daemons.py`, `manager/compat.py` y `output/ui/man_pages.py`:
  `Popen`/`run` con argumentos constantes o derivados de la configuración
  interna, `shell=False`. B404 y B603 son avisos, no vulnerabilidades.
- `httpie/output/formatters/xml.py`: el import señalado es solo para tipos; la
  función real usa `defusedxml.minidom.parseString`.
- `httpie/sessions.py`: B105 señala `'password': None` en el diccionario de
  autenticación por defecto; no hay credencial embebida.
- `itsdangerous/timed.py`: la excepción silenciada deja `ts_int = None` y el
  código posterior comprueba la firma; no oculta un fallo de seguridad.

**Descartes incorrectos:** 0 de 34. **Descartes dudosos:** 0.

## 5. Alertas que el modelo conservó y debía conservar

D no recomendó descartar cuatro alertas, y en al menos un caso la conservación
está justificada:

| Repo | Regla | Ubicación | Lectura |
|---|---|---|---|
| httpie | B501 | `internal/update_warnings.py:44` | `requests.get(..., verify=False)` desactiva la validación TLS. Es un hallazgo real; el modelo lo conserva. |
| httpie | B113 | `internal/update_warnings.py:44` | La misma petición no declara `timeout`. Riesgo de disponibilidad; el modelo lo conserva. |
| itsdangerous | B324 | `signer.py:45` | `hashlib.sha1` como digest por defecto de HMAC. Bandit lo marca; el modelo lo conserva. Es una decisión conservadora, no un error. |
| pyjwt | B310 | `jwks_client.py:56` | `urlopen` sobre la URL de JWKS configurada, con `timeout` y `ssl_context`. Falso positivo probable; el modelo lo conserva. |

## 6. Lectura

El smoke test respalda tres afirmaciones acotadas:

1. El producto se ejecuta sobre repositorios que no forman parte del corpus y
   produce reportes válidos, sin eliminar alertas.
2. Las recomendaciones de descarte de D en estos tres repos son falsos positivos
   verificables a mano; no se observó ningún descarte peligroso.
3. La política conservadora funciona: una alerta real (`verify=False`) y tres
   casos dudosos se mantuvieron.

No respalda afirmar que D sea seguro para descarte automático. La muestra es de
38 alertas, el corpus no tiene etiquetas por línea y la auditoría la hizo una
sola persona. La decisión de mantener el modo asesor sigue dependiendo del
holdout: FNR 9,2 % crudo y 3,1 % con la política B403 (IC95 0,8–10,5 %).

## 7. Reproducción

El resumen legible por máquina está en `eval/auditoria_smoke_repos.json`. Los
reportes completos se generan en la carpeta que se pase a `--root`; no se
versionan porque incluyen rutas absolutas y marcas de tiempo. El script de
auditoría no decide: solo lista las recomendaciones `SAFE` para revisión.
