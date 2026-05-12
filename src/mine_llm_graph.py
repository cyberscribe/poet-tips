#!/usr/bin/env python3
"""Mine LLM-based poet similarity graph using a local Ollama model.

Outputs:
  data/llm_graph/results.jsonl   — append-only edge log (source, rank, name, score, reason)
  data/llm_graph/checkpoint.json — set of completed poet names (resume-safe)
  data/llm_graph/results.parquet — converted at end of run

Usage:
  python src/mine_llm_graph.py [--threshold 10] [--model phi4:14b] [--top-n 10]
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path

import igraph as ig
import pandas as pd
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

GRAPH_FILE = "poet_tips-20191025.graphml"
OUTPUT_DIR = Path("data/llm_graph")
OLLAMA_URL = "http://localhost:11434/api/chat"
REQUEST_TIMEOUT = 120
SLEEP_BETWEEN = 0.5  # seconds between queries; Ollama is local so this is just breathing room

SYSTEM_PROMPT = (
    "You are a literary expert. Respond only with valid JSON. "
    "No markdown, no code fences, no explanation — just the JSON array."
)

USER_TEMPLATE = (
    "List the {n} poets most similar to {name} in descending order of similarity. "
    "Return ONLY a JSON array using this exact schema: "
    '[{{"rank":1,"name":"Poet Name","score":0.95,"reason":"one sentence"}}, ...] '
    'The "name" field must contain only the poet\'s canonical full name. '
    'The "score" field must be a float between 0.0 and 1.0.'
)


def load_poets(min_degree: int) -> list[str]:
    g = ig.Graph.Read_GraphML(GRAPH_FILE)
    pairs = sorted(
        zip(g.vs["id"], g.degree()), key=lambda x: x[1], reverse=True
    )
    poets = [name for name, deg in pairs if deg >= min_degree]
    log.info("Graph loaded: %d poets with degree >= %d", len(poets), min_degree)
    return poets


def load_checkpoint(path: Path) -> set[str]:
    if path.exists():
        with open(path) as f:
            return set(json.load(f))
    return set()


def save_checkpoint(path: Path, done: set[str]) -> None:
    with open(path, "w") as f:
        json.dump(sorted(done), f)


def parse_response(content: str) -> list[dict] | None:
    text = content.strip()
    # Strip markdown code fences if the model ignored instructions
    if text.startswith("```"):
        lines = text.splitlines()
        inner = lines[1:-1] if lines and lines[-1].strip() == "```" else lines[1:]
        text = "\n".join(inner).strip()
    try:
        data = json.loads(text)
        return data if isinstance(data, list) else None
    except json.JSONDecodeError:
        return None


def query_model(poet: str, model: str, top_n: int, retry: bool = True) -> list[dict] | None:
    payload = {
        "model": model,
        "stream": False,
        "options": {"temperature": 0.1, "num_ctx": 2048},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_TEMPLATE.format(n=top_n, name=poet)},
        ],
    }
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        content = resp.json()["message"]["content"]
        result = parse_response(content)
        if result is None:
            log.warning("Parse failed for %s — raw: %.150s", poet, content)
            # One retry with a more explicit nudge
            if retry:
                log.info("Retrying %s...", poet)
                return query_model(poet, model, top_n, retry=False)
        return result
    except requests.Timeout:
        log.error("Timeout for %s", poet)
        return None
    except Exception as e:
        log.error("Request failed for %s: %s", poet, e)
        return None


def finalize(results_file: Path) -> None:
    rows = []
    with open(results_file) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    if not rows:
        log.warning("No results to convert.")
        return
    df = pd.DataFrame(rows)
    out = results_file.with_suffix(".parquet")
    df.to_parquet(out, index=False)
    log.info("Saved %d rows to %s", len(df), out)


def main():
    parser = argparse.ArgumentParser(description="Mine LLM poet similarity graph")
    parser.add_argument("--threshold", type=int, default=10,
                        help="Min degree to include a poet (default: 10 → ~1,278 poets)")
    parser.add_argument("--model", default="phi4:14b",
                        help="Ollama model name (default: phi4:14b)")
    parser.add_argument("--top-n", type=int, default=10,
                        help="Neighbours to request per poet (default: 10)")
    parser.add_argument("--finalize-only", action="store_true",
                        help="Skip querying; just convert existing JSONL to parquet")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    checkpoint_file = OUTPUT_DIR / "checkpoint.json"
    results_file = OUTPUT_DIR / "results.jsonl"

    if args.finalize_only:
        finalize(results_file)
        return

    poets = load_poets(args.threshold)
    done = load_checkpoint(checkpoint_file)
    remaining = [p for p in poets if p not in done]
    log.info("Checkpoint: %d done, %d remaining", len(done), len(remaining))

    if not remaining:
        log.info("All poets processed. Run with --finalize-only to build parquet.")
        return

    with open(results_file, "a") as out:
        for i, poet in enumerate(remaining, 1):
            log.info("[%d/%d] %s", i, len(remaining), poet)
            result = query_model(poet, args.model, args.top_n)

            if result is not None:
                for item in result:
                    item["source"] = poet
                    out.write(json.dumps(item, ensure_ascii=False) + "\n")
                out.flush()
                done.add(poet)
                save_checkpoint(checkpoint_file, done)
                log.info("  -> %d neighbours", len(result))
            else:
                log.warning("  -> failed, skipping (not checkpointed)")

            if i < len(remaining):
                time.sleep(SLEEP_BETWEEN)

    log.info("Run complete. Converting to parquet...")
    finalize(results_file)


if __name__ == "__main__":
    main()
