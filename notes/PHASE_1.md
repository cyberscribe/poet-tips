# Phase 1 — Network Structure

## Scope

Working on the giant component: **5,841 nodes**, **20,427 edges**
(254 nodes excluded — 78 isolates + small components; see Phase 0 PROBE.md).

Per-node reciprocity is not computed: the graph is undirected.

Betweenness centrality is approximated with k=500 pivot nodes (random seed 42).
For a graph of this size the approximation is within ~5% of exact values.

## Community detection

### Louvain

24 communities, modularity **0.6008**

| Community | Size | Top poet by PageRank |
|-----------|------|---------------------|
| 0 | 882 | Melissa Studdard |
| 1 | 764 | John Ashbery |
| 2 | 720 | Meg Johnson |
| 3 | 527 | Danez Smith |
| 4 | 495 | Elaine Feeney |
| 5 | 424 | Amy Lemmon |
| 6 | 358 | Lisa Robertson |
| 7 | 311 | Sharon Olds |
| 8 | 309 | T.S. Eliot |
| 9 | 269 | Federico García Lorca |

### Leiden

26 communities, modularity **0.5865**

| Community | Size | Top poet by PageRank |
|-----------|------|---------------------|
| 0 | 793 | John Ashbery |
| 1 | 572 | Melissa Studdard |
| 2 | 553 | Anne Carson |
| 3 | 507 | Danez Smith |
| 4 | 436 | Elaine Feeney |
| 5 | 433 | Sharon Olds |
| 6 | 427 | Charles Simic |
| 7 | 393 | Larry Levis |
| 8 | 379 | Meg Johnson |
| 9 | 359 | Amy Lemmon |

## Top poets

### By PageRank

| Poet | PageRank | Degree | Betweenness | Community |
|------|----------|--------|-------------|-----------|
| Anne Carson | 0.0035 | 101 | 0.0336 | 10.0 |
| Melissa Studdard | 0.0033 | 73 | 0.0196 | 0.0 |
| Meg Johnson | 0.0031 | 70 | 0.0197 | 2.0 |
| John Ashbery | 0.0027 | 92 | 0.0256 | 1.0 |
| Sharon Olds | 0.0027 | 93 | 0.0262 | 7.0 |
| Sylvia Plath | 0.0026 | 87 | 0.0282 | 7.0 |
| Trace Peterson | 0.0024 | 86 | 0.0232 | 1.0 |
| Anne Sexton | 0.0023 | 77 | 0.0201 | 7.0 |
| Amy Lemmon | 0.0023 | 135 | 0.0463 | 5.0 |
| Richard Siken | 0.0020 | 111 | 0.0339 | 0.0 |
| Elizabeth Bishop | 0.0020 | 87 | 0.0238 | 5.0 |
| Wallace Stevens | 0.0020 | 79 | 0.0206 | 1.0 |
| Elaine Feeney | 0.0020 | 27 | 0.0072 | 4.0 |
| Ocean Vuong | 0.0020 | 44 | 0.0076 | 0.0 |
| Frank O'Hara | 0.0019 | 89 | 0.0268 | 1.0 |

### By Betweenness

| Poet | Betweenness | Degree | PageRank | Community |
|------|-------------|--------|----------|-----------|
| Amy Lemmon | 0.0463 | 135 | 0.0023 | 5.0 |
| Richard Siken | 0.0339 | 111 | 0.0020 | 0.0 |
| Anne Carson | 0.0336 | 101 | 0.0035 | 10.0 |
| Sylvia Plath | 0.0282 | 87 | 0.0026 | 7.0 |
| Frank O'Hara | 0.0268 | 89 | 0.0019 | 1.0 |
| Sharon Olds | 0.0262 | 93 | 0.0027 | 7.0 |
| John Ashbery | 0.0256 | 92 | 0.0027 | 1.0 |
| Elizabeth Bishop | 0.0238 | 87 | 0.0020 | 5.0 |
| Trace Peterson | 0.0232 | 86 | 0.0024 | 1.0 |
| Wallace Stevens | 0.0206 | 79 | 0.0020 | 1.0 |
| Anne Sexton | 0.0201 | 77 | 0.0023 | 7.0 |
| Meg Johnson | 0.0197 | 70 | 0.0031 | 2.0 |
| Melissa Studdard | 0.0196 | 73 | 0.0033 | 0.0 |
| Cecilia Llompart | 0.0189 | 68 | 0.0010 | 2.0 |
| Catherine Daly | 0.0179 | 63 | 0.0009 | 1.0 |

## Artefacts

- `data/derived/poets.parquet` — per-poet metrics (all 6,095 nodes, NaN for excluded); columns include both `betweenness` (unweighted) and `weighted_betweenness` (1/weight distance)
- `data/derived/communities.parquet` — per-community summaries for both algorithms

## Data quality finding: Amy Lemmon and site-gaming

Amy Lemmon ranks **#1 by unweighted betweenness and #1 by degree** (135 edges), but post-analysis revealed her connections are almost certainly an artefact of active site participation rather than genuine reader affinity:

- **89% of her 135 edges have weight=1** (single co-recommendation, never repeated). Compare: Melissa Studdard 0% weight=1, Anne Carson 23%, Sylvia Plath 49%.
- **Mean edge weight 1.13** vs 4.31 (Carson), 6.25 (Studdard), 5.34 (Meg Johnson).
- **Hits/degree ratio = 10.2** — the lowest of any top-20-degree poet and literally the 0th percentile across the giant component. Every comparable poet has more page views per connection.
- **Meg Johnson** is the inverse signal: 70 connections, 17,801 hits, mean weight 5.34 — the strongest organic reader-interest signal in the dataset.

The site's own pre-computed `node_weight` attribute already discounted her (0.46 vs Siken 2.83, Peterson 2.91), suggesting the site's algorithm independently detected the same pattern.

**Consequence:** `weighted_betweenness` (1/weight distance) is the correct column for Phase 3.2 bridge-poet analysis. Amy Lemmon drops from **#1 to #78** under weighted betweenness; the top 15 changes entirely to a more recognisable literary list (Studdard, Carson, Feeney, Sexton, Plath, Meg Johnson, Neruda, Dickinson, Glück, Naomi Shihab Nye). The unweighted rank is retained as a column and is itself an essay finding — evidence that the network is a portrait of the site's users as much as of poetry.

## Assessment for Phase 3

- **Phase 3.1 (canon vs. network):** ready — PageRank computed, Wikipedia lengths come from Phase 2. Use `hits` (in-graph page views) as a parallel canonicity proxy.
- **Phase 3.2 (bridge poets):** ready — use `weighted_betweenness`, not `betweenness`.
- **Phase 3.3 (communities vs. era/nationality):** ready for the pivot from P135 movements to era + nationality (see Phase 0 gating report). P135 coverage ~9% of matched poets; birth year + citizenship are the primary axes.
- **Phase 3.4 (era flow):** ready — community assignments exist; birth years come from Phase 2.
- **Phase 3.5 (gender asymmetries):** ready — gender is in-graph and now joined in poets.parquet.
- **Phase 3.6 (link prediction):** ready — node embeddings will use this graph.
