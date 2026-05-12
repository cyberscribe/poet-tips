"""Phase 5: Write the essay and render to HTML."""

from pathlib import Path

ROOT = Path(__file__).parent.parent
ESSAY_DIR = ROOT / "outputs" / "essay"
ESSAY_DIR.mkdir(parents=True, exist_ok=True)
FIGURES_DIR = ROOT / "outputs" / "figures"

ESSAY_MD = r"""---
title: "What Poet Tips Users Recommended to Each Other"
subtitle: "A network analysis of 75,000 poetry recommendations, 2016–2019"
author: "Robert Peake"
date: "2026"
---

# What Poet Tips Was

Between 2016 and 2019, a website called Poet Tips invited users to answer a simple question: if you like this poet, who else should you read? Over three years, users submitted roughly 75,000 recommendations across approximately 6,500 poets, accumulating a record of reader-driven co-recommendation — who, in the view of these particular users at this particular moment, belonged together.

The site included contemporary poets and not-so-contemporary ones. It included poets writing in languages other than English, though English dominated. It included hip-hop artists — André 3000, Frank Ocean, Lil Wayne — because the site's working definition of "poet" was generous, and because some of its users thought in those terms. The dataset that survives is an archive of those choices.

This analysis treats that archive as a network: 6,095 poets as nodes, 20,526 pairs connected by co-recommendation, edges weighted by how often each pair was mentioned together. The goal is not to produce a ranking, establish a canon, or adjudicate which poets are important. The goal is to find out what structural claims this dataset can actually support — and to be honest about which it cannot.

# What This Data Is and Isn't

Every claim in what follows is a claim about *Poet Tips users between 2016 and 2019*. That sample has a profile: mostly Anglophone, internet-connected, contemporary-leaning. The median birth year of matched poets is around 1953; 75% were born after 1971. This is not a portrait of the poetic tradition. It is a portrait of who was being read and recommended in one corner of the poetry internet during the mid-2010s.

The edges mean: "users who recommended poet A also recommended poet B." An edge weight of 10 between two poets means 10 different co-recommendations. This is not "these poets are similar" or "these poets influenced each other." It is a co-occurrence pattern in recommendation behaviour — useful and interesting, but not the same thing.

A significant minority of poets could not be matched to Wikidata: 35% returned no results, and a further 3% were low-confidence matches. The 65% that were matched are skewed toward more prominent and more Anglophone figures. Findings that rely on Wikidata fields (birth year, nationality, Wikipedia article length) are conditioned on that coverage and should be read with that caveat in mind.

# How We Interrogated It

The analysis follows six questions, stated in advance. Each is tested against a null model — typically a degree-preserving random rewiring of the graph (configuration model), which preserves how many recommendations each poet received while scrambling which poets they were paired with. An effect is reported only where it exceeds what the null model would produce. Null results are reported as such.

Community detection was performed using the Louvain algorithm at resolution 1.0, with a 20-seed ensemble to measure stability. The overall modularity is 0.60 — a robust signal of real community structure. But stability across seeds is low: only 19% of poets are assigned to the same community in ≥70% of runs. The Louvain partition used for figures here is real, but its precise boundaries are sensitive to randomisation. Community-based findings should be read as "tendencies in the Louvain partition" rather than "hard community membership."

# What Survived Testing

## Attention and centrality are correlated, but the gap is where the story is

PageRank in this network — a measure of how centrally positioned a poet is in the co-recommendation graph — correlates with external attention (a combined index of Wikipedia article length and Poet Tips page views) at Spearman ρ = 0.42. This is positive and clearly above chance (permutation p < 0.001), but it is a noisy relationship. Knowing a poet's attention index explains less than 20% of the variance in their network centrality. The residual is interesting.

In the bottom-left of the attention-vs-centrality plot sit the expected names: poets with modest page views and modest network positions. In the top-right sit the poets where both measures agree — figures like Anne Carson and Sharon Olds, who are both central to Poet Tips recommendations and well-documented externally.

The more revealing quadrants are the diagonals. **High network centrality, lower external attention** — poets who were disproportionately central to Poet Tips users' recommendation behaviour relative to their prominence elsewhere — includes contemporary figures like Melissa Studdard, Meg Johnson, and Elaine Feeney. These poets appear to have had genuine reader constituencies on this platform that aren't fully captured by Wikipedia coverage or page-view counts.

The opposite quadrant — **high external attention, lower network centrality** — contains a different kind of surprise. Beyoncé, Paul McCartney, Lil Wayne, and Prince all appear here: figures with vast Wikipedia coverage whose position in the poetry recommendation network is peripheral. Their presence is a reminder that the site's generous definition of "poet" didn't translate into network centrality for those users who nominated them; they were recommended, but not often co-recommended with the poets forming the network's core.

This is not a finding about literary quality. It is a finding about recommendation behaviour: some poets are treated by this dataset's users as widely connectable, others as distinctive choices.

![**Figure 1.** Attention index (Wikipedia article bytes + Poet Tips page views, normalised) vs. PageRank in the co-recommendation network. Coloured quadrants: orange = high network centrality / lower external attention; purple = high external attention / lower centrality. Dashed lines at dataset medians. Spearman ρ = 0.416, permutation p < 0.001 (n=2000 shuffles). Exploratory framing: attention is not canon.](../figures/3_1_attention_vs_pagerank.png)

## Bridge poets: a small group holds the network together

The clearest structural finding concerns bridge poets: figures who link otherwise separate parts of the network. Using weighted betweenness centrality — betweenness computed with edge weight as a measure of recommendation strength, so well-trodden paths carry more traffic — the top 20 poets by this measure all sit far above the 99th percentile of the degree-preserving null model. The z-scores range from 18 to 57; the null produces no values anywhere near the observed.

The list is striking. At the top: **Melissa Studdard** (wb = 0.171, degree 73), **Anne Carson** (wb = 0.154, degree 101), **Elaine Feeney** (wb = 0.127, degree 27). Feeney's case is particularly notable: she ranks third on weighted betweenness with a degree of only 27, far below the network's mean. Her edges are few but heavy. The model says she sits on a disproportionate fraction of the graph's well-travelled paths — a connector between the Irish-British community and the broader Anglophone network, pulling traffic that wouldn't otherwise flow.

Further down the list: **Anne Sexton** and **Sylvia Plath** (co-members of the confessional cluster); **Pablo Neruda** and **Federico García Lorca** (anchors of the international-language community); **Ocean Vuong** and **Danez Smith** (key figures in a contemporary community centred on voices of colour). These are not arbitrary results. The bridge poets are poets who straddle communities — who were recommended by users navigating between zones of the network.

![**Figure 2.** Top 20 poets by weighted betweenness (1/weight distances). Orange: above null 99th percentile; yellow: above 95th. All 20 shown are above the 99th percentile of the degree-preserving null model (5 rewirings × k=200 betweenness). Null thresholds shown as dashed lines.](../figures/3_2_bridge_poets.png)

The unweighted betweenness tells a different story: **Amy Lemmon** ranks first, with degree 135 and 89% of her edges carrying a weight of 1 (a single co-recommendation, never repeated). The site's own internal importance score had already discounted her. The weighted analysis confirms it: she drops from first to 78th. Her unweighted betweenness is an artefact of breadth without depth — many unique pairings, few with any repeated endorsement. This is the network's portrait of active site participation, not literary bridging.

## Community geography: nationality more than era

Two follow-up questions ask whether the network's communities cluster by birth era and by nationality. Both test against a permutation null (shuffling labels 1,000 times).

**Nationality** is the stronger signal: normalised mutual information of 0.143 between Louvain community and nationality region, with permutation p < 0.001. The Irish-British community (C4, anchored by Elaine Feeney) is 80% UK/Ireland/Australia; the international-language community (C9, anchored by Lorca and Neruda) contains a large proportion of European and Latin American poets virtually absent from other communities. The US-dominant communities (C0–C3) are overwhelmingly North American. This is not surprising — readers tend to recommend what they know, and their knowledge is geographically inflected — but the effect size is large enough to be a real finding.

**Era** is a weaker but still statistically significant signal (NMI = 0.042, p < 0.001). The historical-language community (C8, anchored by T.S. Eliot and Gerard Manley Hopkins) has a notably older birth-year profile. The contemporary communities are, predictably, younger. But the NMI is small: birth era explains only 4% of the mutual information between community assignments.

![**Figure 3.** Community × birth era heatmap (proportion within community). NMI = 0.042 (permutation p < 0.001, n=1000). Coverage: 2,756 poets with birth year in top-12 communities. Older profiles visible in C8 (Eliot) and C9 (Lorca); younger profiles in contemporary communities.](../figures/3_3a_community_era.png)

![**Figure 4.** Community × nationality region heatmap (proportion within community). NMI = 0.143 (permutation p < 0.001, n=1000). Coverage: 2,543 poets with nationality in top-12 communities. The UK/Ireland/Aus and US concentrations reflect the Anglophone base of the platform; C9 (Lorca) shows the strongest non-Anglophone signal.](../figures/3_3b_community_nationality.png)

A direct test of whether communities contain poets from *more similar* eras than a random partition of the same sizes found no significant effect (permutation p = 0.34, effect size 0.42σ). Communities are nationally coherent; they are not temporally coherent beyond what chance would produce. This matters for interpretation: community structure in this network appears to be driven primarily by the geography of recommendation — who you know of and recommend — rather than by temporal literary grouping. The fact that someone recommends Sharon Olds alongside Sylvia Plath may reflect their shared confessional register, but the era signal within that community is no stronger than random.

## Gender: uneven communities, even centrality

Gender in this dataset comes from the Poet Tips site's own data, with 99.4% coverage. The overall split is approximately equal: 52.7% men, 47.3% women. But that near-parity masks real variation at the community level.

The gender distribution across communities is significantly non-random: χ² = 164, df = 11, p = 2 × 10⁻²⁹. The community anchored by Sharon Olds (C7, which also includes Sylvia Plath, Anne Sexton, and other confessional poets) is 64% female. The international-language community anchored by Lorca and Neruda (C9) is 25% female. The Amy Lemmon community (C5), which includes many contemporary formal and traditional poets, is 43% female. The contemporary communities clustered around Danez Smith and Richard Siken sit close to parity.

These disparities reflect something about the communities themselves rather than about the overall sample: users navigating toward the confessional-lyric tradition were encountering a canon built substantially by women; users navigating the international-modernist tradition were encountering one that was not.

![**Figure 5.** Left: fraction female per community (dashed = dataset average 47.3%). Right: fraction female by PageRank tercile. Community gender composition varies significantly (χ² = 164, p = 2×10⁻²⁹); centrality band does not (p = 0.96).](../figures/3_5_gender_asymmetry.png)

What is notably absent is any centrality effect. Across the three PageRank bands (low, medium, high), the fraction of women is essentially identical: 47.4%, 47.0%, 47.4%. Chi-square p = 0.96. In this recommendation network, women are not disadvantaged in reaching network centrality relative to men. The gender asymmetry lives in community composition, not in the structure of who holds influence.

## Edge prediction: the structure is learnable

A node2vec embedding trained on 90% of the graph's edges, scoring held-out pairs with cosine similarity, achieves an AUC of 0.76. A random classifier would score 0.50; a perfect one, 1.00. This means neighbourhood patterns alone — without any metadata about the poets — capture substantial structural regularity in the co-recommendation data.

The model's top predicted-but-absent edges pair poets who share highly similar embedding positions: Akeem Olaj and Clint Smith (both contemporary African American poets), Geoff Page and Clive James (both Australian), Gary Ligi and A.D. Winans (both West Coast small-press figures). These predictions are extrapolations of the model's learned structure, not recommendations or findings about affinities. They are listed here to illustrate what the embedding finds coherent — and as a reminder that the model can only see the edges it was trained on.

![**Figure 6.** ROC curve for edge prediction (node2vec dim=64, 10-walk training, 10% edge holdout). AUC = 0.760. A random classifier scores 0.5.](../figures/3_6_link_prediction_roc.png)

An AUC of 0.76 is moderately high but not close to 1.0. The gap is real: a significant fraction of edges cannot be predicted from neighbourhood alone. This is expected. Some co-recommendations reflect idiosyncratic user knowledge, personal associations, or thematic connections invisible to a pure graph-structural analysis. The graph is learnable to a degree, but it is not fully determined by structural regularity.

# What Didn't Work

**Literary movements** (Wikidata P135): only 5% of matched poets have this field populated. The numbers are too small for statistical analysis — 21 Beat Generation, 19 Harlem Renaissance, 14 Romanticism. These are supplementary labels, useful for illustrating specific communities but not for systematic testing.

**Languages written** (Wikidata P6886): this field is populated almost exclusively for non-English-language poets. English-language writers are effectively untagged, making it impossible to test language asymmetries symmetrically. The data is dropped from analysis.

**Era within communities** (Phase 3.4): the direct test of whether communities have tighter birth-year variance than random returned a null result (p = 0.34). Communities in this dataset are geographically coherent but temporally diffuse. The era effect in the community-vs-era alignment finding (3.3) is real but small; the direct variance test is more demanding and does not survive it.

**Gender vs. PageRank**: women and men are equally distributed across centrality bands. Whether this reflects the absence of centrality bias in reader behaviour, or some particular feature of this platform and period, is not answerable from this data alone.

# Where This Signal Sits

This analysis produces findings about a specific recommendation network in a specific time and place. It is not a study of literary tradition, scholarly consensus, or canonical standing. Several of the findings — bridge poets, gender community composition, nationality clustering — are interesting precisely because they differ from what an anthology table of contents or citation index would show. Elaine Feeney does not appear in the standard reference points for contemporary poetry; she anchors a community here because Irish and British Poet Tips users recommended her extensively in 2016–2019.

The dataset's contemporary skew is itself a finding. With a median poet birth year of 1953 and 75% born after 1971, this record is overwhelmingly a portrait of the living and recent. Historical figures appear — Dickinson, Keats, Lorca — but they appear as referents in a contemporary conversation, not as its primary material. This is a network of what readers were reading now, not a map of the tradition.

What the network can say is this: within its own frame, the signal is real. The communities are meaningful even if their edges are uncertain. The bridge poets are genuinely structural — they connect parts of the graph that would otherwise be less well linked, and their elevated betweenness is robust to null-model comparison. The gender composition of communities is not a noise artefact. The correlation between network centrality and external attention is positive and well above chance.

These are findings about Poet Tips users between 2016 and 2019. They are a mirror of that moment, held at that angle, in that light.

---

*Analysis code: `src/phase1.py` through `src/phase5.py`. Data: Poet Tips 2016–2019 archive,
Internet Archive item `poet_tips-20191025`. Wikidata enrichment: `src/phase2.py`.
All null models are degree-preserving configuration-model rewirings.
Per-field Wikidata coverage reported in `notes/PHASE_2.md`.*
"""

# Write markdown
md_path = ESSAY_DIR / "findings.md"
md_path.write_text(ESSAY_MD, encoding="utf-8")
print(f"Wrote {md_path}  ({md_path.stat().st_size // 1024} KB)")

# CSS for HTML render
CSS = """
body { max-width: 680px; margin: 60px auto; padding: 0 24px;
       font-family: Georgia, 'Times New Roman', serif; font-size: 17px;
       line-height: 1.7; color: #1a1a1a; background: #fafaf8; }
h1 { font-size: 1.9em; line-height: 1.2; margin-bottom: 0.2em; }
h2 { font-size: 1.25em; margin-top: 2.2em; margin-bottom: 0.5em;
     border-bottom: 1px solid #ddd; padding-bottom: 0.2em; color: #222; }
.subtitle { font-size: 1.1em; color: #555; margin-bottom: 0.2em; }
.author-date { color: #888; font-size: 0.9em; margin-bottom: 2em; }
p { margin: 0.85em 0; }
strong { color: #111; }
em { font-style: italic; }
hr { border: none; border-top: 1px solid #ddd; margin: 2.5em 0; }
a { color: #3a6fa0; }
@media (max-width: 720px) { body { font-size: 15px; } }
"""

css_path = ESSAY_DIR / "essay.css"
css_path.write_text(CSS, encoding="utf-8")

# Render to HTML with pandoc
html_path = ESSAY_DIR / "findings.html"
result = __import__("subprocess").run(
    ["pandoc", str(md_path),
     "--standalone",
     "--embed-resources",
     "--css", str(css_path),
     "--metadata", "title=What Poet Tips Users Recommended to Each Other",
     "--highlight-style", "tango",
     "-o", str(html_path)],
    capture_output=True, text=True,
    cwd=str(ESSAY_DIR),
)
if result.returncode == 0:
    print(f"Rendered {html_path}  ({html_path.stat().st_size // 1024} KB)")
else:
    print(f"Pandoc error: {result.stderr}")

print("\nPhase 5 complete.")
print(f"  Essay:  {md_path}")
print(f"  HTML:   {html_path}")
"""Phase 5 notes are written inline below."""

# Write PHASE_5.md note
word_count = len(ESSAY_MD.split())
notes_5 = f"""# Phase 5 — Essay

## Deliverable

`outputs/essay/findings.md` — narrative essay, approximately {word_count} words.
`outputs/essay/findings.html` — rendered HTML with single-column stylesheet.

## Coverage

| Phase 3 question | Essay treatment |
|---|---|
| 3.1 Attention vs. centrality | Full section; off-diagonal poets named |
| 3.2 Bridge structure | Full section; Amy Lemmon anomaly covered |
| 3.3 Community–nationality | Full section |
| 3.3 Community–era | Covered within 3.3 section |
| 3.4 Era within communities | "What didn't work" section |
| 3.5 Gender asymmetry (community) | Full section |
| 3.5 Gender vs. PR band | Noted as null in gender section |
| 3.6 Edge prediction | Full section with framing |

## Notes

- All claims qualified as "Poet Tips users 2016–2019"
- "Attention" framing used throughout; "canon" not used without explicit source
- Louvain stability caveat in methodology section
- Data coverage caveats in "what this data is and isn't" section
- Essay ends with reproducibility note (script references)

## Assessment

Phase 5 complete. All six Phase 3 questions addressed (positive, null, or dropped).
"""
(Path(__file__).parent.parent / "notes" / "PHASE_5.md").write_text(notes_5)
print("  Notes:  notes/PHASE_5.md")
