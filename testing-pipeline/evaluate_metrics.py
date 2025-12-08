"""
Evaluator untuk captioning menggunakan BLEU, METEOR, dan CIDEr.

Jalankan dari root repo:

    python testing-pipeline/evaluate_metrics.py \
        --refs testing-pipeline/refs.json \
        --preds testing-pipeline/preds.json

Catatan:
- METEOR memakai NLTK (`nltk.translate.meteor_score`), jadi cukup install nltk.
- Tidak perlu Java. Jika ada id tidak muncul di kedua file, hanya irisan yang dinilai.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

from nltk.translate.bleu_score import SmoothingFunction, sentence_bleu
from nltk.translate.meteor_score import meteor_score as nltk_meteor


def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"File tidak ditemukan: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def normalize_refs(raw: dict) -> Dict[str, List[str]]:
    """Ubah ke format: {id: [caption_str, ...]}"""
    out: Dict[str, List[str]] = {}
    for k, v in raw.items():
        if not isinstance(v, list):
            continue
        captions: List[str] = []
        for item in v:
            if isinstance(item, dict) and "caption" in item:
                if isinstance(item["caption"], str):
                    captions.append(item["caption"])
        if captions:
            out[str(k)] = captions
    return out


def normalize_preds(raw: dict) -> Dict[str, List[str]]:
    """Konversi {id: [ {prediction: "..."} ]} -> {id: [caption_str]}"""
    out: Dict[str, List[str]] = {}
    for k, v in raw.items():
        if not isinstance(v, list):
            continue
        captions: List[str] = []
        for item in v:
            if isinstance(item, dict):
                # Terima "prediction" atau "caption" untuk fleksibilitas
                text = item.get("caption") or item.get("prediction")
                if isinstance(text, str):
                    captions.append(text)
        if captions:
            out[str(k)] = captions
    return out


def _tokenize(sentence: str) -> List[str]:
    """Tokenisasi sederhana spasi-lowercase untuk METEOR NLTK."""
    return sentence.lower().split()


def compute_scores(gts: Dict[str, List[str]], res: Dict[str, List[str]]):
    from pycocoevalcap.cider.cider import Cider

    # Hanya nilai yang overlap
    common_keys = sorted(set(gts.keys()) & set(res.keys()))
    gts_f = {k: gts[k] for k in common_keys}
    res_f = {k: res[k] for k in common_keys}

    if not common_keys:
        raise ValueError("Tidak ada id yang overlap antara refs dan preds.")

    # BLEU via NLTK (per-image, smoothed)
    sf = SmoothingFunction().method1
    per_image: Dict[str, dict] = {}
    bleu_sums = {"bleu-1": 0.0, "bleu-2": 0.0, "bleu-3": 0.0, "bleu-4": 0.0}
    meteor_scores = []

    for k in common_keys:
        refs_k = gts_f[k]
        hyps_k = res_f[k]
        if not hyps_k:
            continue
        hyp = hyps_k[0]  # ambil prediksi pertama
        refs_tok = [_tokenize(r) for r in refs_k]
        hyp_tok = _tokenize(hyp)

        b1 = sentence_bleu(refs_tok, hyp_tok, weights=(1, 0, 0, 0), smoothing_function=sf)
        b2 = sentence_bleu(refs_tok, hyp_tok, weights=(0.5, 0.5, 0, 0), smoothing_function=sf)
        b3 = sentence_bleu(refs_tok, hyp_tok, weights=(1 / 3, 1 / 3, 1 / 3, 0), smoothing_function=sf)
        b4 = sentence_bleu(refs_tok, hyp_tok, weights=(0.25, 0.25, 0.25, 0.25), smoothing_function=sf)
        mtr = nltk_meteor(refs_tok, hyp_tok)

        meteor_scores.append(mtr)
        for key, val in zip(["bleu-1", "bleu-2", "bleu-3", "bleu-4"], [b1, b2, b3, b4]):
            bleu_sums[key] += val

        per_image[k] = {
            "bleu-1": b1,
            "bleu-2": b2,
            "bleu-3": b3,
            "bleu-4": b4,
            "meteor": mtr,
        }

    cider_score, cider_sentence = Cider().compute_score(gts_f, res_f)
    # cider_sentence sejajar dengan common_keys
    for idx, k in enumerate(common_keys):
        if k in per_image:
            per_image[k]["cider"] = float(cider_sentence[idx])
        else:
            per_image[k] = {"cider": float(cider_sentence[idx])}
    for k in per_image:
        per_image[k].setdefault("cider", 0.0)

    count = len(per_image) or 1
    return {
        "averages": {
            "bleu-1": bleu_sums["bleu-1"] / count,
            "bleu-2": bleu_sums["bleu-2"] / count,
            "bleu-3": bleu_sums["bleu-3"] / count,
            "bleu-4": bleu_sums["bleu-4"] / count,
            "meteor": sum(meteor_scores) / count if meteor_scores else 0.0,
            "cider": cider_score,
        },
        "per_image": per_image,
        "evaluated": len(common_keys),
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate captions with BLEU, METEOR, CIDEr.")
    parser.add_argument("--refs", default="testing-pipeline/refs.json", help="Path ke refs.json")
    parser.add_argument("--preds", default="testing-pipeline/preds.json", help="Path ke preds.json")
    parser.add_argument(
        "--json-out",
        default="testing-pipeline/metrics_results.json",
        help="Path file output JSON metrik (per-image dan rata-rata).",
    )
    args = parser.parse_args()

    refs_raw = load_json(Path(args.refs))
    preds_raw = load_json(Path(args.preds))

    refs = normalize_refs(refs_raw)
    preds = normalize_preds(preds_raw)

    missing_in_preds = sorted(set(refs.keys()) - set(preds.keys()))
    missing_in_refs = sorted(set(preds.keys()) - set(refs.keys()))
    if missing_in_preds:
        print(f"[WARN] {len(missing_in_preds)} id ada di refs tapi tidak di preds (contoh: {missing_in_preds[:5]})")
    if missing_in_refs:
        print(f"[WARN] {len(missing_in_refs)} id ada di preds tapi tidak di refs (contoh: {missing_in_refs[:5]})")

    try:
        scores = compute_scores(refs, preds)
    except Exception as exc:
        print(f"[ERROR] Gagal menghitung skor: {exc}")
        sys.exit(1)

    print("\n=== HASIL EVALUASI ===")
    av = scores["averages"]
    print(f"Evaluated pairs : {scores['evaluated']}")
    print(f"BLEU-1          : {av['bleu-1']:.4f}")
    print(f"BLEU-2          : {av['bleu-2']:.4f}")
    print(f"BLEU-3          : {av['bleu-3']:.4f}")
    print(f"BLEU-4          : {av['bleu-4']:.4f}")
    print(f"METEOR (NLTK)   : {av['meteor']:.4f}")
    print(f"CIDEr           : {av['cider']:.4f}")

    # Simpan JSON
    out_path = Path(args.json_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(scores, f, ensure_ascii=False, indent=2)
    print(f"[INFO] JSON results written to: {out_path}")


if __name__ == "__main__":
    main()

