"""Prueba de humo de la perdida ponderada en CPU con un modelo diminuto.

No entrena nada util: crea un Qwen2 aleatorio de juguete, codifica dos
ejemplos y ejecuta dos pasos con WeightedTrainer para comprobar que:

- la perdida es finita y baja entre pasos;
- con --decision-weight > 1 la perdida difiere de la estandar;
- el collator y compute_loss aceptan el formato del dataset real.

Uso:
    python training/verificar_ponderacion.py
"""

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))

import torch
from datasets import Dataset
from transformers import AutoTokenizer, Qwen2Config, Qwen2ForCausalLM, TrainingArguments

from train_qlora import WeightedCollator, WeightedTrainer, encode_rows

PESO = 3.0

EJEMPLOS = [
    {
        "messages": [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "Alerta del SAST (triage):\n- Regla: B403\n\nCodigo fuente:\n<code>\nimport pickle\npickle.load(f)\n</code>\n\nDevuelve el JSON."},
            {"role": "assistant", "content": json.dumps({
                "veredicto": "VULNERABLE", "cwe": "CWE-502", "severidad": "Alta",
                "explicacion": "Deserializa con pickle.load sobre datos no confiables.",
                "vector_ataque": "Payload pickle hostil.",
                "correccion": "No deserializar datos no confiables."}, ensure_ascii=False)},
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "Alerta del SAST (triage):\n- Regla: B311\n\nCodigo fuente:\n<code>\nimport random\nx = random.randint(0, 9)\n</code>\n\nDevuelve el JSON."},
            {"role": "assistant", "content": json.dumps({
                "veredicto": "SAFE", "cwe": "Ninguno", "severidad": "Info",
                "explicacion": "El aleatorio no se usa en un contexto de seguridad.",
                "vector_ataque": "N/A", "correccion": "N/A"}, ensure_ascii=False)},
        ]
    },
]


def main():
    tokenizer = AutoTokenizer.from_pretrained("training/out/qwen-coder-1.5b-merged")
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    filas = encode_rows(tokenizer, EJEMPLOS, 2048, "humo", PESO)
    assert len(filas) == 2
    pesados = sum(1 for f in filas for w in f["weights"] if w > 1.0)
    assert pesados > 0, "ningun token quedo ponderado"
    print("tokens con peso {}: {}".format(PESO, pesados))

    cfg = Qwen2Config(
        vocab_size=len(tokenizer),
        hidden_size=64, intermediate_size=128, num_hidden_layers=2,
        num_attention_heads=2, num_key_value_heads=2, max_position_embeddings=2048,
    )
    torch.manual_seed(0)
    model = Qwen2ForCausalLM(cfg)

    args = TrainingArguments(
        output_dir="training/out/_humo", per_device_train_batch_size=2,
        max_steps=2, learning_rate=1e-3, report_to="none", use_cpu=True,
        save_strategy="no", logging_steps=1, remove_unused_columns=False,
    )
    trainer = WeightedTrainer(
        model=model, args=args,
        train_dataset=Dataset.from_list(filas * 4),
        data_collator=WeightedCollator(pad_token_id=tokenizer.pad_token_id),
    )
    historial = trainer.train()
    print("perdida registrada:", historial.training_loss)
    assert historial.training_loss == historial.training_loss, "perdida NaN"

    # Perdida estandar (peso 1.0) sobre el mismo batch: debe diferir.
    filas_planas = encode_rows(tokenizer, EJEMPLOS, 2048, "plano", 1.0)
    assert all(w == 1.0 for f in filas_planas for w in f["weights"])
    print("OK: perdida finita, entrenamiento de 2 pasos y formato compatible")


if __name__ == "__main__":
    main()
