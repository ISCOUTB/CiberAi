# Pre-registro: política de reglas sin descarte (derivada de desarrollo)

Fecha: 7 de noviembre de 2026. Este documento fija, **antes de cualquier
evaluación nueva**, el criterio con el que se seleccionan las reglas del SAST
para las que el agente nunca recomienda descarte. Sirve para que el efecto de la
política deje de ser un cálculo post hoc: la próxima evaluación sobre un
conjunto nuevo lo validará o lo refutará.

## 1. Criterio de selección

> Ninguna regla para la que el modelo haya recomendado descartar una alerta real
> en el conjunto de desarrollo puede producir un `SAFE` con descarte.

«Alerta real» se adjudica a nivel de alerta con el criterio de patrón de
`docs/AUDITORIA_FN.md` (B403 exige `pickle.load`/`pickle.loads`; B404 exige
`shell=True`; B311 exige un contexto de seguridad). El conjunto de desarrollo es
`eval/eval_set.jsonl` (141 alertas de `val_total`); el holdout no se usa para
esta derivación y permanece cerrado.

## 2. Aplicación al desarrollo

Falsos negativos de D en desarrollo, tras la auditoría (`eval/analisis_fn.json`,
bloque `desarrollo`):

| Alerta | Regla | Adjudicación |
|---|---|---|
| `f12443.py:1` | B403 | real |
| `f1448.py:1` | B403 | ruido (solo `pickle.dump`) |
| `f14508.py:1` | B403 | real |
| `f2077.py:1` | B403 | ruido (solo `pickle.dump`) |
| `f8631.py:1` | B403 | real |

Las omisiones reales son todas de **B403**. Ninguna otra regla produce un
descarte de alerta real en desarrollo. Por tanto:

```
NEVER_DISCARD = {"B403"}
```

Coincide con la política que ya implementa `triage.py`
(`DEFAULT_NEVER_DISCARD = {"B403"}`), pero ahora con una regla de selección
explícita y derivada únicamente de desarrollo. **B311 queda excluida**: sus dos
casos aparecieron solo en el holdout y la auditoría los clasificó como ruido;
incluirla sería ajustar con datos del holdout.

## 3. Hipótesis a validar en la próxima evaluación

1. Con `NEVER_DISCARD = {"B403"}`, el FNR ajustado del modelo sobre un conjunto
   nuevo será ≤ 5 %.
2. La política no degradará el FPRR por debajo de lo observado en desarrollo de
   forma material (referencia de desarrollo: D pasa de 52,0 % a 38,0 % de FPRR
   ajustado al aplicarla).
3. Si aparece una regla nueva con omisión real, se documenta y se añade a la
   política **antes** de la siguiente iteración, no después de ver el conjunto.

## 4. Lo que este documento no hace

- No reetiqueta el holdout ni cambia el resultado pre-registrado del Sprint 7.
- No justifica el descarte automático: el producto sigue en modo asesor.
- No selecciona B311 ni B404: en desarrollo no omitieron ninguna alerta real.
