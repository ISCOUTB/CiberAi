# Auditoría de falsos negativos (C0 y D)

Análisis de sensibilidad sobre las alertas reales que C0 y D recomiendan
descartar. No reemplaza el resultado del holdout: lo complementa. La etiqueta
del conjunto es **a nivel de fragmento** (`is_vulnerable`), de modo que cualquier
alerta de Bandit sobre un fragmento vulnerable cuenta como real, aunque la línea
señalada sea otra. Aquí se adjudica **a nivel de alerta**: si la línea señalada
corresponde a una vulnerabilidad real en ese contexto.

Cifras reproducibles con:

```
python eval/auditar_fn.py
```

El script lee `eval/auditoria_fn.json` (adjudicación manual), los conjuntos
`eval/eval_set.jsonl` y `eval/holdout_set.jsonl`, y los cuatro archivos de
resultados. Verifica que cada falso negativo tenga un caso auditado, que la
evidencia objetiva no contradiga el veredicto y escribe `eval/analisis_fn.json`.

## 1. Criterio de adjudicación

| Regla | Se considera real si… | Se considera ruido si… |
|---|---|---|
| B403 (pickle) | el fragmento deserializa (`pickle.load` o `pickle.loads`) | solo importa `pickle` o solo hace `pickle.dump` |
| B404 (subprocess) | el import acompaña a `shell=True` sobre entrada externa | el import no se usa en un flujo peligroso |
| B311 (random) | el valor aleatorio alimenta token, clave, nonce o sesión | se usa en cálculos, demos o pruebas |

El criterio es de **patrón**: importar `pickle` es un aviso, pero la
vulnerabilidad aparece cuando hay deserialización. No se exige que el dato sea
no confiable en este fragmento concreto; si se exigiera, los cinco casos de
pickle que aquí se consideran reales también serían dudosos, porque el payload
lo genera el propio script. Esa es la principal limitación del análisis.

## 2. Los doce casos auditados

| Conjunto | Alerta | Regla | Veredicto | Evidencia |
|---|---|---|---|---|
| Desarrollo | `f12443.py:1` | B403 | real | `pickle.load` + `pickle.loads` |
| Desarrollo | `f1448.py:1` | B403 | ruido | solo `pickle.dump` |
| Desarrollo | `f14508.py:1` | B403 | real | `pickle.load` (FN de C0 y D) |
| Desarrollo | `f2077.py:1` | B403 | ruido | solo `pickle.dump` |
| Desarrollo | `f8631.py:1` | B403 | real | `pickle.loads` |
| Desarrollo | `f2404.py:2` | B404 | real | `check_output(..., shell=True)` con `input()` |
| Holdout | `f11445.py:1` | B403 | real | `pickle.load` + `pickle.loads` |
| Holdout | `f15804.py:1` | B403 | ruido | solo `pickle.dump` |
| Holdout | `f16317.py:7` | B311 | ruido | `random.randint` para una división |
| Holdout | `f16317.py:8` | B311 | ruido | segunda alerta del mismo fragmento |
| Holdout | `f1878.py:1` | B403 | real | `pickle.load` |
| Holdout | `f2231.py:1` | B403 | ruido | solo `pickle.dump` |

En total: **5 reales y 7 ruido** entre los doce. La distribución por modelo y
conjunto se resume abajo.

## 3. Métricas corregidas

| Conjunto | Modelo | FN brutos | FN reales | Ruido | FNR bruto | FNR ajustado | FPRR bruto | FPRR ajustado |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Desarrollo | C0 | 2 | 2 | 0 | 2,2 % | 2,2 % | 22,0 % | 22,0 % |
| Desarrollo | D | 5 | 3 | 2 | 5,5 % | 3,3 % | 48,0 % | 52,0 % |
| Holdout | C0 | 0 | 0 | 0 | 0,0 % | 0,0 % | 10,9 % | 10,9 % |
| Holdout | D | 6 | 2 | 4 | 9,2 % | 3,1 % | 30,4 % | 39,1 % |

La precisión de las recomendaciones de descarte de D sube de 82,8 % a 89,7 % en
desarrollo y de 70,0 % a 90,0 % en el holdout: **nueve de cada diez descartes
recomendados son correctos** cuando se juzga la línea señalada y no el fragmento.

## 4. Qué cambia y qué no

Lo que no cambia:

- El resultado pre-registrado sigue siendo el de la etiqueta de fragmento:
  D omite más que C0 (5,5 % frente a 2,2 % en desarrollo; 9,2 % frente a 0 % en
  holdout). La auditoría no reetiqueta el holdout ni sustituye esa medición.
- El ajuste fino sigue sin ser una mejora automática: la ganancia en reducción
  de ruido no está demostrada en el holdout (su IC95 incluye el cero).

Lo que cambia:

- De las 11 omisiones brutas (5 en desarrollo, 6 en holdout), **6 son ruido de
  etiqueta** y no vulnerabilidades de la línea señalada. La omisión real de D
  baja a 3 y 2 alertas.
- La diferencia frente a C0 se reduce a **1 alerta en desarrollo y 2 en el
  holdout**. Con esa magnitud, la prueba exacta de McNemar sobre alertas reales
  ya no es significativa (desarrollo: b = 2, c = 1, p = 1,00; holdout: b = 2,
  c = 0, p = 0,50). El empeoramiento de FNR **no está demostrado** una vez
  descontado el ruido.
- El intercambio se lee mejor: D elimina 16 falsos positivos por cada 2 alertas
  reales que pierde, en ambos conjuntos (frente a 4,3 y 1,5 con la etiqueta de
  fragmento). Sigue siendo un intercambio, pero mucho menos desfavorable.

## 5. Efecto de la política de no descarte

Si se aplica la política ya existente (`DEFAULT_NEVER_DISCARD = {"B403"}`, que
convierte todo `SAFE` de esa regla en `SOSPECHOSA`):

| Conjunto | Modelo | FNR | FPRR | Precisión del descarte |
|---|---|---:|---:|---:|
| Desarrollo | C0 | 1,1 % | 20,0 % | 90,9 % |
| Desarrollo | D | 0,0 % | 38,0 % | 100,0 % |
| Holdout | C0 | 0,0 % | 8,7 % | 100,0 % |
| Holdout | D | 0,0 % | 23,9 % | 100,0 % |

D con la política domina a C0 en reducción de ruido sin perder ninguna alerta
real en el holdout. Pero el número es **post hoc**: la regla B403 se fijó después
de ver los errores. Lo que sí se puede afirmar es que un criterio derivado solo
de desarrollo —«ninguna regla donde el modelo haya descartado una alerta real
puede producir SAFE»— habría seleccionado B403, porque en desarrollo es la regla
con más descartes y la única con omisiones reales. Esa es la hipótesis que debe
pre-registrarse y validarse en la próxima evaluación, no un resultado ya probado.

## 6. Limitaciones

- La adjudicación es manual y **no fue a ciegas**: se conocía el veredicto del
  modelo. El criterio es objetivo (presencia o ausencia del sink), y el script
  comprueba que la evidencia no lo contradiga, pero falta una segunda revisión
  independiente. La hoja ciega ya está generada en
  `eval/rubrica/auditoria_fn_ciega.csv` (12 casos mezclados, sin veredicto del
  modelo ni etiqueta del conjunto) y el acuerdo se calculará con
  `python eval/acuerdo_auditoria.py`.
- El criterio es de patrón, no de flujo de datos. Si se exige un origen no
  confiable, los cinco casos de pickle con `load` también serían discutibles y
  el FNR ajustado de ambos modelos bajaría a cero.
- La muestra es pequeña: 12 casos. No permite afirmar equivalencia entre C0 y D,
  solo descartar que la diferencia observada sea grande.
- La etiqueta de fragmento sigue siendo la referencia del conjunto; esta
  auditoría no la corrige, solo mide cuánto pesa en el resultado.
