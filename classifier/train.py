# classifier/train.py
import sys
import time
import argparse
import logging

import openai
from config import settings
from classifier.model import load_labels  # to count classes for metrics

# set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

openai.api_key = settings.OPENAI_API_KEY

def create_fine_tune(
    training_file: str,
    validation_file: str,
    model: str,
    n_epochs: int,
    learning_rate_multiplier: float,
    prompt_loss_weight: float
):
    # 1) upload files
    train_upload = openai.File.create(
        file=open(training_file, "rb"),
        purpose="fine-tune"
    )
    val_upload = openai.File.create(
        file=open(validation_file, "rb"),
        purpose="fine-tune"
    )
    logger.info("Uploaded train file %s, val file %s",
                train_upload.id, val_upload.id)

    # 2) kick off fine-tune job with validation metrics
    params = {
        "training_file": train_upload.id,
        "validation_file": val_upload.id,
        "model": model,
        "n_epochs": n_epochs,
        "compute_classification_metrics": True,
        "classification_n_classes": len(load_labels()),
    }
    if learning_rate_multiplier is not None:
        params["learning_rate_multiplier"] = learning_rate_multiplier
    if prompt_loss_weight is not None:
        params["prompt_loss_weight"] = prompt_loss_weight

    job = openai.FineTune.create(**params)
    logger.info("Started fine-tune job %s on model %s", job.id, model)

    # 3) poll job status until done
    while True:
        status = openai.FineTune.retrieve(job.id)
        st = status["status"]
        logger.info("Job %s status: %s", job.id, st)
        if st in ("succeeded", "failed"):
            break
        time.sleep(30)

    if status["status"] == "succeeded":
        logger.info("✅ Fine-tune complete! New model: %s",
                    status["fine_tuned_model"])
    else:
        logger.error("❌ Fine-tune failed: %s", status)

    return status

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Kick off an OpenAI fine-tune with train+validation data"
    )
    parser.add_argument("training_file", help="Path to your training JSONL")
    parser.add_argument("validation_file", help="Path to your validation JSONL")
    parser.add_argument(
        "--model",
        default=settings.CLASSIFIER_MODEL,
        help="Base model to fine-tune (e.g. o4-mini)"
    )
    parser.add_argument(
        "--n_epochs",
        type=int,
        default=2,
        help="How many epochs to train"
    )
    parser.add_argument(
        "--learning_rate_multiplier",
        type=float,
        default=None,
        help="Optional LR multiplier for fine-tuning"
    )
    parser.add_argument(
        "--prompt_loss_weight",
        type=float,
        default=None,
        help="Optional prompt_loss_weight"
    )
    args = parser.parse_args()

    create_fine_tune(
        training_file=args.training_file,
        validation_file=args.validation_file,
        model=args.model,
        n_epochs=args.n_epochs,
        learning_rate_multiplier=args.learning_rate_multiplier,
        prompt_loss_weight=args.prompt_loss_weight
    )
