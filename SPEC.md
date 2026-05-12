# Poet Tips: Network Analysis Specification

## Context

Poet Tips (2016–2019) was a poet-recommendation website that collected ~75,000 reader recommendations covering ~6,500 poets. The full dataset is archived on the Internet Archive in GraphML format:

  https://archive.org/details/poet_tips-20191025

This project is a **structured probe** of that dataset. The goal is not to produce a pre-decided set of findings about "what readers think." The goal is to discover, phase by phase, which claims this specific dataset can actually support — and which it can't. The narrative deliverable at the end is shaped by what survives testing, not by a headline written in advance.

**Frame to hold throughout:** the data captures recommendations made by *Poet Tips users between 2016 and 2019* — a particular, mostly Anglophone, internet-connected, contemporary-leaning sample. References to "readers" or "reader behaviour" without that qualifier silently over-generalise. The spec uses "Poet Tips users" or "the dataset" throughout. So should the essay.

## Operating principle: step-by-step gating

Every phase is a gate. Each ends with a written checkpoint in `notes/PHASE_N.md` covering: what was attempted, what worked, what didn't, what's still ambiguous, and a green/yellow/red recommendation for proceeding to the next phase as specified. The spec is a hypothesis about how the work could go; the data is the final authority. If a phase reveals that downstream phases are less supportable than the spec assumes, the spec gets revised, not pushed through.

Phase 0 is a *hard* gate — wait for explicit human approval before proceeding. Phases 1 onward are *soft* gates — the agent writes the checkpoint, decides whether to continue or pause, and surfaces the decision in the checkpoint.

## Deliverables

```
poet-tips/
  SPEC.md                          (this file)
  README.md                        (project overview, how to reproduce)
  data/
    raw/                           (downloaded GraphML, untouched)
    enriched/                      (poets joined with Wikidata)
    derived/                       (computed metrics, community assignments, null-model baselines)
  src/                             (Python scripts; one script per phase + run_all.py)
  notebooks/                       (exploratory only; not in the reproducible path)
  notes/
    PHASE_0.md ... PHASE_5.md      (per-phase gating reports)
    decisions.md                   (every threshold, seed, parameter, and rule with rationale)
  outputs/
    figures/                       (PNG/SVG for the essay)
    interactive/explorer.html      (self-contained viewer)
    essay/findings.md              (the write-up)
    essay/findings.html            (rendered)
  requirements.txt
  Makefile                         (or src/run_all.py)
```

## Methodological commitments

These apply to every phase. Violating them invalidates the work.

1. **Sampling specificity is load-bearing.** Every claim is about Poet Tips users 2016–2019. Never "readers" without that qualifier.
2. **Null models for every "surprising" claim.** Use a configuration-model null preserving the degree sequence (and edge weights if present). No effect is reported without comparison to null.
3. **Stability before labels.** Community labels are applied only to *consensus* structure across ensemble detection runs, never a single partition.
4. **Coverage transparency.** For every external field used, report what fraction of poets have that field. Findings are conditioned on coverage.
5. **Decision provenance.** Every threshold, seed, resolution parameter, and reconciliation rule goes to `notes/decisions.md` with a one-line rationale at the time of decision.
6. **"Attention," not "canon."** Without explicit canonical sources (anthology tables of contents, MLA citation counts), use "attention" framing, not "canon." Wikipedia is one signal of contemporary editor attention, not a measure of canonicity.
7. **Mismatch verification, not just match-rate reporting.** Reconciliation includes consistency checks (e.g. plausible birth/death years), not just success counts. A confident-wrong match is more damaging than an honest miss.
8. **No fishing.** The six questions in Phase 3 are stated in advance. Each gets answered honestly — positive, negative, or null. New questions can be added if motivated by what shows up, but the original six are all reported on.

## Phases

### Phase 0 — Acquire, probe, and gate (HARD GATE)

**Goal:** produce enough evidence to decide whether Phases 1–5 are viable as specified, need adjustment, or call for a different analytical frame entirely.

**Steps:**

1. Download the GraphML from the Internet Archive item. The item page lists multiple files; pick the GraphML (likely gzip- or zip-wrapped). Save the raw archive download under `data/raw/` untouched, then extract alongside it. Record the source URL, file hash, and size in `data/raw/PROVENANCE.md`.
2. Load with NetworkX. Write `data/raw/PROBE.md` reporting:
   - node count, edge count, directed/undirected, multigraph or simple
   - all node attributes, with value distributions (categorical) or ranges (numeric); flag any attribute present on <50% of nodes
   - all edge attributes (weights? timestamps? recommender identity?); same coverage check
   - five sample nodes and ten sample edges with full attributes, raw
   - connected-component count and sizes of the top five (weak components if directed)
   - degree distribution: min, median, mean, 95th, max; top 20 nodes by total degree
   - edge-weight distribution if present
   - obvious data-quality issues: duplicate node names, empty labels, self-loops, isolates, suspicious clusters
3. **Edge semantics check.** What does an edge actually mean in this graph? "If you like A, try B"? "I recommend A in general"? Something else? Look at edge attributes, edge labels, any embedded documentation. If unclear from the data, surface as a question to Robert (who built the system) — do not proceed without knowing what an edge means. The semantics of an edge determines what any centrality or community result is *about*.
4. **Name uniqueness check.** Count duplicate poet names. Flag candidates for ambiguous reconciliation downstream. If there are pre-existing identifiers in the node attributes (Wikidata QIDs, VIAF, OpenLibrary IDs), call that out — it reshapes Phase 2.
5. **Elicitation mechanism check.** Surface anything known about how the Poet Tips UI elicited recommendations. The two YouTube videos linked from Robert's project page, the project page itself, and Robert's blog may contain it. If the UI clustered or pre-filtered suggestions, the graph partly reflects the UI rather than reader judgement, and that has to be named upfront.
6. Write `notes/PHASE_0.md` — the **gating report** — assessing each downstream phase against what's in the data. For each item below, mark **green / yellow / red** with one paragraph of reasoning:
   - Phase 1 (centralities, stability, null baselines): green unless graph is implausibly sparse or fragmented.
   - Phase 2 (Wikidata enrichment): depends on name uniqueness and any pre-existing identifiers.
   - Phase 3.1 (attention vs. centrality): green if Phase 2 viable.
   - Phase 3.2 (bridge structure): green if Phase 1 viable.
   - Phase 3.3 (community-movement alignment): depends on Phase 2 movement coverage.
   - Phase 3.4 (era structure): depends on birth-year coverage.
   - Phase 3.5 (population asymmetries): depends on gender/language coverage and the existence of a defensible population baseline.
   - Phase 3.6 (edge prediction): green unless edges are too sparse to hold out meaningfully.
   - Phase 4 (viewer): green almost regardless.
   - Phase 5 (essay): adapts to which Phase 3 questions survive.
7. Close with a one-paragraph **recommendation**: proceed as specified, proceed with named modifications, or pause for re-spec. If recommending modifications, list them concretely. If recommending re-spec, sketch the alternative frame.
8. **Stop.** Wait for explicit approval. If the recommendation is to re-spec, this SPEC.md is updated before any further work — no executing against a stale plan.

**Time budget:** a few hours of agent time. If it takes meaningfully longer, that's itself a signal worth surfacing.

### Phase 1 — Network structure

Compute and persist as parquet under `data/derived/`:

- Centralities: degree, weighted-degree (if edges weighted), betweenness, eigenvector, PageRank.
- Reciprocity per node, if directed.
- **Community ensemble.** Louvain at 3–5 resolution values and 20+ random seeds; Leiden similarly. Compute pairwise normalised mutual information across runs. Persist the consensus partition (nodes that co-cluster in a supermajority of runs) and a stability score per node indicating how often it sits with its consensus community. Single-partition community labels are not used downstream.
- **Null baseline.** Generate a configuration-model null preserving the degree sequence (and edge weights if present). Compute the same centralities and run the same community-detection ensemble on the null. Persist the null statistics. Every downstream "is this surprising?" claim references this baseline.

Final artefact: `data/derived/poets.parquet` joining all per-poet metrics, including stability score and z-scores against the null where applicable.

Phase 1 closes with `notes/PHASE_1.md`: which communities are stable, which aren't, and what fraction of the graph is in stable communities. If less than ~60% of nodes are in stable consensus communities, downstream community-based questions get demoted or dropped.

### Phase 2 — External enrichment

For each poet, fetch from Wikidata via SPARQL (`https://query.wikidata.org/sparql`):

- birth year, death year, country of citizenship, gender, languages written in
- literary movements / schools (P135)
- sitelink count (a multi-language attention signal, less Anglo-biased than English Wikipedia length)
- English Wikipedia article length (one signal, not the anchor)

If reachable within budget, also pull from Open Library and VIAF as additional attention signals. The "attention index" is a documented combination, not a single number.

**Reconciliation:**

- First pass: `wbsearchentities` exact-name search.
- Disambiguate: prefer entities whose `instance of` (P31) is human and whose `occupation` (P106) includes poet/writer; if still tied, prefer the entity with the most sitelinks.
- **Mismatch verification.** For every matched poet, check that birth/death years are plausible given the recommendation context. A poet linked to recommenders who were active in the 2010s should not have died in 1612. Flag inconsistencies for a manual-sample review. Persist a confidence score per match.
- Log unmatched, ambiguous, and flagged-inconsistent poets to `data/enriched/reconciliation_log.csv`. The log is itself a finding.

**Coverage reporting.** For each field, report the fraction of poets for whom we have it. Movements (P135) are typically sparse; gender (P21) is incomplete for non-Anglophone and pre-modern poets. Wikidata's biases (editor demographics, anachronistic categories) are noted in `notes/PHASE_2.md` and inherited by every downstream finding.

Persist `data/enriched/poets_wikidata.parquet`. Aim for >70% match on at least one identifier; report actual.

Phase 2 closes with `notes/PHASE_2.md`: coverage per field, mismatch rate after verification, and a recommendation about which Phase 3 questions remain viable given coverage.

### Phase 3 — Questions to test

Each item is a **test**, not a finding. State the question, the null model, the criterion for a positive result, and what would falsify it. If a test comes back null or ambiguous, the result is "no support for this claim," not a forced headline. Drop a question outright if Phase 0–2 results make it unsupportable.

1. **Attention vs. graph centrality.** Plot the multi-signal attention index against PageRank. Test: does any off-diagonal structure survive comparison against the configuration-model null? Honest finding: name off-diagonal poets only where their position is robust to rewiring. Frame as "attention vs. centrality in this dataset," not "canon vs. readers."

2. **Bridge structure.** High-betweenness, moderate-degree poets. Test: is observed betweenness elevated above the betweenness distribution in the degree-preserving null? Report only poets whose betweenness exceeds the null at a stated threshold. Acknowledge that even robust bridges might be popular generalists rather than literary bridges; that distinction can't be cleanly settled by graph structure alone, only suggested.

3. **Community-movement alignment.** Heatmap of consensus communities × Wikidata movements (where coverage permits). Test: does mutual information between community and movement exceed what we'd see in a randomly relabelled null? Report both alignment strength and which movements are too sparsely populated to support conclusions.

4. **Era structure.** Birth-year distribution within consensus communities. Test: do communities have tighter birth-year variance than random partitions of the same sizes? Report effect size, not just direction. Honest framing: if communities are time-clustered, that may reflect Poet Tips UI behaviour (era filters, browse paths) as much as reader temporal preferences. State this in the finding, not in a footnote.

5. **Population asymmetries.** Gender (where coverage is adequate) and language-of-writing across communities and centrality bands. Test: are women / non-English-language poets distributed differently from chance, **conditional on the underlying poet population in the dataset**? Without conditioning, every asymmetry is partly a restatement of the population, not a finding. Use a population-controlled null. Acknowledge Wikidata's known underreporting of women and historical figures as a confound.

6. **Edge prediction as structure summary.** Train a simple node2vec + cosine link-prediction model on 90% of edges; predict on the held-out 10%. **Frame:** this measures *how much of the graph's structure is captured by neighbourhood patterns*, not a discovery procedure. Top predicted-but-absent edges are model extrapolations, not "hidden affinities." Report top edges as illustrative of model behaviour, with explicit framing that they are predictions of structure, not findings about reader judgement.

Phase 3 closes with `notes/PHASE_3.md`: which tests came back positive, null, or ambiguous; which questions got dropped; what surprised the agent that wasn't on this list.

### Phase 4 — Interactive viewer

Single self-contained HTML file at `outputs/interactive/explorer.html`:

- Force-directed layout, **pre-computed** in Python and embedded as static node coordinates.
- Node colour = consensus community; node size = PageRank; label on hover.
- Stability indicator: nodes that don't sit in a stable community are visibly distinct (e.g. lower opacity or dashed outline).
- Search box: type a poet name → centre on node, highlight neighbourhood.
- Side panel on selection: top 10 recommended neighbours, community label (with stability score), Wikidata enrichment summary.
- Toggles: "bridge poets only" and "top 100 by PageRank only."
- **About-this-view panel** (always visible or one click away) stating: proximity in the layout is a 2D projection artefact, not a measure of similarity; communities reflect consensus across ensemble runs; the data is Poet Tips users 2016–2019. Without this panel the viewer flatters the data.

Tech: pre-compute layout with `fa2` (ForceAtlas2) or `graph-tool` SFDP. Render with vanilla JS + Canvas. Evaluate `pyvis` first; use it only if its output meets the bar above and supports the about-panel.

### Phase 5 — Essay

`outputs/essay/findings.md` as a coherent narrative. Arc:

1. **What Poet Tips was** — the site, the period, the user base.
2. **What this data is and isn't** — explicit about sample, edge semantics, coverage, biases. This section is not an apology; it's the analytical frame.
3. **How we interrogated it** — methodological commitments (null models, stability, coverage transparency) in plain language.
4. **What survived testing** — one section per Phase 3 question that came back positive or interestingly null. Each with effect size, null comparison, and the Poet-Tips-specific qualifier.
5. **What didn't work** — questions we asked that the data couldn't answer, and what would be needed to answer them. This section is a feature, not a confession.
6. **Where this signal sits** — alongside academic, anthological, and editorial signals, not against them.

Length: 2,500–4,000 words if findings sustain it. Shorter if not. Padding is worse than concision.

The essay does *not* lead with a headline-grabbing finding. It leads with frame and method. Headline-first writing creates pressure to overclaim, and that's the failure mode this whole spec is built to avoid.

Render to HTML with a clean single-column stylesheet, readable typography, figures inline. Pandoc is sufficient.

## Tech stack

- Python 3.11+
- `networkx`, `python-igraph` (Leiden), `pandas`, `pyarrow`, `numpy`
- `matplotlib` + `seaborn` for static charts
- `requests` + `SPARQLWrapper` for Wikidata; on-disk cache keyed by query hash
- `node2vec` or `gensim` for embeddings
- `fa2` or `graph-tool` for layout
- `pandoc` for final HTML render
- `jupyter` for exploration only — final pipeline runs headless as `python src/run_all.py` or `make all`

A null-model utility (configuration-model rewiring with optional weight preservation) lives in `src/nulls.py` and is used across phases. A reconciliation-verification module lives in `src/reconciliation.py`.

Pin everything in `requirements.txt`.

## Quality bar

- Single-command reproducibility: `make all` (or `python src/run_all.py`) produces every artefact from a clean clone, given an internet connection.
- The essay reads as essay. Narrative first, evidence in service of it. Not commented-out code, not a Jupyter dump.
- Every chart caption states the null it's tested against (or labels itself "exploratory, not tested").
- Every claim about a poet subgroup (women, non-Anglophone, etc.) is conditioned on the in-dataset population baseline.
- Wikidata match rate and per-field coverage reported honestly.
- Interactive viewer loads in <3s on a laptop and remains responsive while panning.
- Code passes `ruff check`. Comments explain non-obvious choices for future readers; no change-justification, no pedantry.
- `notes/decisions.md` lists every threshold, seed, and parameter with rationale.

## Anti-goals

- No deep learning unless a simpler method demonstrably fails. Node2vec + cosine is the ceiling for link prediction.
- No 50-figure data-dump dashboard. The essay is the deliverable; figures earn their place.
- No code comments justifying changes or restating what the code says.
- No fabricated findings. Null results are part of the story.
- No headline-first writing. Frame and method come before findings.
- No community-as-object claims without stability evidence.
- No "readers think X" claims; every claim names the Poet-Tips-user sample.
- No invocation of "canon" without an explicit canonical source.
- No fishing. The six Phase 3 questions are reported on (positive, null, or dropped) regardless of how flattering the answer is.

## Judgement calls left to the agent

- If the GraphML lacks edge weights, treat recommendations as binary; adjust centrality and null-model calls accordingly. Report in Phase 0.
- If the graph is highly disconnected, work on the largest weakly-connected component; report the size of what's excluded and why excluding it is defensible.
- If Wikidata match rate is below 50%, try Wikipedia search and VIAF before declaring defeat. Don't disguise low match rates with aggregate stats.
- If a Phase 3 question is unsupportable given coverage, drop it cleanly and say so in the essay's "what didn't work" section.

## Handoff notes

This spec is the brief; further questions should be resolved by reading the data (Phase 0) before asking. If something genuinely needs human input — edge semantics is the most likely candidate — surface it at the end of the relevant phase, not mid-stream.

If at any phase the data turns out thinner, messier, or shaped differently than the spec assumes, the response is to surface and revise the spec, not to force the original plan through.
