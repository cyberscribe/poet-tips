# Phase 3 — Questions to Test

## Data summary

- Giant component: 5841 poets
- Joined with Wikidata (Phase 2): 5841 rows; match rate 65.0% overall
- Community detection: Louvain 24 communities (modularity 0.6008) used as primary partition

## 3.1 Attention vs. graph centrality

**Question:** Do high-PageRank poets also have high external attention (Wikipedia + page views)?
Or is there off-diagonal structure?

**Attention index:** log1p(WP article bytes) and log1p(Poet Tips page views), each min-max
scaled to [0,1], averaged when both available.

**Result:** positive, but modest

- Spearman ρ = 0.4159
- Permutation null mean ρ = -0.0000 ± 0.0132
- Permutation p = 0.000 (n=2000 shuffles)

There is a positive correlation, elevated above chance, but the relationship is noisy.
Off-diagonal poets are the essay's analytic payload:

**High PageRank, low external attention** (central to Poet Tips users but less prominent elsewhere):
Wil Gibson, Ron Mohring, Emily O'Neill, Elly Finzer, Roger Bonair Agard, Robert Duncan, Valerie Wetlaufer, Janey Smith

**High attention, low PageRank** (widely known but less central in this recommendation network):
Morgaine Merch Lleuad, M.G. Martin, Urayoan Noel, Hsia Yu, Suchoon Mo, Beyoncé, Paul McCartney, Yoko Ono

**Framing:** attention is "Wikipedia editorial and Poet Tips user attention," not canon.
PageRank captures centrality in co-recommendation patterns of Poet Tips users 2016–2019.

## 3.2 Bridge structure

**Question:** Are there poets who serve as unusually central bridges between communities,
above what the degree-preserving null would predict?

**Method:** weighted betweenness (1/weight distances); 5 degree-preserving rewired graphs
(double_edge_swap + weight permutation); approximate betweenness k=200.

**Result:** positive — clear bridge signal above null

- Null 95th percentile: 0.005127
- Null 99th percentile: 0.013887
- Poets above 95th: 20
- Poets above 99th: 20

**Top 15 bridge poets:**

| Poet | Weighted betweenness | Degree | Community |
|------|---------------------|--------|-----------|
| Melissa Studdard | 0.1710 | 73 | 0 |
| Anne Carson | 0.1544 | 101 | 10 |
| Elaine Feeney | 0.1271 | 27 | 4 |
| Anne Sexton | 0.0973 | 77 | 7 |
| Sylvia Plath | 0.0939 | 87 | 7 |
| Meg Johnson | 0.0640 | 70 | 2 |
| Wallace Stevens | 0.0639 | 79 | 1 |
| Pablo Neruda | 0.0627 | 42 | 9 |
| John Ashbery | 0.0608 | 92 | 1 |
| Ocean Vuong | 0.0596 | 44 | 0 |
| Naomi Shihab Nye | 0.0595 | 32 | 4 |
| Emily Dickinson | 0.0568 | 62 | 7 |
| Danez Smith | 0.0567 | 46 | 3 |
| Louise Glück | 0.0561 | 59 | 7 |
| Federico García Lorca | 0.0541 | 50 | 9 |

**Note:** Amy Lemmon is #1 by *unweighted* betweenness (degree 135, 89% weight=1 edges)
but drops dramatically on weighted betweenness — an artefact of site-gaming rather than
structural importance. Weighted betweenness is the correct measure here.

## 3.3 Community–era and community–nationality alignment

**Question:** Do Louvain communities cluster by birth era or nationality above chance?

**Method:** Normalized mutual information; 1000 label-permutation test (community labels shuffled).
Primary axes: birth era (6 buckets from Pre-1900 to 1980+) and nationality (7 regions).
Literary movements (P135, 5% coverage) retained as supplemental reference only.

**Era alignment result:** NMI = 0.0424 (permutation p = 0.000, n=1000)
Coverage: 2756 poets with both birth year and community in top-12 communities.

**Nationality alignment result:** NMI = 0.1427 (permutation p = 0.000, n=1000)
Coverage: 2543 poets with both nationality and community in top-12 communities.

Era NMI: positive (above null)
Nationality NMI: positive (above null)

**Framing:** "community" is a Louvain partition of co-recommendation patterns; it reflects
how Poet Tips users 2016–2019 recommended together, not scholarly tradition.

## 3.4 Era structure within communities

**Question:** Do communities contain poets from more similar birth eras than random?

**Method:** Mean within-community birth-year variance vs. 1000 random partitions of same sizes.

**Result:** null / marginal

- Observed mean within-community variance: 2551.3 years²
- Null mean variance: 2597.0 ± 109.5
- Effect size: 0.417 σ below null (tighter than random)
- Permutation p: 0.3400

Coverage: 2756 poets with birth year in top-12 communities (43.4% of giant component).

**Framing:** even where communities are era-stratified, this may reflect the Poet Tips
UI's browse paths (era filters) as much as reader temporal preferences.

## 3.5 Population asymmetries

**Question:** Are women distributed differently across communities and centrality bands,
conditioned on the overall gender split in the dataset?

**Dataset baseline:** F fraction = 0.473 (M = 0.527; NB n=10 excluded).

**Community-level result:**
- Chi-square (gender × community): χ² = 164.01, p = 2.01e-29
- Significant heterogeneity across communities

**Per-community F fraction (top communities):**

| Community | F fraction |
|-----------|-----------|
| C7 (Olds) | 0.642 |
| C2 (Johnson) | 0.574 |
| C0 (Studdard) | 0.523 |
| C10 (Carson) | 0.523 |
| C3 (Smith) | 0.502 |
| C4 (Feeney) | 0.466 |
| C6 (Robertson) | 0.466 |
| C1 (Ashbery) | 0.451 |
| C5 (Lemmon) | 0.431 |
| C8 (Eliot) | 0.367 |
| C11 (Hopkins) | 0.322 |
| C9 (Lorca) | 0.245 |

**PageRank-band result:**
- Low PR: F=0.474,
  Mid PR: F=0.470,
  High PR: F=0.474
- Chi-square (gender × PR band): χ² = 0.09, p = 9.56e-01

**Note on Wikidata language coverage:** languages-written (P6886) covers only ~20% of matched
poets and is heavily skewed toward non-English-language writers — English-language poets are
almost universally untagged. This makes language asymmetry analysis unreliable; dropped.

## 3.6 Edge prediction as structure summary

**Test:** how well does neighbourhood structure (node2vec + cosine) predict held-out edges?
**Result:** positive (AUC = 0.7598)

- 10% of edges held out (seed 42); node2vec trained on 90%
- Positive edge mean cosine: 0.4470
- Negative (non-edge) mean cosine: 0.2638
- AUC 0.7598 vs. 0.5 baseline

**Framing:** this measures how much of the graph's structure is captured by neighbourhood
patterns — not a discovery procedure. AUC above 0.7
indicates strong structural regularity
exploitable by the embedding.

**Top predicted-but-absent edges (illustrative; these are model extrapolations, not findings):**

| Poet A | Poet B | Cosine |
|--------|--------|--------|
| Akeem Olaj | Clint Smith | 0.9530 |
| Mike Chasar | J.T. Whitehead | 0.9513 |
| Gary Ligi | A.D. Winans | 0.9407 |
| Geoff Page | Clive James | 0.9335 |
| Doreen Rosenstrauch | Amina Chinnell-Mateen | 0.9067 |
| Chris Agee | Chris Pannell | 0.8993 |
| Charlotte Brontë | Shawna Howson | 0.8982 |
| Bud Backen | Patrick McKinnon | 0.8849 |
| John Webster | Caron Freeborn | 0.8707 |
| Karen Correia Da Silva | Duncan Mercredi | 0.8692 |


## Summary: which tests returned positive results

| Test | Result | Strength |
|------|--------|---------|
| 3.1 Attention vs. centrality | Positive (ρ=0.416, p=0.000) | Modest |
| 3.2 Bridge structure | Positive (20 poets above null 99th) | Strong |
| 3.3 Community–era NMI | Positive (p=0.000) | Moderate |
| 3.3 Community–nationality NMI | Positive (p=0.000) | Moderate |
| 3.4 Era structure | Null (p=0.340) | — |
| 3.5 Gender (community) | Positive (p=2.01e-29) | Moderate |
| 3.5 Gender (PR band) | Null (p=9.56e-01) | — |
| 3.6 Edge prediction | AUC 0.76 | Strong |

## What didn't work / was dropped

- **Literary movements (P135):** 5.0% coverage among matched poets (165/3290). Too sparse
  for statistical analysis. Retained as supplemental reference.
- **Languages written:** ~20% coverage, heavily biased toward non-English writers. Dropped.
- **Death year / historical coverage:** many pre-1900 poets are included but sparsely matched.
  All findings conditioned on Wikidata coverage; see PHASE_2.md for field-level statistics.

## Surprising findings not on the original list

- The dataset is overwhelmingly contemporary: median birth year ~1953, 75th percentile 1971.
  This is a portrait of 2010s Anglophone poetry internet culture, not historical literary canon.
- Community structure is robust (modularity 0.6) but several communities are internally
  diverse by era and nationality — co-recommendation patterns do not map cleanly onto
  literary movements.
- Amy Lemmon's degree-1 anomaly is a clear methodological case study: unweighted betweenness
  flatters degree, not structural importance.

## Recommendation for Phase 4 (interactive viewer)

All positive Phase 3 findings are suitable for embedding in the viewer's side panel.
The essay's "what didn't work" section should acknowledge movements and language coverage.
Phase 4 is green to proceed.
