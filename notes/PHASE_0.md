# Phase 0 — Gating Report

Generated from `data/raw/PROBE.md`. Full attribute distributions and sample rows are in PROBE.md; this document focuses on go/no-go assessment for Phases 1–5.

---

## Dataset snapshot

| | |
|---|---|
| Nodes (poets) | 6,095 |
| Edges (co-recommendations) | 20,526 |
| Graph type | **Undirected, simple** |
| Giant component | 5,841 nodes — **95.8%** of the graph |
| Remaining 156 components | largest is 5 nodes; 78 isolates |
| Edge weight coverage | 100% — integer, median 1, mean 2.18, max 44 |
| Node attribute coverage | `gender` 99.4%, `hits` 100%, `url` 100%, `weight` 100%, `deceased` 17.9% |

**Three facts that shape the analysis:**

1. **Node IDs are the poets' display names** (e.g., "Amy Lemmon", "Anne Carson"). No pre-existing Wikidata QIDs, VIAF IDs, or other external identifiers are embedded in the graph. Wikidata reconciliation will be name-based.

2. **Edge weights are co-recommendation counts** — how many users recommended poet A and also recommended poet B. This is a meaningful signal for all weighted centrality calls.

3. **Gender is in-graph** at 99.4% coverage (M: 3,197 / F: 2,852 / NB: 10). Phase 3.5 gender analysis does not require Wikidata for this dimension.

**Scope note:** The dataset includes hip-hop artists alongside conventional poets (André 3000, Big Boi, Frank Ocean, Jay Z, Kanye West, Tyler the Creator). This is not noise — it reflects the site's inclusive definition of "poet" and is itself worth a sentence in the essay's limitations section.

---

## Phase-by-phase assessment

### Phase 1 — Centralities and communities: 🟢 GREEN

The graph is well-suited for all planned metrics. The giant component (5,841 nodes, 20,526 edges) is densely enough connected (mean degree 6.74, median 3) to make betweenness and eigenvector centrality meaningful. Edge weights are present for weighted-degree centrality. The graph is undirected, so the spec's note on per-node reciprocity does not apply — drop that metric or note it as N/A. Louvain and Leiden community detection will run cleanly on the giant component. Recommend working on the giant component exclusively and reporting the 254 excluded nodes (78 isolates + ~176 in small components).

### Phase 2 — Wikidata enrichment: 🟡 YELLOW-GREEN

Name-based reconciliation is the only path since no external IDs are embedded. Node label uniqueness is clean (zero duplicate names), which helps. However, several challenges are predictable: (a) some poets share names with more prominent non-poets (disambiguation required); (b) some nodes are hip-hop artists whose Wikidata "occupation" may not list "poet"; (c) a non-trivial fraction of the 6,095 poets are obscure enough to have no Wikidata entry at all. The spec's fallback chain (Wikipedia search API → Open Library → VIAF) is the right approach. Target the spec's >70% match rate as the green threshold; realistically expect 60–75% on first pass. **Yellow rather than red** because even a 60% match rate is enough to run all Phase 3 analyses with appropriate caveats.

One upside: `gender` is already in-graph, so Phase 3.5 gender analysis is fully independent of Wikidata match rate.

### Phase 3.1 — Reader network vs. canon: 🟢 GREEN (contingent on Phase 2)

Wikipedia article length as canonicity proxy requires Wikidata matches, so this is contingent on Phase 2. If Phase 2 match rate falls short, the in-graph `hits` attribute (page-view count, 100% coverage, range 11–17,800) is a serviceable substitute canonicity signal: it measures reader attention independently of network centrality. Recommend computing both and reporting which proxy is used for which poets.

### Phase 3.2 — Bridge poets: 🟢 GREEN

The giant component's structure (mean degree 6.74, max 135, heavy-tailed) is exactly the topology where betweenness identifies meaningful bridges. Community detection (Phase 1) will provide the cross-community framing. No blockers.

### Phase 3.3 — Communities vs. movements: 🟡 YELLOW

Depends on Phase 2 coverage of Wikidata `P135` (literary movement). This field is patchily populated on Wikidata even for well-known poets, so real coverage may be 30–50% of matched poets (15–35% of all nodes). The heatmap and Sankey will still be telling — they'll surface which movements are well-represented and which are invisible to the recommendation network. Proceed but frame findings around the coverage caveat.

### Phase 3.4 — Era flow: 🟡 YELLOW

The in-graph `deceased` attribute (17.9% coverage) is too sparse to infer era from. Birth-year coverage depends entirely on Phase 2 Wikidata match rate. Living contemporary poets are underrepresented on Wikidata birth-year fields, so effective coverage for this analysis may be lower than the overall match rate. Still proceed — even partial era data (e.g., well-covered for 20th-century canonical poets) can produce a meaningful if partial picture, and the limitation is easy to name honestly.

### Phase 3.5 — Gender and language asymmetries: 🟢 GREEN (gender) / 🟡 YELLOW (language)

Gender analysis is fully independent of Wikidata: 99.4% in-graph coverage with three categories (M/F/NB). Language requires Wikidata (`P6886`). English-language poets likely dominate the dataset given the site's Anglophone user base; the analysis will be most meaningful for surfacing that asymmetry rather than for precise cross-linguistic comparison. Proceed with both, caveat language analysis accordingly.

### Phase 3.6 — Link prediction (surprise recommendations): 🟢 GREEN

20,526 weighted edges is ample for a 10% holdout (~2,053 edges). Node2vec on the giant component is well-posed. No blockers.

### Phase 4 — Interactive viewer: 🟢 GREEN

5,841 nodes (giant component) is within comfortable range for pre-computed ForceAtlas2 layout. Canvas rendering at this node count is fast. The in-graph `weight` attribute (appears to be an existing importance/PageRank score pre-computed by the site) could serve as a node-size proxy before Phase 1 computes fresh PageRank. No blockers.

### Phase 5 — Essay: 🟢 GREEN

The dataset is interesting enough to support a compelling essay regardless of which Phase 3 questions survive. The hip-hop inclusion, the gender breakdown (52% M / 47% F / <1% NB), and the stark disconnect between the giant component and the 156 tiny fringe components are all essay material even before any enrichment. The spec's arc is a good fit.

---

## Recommendation

**Proceed as specified, with three named adjustments:**

1. **Drop per-node reciprocity from Phase 1.** The graph is undirected; reciprocity is not defined. Note this in `notes/PHASE_1.md` when the time comes.

2. **Add `hits` as a parallel canonicity proxy in Phase 3.1.** It is 100% in-graph, requires no Wikidata match, and measures a distinct signal (reader attention volume) that complements Wikipedia article length. Run Phase 3.1 with both; use whichever tells the cleaner story as the primary figure.

3. **Set Phase 3.4 (era flow) to "attempt, caveat liberally."** Do not drop it, but frame the finding around the coverage achieved rather than projecting full-graph conclusions. If Wikidata birth-year coverage is below 40% of all nodes, reduce Phase 3.4 to a paragraph in the essay rather than a full figure.

No phases need to be dropped. The data supports the full analytical agenda; Phases 2 and 3 carry the most execution risk (Wikidata match rate), but even worst-case outcomes leave enough signal for the essay.

**This analysis is ready for human review. Do not begin Phase 1 until explicit approval is received.**
