# classifier/model.py
import json
import yaml
from openai import OpenAI
import logging
from functools import lru_cache
from typing import List, Optional, Union
from config import settings

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=settings.OPENAI_API_KEY)
logger.info(f"OpenAI API Key present: {bool(settings.OPENAI_API_KEY)}")
logger.info(f"Classifier Model: {settings.CLASSIFIER_MODEL}")

# 1) Load your allowed labels once
@lru_cache(maxsize=1)
def load_labels() -> List[str]:
    with open(settings.BASE_DIR / "classifier" / "stance_labels.yaml") as f:
        data = yaml.safe_load(f)
    # assume YAML is a list under the key "labels"
    return data.get("labels", [])

LABELS = load_labels()


def _build_system_prompt(top_k: int, allow_all: bool) -> str:
    if allow_all:
        return (
            "You are a multi-label classifier. "
            "Select all labels that apply, ordered most to least relevant, "
            f"up to a maximum of {top_k}. "
            "Respond ONLY with a JSON array of label strings."
        )
    else:
        label_list = "\n".join(f"- {lbl}" for lbl in LABELS)
        return (
            "You are a multi-label classifier. "
            "From the following list of labels:\n"
            f"{label_list}\n"
            f"Select the top {top_k} that apply to this bio. "
            "Respond ONLY with a JSON array of label strings."
        )


def predict_stance(
    text: str,
    top_k: int = 7,
    *,
    allow_all: bool = False,
    retry_on_fail: bool = True
) -> List[str]:
    """
    Classify `text` into up to `top_k` labels.
    - allow_all: if True, return all labels above threshold (up to `top_k`)
    - retry_on_fail: if JSON parsing fails, retry once with a corrective prompt
    """
    system_prompt = _build_system_prompt(top_k, allow_all)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Bio: {text}"},
    ]

    def call_model(msgs):
        try:
            response = client.chat.completions.create(
                model=settings.CLASSIFIER_MODEL,
                messages=msgs,
                max_completion_tokens=256,
            )
            return response
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {e}")
            raise

    # 1st attempt
    resp = call_model(messages)
    content = resp.choices[0].message.content.strip()
    logger.info(f"OpenAI API Response: {content}")

    try:
        # Handle empty content case
        if not content:
            logger.warning("Empty response from OpenAI API")
            return []
        
        labels = json.loads(content)
        if not isinstance(labels, list):
            raise ValueError("Response not a JSON list")
        return labels
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("Failed to parse labels JSON: %s\n--%s", content, e)
        if not retry_on_fail:
            raise

        # retry once
        followup = {
            "role": "user",
            "content": (
                "Oops, that wasn't valid JSON.  "
                "Please respond only with a JSON array of strings, "
                f"e.g. [\"{LABELS[0]}\", \"{LABELS[1]}\"]"
            )
        }
        resp2 = call_model(messages + [followup])
        content2 = resp2.choices[0].message.content.strip()
        try:
            return json.loads(content2)
        except Exception as e2:
            logger.error("Retry also failed to produce valid JSON: %s\n--%s", content2, e2)
            # fallback: empty or raise
            return []


def classify_batch(
    texts: List[str],
    top_k: int = 7,
    *,
    allow_all: bool = False
) -> List[List[str]]:
    """
    Classify a batch of inputs in parallel.
    Falls back to per-item calls if the model's context window is too small.
    """
    # naive: one-by-one
    return [predict_stance(text, top_k, allow_all=allow_all) for text in texts]
