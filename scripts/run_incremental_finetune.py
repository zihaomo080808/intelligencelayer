# scripts/run_incremental_finetune.py
import time, json
from pathlib import Path
import openai
from config import settings

openai.api_key = settings.OPENAI_API_KEY

FILE_MAP = {
    "classifier": "data/incremental_classifier.jsonl",
    "generator":  "data/incremental_generator.jsonl",
}
BASE_MODEL = "o4-mini"
SUFFIX     = f"auto-{int(time.time())}"
ORG        = "your_org"  # replace with your org name

def run_finetune(task: str):
    fn = FILE_MAP[task]
    p = Path(fn)
    if not p.exists() or p.stat().st_size == 0:
        print("No new examples for", task)
        return

    # 1) Upload
    resp = openai.File.create(
        file=open(fn,"rb"),
        purpose="fine-tune"
    )
    print("Uploaded:", resp["id"])

    # 2) Create job
    job = openai.FineTune.create(
        training_file=resp["id"],
        model=BASE_MODEL,
        suffix=SUFFIX,
        n_epochs=2
    )
    print("Job:", job["id"])

    # 3) Poll
    status = None
    while status not in ("succeeded","failed"):
        time.sleep(30)
        info = openai.FineTune.retrieve(job["id"])
        status = info["status"]
        print("Status:", status)

    if status=="succeeded":
        new_model = info["fine_tuned_model"]
        print("New model:", new_model)
        key = "CLASSIFIER_MODEL" if task=="classifier" else "GENERATOR_MODEL"
        with open(".env","a") as f:
            f.write(f"\n{key}={new_model}\n")
        p.unlink()
    else:
        print("Failed:", info)

if __name__=="__main__":
    for t in ("classifier","generator"):
        run_finetune(t)
