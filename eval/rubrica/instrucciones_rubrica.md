# Rúbrica de Auditoría de Explicaciones (Sprint 7)

Esta auditoría evalúa cualitativamente la calidad técnica de las explicaciones generadas
por el modelo de triage (`qwen2.5-coder-triage`).

## Procedimiento
1. Dos evaluadores califican de forma independiente y a ciegas la muestra en sus respectivos archivos CSV.
2. Cada fila corresponde a una alerta analizada con su fragmento de código y la respuesta del modelo.
3. Asigne a cada criterio un puntaje entero entre **0** y **2** según la siguiente escala:

| Criterio | 0 (Deficiente) | 1 (Aceptable / Parcial) | 2 (Excelente / Preciso) |
|---|---|---|---|
| **CWE correcto** | Incorrecto o ausente | Familia equivalente o relacionada | CWE exacto y pertinente |
| **Vector de ataque** | Ausente, ficticio o genérico | Plausible conceptualmente pero sin detalle del código | Concreto, identifica variables y flujo consistente |
| **Corrección** | Ausente, sintácticamente errónea o insegura | Recomendación genérica (ej. "validar entrada") | Código aplicable, idiomático y preserva el comportamiento |
| **Claridad** | Incomprensible, redundante o contradictoria | Comprensible con esfuerzo o ambigua | Directa, técnica, concisa y sin ambigüedad |

## Cálculo de Acuerdo
Al completar ambas hojas, ejecute:
```powershell
python eval/rubrica_explicaciones.py calcular-acuerdo --r1 eval/rubrica/evaluador_1.csv --r2 eval/rubrica/evaluador_2.csv
```
