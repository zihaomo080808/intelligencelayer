# classifier/evaluate.py
import json
from sklearn.metrics import classification_report
from sklearn.preprocessing import MultiLabelBinarizer
from classifier.model import predict_stance, load_labels

def evaluate_classifier(
    data_path: str = "data/incremental_classifier.jsonl"
):
    # 1) load your allowed labels
    labels = load_labels()
    mlb = MultiLabelBinarizer(classes=labels)

    y_true = []
    y_pred = []

    with open(data_path) as f:
        for line in f:
            rec = json.loads(line)

            # extract text → label
            text = rec.get("prompt") or rec.get("text")
            if not text:
                continue

            # extract ground-truth labels
            true_raw = rec.get("completion") or rec.get("labels")
            if isinstance(true_raw, str):
                try:
                    true_labels = json.loads(true_raw)
                except json.JSONDecodeError:
                    continue
            else:
                true_labels = true_raw or []

            # run classifier
            preds = predict_stance(text)

            y_true.append(true_labels)
            y_pred.append(preds)

    # 2) binarize and report
    y_true_bin = mlb.fit_transform(y_true)
    y_pred_bin = mlb.transform(y_pred)

    print(classification_report(
        y_true_bin,
        y_pred_bin,
        target_names=labels,
        zero_division=0
    ))


if __name__ == "__main__":
    evaluate_classifier()
