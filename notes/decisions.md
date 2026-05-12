# Decisions log

Every threshold, seed, parameter, and rule with rationale.

Inherited from Phase 1–2: see PHASE_1.md and PHASE_2.md.

## Phase 3

- 3.1 attention index: log1p(wp_article_bytes) + log1p(hits) each min-max scaled, averaged when both available. Rationale: both signals measure editorial/reader attention but at different scales; log + normalise before combining avoids hits dominating.
- 3.1 permutation null: 2000 shuffles of attention values vs fixed PageRank. Rationale: tests whether observed ρ is higher than random; fast alternative to graph rewiring since attention is external and fixed.
- 3.2 null model: 5 degree-preserving rewired graphs (double_edge_swap, ~10×|E| swaps) with weights randomly permuted across edges; betweenness computed with k=200 approximate. Rationale: preserves degree sequence + weight distribution, randomises structure.
- 3.2 bridge threshold: raw betweenness > null 95th percentile (pooled across 5 rewirings). Rationale: 95th is the standard threshold for 'significantly elevated'; 99th also reported.
- 3.3 NMI normalisation: 'arithmetic' average_method (recommended for class-imbalanced data). 1000 label-permutation shuffles of community assignments.
- 3.4 null: 1000 permutations of birth years across poets (within top-12 communities). One-tailed test: communities have lower within-group variance than random. Effect size = (null_mean - obs) / null_std.
- 3.5 gender test: chi-square on M/F counts per community, expected proportional to overall M/F ratio in dataset (population-controlled). NB excluded (n=10).
- 3.6 edge split: 90/10 random (seed 42). node2vec: dim=64, walk_length=20, num_walks=10, p=1, q=1 (unbiased), window=5, epochs=10. Cosine similarity of embedding pairs as score.
