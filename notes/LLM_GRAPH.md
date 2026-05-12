# LLM Graph — Parallel Similarity Mining

## Motivation

The five-phase analysis produced a human-generated co-recommendation graph. This extension mines a second, parallel graph from a local LLM to compare canonical similarity judgements (what an LLM trained on literary-critical writing "knows") against reader behaviour (what Poet Tips users actually did).

The divergence between the two graphs is the analytical target — not either graph alone.

## Method

For each poet in the high-degree subset (degree ≥ 10, n ≈ 1,278), query a local Ollama model:

> "List the {n} poets most similar to {name} in descending order of similarity. Return ONLY a JSON array …"

Model: `phi4:14b` (Microsoft Phi-4, Q4_K_M, 14.7B params)  
Host: MacBook Pro 16-inch M3, 36 GB unified memory  
Throughput: ~27s/query → full high-degree run ≈ 9.5 hrs  
Top-N: 10 neighbours per poet

Output is a directed edge list: `(source_poet, target_poet, rank, score, reason)`.

## Script

`src/mine_llm_graph.py` — checkpoint-safe, resume-friendly.  
Output: `data/llm_graph/results.jsonl` (append-only) → `data/llm_graph/results.parquet` on completion.

Run command:
```bash
nohup python3 src/mine_llm_graph.py --threshold 10 > logs/llm_graph.log 2>&1 &
echo $! > logs/llm_graph.pid
```

## POC smoke test (2026-05-12)

Three highest-degree poets queried (Amy Lemmon, Richard Siken, Anne Carson). Results look substantively reasonable. Two output artefacts to clean in post-processing:

1. **Markdown fences** — phi4 occasionally wraps output in ` ```json ``` ` despite system-prompt instruction. `parse_response()` strips these.
2. **Inverted names** — phi4 occasionally produces `"Plath Sylvia"` instead of `"Sylvia Plath"`. Flag and clean before graph construction.
3. **Score compression** — all lists run ~0.73–0.92 with near-uniform step. Treat scores as within-query ordinal ranks, not calibrated cross-query distances.

## Planned comparisons (post-run)

| Comparison | What it reveals |
|---|---|
| Edge overlap (LLM ∩ human) | Fraction of reader edges that are "canonically expected" |
| Community NMI (LLM vs human) | Whether Louvain communities reflect canonical groupings or reader-specific formations |
| Centrality rank correlation (PageRank on each) | Whether the graph's hierarchy mirrors literary fame or reader engagement |
| High human / low LLM similarity | Reader-discovered affinities outside received canon — most interesting zone |
| High LLM / low human similarity | Canonical neighbours readers didn't connect |
| Bridge poets revisited | Do Phase 3.2 bridges also bridge in LLM space? If not, their role is social not stylistic |

## Model selection notes

Available locally at time of writing: `phi4:14b`, `glm-4.7-flash:latest` (29.9B), `gemma4:latest` (8B), `llama3:latest` (8B), `qwen:14b`, `deepseek-r1:8b`.

`phi4:14b` chosen over larger models for the POC: no extended-thinking overhead, strong instruction following, good English literary breadth, fast enough for a ≤10hr overnight run on M3.

`qwen3.5:latest` was removed from local storage during testing (accidental `ollama delete`). If a second pass with a different model is wanted, `qwen2.5:32b` (~18 GB) is recommended.

## Known limitations

- LLM graph reflects training-data biases (anglophone, academic, anthology-skewed), not a neutral ground truth.
- ~2,000 low-degree poets excluded from this run; their LLM neighbourhood would be noisier (less training data on obscure contemporaries).
- Scores are not calibrated across queries; cross-poet score comparisons are unreliable.
- The directed LLM graph (A's top-10 ≠ B's top-10) must be symmetrised before comparing to the undirected human graph. Symmetrisation strategy TBD (max / mean / mutual-only).
