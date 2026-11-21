# OWASP como eje del proyecto

Documento de trabajo para la memoria final. OWASP no se agrega como apéndice:
organiza el alcance, el modelo de amenaza del agente y la lectura de los
resultados. Aquí se declara qué se cubre, qué no se cubre y con qué evidencia.

Normas y versiones usadas:

| Norma | Versión | Uso en el proyecto |
|---|---|---|
| OWASP Top 10 | 2021 | Taxonomía de los CWE que Bandit reporta; matriz de cobertura. |
| OWASP Top 10 for LLM Applications | 2025 | Modelo de amenaza del componente inteligente. |
| OWASP ASVS | 5.0.0 (mayo 2025) | Checklist parcial con exclusiones declaradas. |

La versión 2021 del Top 10 se eligió porque es la que usa el dataset del proyecto
para su columna `owasp` y porque sus listas de CWE son las que corresponden a los
CWE del corpus. Usar la edición 2025 del Top 10 web habría roto la trazabilidad
con las etiquetas de entrenamiento.

## 1. Método de mapeo

El mapeo se calcula, no se declara:

1. Se toma el CWE que reporta el **detector que originó el hallazgo**: Bandit,
   el escáner OWASP propio o la auditoría directa del modelo. No se usa el CWE
   etiquetado en el dataset.
2. Se ubica ese CWE en la lista oficial de CWE de cada categoría del Top 10 2021.
3. Si el CWE no aparece en ninguna lista oficial, se reporta como
   `sin_categoria`. No se fuerza a la categoría más parecida.

El cálculo está en `eval/cobertura_owasp.py` y el resultado en
`eval/cobertura_owasp.json`. Se ejecuta con:

```
python eval/cobertura_owasp.py
```

Se usa el CWE del detector por una razón concreta: la columna `owasp` del dataset
asigna categoría al CWE **etiquetado** en el corpus, que describe la función
completa y no la línea que Bandit señala. En el holdout, por ejemplo, dos alertas
B311 (CWE-330, A02) están etiquetadas como CWE-94 (A03). Mapear por la etiqueta
del dataset habría puesto esas alertas en Injection.

### 1.1 OWASP en el producto

La misma función de mapeo que usa la evaluación está en el producto
(`agente/src/agente_seguridad/owasp.py`). No es una tabla duplicada: el campo
`Finding.owasp` se calcula al construir el hallazgo en `bandit_runner.py`,
`sast/owasp_runner.py` o `llm/code_audit.py`, y viaja con la alerta hasta las tres
salidas:

- **JSON**: cada hallazgo incluye `owasp`; `resumen.por_owasp` cuenta las alertas
  por categoría y `resumen.owasp_nombres` da el nombre legible.
- **SARIF**: la regla y cada resultado llevan `properties.owasp`; los tags
  incluyen `OWASP-Axx` y el CWE, de modo que cualquier visor puede filtrar por
  categoría sin perder la trazabilidad.
- **Consola**: se imprime el resumen `OWASP Top 10 2021: A03=..., A08=...` y una
  columna de categoría por hallazgo.

Las pruebas de `agente/tests/test_agente.py` cubren el mapeo, el campo en el
reporte, el SARIF y los hallazgos reales de Bandit. La integración no cambia el
modo asesor: la categoría organiza la alerta, no decide su descarte.

### 1.2 Escáner OWASP propio

El producto también puede detectar vulnerabilidades sin Bandit. El runner
`sast/owasp_runner.py` recorre el AST de los archivos Python y aplica el catálogo
de `sast/owasp_rules.py`. Sus reglas cubren las clases del dataset que son
inferibles del código Python: inyección SQL, comandos, código y XSS; path
traversal, SSRF y open redirect; deserialización insegura; credenciales y
autenticación con secretos embebidos; criptografía y aleatoriedad débiles;
permisos, CSRF, control de acceso y carga de archivos. Las clases de seguridad
de memoria del corpus (CWE-119, 125, 190, 401, 416, 476 y 787) son de C/C++ y se
declaran fuera del alcance del runner.

Cada hallazgo se construye como un `Finding` con su CWE propio y la categoría se
calcula con `owasp.py`; no se usa la columna `owasp` del dataset. La CLI permite
elegir motor con `--scanner both|bandit|owasp`; por defecto ejecuta ambos y
deduplica cada motor por separado. El escáner es heurístico y conservador: no
elimina hallazgos y sus alertas pasan por el mismo triage y modo asesor que las
de Bandit.

### 1.3 Auditoría LLM-first (`--scanner llm`)

El modo **modelo primero** invierte el flujo del triage. En lugar de recibir una
alerta y decidir si es real, el modelo recibe únicamente fragmentos de código
Python (funciones o código de módulo) y emite por sí mismo un JSON con
`veredicto`, `cwe`, `severidad`, `explicacion`, `vector_ataque` y `correccion`.
Solo las respuestas `VULNERABLE` se convierten en `Finding`; las respuestas `SAFE`
no crean hallazgo y las respuestas inválidas se descartan.

La categoría OWASP se calcula con `owasp.etiqueta` a partir del CWE que declara el
modelo. Es la única excepción a la regla de «CWE del SAST»: aquí no hay SAST,
porque el detector es el propio modelo. La categoría nunca se toma de la columna
`owasp` del dataset ni de un campo OWASP que el modelo pudiera inventar. Si el
CWE no es numérico, la respuesta se considera inválida y no se crea el hallazgo.

El pipeline de entrenamiento está en `training/build_audit_sft.py` y usa
`train_80` / `val_total`. Para evitar etiquetas de lenguaje ruidosas, los
fragmentos marcados como Python se validan con `ast.parse` antes de entrar en el
SFT. El conjunto de evaluación se construye con
`eval/build_audit_eval_set.py` y se mide con `eval/run_audit_eval.py`; nunca se
usa el holdout para ajustar este modo.

La CLI ejecuta este modo **antes** de Bandit y del escáner OWASP, y `--scanner all`
combina los tres. En el reporte, los hallazgos del modelo llevan la herramienta
`llm-audit` y no se vuelven a triagear: su veredicto y explicación ya son la
respuesta del detector.

## 2. Cobertura medida del Top 10 2021

| Categoría | Nombre | Desarrollo (141) | Holdout (111) |
|---|---|---:|---:|
| A01 | Broken Access Control | 3 | 1 |
| A02 | Cryptographic Failures | 1 | 3 |
| A03 | Injection | 83 | 76 |
| A04 | Insecure Design | 0 | 0 |
| A05 | Security Misconfiguration | 0 | 0 |
| A06 | Vulnerable and Outdated Components | 0 | 0 |
| A07 | Identification and Authentication Failures | 0 | 0 |
| A08 | Software and Data Integrity Failures | 53 | 30 |
| A09 | Security Logging and Monitoring Failures | 0 | 0 |
| A10 | Server Side Request Forgery (SSRF) | 0 | 0 |
| — | Fuera del Top 10 2021 | 1 | 1 |

Dos categorías concentran el 96,5 % de las alertas de desarrollo (83 + 53 de
141) y el 95,5 % del holdout (76 + 30 de 111): **A03 Injection** y **A08 Software
and Data Integrity Failures**. No es un defecto del mapeo, es la consecuencia de
elegir Bandit: sus reglas más frecuentes son ejecución de comandos, `eval`,
plantillas y deserialización.

Reglas por categoría:

| Regla | CWE del SAST | Categoría | Desarrollo | Holdout |
|---|---|---|---:|---:|
| B102 | CWE-78 | A03 | 7 | 7 |
| B201 | CWE-94 | A03 | 10 | 9 |
| B307 | CWE-78 | A03 | 21 | 27 |
| B404 | CWE-78 | A03 | 16 | 11 |
| B602 | CWE-78 | A03 | 5 | 2 |
| B603 | CWE-78 | A03 | 7 | 3 |
| B605 | CWE-78 | A03 | 11 | 9 |
| B608 | CWE-89 | A03 | 6 | 8 |
| B301 | CWE-502 | A08 | 25 | 15 |
| B403 | CWE-502 | A08 | 28 | 15 |
| B310 | CWE-22 | A01 | 1 | 0 |
| B311 | CWE-330 | A02 | 1 | 3 |
| B104 | CWE-605 | sin categoría | 1 | 0 |
| B108 | CWE-377 | A01 | 2 | 1 |
| B110 | CWE-703 | sin categoría | 0 | 1 |

Los CWE sin categoría son reales y hay que explicarlos: CWE-605 (múltiples binds
al mismo puerto) en desarrollo y CWE-703 (verificación de estado incorrecta) en el
holdout **no forman parte del Top 10 2021**. CWE-377 (archivo temporal inseguro)
figura en la lista oficial de A01 como entrada obsoleta, de modo que se clasifica
como A01 y no como `sin_categoria`. Decir que el agente «cubre el Top 10» sería
falso; decir que cubre cuatro categorías con evidencia medida —A03 y A08 de forma
dominante, A01 y A02 de forma marginal— es verificable.

## 3. Discrepancias entre el dataset y las listas oficiales

El dataset publica una categoría OWASP para cada una de sus 30 etiquetas CWE. Al
contrastarla con las listas oficiales, **10 de 30 etiquetas no coinciden** y 7 de
esas 10 están forzadas a A03:

| CWE | Dataset | Oficial | Observación |
|---|---|---|---|
| CWE-119 | A03 | sin categoría | Desbordamiento de búfer; el Top 10 2021 no cubre memoria. |
| CWE-125 | A03 | sin categoría | Lectura fuera de límites; ídem. |
| CWE-190 | A03 | sin categoría | Desbordamiento de entero; ídem. |
| CWE-401 | A03 | sin categoría | Fuga de memoria; ídem. |
| CWE-416 | A03 | sin categoría | Uso después de liberar; ídem. |
| CWE-476 | A03 | sin categoría | Desreferencia de puntero nulo; ídem. |
| CWE-787 | A03 | sin categoría | Escritura fuera de límites; ídem. |
| CWE-362 | A04 | sin categoría | Condición de carrera; no está en A04. |
| CWE-399 | A04 | sin categoría | Gestión de recursos; no está en A04. |
| CWE-269 | A01 | A04 | Gestión de privilegios; A04 la incluye explícitamente. |

La consecuencia no es cosmética. Si la memoria usara la columna `owasp` del
dataset como si fuera la norma:

- atribuiría a A03 siete clases de memoria que el Top 10 2021 no clasifica;
- subiría artificialmente la cobertura de A03;
- y ubicaría CWE-269 en A01 cuando la lista oficial lo pone en A04.

Por eso el análisis primario se hace sobre el CWE del SAST y la discrepancia se
reporta como hallazgo de calidad de datos. Esto conecta con el riesgo
**LLM04 Data and Model Poisoning**: el ruido de etiquetas del corpus es una
amenaza real para el componente entrenado, no una nota al pie.

## 4. Categorías no alcanzables y por qué

| Categoría | ¿Bandit puede? | Motivo |
|---|---|---|
| A01 | Parcial | CWE-22 (B310) y CWE-377 (B108); el control de acceso no se infiere del AST. |
| A02 | Parcial | Solo aleatoriedad débil (B311) y criptografía rota (B303/B304/B324). |
| A03 | Sí | Núcleo de Bandit: comandos, `eval`, SQL, plantillas. |
| A04 | Marginal | Requiere diseño y flujo; B201 no distingue intención. |
| A05 | No | Configuración de despliegue, no código fuente. |
| A06 | No | Requiere inventario y versiones de dependencias; no es tarea de Bandit. |
| A07 | Marginal | B105–B107 detectan credenciales embebidas, fuera del corpus evaluado. |
| A08 | Sí | B301/B403 (pickle), B614 (torch). |
| A09 | No | Requiere observar el runtime y los logs. |
| A10 | No | Bandit no sigue destinos de red. |

Esto fija el alcance real del producto: **es un triage de alertas SAST, un
escáner heurístico de reglas OWASP y una auditoría LLM-first, no un escáner del
Top 10 completo**. Un producto que prometiera A01–A10 necesitaría, como mínimo,
análisis de flujo, inventario de dependencias y telemetría de runtime. El escáner
propio y el modelo añaden detección directa de patrones en Python, pero no
sustituyen esas capacidades.

## 5. OWASP LLM Top 10 2025 aplicado al agente

El componente inteligente también es un sistema LLM, y su entrada —el código
analizado— es no confiable. Aplicar el LLM Top 10 al propio agente es lo que
convierte a OWASP en eje y no en adorno.

| Riesgo | ¿Aplica? | Evidencia en el proyecto | Control |
|---|---|---|---|
| LLM01 Prompt Injection | Sí | `eval/pruebas/inyeccion.py`: un comentario ordena responder SAFE; las 4 alertas se conservaron y las 2 reales se clasificaron VULNERABLE. | Formato fijo, delimitadores, temperatura 0, política de no descarte y revisión humana. Los delimitadores no se consideran defensa suficiente. |
| LLM02 Sensitive Information Disclosure | Sí | El código del cliente entra completo al prompt y queda guardado en reportes JSON y SARIF. | Ejecución local con Ollama; sin API externa ni telemetría. Falta documentar la retención de reportes. |
| LLM03 Supply Chain | Sí | Modelo base de Hugging Face, adaptador LoRA, fusión, GGUF y etiqueta en Ollama. | SHA-256 de los artefactos producidos en `training/out/SHA256SUMS.txt`. El modelo base se carga por nombre, sin `revision` fija: es la brecha a cerrar. |
| LLM04 Data and Model Poisoning | Sí | 10 de 30 etiquetas OWASP del dataset no coinciden con la norma; 2 B311 del holdout están etiquetadas CWE-94. | Auditoría de etiquetas, particiones separadas y reporte de la discrepancia. El ruido se documenta, no se corrige post hoc. |
| LLM05 Improper Output Handling | Sí | La respuesta se parsea con `json.loads`, se valida el veredicto y se exige justificación para SAFE; el frontend renderiza la explicación como texto (React escapa HTML). | Validación de esquema y degradación a SOSPECHOSA. El riesgo residual está en consumidores que interpreten la explicación como HTML o Markdown. |
| LLM06 Excessive Agency | Sí | El agente podría suprimir alertas; el modo asesor lo impide. | `DEFAULT_NEVER_DISCARD`, SAFE solo como recomendación y todas las alertas en JSON y SARIF. Es el control central del producto. |
| LLM07 System Prompt Leakage | Bajo | El prompt de sistema no contiene secretos ni rutas privadas. | Puede publicarse sin riesgo; no se trata como control de seguridad. |
| LLM08 Vector and Embedding Weaknesses | No | No hay RAG ni base vectorial. | Se declara la exclusión. |
| LLM09 Misinformation | Sí | D copia el CWE del SAST en 112 de 141 alertas y su exactitud CWE (43,0 %) no supera a la del SAST; en el holdout produce 11 explicaciones únicas para 111 alertas. | En triage el CWE se conserva del SAST y el modelo solo aporta veredicto; en auditoría LLM-first se mide la exactitud de su CWE. La explicación se evalúa con rúbrica y se reporta su diversidad. |
| LLM10 Unbounded Consumption | Sí | Una B102 de 1.818 caracteres agotó 180 s sin `num_predict`; con `num_predict: 512` se truncó y se conservó como SOSPECHOSA. Consumo medido: 1.115 MB de VRAM y ~4,8 s por alerta. | Límite de generación, timeout, degradación a SOSPECHOSA y ausencia de paralelismo sin medición. |

Ocho de los diez riesgos aplican con evidencia propia y uno más (LLM07) aplica con
riesgo bajo; solo LLM08 queda excluido porque no hay RAG ni base vectorial. Los
riesgos excluidos o de riesgo bajo se declaran, no se omiten.

### 5.1 Riesgo residual detectado en la capa de presentación

Antes, `frontend/src/lib/reportParser.ts` y las vistas rotulaban como
«descartadas» todas las alertas con veredicto SAFE. En el producto, un SAFE es
solo una recomendación: la alerta sigue en el JSON y en el SARIF. La vista podía
transmitir la idea de que el agente suprimió el hallazgo aunque no lo hubiera
hecho.

Riesgo de **LLM06 Excessive Agency** en la percepción del usuario, ya corregido.
Las etiquetas visibles dicen ahora «recomendadas para descarte» (commit
`2f4d589`). El parser sigue distinguiendo SAFE válido de SOSPECHOSA en el modelo
de datos. Los identificadores internos (`descartadas`) se mantienen para no
romper enlaces.

## 6. ASVS 5.0.0 como checklist parcial

ASVS verifica aplicaciones web; el agente es una CLI local con un visor estático.
Aplicarlo entero sería otra forma de sobreafirmar. Se usan solo los capítulos que
tienen superficie real, y se declaran las exclusiones.

| Capítulo ASVS 5.0 | ¿Aplica? | Estado |
|---|---|---|
| V1 Encoding and Sanitization | Parcial | La salida se muestra como texto; no se genera HTML. |
| V2 Validation and Business Logic | Sí | Se valida el JSON del modelo y se exige justificación para SAFE. |
| V5 File Handling | Parcial | Se leen archivos del repositorio y se escriben reportes; falta prueba de rutas con `..`. |
| V13 Configuration | Parcial | URL de Ollama y etiqueta de modelo por argumento; sin secretos en el código. |
| V14 Data Protection | Parcial | El código analizado es sensible; la promesa es ejecución local. Falta política de retención. |
| V15 Secure Coding and Architecture | Sí | Modelo de amenaza en este documento, modo asesor por defecto, sin descarte automático. |
| V16 Security Logging and Error Handling | Parcial | Todo error del modelo degrada a SOSPECHOSA y el proceso termina con código 0. |
| V3, V4, V6–V12, V17 | No | No hay frontend autenticado, sesiones, tokens, OAuth, criptografía propia ni WebRTC. |

El valor de la tabla no es el porcentaje de cumplimiento: es que cada exclusión
tiene un motivo y cada capítulo aplicable tiene una prueba asociada.

## 7. Trazabilidad: decisión de diseño → riesgo OWASP

| Decisión | Riesgo que atiende | Dónde está |
|---|---|---|
| Modo asesor, sin supresión | LLM06 Excessive Agency; A04 Insecure Design | `triage.py`, `report.py`, contrato de decisión |
| Política B403 obligatoria con D | A08 Software and Data Integrity Failures | `DEFAULT_NEVER_DISCARD` |
| CWE del detector; en triage nunca el del modelo | LLM09 Misinformation | `report.py`, sección de resultados |
| OWASP calculado desde el CWE, no desde el dataset | LLM04 Data and Model Poisoning | `owasp.py`, `llm/code_audit.py` |
| Límite `num_predict` y timeout | LLM10 Unbounded Consumption | `ollama_client.py` |
| Validación de JSON y de veredicto | LLM05 Improper Output Handling | `triage.py` |
| Ejecución local sin API | LLM02 y LLM03 | `llm/ollama_client.py`, despliegue |
| Prueba de inyección en el código | LLM01 Prompt Injection | `eval/pruebas/inyeccion.py` |
| Auditoría de etiquetas del dataset | LLM04 Data and Model Poisoning | este documento y `eval/cobertura_owasp.py` |

Las decisiones ya estaban tomadas antes de este documento. La tabla no inventa
un marco: muestra que el diseño ya respondía a riesgos de OWASP y que faltaba
nombrarlos.

## 8. Lo que este documento no afirma

- No afirma que el agente cubra el OWASP Top 10 2021. La evidencia medida de las
  herramientas se concentra en A01–A03 y A08; la auditoría LLM-first puede emitir
  otras categorías cuando el CWE lo justifica, pero no se ha medido cobertura
  completa. A04–A07, A09 y A10 quedan fuera del alcance medido.
- No afirma cumplimiento de ASVS 5.0.0. Aplica 6 capítulos de 17, uno de ellos
  de forma parcial.
- No afirma que el mapeo del dataset sea correcto. Documenta 10 discrepancias y
  usa el CWE del detector para el análisis primario.
- No afirma que el agente sea resistente a prompt injection. Un caso de prueba
  no es una propiedad del sistema.
- No usa OWASP como métrica de calidad del modelo. La calidad se mide con FPRR,
  FNR y la rúbrica; OWASP ordena el alcance y el modelo de amenaza.
