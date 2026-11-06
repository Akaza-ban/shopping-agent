import argparse
import itertools
import json
import os
import sys
from dataclasses import replace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.rag import Thresholds, rag_service  # noqa: E402
from services.rag.evaluation import evaluate_service, load_eval_set  # noqa: E402


def objective(s):
    return (s["recall@5"] + s["precision@5"] + s["mrr@10"] + s["negative_reject_rate"]) / 4


def calibrate():
    queries = load_eval_set()
    grid = itertools.product(
        [0.30, 0.33, 0.36, 0.39, 0.42, 0.45, 0.48], [0.45, 0.50, 0.55, 0.60], [0.5, 0.67, 0.99]
    )
    results = []
    for accept, weak, lex in grid:
        if weak < accept:
            continue
        rag_service.thresholds = replace(Thresholds(), vec_accept=accept, vec_weak=weak, lex_support=lex)
        s = evaluate_service(rag_service, queries)["summary"]
        results.append((objective(s), rag_service.thresholds, s))
    results.sort(key=lambda r: r[0], reverse=True)
    for obj, t, s in results[:10]:
        print(f"obj={obj:.3f} {t} -> {s}")


def print_report(report):
    for r in report["rows"]:
        if r.get("negative"):
            print(f"{'OK ' if r['ok'] else 'BAD'} [neg] {r['query']:<40} trả {r['returned']} {r['top']}")
        else:
            print(f"R@5={r['recall@5']:.2f} P@5={r['precision@5']:.2f} MRR={r['mrr@10']:.2f} "
                  f"{r['query']:<40} ({r['n_relevant']} đáp án) {r['top']}")
    print(json.dumps(report["summary"], ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--calibrate", action="store_true")
    ap.add_argument("--mode", choices=["hybrid", "vector"], default="hybrid")
    ap.add_argument("--json", help="ghi kết quả ra tệp JSON")
    args = ap.parse_args()

    if args.calibrate:
        calibrate()
        return
    rag_service.hybrid = args.mode == "hybrid"
    report = evaluate_service(rag_service)
    print_report(report)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
