# Phase 2 — External Enrichment

## Run details

- Launched: 2026-05-11 ~18:49 BST; completed 2026-05-12
- Rate: 5 s per API call + 0.5 s cache-hit sleep; ~0 rate-limit errors
- Resume-from-checkpoint logic: checkpoints every 200 entries
- Output: `data/enriched/poets_wikidata.parquet`, `data/enriched/unmatched.csv`
- Contact header: `robert@peakepro.com` per Wikidata bot policy

## Match results

| Status | Count | % of 6,095 |
|--------|-------|------------|
| matched | 3,290 | 54.0% |
| ambiguous | 674 | 11.1% |
| no_results | 1,945 | 31.9% |
| low_confidence | 186 | 3.1% |
| **Total matched + ambiguous** | **3,964** | **65.0%** |

The Phase 0 sample predicted 65–71% overall match rate. The final run lands at the lower end (65.0%), consistent with the predicted decline for obscure and contemporary poets not yet in Wikidata.

Matched poets = `match_status == 'matched'` (strict); ambiguous = multiple plausible candidates, resolver picked highest-sitelink entity but confidence is lower.

## Per-field coverage

Coverage is reported across all 6,095 queried poets and across the 3,290 strictly matched poets.

| Field | All poets | Matched only |
|-------|-----------|--------------|
| Birth year | 2,643 / 6,095 (43.4%) | 2,643 / 3,290 (80.3%) |
| Death year | 945 / 6,095 (15.5%) | 945 / 3,290 (28.7%) |
| Wikipedia article bytes | 2,588 / 6,095 (42.5%) | 2,588 / 3,290 (78.7%) |
| Nationality (citizenship) | 2,421 / 6,095 (39.7%) | 2,421 / 3,290 (73.6%) |
| Literary movements (P135) | 165 / 6,095 (2.7%) | 165 / 3,290 (5.0%) |
| Languages written (P6886) | 652 / 6,095 (10.7%) | 652 / 3,290 (19.8%) |

Birth-year coverage across all poets queried: **43.4%** — above the Phase 3.4 viability threshold of 40%.

## Wikidata bias notes

These biases propagate into every downstream finding that uses Wikidata fields:

- **Nationality**: heavily Anglo-American. Non-Anglophone poets are matched at lower rates.
- **Literary movements (P135)**: 5.0% coverage among matched poets — confirmed too sparse for Phase 3.3 primary analysis. Pivot to era + nationality stands.
- **Languages (P6886)**: primarily tagged for non-English-language writers. English-language poets are almost entirely untagged, making this field unsuitable as a symmetrical measure.
- **Gender (P21)**: not used — the in-graph `gender` attribute covers 99.4% of nodes.
- **Birth year**: plausible range check applied during Phase 3 data prep; 32 anomalous values (outside 1400–2010) excluded.

## Top nationalities (among matched poets)

| Nationality | Count |
|-------------|-------|
| United States | 1,297 |
| United Kingdom | 307 |
| Canada | 228 |
| France | 62 |
| Ireland | 51 |
| Australia | 32 |
| Other | ~444 |

(Historical UK variants — "Kingdom of England", "Kingdom of Great Britain", "United Kingdom of Great Britain and Ireland" — are normalised to "United Kingdom" in Phase 3.)

## Top literary movements (P135)

| Movement | Count |
|----------|-------|
| Beat Generation | 21 |
| Harlem Renaissance | 19 |
| Romanticism | 14 |
| Symbolism | 7 |
| Scottish Renaissance | 6 |

165 poets total with P135 data; too sparse for statistical analysis but retained as supplemental reference in Phase 3.3.

## Reconciliation log

- `data/enriched/unmatched.csv` — 2,131 poets with no confident match
- Mismatch verification: birth/death year plausibility checked at reconciliation time; dates outside 1400–2010 range flagged as likely wrong matches during Phase 3 prep

## Phase 3 viability assessment

| Sub-question | Status |
|---|---|
| 3.1 Attention vs. centrality | **Green** — WP article bytes + in-graph hits both available |
| 3.2 Bridge structure | **Green** — weighted_betweenness computed in Phase 1 |
| 3.3 Community alignment | **Green (modified)** — era + nationality as axes; movements supplemental |
| 3.4 Era structure | **Green** — 43.4% birth-year coverage overall; exceeds 40% threshold |
| 3.5 Population asymmetries | **Green** — gender in-graph at 99.4%; language too Anglo-biased to use |
| 3.6 Edge prediction | **Green** — no Wikidata dependency |
