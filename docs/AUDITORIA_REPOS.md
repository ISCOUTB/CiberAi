# Auditoría manual de alertas en repositorios reales

Auditoría de las alertas que D recomendó descartar (`SAFE`) y de las que conservó
(`VULNERABLE`) sobre `itsdangerous`, `pyjwt` y `httpie`. Cada alerta se etiquetó
como `real` (merece conservarse) o `falso_positivo` (se puede descartar).

## Resumen

| Métrica | Valor |
|---|---:|
| Alertas auditadas | 38 |
| SAFE auditados | 34 |
| Reales | 7 |
| Falsos positivos | 31 |
| FPRR (FP descartados / total FP) | 100.0 % |
| FNR (reales descartados / total reales) | 0.0 % |
| Precisión de los descartes | 91.2 % |
| Exactitud | 92.1 % |

## Matriz de decisión

|  | D recomienda descarte (SAFE) | D conserva (VULNERABLE) |
|---|---:|---:|
| Falso positivo real | 31 | 0 |
| Alerta real | 3 | 4 |

## Límites

- Muestra pequeña (38 alertas) y un solo anotador.
- Los repos se eligieron por ser conocidos y estar pinneados por commit; no son
  una muestra aleatoria de proyectos Python.
- La etiqueta depende del contexto del caso; la justificación de cada fila está en
  `eval/auditoria_repos.jsonl`.

## Detalle por alerta

| # | Repo | Regla | Severidad | D | Etiqueta | Justificación |
|---|---|---|---|---|---|---|
| 1 | itsdangerous | B324 | alta | VULNERABLE | real | uso de SHA-1 como algoritmo de firma; aunque sea configurable, es un hash débil. |
| 2 | itsdangerous | B110 | baja | SAFE | falso_positivo | pass intencional en manejo de formato de timestamp. |
| 3 | pyjwt | B310 | media | VULNERABLE | real | urlopen sin validación de URL; potencial SSRF. |
| 4 | httpie | B101 | baja | SAFE | falso_positivo | assert en prueba o código auxiliar; no es control de seguridad. |
| 5 | httpie | B101 | baja | SAFE | falso_positivo | assert en prueba o código auxiliar; no es control de seguridad. |
| 6 | httpie | B101 | baja | SAFE | falso_positivo | assert en prueba o código auxiliar; no es control de seguridad. |
| 7 | httpie | B101 | baja | SAFE | falso_positivo | assert en prueba o código auxiliar; no es control de seguridad. |
| 8 | httpie | B101 | baja | SAFE | falso_positivo | assert en prueba o código auxiliar; no es control de seguridad. |
| 9 | httpie | B101 | baja | SAFE | falso_positivo | assert en prueba o código auxiliar; no es control de seguridad. |
| 10 | httpie | B101 | baja | SAFE | falso_positivo | assert en prueba o código auxiliar; no es control de seguridad. |
| 11 | httpie | B101 | baja | SAFE | falso_positivo | assert en prueba o código auxiliar; no es control de seguridad. |
| 12 | httpie | B101 | baja | SAFE | falso_positivo | assert en prueba o código auxiliar; no es control de seguridad. |
| 13 | httpie | B101 | baja | SAFE | falso_positivo | assert en prueba o código auxiliar; no es control de seguridad. |
| 14 | httpie | B101 | baja | SAFE | falso_positivo | assert en prueba o código auxiliar; no es control de seguridad. |
| 15 | httpie | B101 | baja | SAFE | falso_positivo | assert en prueba o código auxiliar; no es control de seguridad. |
| 16 | httpie | B101 | baja | SAFE | falso_positivo | assert en prueba o código auxiliar; no es control de seguridad. |
| 17 | httpie | B101 | baja | SAFE | falso_positivo | assert en prueba o código auxiliar; no es control de seguridad. |
| 18 | httpie | B101 | baja | SAFE | falso_positivo | assert en prueba o código auxiliar; no es control de seguridad. |
| 19 | httpie | B404 | baja | SAFE | falso_positivo | import de módulo considerado inseguro; el uso es legítimo y controlado. |
| 20 | httpie | B603 | baja | SAFE | real | Popen recibe cmd como parámetro; potencial inyección si viene de entrada externa. |
| 21 | httpie | B404 | baja | SAFE | falso_positivo | import de módulo considerado inseguro; el uso es legítimo y controlado. |
| 22 | httpie | B501 | alta | VULNERABLE | real | requests.get con verify=False; omite verificación de certificado TLS. |
| 23 | httpie | B113 | media | VULNERABLE | real | requests.get con verify=False; omite verificación de certificado TLS. |
| 24 | httpie | B101 | baja | SAFE | falso_positivo | assert en prueba o código auxiliar; no es control de seguridad. |
| 25 | httpie | B404 | baja | SAFE | falso_positivo | import de módulo considerado inseguro; el uso es legítimo y controlado. |
| 26 | httpie | B603 | baja | SAFE | falso_positivo | pip_location viene de shutil.which y args son internos; uso controlado. |
| 27 | httpie | B603 | baja | SAFE | falso_positivo | pip_executable y args son internos del gestor; uso controlado. |
| 28 | httpie | B408 | baja | SAFE | falso_positivo | import de módulo considerado inseguro; el uso es legítimo y controlado. |
| 29 | httpie | B101 | baja | SAFE | falso_positivo | assert en prueba o código auxiliar; no es control de seguridad. |
| 30 | httpie | B101 | baja | SAFE | falso_positivo | assert en prueba o código auxiliar; no es control de seguridad. |
| 31 | httpie | B404 | baja | SAFE | falso_positivo | import de módulo considerado inseguro; el uso es legítimo y controlado. |
| 32 | httpie | B603 | baja | SAFE | real | program puede venir de la CLI del usuario; advierte ejecución de comando. |
| 33 | httpie | B603 | baja | SAFE | real | program puede venir de la CLI del usuario; advierte ejecución de comando. |
| 34 | httpie | B101 | baja | SAFE | falso_positivo | assert en prueba o código auxiliar; no es control de seguridad. |
| 35 | httpie | B101 | baja | SAFE | falso_positivo | assert en prueba o código auxiliar; no es control de seguridad. |
| 36 | httpie | B105 | baja | SAFE | falso_positivo | password: None es una clave de diccionario, no credencial embebida. |
| 37 | httpie | B105 | baja | SAFE | falso_positivo | password: None es una clave de diccionario, no credencial embebida. |
| 38 | httpie | B101 | baja | SAFE | falso_positivo | assert en prueba o código auxiliar; no es control de seguridad. |

## Reproducción

```powershell
python eval/auditoria_repos.py --preparar
# editar eval/auditoria_repos.jsonl
python eval/auditoria_repos.py --calcular
```
