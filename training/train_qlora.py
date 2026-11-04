import argparse
import json
import sys
from pathlib import Path

import torch
from datasets import Dataset
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    DataCollatorForSeq2Seq,
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


def encode(tokenizer, messages, max_seq):
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
    return {"input_ids": full_ids, "labels": labels, "attention_mask": [1] * len(full_ids)}


def encode_rows(tokenizer, rows, max_seq, name):
    """Codifica y descarta ejemplos que, tras truncar, no conservan respuesta.

    Si el prompt ocupa toda la ventana, todos los labels quedan en -100 y la
    perdida de ese lote es NaN. Esos ejemplos no aportan aprendizaje y
    envenenan eval_loss, asi que se excluyen del conjunto.
    """
    encoded = []
    dropped = 0
    for row in rows:
        ex = encode(tokenizer, row["messages"], max_seq)
        if all(label == -100 for label in ex["labels"]):
            dropped += 1
            continue
        encoded.append(ex)
    if dropped:
        print("{}: {} ejemplos descartados por truncamiento sin respuesta".format(name, dropped))
    return encoded


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
    ap.add_argument("--quant", default="4bit", choices=["4bit", "none"],
                    help="4bit: cuantizar base a 4-bit (requiere Ampere+); none: fp16 sin cuantizar (recomendado para GTX 1650 / Turing)")
    args = ap.parse_args()

    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    train_rows = load_rows(args.train, args.limit)
    val_rows = load_rows(args.val, args.limit)
    print("train:", len(train_rows), "| val:", len(val_rows))

    train_ds = Dataset.from_list(encode_rows(tokenizer, train_rows, args.max_seq, "train"))
    val_ds = Dataset.from_list(encode_rows(tokenizer, val_rows, args.max_seq, "val"))
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
    )
    collator = DataCollatorForSeq2Seq(tokenizer=tokenizer, padding=True, label_pad_token_id=-100)

    trainer = Trainer(
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
