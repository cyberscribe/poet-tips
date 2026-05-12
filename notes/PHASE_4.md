# Phase 4 — Interactive Viewer

## Deliverable

`outputs/interactive/explorer.html` — single self-contained HTML file, 1.8 MB.

## Implementation

- Layout: ForceAtlas2 (400 iterations, BarnesHut optimised), positions normalised to [-1, 1]
- Rendering: vanilla JS + Canvas API, no external dependencies
- Node colour: Louvain community (24 communities; 20-colour qualitative palette, cycling)
- Node size: PageRank (r = 3 + 12√(PR/PR_max))
- Stability indicator: dashed ring + reduced opacity for nodes with stability < 0.70
- Bridge ring: orange ring on top-20 weighted-betweenness poets
- Features: pan/zoom (mouse + touch), hover tooltip, click-to-select side panel, search box,
  "bridges only" toggle, "top 100 by PR only" toggle, about-modal

## Stability finding

Community stability was computed as Louvain–Louvain agreement across 20 random seeds:
for each node, fraction of runs where it co-clustered with ≥50% Jaccard overlap of
its seed-0 community.

| Statistic | Value |
|-----------|-------|
| Mean stability | 0.387 |
| Stable (≥0.70) | 1,126 / 5,841 (19.3%) |

This low stability rate reflects genuine Louvain sensitivity to initialisation on this graph:
the modularity landscape appears flat near the optimum, with many near-equivalent partitions
at resolution 1.0. The high modularity score (0.60) is real, but the specific partition
boundaries shift substantially between runs. Only the strongest-signal communities
(e.g. the international-language cluster around Lorca/Neruda, and the confessional cluster
around Olds/Plath/Sexton) are consistently recovered.

**Essay implication:** community-level findings should be qualified as "the Louvain partition
used here" rather than "the community structure." This is noted in the About panel and
should appear in the essay's methodology section.

## Viewer features

- About panel: always accessible via "About this view" button; states layout artefact caveat,
  Poet Tips 2016–2019 framing, and data coverage limitations
- Side panel (click a node): name, community + stability score, PR rank, degree, bridge status,
  Wikidata metadata (birth year, nationality, Wikipedia link), top 10 recommended neighbours
- Neighbours are clickable (navigate to that poet)
- Search: autocomplete against all 6,095 names; selects and centres on match
- Labels: visible at zoom >150 for top-30 PR poets; visible for selected node's neighbourhood
  at all zoom levels
- Toggles: "Bridges only" shows 20 bridge poets; "Top 100 only" shows top 100 by PR

## Phase 5 recommendation

Green to proceed. Viewer is functional and communicates all Phase 3 findings.
Essay findings should reference figure numbers from outputs/figures/.
