import argparse
import json
import re
import sys
from pathlib import Path

import torch
from datasets import Dataset
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    Trainer,
    TrainingArguments,
)

sys.stdout.reconfigure(encoding="utf-8")


def load_rows(path, limit=0):
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                rows.append(json.loads(line))
            if limit and len(rows) >= limit:
                break
    return rows


DECISION_RE = re.compile(r'"(?:veredicto|cwe)"\s*:\s*"[^"]*"')


def response_weights(tokenizer, ids, weight):
    """Peso por token de la respuesta: `weight` en veredicto/cwe, 1.0 en el resto.

    Reconstruye el texto de la respuesta decodificando token a token para
    obtener el rango de caracteres de cada token, localiza los campos
    "veredicto" y "cwe" del JSON y marca los tokens que los cubren. Si la
    reconstruccion falla, devuelve peso uniforme (el entrenamiento no se rompe,
    solo pierde el enfasis).
    """
    weights = [1.0] * len(ids)
    if weight == 1.0 or not ids:
        return weights
    text = tokenizer.decode(ids, skip_special_tokens=False)
    offsets = []
    pos = 0
    for token_id in ids:
        piece = tokenizer.decode([token_id], skip_special_tokens=False)
        idx = text.find(piece, pos)
        if idx == -1:
            return weights
        offsets.append((idx, idx + len(piece)))
        pos = idx + len(piece)
    for match in DECISION_RE.finditer(text):
        s, e = match.span()
        for i, (a, b) in enumerate(offsets):
            if a < e and b > s:
                weights[i] = weight
    return weights


def encode(tokenizer, messages, max_seq, decision_weight=1.0):
    prompt_ids = tokenizer.apply_chat_template(
        messages[:-1], tokenize=True, add_generation_prompt=True, return_dict=True
    )["input_ids"]
    full_ids = tokenizer.apply_chat_template(
        messages, tokenize=True, add_generation_prompt=False, return_dict=True
    )["input_ids"]
    full_ids = list(full_ids)
    if len(full_ids) > max_seq:
        full_ids = full_ids[:max_seq]
    # prompt_ids termina en el token de inicio del turno assistant (add_generation_prompt);
    # ese token no existe en full_ids (add_generation_prompt=False), asi que el contenido
    # del assistant comienza en len(prompt_ids) - 1.
    start = min(max(len(prompt_ids) - 1, 0), len(full_ids))
    labels = [-100] * start + full_ids[start:]
    weights = [1.0] * start + response_weights(tokenizer, full_ids[start:], decision_weight)
    return {
        "input_ids": full_ids,
        "labels": labels,
        "attention_mask": [1] * len(full_ids),
        "weights": weights,
    }


def encode_rows(tokenizer, rows, max_seq, name, decision_weight=1.0):
    """Codifica y descarta ejemplos que, tras truncar, no conservan respuesta.

    Si el prompt ocupa toda la ventana, todos los labels quedan en -100 y la
    perdida de ese lote es NaN. Esos ejemplos no aportan aprendizaje y
    envenenan eval_loss, asi que se excluyen del conjunto.
    """
    encoded = []
    dropped = 0
    for row in rows:
        ex = encode(tokenizer, row["messages"], max_seq, decision_weight)
        if all(label == -100 for label in ex["labels"]):
            dropped += 1
            continue
        encoded.append(ex)
    if dropped:
        print("{}: {} ejemplos descartados por truncamiento sin respuesta".format(name, dropped))
    return encoded


class WeightedCollator:
    """Rellena input_ids, labels y pesos; los pesos del relleno quedan en 0."""

    def __init__(self, pad_token_id):
        self.pad_token_id = pad_token_id

    def __call__(self, features):
        maxlen = max(len(f["input_ids"]) for f in features)
        batch = {"input_ids": [], "attention_mask": [], "labels": [], "weights": []}
        for f in features:
            pad = maxlen - len(f["input_ids"])
            batch["input_ids"].append(f["input_ids"] + [self.pad_token_id] * pad)
            batch["attention_mask"].append(f["attention_mask"] + [0] * pad)
            batch["labels"].append(f["labels"] + [-100] * pad)
            batch["weights"].append(f["weights"] + [0.0] * pad)
        return {
            "input_ids": torch.tensor(batch["input_ids"], dtype=torch.long),
            "attention_mask": torch.tensor(batch["attention_mask"], dtype=torch.long),
            "labels": torch.tensor(batch["labels"], dtype=torch.long),
            "weights": torch.tensor(batch["weights"], dtype=torch.float),
        }


class WeightedTrainer(Trainer):
    """Cross-entropy por token multiplicada por el peso de cada token.

    Con peso uniforme 1.0 coincide con la perdida estandar (media sobre los
    tokens de respuesta). Con peso > 1 en veredicto/cwe, el error en la
    decision pesa mas que el error en la redaccion de la explicacion.
    """

    def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
        weights = inputs.pop("weights")
        outputs = model(**inputs)
        logits = outputs.logits[..., :-1, :].contiguous()
        labels = inputs["labels"][..., 1:].contiguous()
        w = weights[..., 1:].contiguous()
        loss = torch.nn.functional.cross_entropy(
            logits.view(-1, logits.size(-1)),
            labels.view(-1),
            ignore_index=-100,
            reduction="none",
        ).view(labels.size())
        mask = labels != -100
        w = w * mask
        total = (loss * w).sum() / w.sum().clamp(min=1e-6)
        return (total, outputs) if return_outputs else total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Qwen/Qwen2.5-Coder-1.5B-Instruct")
    ap.add_argument("--train", default="training/data/train_sft.jsonl")
    ap.add_argument("--val", default="training/data/val_sft.jsonl")
    ap.add_argument("--out", default="training/out/qwen-coder-1.5b-lora")
    ap.add_argument("--epochs", type=float, default=1.0)
    ap.add_argument("--max-seq", type=int, default=2048)
    ap.add_argument("--batch-size", type=int, default=1)
    ap.add_argument("--grad-accum", type=int, default=8)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--lora-r", type=int, default=16)
    ap.add_argument("--lora-alpha", type=int, default=32)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--save-steps", type=int, default=500)
    ap.add_argument("--decision-weight", type=float, default=1.0,
                    help="peso extra de los tokens de veredicto/cwe (1.0 = perdida estandar; 3.0 = decision centrada)")
    ap.add_argument("--quant", default="4bit", choices=["4bit", "none"],
                    help="4bit: cuantizar base a 4-bit (requiere Ampere+); none: fp16 sin cuantizar (recomendado para GTX 1650 / Turing)")
    args = ap.parse_args()

    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    train_rows = load_rows(args.train, args.limit)
    val_rows = load_rows(args.val, args.limit)
    print("train:", len(train_rows), "| val:", len(val_rows))

    train_ds = Dataset.from_list(
        encode_rows(tokenizer, train_rows, args.max_seq, "train", args.decision_weight))
    val_ds = Dataset.from_list(
        encode_rows(tokenizer, val_rows, args.max_seq, "val", args.decision_weight))
    print("tokens promedio train:", int(sum(len(x["input_ids"]) for x in train_ds) / len(train_ds)))

    if args.quant == "4bit":
        bnb = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
        )
        model = AutoModelForCausalLM.from_pretrained(
            args.model, quantization_config=bnb, device_map="auto", trust_remote_code=True
        )
        model = prepare_model_for_kbit_training(model)
    else:
        # Sin cuantizar: fp16 (el GTX 1650 es Turing y no soporta bf16)
        model = AutoModelForCausalLM.from_pretrained(
            args.model, device_map="auto", trust_remote_code=True
        )
    model.config.use_cache = False

    lora = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
    )
    model = get_peft_model(model, lora)
    model.print_trainable_parameters()

    training_args = TrainingArguments(
        output_dir=args.out,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr,
        num_train_epochs=args.epochs,
        lr_scheduler_type="cosine",
        warmup_ratio=0.03,
        logging_steps=20,
        save_steps=args.save_steps,
        eval_strategy="steps",
        eval_steps=args.save_steps,
        bf16=torch.cuda.is_bf16_supported(),
        fp16=not torch.cuda.is_bf16_supported() and torch.cuda.is_available(),
        optim="paged_adamw_8bit",
        gradient_checkpointing=True,
        report_to="none",
        save_total_limit=2,
        # "weights" no esta en la signatura del modelo; sin esto el Trainer la
        # descarta y la perdida ponderada no recibe los pesos.
        remove_unused_columns=False,
    )
    collator = WeightedCollator(pad_token_id=tokenizer.pad_token_id)

    trainer = WeightedTrainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        data_collator=collator,
    )
    trainer.train()
    trainer.save_model(args.out)
    tokenizer.save_pretrained(args.out)
    print("adaptador guardado en:", args.out)


if __name__ == "__main__":
    main()
