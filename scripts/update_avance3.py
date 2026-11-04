import copy
import docx
from docx.text.paragraph import Paragraph

DOCX = r"C:\Games\u\proyecto ing\Avance 3.docx"

doc = docx.Document(DOCX)
ps = doc.paragraphs

p_periodo = ps[6]
p_54_fin = ps[80]
p_lim_fin = ps[123]
p_pasos_fin = ps[133]
p_concl_fin = ps[143]

T_HEAD = ps[79]
T_BODY = ps[80]
T_BULLET = ps[117]
T_NUM = ps[125]

def clone_after(reference, template, text, mode="first"):
    new_el = copy.deepcopy(template._p)
    reference._p.addnext(new_el)
    new_p = Paragraph(new_el, reference._parent)
    runs = new_p.runs
    if mode == "first":
        for r in runs[1:]:
            r._element.getparent().remove(r._element)
        if runs:
            runs[0].text = text
    elif mode == "last":
        runs[-1].text = text
    return new_p

reference = clone_after(
    p_periodo, p_periodo,
    "Periodo: 29 de septiembre – 12 de octubre de 2026  |  Actualización: 20 de octubre de 2026 (Sprint 2)"
)

sub = clone_after(p_54_fin, T_HEAD, "5.4.1 Actualización del dataset (Sprint 2, 20 de octubre de 2026)")

p1 = clone_after(sub, T_BODY,
    "Con posterioridad a la entrega del Avance 3 se reemplazó el conjunto de demostración de ocho "
    "ejemplos por un corpus real de gran escala. Se adoptó el dataset público "
    "ayshajavd/code-security-vulnerability-dataset (licencia Apache 2.0), con 175.419 muestras, 31 "
    "clases (30 familias CWE más la clase segura) y dieciséis etiquetas de lenguaje; la partición "
    "original conserva 140.335 muestras de entrenamiento y 17.542 de validación y de prueba.")

p2 = clone_after(p1, T_BODY,
    "La auditoría detectó fuga de datos entre las particiones originales: 2.025 hashes de código "
    "compartidos entre entrenamiento y prueba, 2.088 entre entrenamiento y validación y 292 entre "
    "validación y prueba. Además, 433 hashes presentaban etiquetas contradictorias. Como el dataset "
    "no incluye identificador de repositorio, el control se realizó mediante el hash SHA-256 del "
    "código normalizado (sin espacios en blanco): se retiraron de entrenamiento y validación todas "
    "las muestras cuyo hash apareciera en prueba o en otra partición, y se descartaron los hashes "
    "con etiqueta inconsistente. La partición de prueba se mantuvo intacta como holdout final "
    "(17.542 muestras).")

p3 = clone_after(p2, T_BODY,
    "Tras el filtrado quedaron 127.348 muestras únicas de entrenamiento, sobre las que se aplicó una "
    "división aleatoria 80/20 con semilla fija 42: 101.878 ejemplos para ajuste y 25.470 para "
    "validación; sumados a las 17.066 muestras de validación original depuradas, la validación total "
    "queda en 42.536 registros. La distribución de clases está fuertemente desbalanceada: 6.178 "
    "muestras vulnerables en entrenamiento (6,1 %) frente a 93,9 % seguras, por lo que el "
    "entrenamiento deberá ponderar clases y la evaluación deberá reportarse tanto con la "
    "distribución natural como balanceada.")

p4 = clone_after(p3, T_BODY,
    "El corpus está dominado por C (94,1 % de las muestras de entrenamiento); Python representa el "
    "1,4 %, seguido de C++, Java, JavaScript, PHP y Go. Dado que el flujo de la CLI analiza Python "
    "con Bandit, la evaluación se reportará por lenguaje y se definirá si el desbalance justifica un "
    "submuestreo o una segunda iteración del corpus. Cada registro se tradujo al esquema de datos "
    "del agente en formato JSONL (prompt y target con veredicto, CWE, severidad, explicación, vector "
    "de ataque y corrección), con finding_id derivado del hash del código.")

upd_lim = clone_after(p_lim_fin, T_BULLET,
    "Actualización (Sprint 2): la limitación sobre el dataset de demostración queda resuelta con el "
    "corpus descrito en 5.4.1. Permanecen pendientes el cálculo de FOR y FPRR sobre el conjunto de "
    "validación (Sprint 4), la prueba de modelos alternativos, la conexión del prototipo con el "
    "modelo real y la reevaluación del falso negativo observado. Se añaden como limitaciones la "
    "fuga residual que el hash exacto no captura (código equivalente con cambios menores) y el "
    "desbalance de clases del corpus.", mode="last")

upd_pasos = clone_after(p_pasos_fin, T_BODY,
    "Estado a la fecha (20 de octubre): los pasos 1 y 2 se completaron. El dataset real fue "
    "construido, auditado y particionado con control de fuga por hash, y la muestra de verificación "
    "manual se definirá sobre el holdout para redactar las explicaciones de referencia. Los pasos 3 "
    "a 6 se mantienen como trabajo de los sprints 3 a 7.")

upd_concl = clone_after(p_concl_fin, T_BODY,
    "La actualización del corpus convierte la prueba de concepto en una base verificable: 175.419 "
    "muestras auditadas, 101.878 ejemplos de ajuste y 42.536 de validación, con control de fuga por "
    "hash y partición de prueba intacta. El siguiente paso es conectar esa base al flujo de extremo "
    "a extremo (Bandit, deduplicación y Ollama) y medir FOR y FPRR sobre el conjunto de validación.")

doc.save(DOCX)
print("Documento actualizado:", DOCX)
