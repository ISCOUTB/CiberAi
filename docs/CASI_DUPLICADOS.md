# Casi-duplicados entre train/val y holdout

Generado por `eval/casi_duplicados.py` el 2026-11-08.

## 1. Qué se midió

El dataset original eliminó duplicados exactos por hash normalizado (`dataset/scripts/build_splits.py`), pero no midió similitud difusa. Este análisis compara cada función Python del holdout contra todas las funciones Python de `train_80` y `val_total`, usando similitud de secuencias de tokens sobre el código normalizado.

- Train (`dataset/splits/train_80.jsonl`): 1464 funciones Python.
- Validación (`dataset/splits/val_total.jsonl`): 649 funciones Python.
- Holdout (`eval/holdout_set.jsonl`): 111 funciones Python.

Umbral de alerta: **0.8**.

## 2. Resultados

| Métrica | Valor |
|---|---:|
| Funciones holdout analizadas | 111 |
| Funciones con vecino ≥ 0.8 | 78 |
| Porcentaje con vecino ≥ 0.8 | 70.3 % |
| Máxima similitud | 0.996 |
| Mediana de la máxima similitud | 0.861 |

Distribución de la máxima similitud por función holdout:

| Rango | Funciones | % |
|---|---:|---:|
| 0.0-0.5 | 0 | 0.0 % |
| 0.5-0.7 | 18 | 16.2 % |
| 0.7-0.8 | 19 | 17.1 % |
| 0.8-0.9 | 29 | 26.1 % |
| 0.9-1.0 | 45 | 40.5 % |

## 3. Interpretación

- Los duplicados exactos ya fueron eliminados en `build_splits.py`; este análisis mide funciones que no son idénticas pero que podrían compartir el mismo patrón o provenir del mismo proyecto.
- Un porcentaje alto de vecinos ≥ 0.8 no demuestra fuga, pero sí debilita la validez externa: el modelo pudo haber visto variantes muy similares durante el entrenamiento.
- La partición es aleatoria por función y el dataset no incluye identificador de repositorio, así que no se puede descartar que funciones del mismo proyecto caigan en train y en test.

## 4. Pares más similares

| Holdout | Similitud | Vecino en | ID vecino | Código holdout | Código vecino |
|---|---:|---|---|---|---|
| f14299.py:14 | 0.996 | train | 02b2fbb4aea78898780576876b85abd64f2914f52acc1f77c6191fed51984aec | import sqlite3 from flask import Flask, request  app = Flask(__name__)  @app.rou… | import sqlite3 from flask import Flask, request  app = Flask(__name__)  @app.rou… |
| f14299.py:23 | 0.996 | train | 02b2fbb4aea78898780576876b85abd64f2914f52acc1f77c6191fed51984aec | import sqlite3 from flask import Flask, request  app = Flask(__name__)  @app.rou… | import sqlite3 from flask import Flask, request  app = Flask(__name__)  @app.rou… |
| f14938.py:1 | 0.991 | val | a2886b16267d2d63025afda5f7aef2787af0252e544dc2ff6231ed17e5d61d75 | import pickle import os  class VulnerableClass:     def __reduce__(self):       … | import pickle import os  class VulnerableClass:     def __reduce__(self):       … |
| f14938.py:10 | 0.991 | val | a2886b16267d2d63025afda5f7aef2787af0252e544dc2ff6231ed17e5d61d75 | import pickle import os  class VulnerableClass:     def __reduce__(self):       … | import pickle import os  class VulnerableClass:     def __reduce__(self):       … |
| f13744.py:1 | 0.981 | val | d47c287fc970ca2d8140dafa583e7e0cbb4b0b362f6b9bb033d5abb11cf3fe6b | import pickle import os  class EvilClass(object):     def __reduce__(self):     … | import pickle import os  class EvilClass(object):     def __reduce__(self):     … |
| f13744.py:10 | 0.981 | val | d47c287fc970ca2d8140dafa583e7e0cbb4b0b362f6b9bb033d5abb11cf3fe6b | import pickle import os  class EvilClass(object):     def __reduce__(self):     … | import pickle import os  class EvilClass(object):     def __reduce__(self):     … |
| f11445.py:1 | 0.98 | train | 8c10168c10ab1ceac085ed203ff4f537db04159c387f20791463ed09cc93e267 | import pickle import os  class RunBinSh(object):     def __reduce__(self):      … | import pickle import os  class RunBinSh(object):     def __reduce__(self):      … |
| f11445.py:15 | 0.98 | train | 8c10168c10ab1ceac085ed203ff4f537db04159c387f20791463ed09cc93e267 | import pickle import os  class RunBinSh(object):     def __reduce__(self):      … | import pickle import os  class RunBinSh(object):     def __reduce__(self):      … |
| f11445.py:16 | 0.98 | train | 8c10168c10ab1ceac085ed203ff4f537db04159c387f20791463ed09cc93e267 | import pickle import os  class RunBinSh(object):     def __reduce__(self):      … | import pickle import os  class RunBinSh(object):     def __reduce__(self):      … |
| f3232.py:1 | 0.977 | train | 6402e887e6f33cb0cf2afc4811254bb91b23dd1e2df0bb37963cc2f7bcd9c446 | import pickle import os  class EvilPickle(object):     def __reduce__(self):    … | import pickle import os  class EvilPickle(object):     def __reduce__(self):    … |

## 5. Reproducción

```powershell
python eval/casi_duplicados.py
```
