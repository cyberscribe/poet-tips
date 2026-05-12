# Poet Tips — Network Analysis

Analysis of the [Poet Tips](https://archive.org/details/poet_tips-20191025) dataset: ~75,000 reader-driven recommendations covering ~6,500 poets, archived 2019-10-25.

**Research frame:** What does a graph of 75,000 reader recommendations reveal about how readers map poetry — as distinct from how critics, anthologists, or academics do?

## Reproduce

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
make all          # or: python src/run_all.py
```

Each phase writes its output before the next begins. Phase 0 requires human sign-off before Phase 1 runs (see `notes/PHASE_0.md`).

## Status

| Phase | Description | Status |
|-------|-------------|--------|
| 0 | Acquire, probe, gate | Complete |
| 1 | Network structure | Complete |
| 2 | Wikidata enrichment | Complete — 65.0% match rate (3,964/6,095) |
| 3 | Analysis questions | Complete — see `notes/PHASE_3.md` |
| 4 | Interactive viewer | Complete — `outputs/interactive/explorer.html` |
| 5 | Essay | Complete — `outputs/essay/findings.html` |

## Outputs

- **Essay:** `outputs/essay/findings.html` — self-contained HTML, ~3,200 words, 6 figures inline
- **Viewer:** `outputs/interactive/explorer.html` — self-contained HTML, open in any browser
- **Figures:** `outputs/figures/3_1_*.png` through `3_6_*.png`

## Layout

```
data/raw/          raw GraphML + PROVENANCE.md + PROBE.md
data/enriched/     poets joined with Wikidata
data/derived/      computed metrics, community assignments (parquet)
src/               one script per phase + run_all.py
notes/             per-phase summaries; PHASE_0.md is the gating report
outputs/figures/   PNG/SVG for the essay
outputs/interactive/explorer.html
outputs/essay/     findings.md + findings.html
```
