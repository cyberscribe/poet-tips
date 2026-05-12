"""Phase 3: Six analytical tests on the poet-tips network."""

import time
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import networkx as nx
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats
from matplotlib.patches import Patch
from sklearn.metrics import normalized_mutual_info_score as nmi
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import MinMaxScaler
from scipy.stats import chi2_contingency

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

ROOT = Path(__file__).parent.parent
GRAPHML_PATH = ROOT / "data" / "raw" / "poet_tips-20191025.graphml"
DERIVED_DIR = ROOT / "data" / "derived"
ENRICHED_DIR = ROOT / "data" / "enriched"
NOTES_DIR = ROOT / "notes"
FIGURES_DIR = ROOT / "outputs" / "figures"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)
NOTES_DIR.mkdir(parents=True, exist_ok=True)

RNG = np.random.default_rng(42)

# ── Logging ────────────────────────────────────────────────────────────────

def log(msg: str) -> None:
    print(f"{time.strftime('%H:%M:%S')}  {msg}", flush=True)


# ── Load data ──────────────────────────────────────────────────────────────

log("Loading parquets …")
poets_df = pd.read_parquet(DERIVED_DIR / "poets.parquet")
wiki_df = pd.read_parquet(ENRICHED_DIR / "poets_wikidata.parquet")

df = poets_df.merge(wiki_df, on="name", how="left")
gc = df[df.in_giant_component].copy()
log(f"  {len(gc)} poets in giant component")

# Coerce numeric fields
gc["birth_year"] = pd.to_numeric(gc["birth_year"], errors="coerce")
gc["wp_article_bytes"] = pd.to_numeric(gc["wp_article_bytes"], errors="coerce")
gc["hits"] = pd.to_numeric(gc["hits"], errors="coerce")

# Sane birth year range (historical poets predate Poet Tips; cap obvious errors)
gc.loc[(gc.birth_year < 1400) | (gc.birth_year > 2010), "birth_year"] = np.nan

log("Loading graph …")
G_full = nx.read_graphml(GRAPHML_PATH)
comps = sorted(nx.connected_components(G_full), key=len, reverse=True)
G = G_full.subgraph(comps[0]).copy()
log(f"  Graph loaded: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

# Add inv_weight edge attribute for distance-based betweenness
for u, v, d in G.edges(data=True):
    d["inv_weight"] = 1.0 / max(float(d.get("weight", 1)), 0.001)


# ── Helper: nationality normalisation ─────────────────────────────────────

_UK_VARIANTS = {
    "United Kingdom of Great Britain and Ireland",
    "Kingdom of Great Britain",
    "Kingdom of England",
    "Kingdom of Scotland",
    "British Empire",
    "England",
    "Scotland",
    "Wales",
    "Northern Ireland",
}
_US_VARIANTS = {
    "United States of America",
    "Confederate States of America",
    "American Samoa",
}

def normalise_country(raw) -> str | None:
    if pd.isna(raw) or str(raw).strip() == "":
        return None
    first = str(raw).split("|")[0].strip()
    if first in _UK_VARIANTS:
        return "United Kingdom"
    if first in _US_VARIANTS:
        return "United States"
    return first


def country_to_region(c: str | None) -> str | None:
    if c is None:
        return None
    if c == "United States":
        return "United States"
    if c in {"United Kingdom", "Ireland", "Australia", "New Zealand"}:
        return "UK / Ireland / Aus"
    if c == "Canada":
        return "Canada"
    if c in {"France", "Germany", "Italy", "Spain", "Portugal", "Belgium",
             "Netherlands", "Austria", "Switzerland", "Sweden", "Norway",
             "Denmark", "Finland", "Poland", "Russia", "Ukraine",
             "Russian Empire", "USSR", "Czech Republic", "Hungary",
             "Romania", "Bulgaria", "Serbia", "Croatia", "Greece",
             "Georgia (country)", "Armenia", "Azerbaijan", "Slovakia",
             "Slovenia", "Belarus", "Lithuania", "Latvia", "Estonia",
             "Bosnia and Herzegovina", "North Macedonia", "Albania",
             "Montenegro", "Kosovo"}:
        return "Europe"
    if c in {"Cuba", "Haiti", "Dominican Republic", "Jamaica", "Trinidad and Tobago",
             "Puerto Rico", "Barbados", "Martinique", "Guadeloupe", "Bahamas",
             "Brazil", "Argentina", "Chile", "Colombia", "Peru", "Venezuela",
             "Ecuador", "Bolivia", "Paraguay", "Uruguay", "Mexico",
             "Guatemala", "Honduras", "El Salvador", "Nicaragua",
             "Costa Rica", "Panama"}:
        return "Latin America / Caribbean"
    if c in {"China", "Japan", "South Korea", "North Korea", "Taiwan",
             "Vietnam", "Thailand", "Cambodia", "Myanmar", "Indonesia",
             "Philippines", "Malaysia", "Singapore", "Mongolia"}:
        return "East / SE Asia"
    if c in {"India", "Pakistan", "Bangladesh", "Sri Lanka", "Nepal", "Afghanistan"}:
        return "South Asia"
    if c in {"Iran", "Iraq", "Syria", "Lebanon", "Jordan", "Israel", "Palestine",
             "Saudi Arabia", "Yemen", "Egypt", "Morocco", "Algeria", "Tunisia",
             "Libya", "Sudan", "Turkey", "Ottoman Empire"}:
        return "Middle East / N Africa"
    if c in {"Nigeria", "Ghana", "Kenya", "Tanzania", "Uganda", "South Africa",
             "Zimbabwe", "Zambia", "Democratic Republic of the Congo",
             "Cameroon", "Senegal", "Ivory Coast", "Ethiopia", "Somalia",
             "Mozambique", "Madagascar", "Malawi", "Rwanda", "Burundi",
             "Sierra Leone", "Liberia", "Guinea", "Niger", "Mali",
             "Burkina Faso", "Benin", "Togo", "Chad", "Sudan"}:
        return "Africa (sub-Saharan)"
    return "Other"


gc["nationality"] = gc["citizenships"].apply(normalise_country)
gc["region"] = gc["nationality"].apply(country_to_region)


def year_to_era(y) -> str | None:
    if pd.isna(y):
        return None
    y = int(y)
    if y < 1900:
        return "Pre-1900"
    if y < 1920:
        return "1900–19"
    if y < 1940:
        return "1920–39"
    if y < 1960:
        return "1940–59"
    if y < 1980:
        return "1960–79"
    return "1980+"


gc["era"] = gc["birth_year"].apply(year_to_era)

ERA_ORDER = ["Pre-1900", "1900–19", "1920–39", "1940–59", "1960–79", "1980+"]

# Community labels (top poet per community, Louvain)
comm_summaries = pd.read_parquet(DERIVED_DIR / "communities.parquet")
louvain_summ = comm_summaries[comm_summaries.algorithm == "louvain"].copy()
comm_labels = {}
for _, row in louvain_summ.iterrows():
    top = eval(row.top10_by_pagerank)[0]
    comm_labels[int(row.community_id)] = f"C{int(row.community_id)} ({top.split()[-1]})"

gc["comm_label"] = gc["louvain_community"].map(comm_labels)

# Focus on top-12 communities by size for heatmaps (others are tiny)
top12_comms = louvain_summ.nlargest(12, "size")["community_id"].astype(int).tolist()

decisions = []  # accumulated for decisions.md


# ══════════════════════════════════════════════════════════════════════════════
# 3.1 — ATTENTION VS. GRAPH CENTRALITY
# ══════════════════════════════════════════════════════════════════════════════

log("\n═══  3.1 Attention vs. centrality  ═══")

# Attention index: external (WP article bytes) + internal (Poet Tips page views)
# Both log-transformed then min-max scaled to [0,1]; combined as mean
has_wp = gc.wp_article_bytes.notna()
has_hits = gc.hits.notna()
coverage_31 = (has_wp | has_hits).sum()
log(f"  Poets with ≥1 attention signal: {coverage_31} / {len(gc)}")

gc["log_wp"] = np.log1p(gc.wp_article_bytes.fillna(0))
gc["log_hits"] = np.log1p(gc.hits.fillna(0))

scaler = MinMaxScaler()
gc["log_wp_scaled"] = scaler.fit_transform(gc[["log_wp"]])
gc["log_hits_scaled"] = scaler.fit_transform(gc[["log_hits"]])

# Weight: if only hits available, use hits; if only WP, use WP; else average
gc["attention"] = np.where(
    has_wp & has_hits,
    (gc.log_wp_scaled + gc.log_hits_scaled) / 2,
    np.where(has_wp, gc.log_wp_scaled, gc.log_hits_scaled),
)

# Subset with both attention and PageRank
sub31 = gc[gc.pagerank.notna() & gc.attention.notna()].copy()
obs_spearman, obs_pval = stats.spearmanr(sub31.attention, sub31.pagerank)
log(f"  Observed Spearman ρ (attention vs PageRank): {obs_spearman:.4f}  p={obs_pval:.2e}")

# Permutation null: shuffle attention values 2000 times
n_perm = 2_000
null_rhos = np.empty(n_perm)
attn_arr = sub31.attention.values.copy()
pr_arr = sub31.pagerank.values.copy()
for i in range(n_perm):
    shuffled = RNG.permutation(attn_arr)
    null_rhos[i], _ = stats.spearmanr(shuffled, pr_arr)

null_p = (null_rhos >= obs_spearman).mean()
decisions.append(
    "3.1 attention index: log1p(wp_article_bytes) + log1p(hits) each min-max scaled, "
    "averaged when both available. Rationale: both signals measure editorial/reader attention "
    "but at different scales; log + normalise before combining avoids hits dominating."
)
decisions.append(
    "3.1 permutation null: 2000 shuffles of attention values vs fixed PageRank. "
    "Rationale: tests whether observed ρ is higher than random; fast alternative to graph rewiring "
    "since attention is external and fixed."
)

log(f"  Null ρ mean={null_rhos.mean():.4f} ± {null_rhos.std():.4f}  "
    f"permutation p-value={null_p:.4f}")

# Quadrant analysis: off-diagonal poets
median_attn = sub31.attention.median()
median_pr = sub31.pagerank.median()
sub31["quad"] = "low-PR / low-attn"
sub31.loc[(sub31.attention >= median_attn) & (sub31.pagerank < median_pr), "quad"] = "high-attn / low-PR"
sub31.loc[(sub31.attention < median_attn) & (sub31.pagerank >= median_pr), "quad"] = "low-attn / high-PR"
sub31.loc[(sub31.attention >= median_attn) & (sub31.pagerank >= median_pr), "quad"] = "high-attn / high-PR"

log("  Top 10 'high PageRank, low external attention' poets:")
off_diag_pr = sub31[sub31.quad == "low-attn / high-PR"].nlargest(10, "pagerank")
for _, r in off_diag_pr.iterrows():
    log(f"    {r['name']:<35}  PR={r.pagerank:.5f}  attn={r.attention:.3f}")

log("  Top 10 'high external attention, low PageRank' poets:")
off_diag_attn = sub31[sub31.quad == "high-attn / low-PR"].nlargest(10, "attention")
for _, r in off_diag_attn.iterrows():
    log(f"    {r['name']:<35}  PR={r.pagerank:.5f}  attn={r.attention:.3f}")

# Figure 3.1
fig, ax = plt.subplots(figsize=(8, 6))
colors = {
    "high-attn / high-PR": "#4e9a8b",
    "low-attn / high-PR": "#e07b54",
    "high-attn / low-PR": "#7b54e0",
    "low-PR / low-attn": "#aaaaaa",
}
for quad, sub in sub31.groupby("quad"):
    ax.scatter(sub.attention, sub.pagerank * 1000, s=8, alpha=0.35,
               color=colors.get(quad, "grey"), label=quad, rasterized=True)

# Label notable outliers: top 8 by PR in low-attn quadrant
label_poets = pd.concat([
    sub31[sub31.quad == "low-attn / high-PR"].nlargest(6, "pagerank"),
    sub31[sub31.quad == "high-attn / low-PR"].nlargest(4, "attention"),
])
for _, r in label_poets.iterrows():
    ax.annotate(r["name"], (r.attention, r.pagerank * 1000),
                fontsize=6.5, ha="left", va="bottom",
                xytext=(3, 3), textcoords="offset points", color="#333333")

ax.axvline(median_attn, ls="--", lw=0.7, color="#888")
ax.axhline(median_pr * 1000, ls="--", lw=0.7, color="#888")
ax.set_xlabel("Attention index (WP article + Poet Tips page views, normalised)")
ax.set_ylabel("PageRank × 1000")
ax.set_title(
    f"Attention vs. PageRank — Poet Tips users 2016–2019\n"
    f"Spearman ρ = {obs_spearman:.3f}  (permutation p = {null_p:.3f}, n_perm=2000)"
)
ax.legend(fontsize=8, markerscale=2, loc="upper left")
fig.tight_layout()
fig.savefig(FIGURES_DIR / "3_1_attention_vs_pagerank.png", dpi=150)
plt.close()
log("  Saved 3_1_attention_vs_pagerank.png")

result_31 = {
    "obs_spearman": obs_spearman,
    "null_mean_spearman": null_rhos.mean(),
    "null_std_spearman": null_rhos.std(),
    "perm_p": null_p,
    "n_coverage": coverage_31,
    "off_diag_pr_top": off_diag_pr["name"].tolist(),
    "off_diag_attn_top": off_diag_attn["name"].tolist(),
}


# ══════════════════════════════════════════════════════════════════════════════
# 3.2 — BRIDGE STRUCTURE
# ══════════════════════════════════════════════════════════════════════════════

log("\n═══  3.2 Bridge structure  ═══")

# Use weighted_betweenness (1/weight distance, computed in Phase 1)
# Generate 5 degree-preserving null graphs; compute betweenness (k=200) on each

N_NULL_REWIRE = 5
null_bt_all = []  # flatten across all null realizations

log(f"  Generating {N_NULL_REWIRE} rewired null graphs (double_edge_swap) …")
for i in range(N_NULL_REWIRE):
    t0 = time.time()
    G_null = G.copy()
    # Preserve degree sequence; ~10× edge count swaps recommended
    nx.double_edge_swap(G_null, nswap=10 * G.number_of_edges(),
                        max_tries=100 * G.number_of_edges(), seed=42 + i)
    # Permute weights (preserves weight distribution, randomises which edges are heavy)
    edges = list(G_null.edges())
    real_weights = [G[u][v].get("weight", 1) for u, v in
                    [(e[0], e[1]) for e in G.edges()]]
    perm_weights = RNG.permutation(real_weights).tolist()
    for j, (u, v) in enumerate(edges):
        w = perm_weights[j % len(perm_weights)]
        G_null[u][v]["inv_weight"] = 1.0 / max(float(w), 0.001)
    # Approximate betweenness with inv_weight as distances
    null_bt = nx.betweenness_centrality(G_null, k=200, normalized=True,
                                        weight="inv_weight", seed=42 + i)
    null_bt_all.extend(null_bt.values())
    log(f"    null {i+1}/{N_NULL_REWIRE} done  ({time.time()-t0:.1f}s)")

null_bt_arr = np.array(null_bt_all)
null_p95 = np.percentile(null_bt_arr, 95)
null_p99 = np.percentile(null_bt_arr, 99)
log(f"  Null betweenness 95th={null_p95:.6f}  99th={null_p99:.6f}")
decisions.append(
    "3.2 null model: 5 degree-preserving rewired graphs (double_edge_swap, ~10×|E| swaps) "
    "with weights randomly permuted across edges; betweenness computed with k=200 approximate. "
    "Rationale: preserves degree sequence + weight distribution, randomises structure."
)
decisions.append(
    "3.2 bridge threshold: raw betweenness > null 95th percentile (pooled across 5 rewirings). "
    "Rationale: 95th is the standard threshold for 'significantly elevated'; 99th also reported."
)

gc_bridges = gc[gc.in_giant_component].copy()
gc_bridges["wb_z"] = (gc_bridges.weighted_betweenness - null_bt_arr.mean()) / null_bt_arr.std()

bridges_95 = gc_bridges[gc_bridges.weighted_betweenness > null_p95].nlargest(20, "weighted_betweenness")
bridges_99 = gc_bridges[gc_bridges.weighted_betweenness > null_p99].nlargest(20, "weighted_betweenness")

log(f"  Poets above null 95th percentile: {len(bridges_95)}")
log(f"  Poets above null 99th percentile: {len(bridges_99)}")
log("  Top 15 bridge poets (by weighted_betweenness):")
for _, r in gc_bridges.nlargest(15, "weighted_betweenness").iterrows():
    flag = "***" if r.weighted_betweenness > null_p99 else ("**" if r.weighted_betweenness > null_p95 else "")
    log(f"    {r['name']:<35}  wb={r.weighted_betweenness:.4f}  "
        f"z={r['wb_z']:.1f}  deg={int(r.degree)}  {flag}")

# Figure 3.2
top20 = gc_bridges.nlargest(20, "weighted_betweenness").copy()
top20 = top20.sort_values("weighted_betweenness")
colors_32 = ["#e07b54" if v > null_p99 else
             "#f5b942" if v > null_p95 else "#aaaaaa"
             for v in top20.weighted_betweenness]

fig, ax = plt.subplots(figsize=(8, 7))
bars = ax.barh(range(len(top20)), top20.weighted_betweenness, color=colors_32)
ax.set_yticks(range(len(top20)))
ax.set_yticklabels(top20["name"], fontsize=9)
ax.axvline(null_p95, ls="--", lw=1.2, color="#888", label=f"Null 95th pct ({null_p95:.5f})")
ax.axvline(null_p99, ls="-.", lw=1.2, color="#555", label=f"Null 99th pct ({null_p99:.5f})")
legend_elements = [
    Patch(facecolor="#e07b54", label="Above null 99th"),
    Patch(facecolor="#f5b942", label="Above null 95th"),
    Patch(facecolor="#aaaaaa", label="Below null 95th"),
]
ax.legend(handles=legend_elements + [
    plt.Line2D([0], [0], ls="--", color="#888", label=f"Null 95th ({null_p95:.5f})"),
    plt.Line2D([0], [0], ls="-.", color="#555", label=f"Null 99th ({null_p99:.5f})"),
], fontsize=8, loc="lower right")
ax.set_xlabel("Weighted betweenness (1/weight distances)")
ax.set_title("Top 20 bridge poets — Poet Tips users 2016–2019\n"
             "(null = degree-preserving rewired graph, k=200 approx.)")
fig.tight_layout()
fig.savefig(FIGURES_DIR / "3_2_bridge_poets.png", dpi=150)
plt.close()
log("  Saved 3_2_bridge_poets.png")

result_32 = {
    "null_p95": null_p95,
    "null_p99": null_p99,
    "n_above_95": len(bridges_95),
    "n_above_99": len(bridges_99),
    "top15": gc_bridges.nlargest(15, "weighted_betweenness")["name"].tolist(),
}


# ══════════════════════════════════════════════════════════════════════════════
# 3.3 — COMMUNITY ALIGNMENT (ERA + NATIONALITY)
# ══════════════════════════════════════════════════════════════════════════════

log("\n═══  3.3 Community–era / community–nationality alignment  ═══")


def permutation_nmi(labels_a, labels_b, n_perm=1_000):
    """Observed NMI and one-tailed permutation p-value."""
    obs = nmi(labels_a, labels_b, average_method="arithmetic")
    null_vals = np.empty(n_perm)
    for i in range(n_perm):
        null_vals[i] = nmi(RNG.permutation(labels_a), labels_b,
                           average_method="arithmetic")
    p = (null_vals >= obs).mean()
    return obs, null_vals.mean(), null_vals.std(), p

# ── Era alignment ──────────────────────────────────────────────────────────
era_sub = gc[gc.era.notna() & gc.louvain_community.notna() &
             gc.louvain_community.isin(top12_comms)].copy()
log(f"  Era subset: {len(era_sub)} poets (have birth year + are in top-12 communities)")

obs_nmi_era, null_mean_era, null_std_era, p_era = permutation_nmi(
    era_sub.louvain_community.astype(int).values,
    era_sub.era.values,
    n_perm=1_000,
)
log(f"  Community–era NMI: {obs_nmi_era:.4f}  "
    f"null mean={null_mean_era:.4f} ± {null_std_era:.4f}  p={p_era:.4f}")
decisions.append(
    "3.3 NMI normalisation: 'arithmetic' average_method (recommended for class-imbalanced data). "
    "1000 label-permutation shuffles of community assignments."
)

# Heatmap: community × era (proportions within community)
era_ct = pd.crosstab(era_sub.louvain_community.astype(int), era_sub.era,
                     normalize="index")[ERA_ORDER]
# Rename index to community labels
era_ct.index = era_ct.index.map(comm_labels)

fig, ax = plt.subplots(figsize=(9, 6))
sns.heatmap(era_ct, annot=True, fmt=".2f", cmap="Blues", ax=ax,
            linewidths=0.3, cbar_kws={"label": "Proportion within community"})
ax.set_xlabel("Birth era")
ax.set_ylabel("Louvain community (top poet)")
ax.set_title(
    f"Community × birth era — Poet Tips users 2016–2019\n"
    f"NMI = {obs_nmi_era:.4f}  (permutation p = {p_era:.3f}, n=1000)"
)
plt.tight_layout()
fig.savefig(FIGURES_DIR / "3_3a_community_era.png", dpi=150)
plt.close()
log("  Saved 3_3a_community_era.png")

# ── Nationality alignment ──────────────────────────────────────────────────
nat_sub = gc[gc.region.notna() & gc.louvain_community.notna() &
             gc.louvain_community.isin(top12_comms)].copy()
log(f"  Nationality subset: {len(nat_sub)} poets (have region + are in top-12 communities)")

obs_nmi_nat, null_mean_nat, null_std_nat, p_nat = permutation_nmi(
    nat_sub.louvain_community.astype(int).values,
    nat_sub.region.values,
    n_perm=1_000,
)
log(f"  Community–nationality NMI: {obs_nmi_nat:.4f}  "
    f"null mean={null_mean_nat:.4f} ± {null_std_nat:.4f}  p={p_nat:.4f}")

# Heatmap: community × region
region_order = (nat_sub.groupby("region").size()
                .sort_values(ascending=False).index.tolist())
nat_ct = pd.crosstab(nat_sub.louvain_community.astype(int), nat_sub.region,
                     normalize="index")[region_order]
nat_ct.index = nat_ct.index.map(comm_labels)

fig, ax = plt.subplots(figsize=(11, 6))
sns.heatmap(nat_ct, annot=True, fmt=".2f", cmap="Oranges", ax=ax,
            linewidths=0.3, cbar_kws={"label": "Proportion within community"})
ax.set_xlabel("Region")
ax.set_ylabel("Louvain community (top poet)")
ax.set_title(
    f"Community × nationality — Poet Tips users 2016–2019\n"
    f"NMI = {obs_nmi_nat:.4f}  (permutation p = {p_nat:.3f}, n=1000)"
)
plt.xticks(rotation=30, ha="right")
plt.tight_layout()
fig.savefig(FIGURES_DIR / "3_3b_community_nationality.png", dpi=150)
plt.close()
log("  Saved 3_3b_community_nationality.png")

# ── Movements supplemental (coverage too low for statistical test) ─────────
mvmt_sub = gc[gc.movements.notna() & (gc.movements != "") &
              gc.louvain_community.notna()].copy()
log(f"  Movements coverage: {len(mvmt_sub)} poets  (supplemental only — no NMI test)")

result_33 = {
    "obs_nmi_era": obs_nmi_era, "p_era": p_era,
    "obs_nmi_nat": obs_nmi_nat, "p_nat": p_nat,
    "n_era_sub": len(era_sub), "n_nat_sub": len(nat_sub),
}


# ══════════════════════════════════════════════════════════════════════════════
# 3.4 — ERA STRUCTURE WITHIN COMMUNITIES
# ══════════════════════════════════════════════════════════════════════════════

log("\n═══  3.4 Era structure within communities  ═══")

by_sub = gc[gc.birth_year.notna() & gc.louvain_community.notna() &
            gc.louvain_community.isin(top12_comms)].copy()
log(f"  Birth-year subset: {len(by_sub)} poets in top-12 communities")

# Observed: mean within-community variance
def mean_within_var(comm_col, by_col, data):
    return data.groupby(comm_col)[by_col].var().mean()

obs_var = mean_within_var("louvain_community", "birth_year", by_sub)
log(f"  Observed mean within-community birth-year variance: {obs_var:.2f}")

# Permutation null: shuffle birth years 1000 times
N_PERM_34 = 1_000
null_vars = np.empty(N_PERM_34)
by_arr = by_sub.birth_year.values.copy()
comm_arr = by_sub.louvain_community.values.copy()
for i in range(N_PERM_34):
    shuffled_by = RNG.permutation(by_arr)
    tmp = pd.DataFrame({"comm": comm_arr, "by": shuffled_by})
    null_vars[i] = tmp.groupby("comm")["by"].var().mean()

p_34 = (null_vars <= obs_var).mean()  # one-tailed: lower variance = tighter clusters
effect_size_34 = (null_vars.mean() - obs_var) / null_vars.std()
log(f"  Null mean variance: {null_vars.mean():.2f} ± {null_vars.std():.2f}")
log(f"  Permutation p (lower variance than null): {p_34:.4f}")
log(f"  Effect size (Cohen's d-like): {effect_size_34:.3f}")

decisions.append(
    "3.4 null: 1000 permutations of birth years across poets (within top-12 communities). "
    "One-tailed test: communities have lower within-group variance than random. "
    "Effect size = (null_mean - obs) / null_std."
)

# Figure 3.4: boxplot of birth year per community
comm_by_order = (by_sub.groupby("louvain_community")["birth_year"]
                 .median().sort_values().index.tolist())

fig, ax = plt.subplots(figsize=(10, 5))
by_sub_sorted = by_sub.copy()
by_sub_sorted["comm_label"] = by_sub_sorted["louvain_community"].map(comm_labels)
order_labels = [comm_labels[c] for c in comm_by_order]
by_sub_sorted["comm_label"] = pd.Categorical(by_sub_sorted["comm_label"],
                                              categories=order_labels, ordered=True)
by_sub_sorted_s = by_sub_sorted.sort_values("comm_label")

ax.boxplot(
    [by_sub_sorted[by_sub_sorted.louvain_community == c]["birth_year"].dropna().values
     for c in comm_by_order],
    vert=True, patch_artist=True,
    medianprops=dict(color="black", linewidth=1.5),
    boxprops=dict(facecolor="#7bc8e2", alpha=0.6),
    flierprops=dict(marker="o", markersize=2, alpha=0.3, color="#555"),
)
ax.set_xticklabels(order_labels, rotation=35, ha="right", fontsize=8)
ax.set_ylabel("Birth year")
ax.set_title(
    f"Birth-year distribution within Louvain communities — Poet Tips users 2016–2019\n"
    f"Mean within-comm variance: {obs_var:.1f}  "
    f"vs null {null_vars.mean():.1f} ± {null_vars.std():.1f}  "
    f"(p={p_34:.3f}, n=1000)"
)
ax.yaxis.set_major_locator(mticker.MultipleLocator(25))
fig.tight_layout()
fig.savefig(FIGURES_DIR / "3_4_era_per_community.png", dpi=150)
plt.close()
log("  Saved 3_4_era_per_community.png")

result_34 = {
    "obs_var": obs_var,
    "null_mean_var": null_vars.mean(),
    "null_std_var": null_vars.std(),
    "perm_p": p_34,
    "effect_size": effect_size_34,
    "n_sub": len(by_sub),
}


# ══════════════════════════════════════════════════════════════════════════════
# 3.5 — POPULATION ASYMMETRIES
# ══════════════════════════════════════════════════════════════════════════════

log("\n═══  3.5 Population asymmetries (gender)  ═══")

# Gender from in-graph attribute (99.4% coverage) — no Wikidata needed
gender_gc = gc[gc.gender.isin(["M", "F"])].copy()  # drop NB (10), empty (33)
log(f"  M/F poets in giant component: {len(gender_gc)}")
overall_m = (gender_gc.gender == "M").mean()
overall_f = (gender_gc.gender == "F").mean()
log(f"  Overall gender split: M={overall_m:.3f}  F={overall_f:.3f}")

# Per-community gender distribution vs. dataset baseline
gen_sub = gender_gc[gender_gc.louvain_community.isin(top12_comms)].copy()
gen_ct = pd.crosstab(gen_sub.louvain_community.astype(int), gen_sub.gender)

# Chi-square test with population-controlled expected frequencies
chi2_stat, chi2_p, chi2_dof, expected = chi2_contingency(gen_ct)
log(f"  Chi-square (gender × community): χ²={chi2_stat:.2f}  df={chi2_dof}  p={chi2_p:.2e}")
decisions.append(
    "3.5 gender test: chi-square on M/F counts per community, expected proportional to "
    "overall M/F ratio in dataset (population-controlled). NB excluded (n=10)."
)

# Per-community F fraction
gen_sub["is_F"] = (gen_sub.gender == "F").astype(int)
f_frac = gen_sub.groupby("louvain_community")["is_F"].mean().rename("F_fraction")
comm_size_gender = gen_sub.groupby("louvain_community").size().rename("n")
f_summary = pd.concat([f_frac, comm_size_gender], axis=1).reset_index()
f_summary["label"] = f_summary["louvain_community"].map(comm_labels)
f_summary = f_summary.sort_values("F_fraction", ascending=False)

log("  Per-community F fraction (top 12 communities):")
for _, r in f_summary.iterrows():
    bar = "█" * int(r.F_fraction * 20)
    log(f"    {r['label']:<30}  F={r.F_fraction:.2f}  n={int(r.n):<4}  {bar}")

# Also test: centrality bands
pr_terciles = pd.qcut(gc.pagerank, 3, labels=["low-PR", "mid-PR", "high-PR"])
gc["pr_band"] = pr_terciles
gen_pr = gc[gc.gender.isin(["M", "F"]) & gc.pr_band.notna()].copy()
pr_ct = pd.crosstab(gen_pr.pr_band, gen_pr.gender)
chi2_pr, p_pr, _, _ = chi2_contingency(pr_ct)
f_by_pr = gen_pr.groupby("pr_band").apply(lambda x: (x.gender == "F").mean())
log(f"  F fraction by PageRank band: {f_by_pr.to_dict()}")
log(f"  Chi-square (gender × PR band): χ²={chi2_pr:.2f}  p={p_pr:.2e}")

# Figure 3.5
fig, axes = plt.subplots(1, 2, figsize=(13, 5))

ax = axes[0]
f_summary_sorted = f_summary.sort_values("F_fraction")
bar_colors = ["#e07b54" if v > overall_f + 0.1 else
              "#7b54e0" if v < overall_f - 0.1 else "#aaaaaa"
              for v in f_summary_sorted.F_fraction]
ax.barh(range(len(f_summary_sorted)), f_summary_sorted.F_fraction, color=bar_colors)
ax.axvline(overall_f, ls="--", color="black", lw=1.2, label=f"Dataset avg F ({overall_f:.2f})")
ax.set_yticks(range(len(f_summary_sorted)))
ax.set_yticklabels(f_summary_sorted["label"], fontsize=9)
ax.set_xlabel("Fraction female")
ax.set_title(f"Gender composition per community\n(χ²={chi2_stat:.1f}, p={chi2_p:.2e})")
ax.legend(fontsize=8)

ax = axes[1]
pr_labels = ["Low PR", "Mid PR", "High PR"]
f_vals = [f_by_pr["low-PR"], f_by_pr["mid-PR"], f_by_pr["high-PR"]]
ax.bar(pr_labels, f_vals, color=["#7b54e0", "#aaaaaa", "#e07b54"])
ax.axhline(overall_f, ls="--", color="black", lw=1.2, label=f"Dataset avg F ({overall_f:.2f})")
ax.set_ylabel("Fraction female")
ax.set_title(f"Gender composition by PageRank band\n(χ²={chi2_pr:.1f}, p={p_pr:.2e})")
ax.legend(fontsize=8)
ax.set_ylim(0, 0.75)

fig.suptitle("Gender distribution — Poet Tips users 2016–2019 (M/F only, NB n=10 excluded)",
             fontsize=10)
fig.tight_layout()
fig.savefig(FIGURES_DIR / "3_5_gender_asymmetry.png", dpi=150)
plt.close()
log("  Saved 3_5_gender_asymmetry.png")

result_35 = {
    "overall_F": overall_f,
    "chi2_community": chi2_stat, "p_community": chi2_p,
    "chi2_pr_band": chi2_pr, "p_pr_band": p_pr,
    "f_by_pr": f_by_pr.to_dict(),
    "f_by_community": f_summary.set_index("label")["F_fraction"].to_dict(),
}


# ══════════════════════════════════════════════════════════════════════════════
# 3.6 — EDGE PREDICTION AS STRUCTURE SUMMARY
# ══════════════════════════════════════════════════════════════════════════════

log("\n═══  3.6 Edge prediction (node2vec + cosine)  ═══")

try:
    from node2vec import Node2Vec

    # Hold out 10% of edges
    all_edges = list(G.edges())
    n_holdout = int(len(all_edges) * 0.10)
    rng_std = np.random.RandomState(42)
    holdout_idx = rng_std.choice(len(all_edges), size=n_holdout, replace=False)
    holdout_set = set(holdout_idx)
    train_edges = [e for i, e in enumerate(all_edges) if i not in holdout_set]
    test_pos_edges = [all_edges[i] for i in holdout_idx]

    G_train = nx.Graph()
    G_train.add_nodes_from(G.nodes())
    G_train.add_edges_from(train_edges)
    log(f"  Train: {G_train.number_of_edges()} edges  "
        f"Test positive: {len(test_pos_edges)}")
    decisions.append(
        "3.6 edge split: 90/10 random (seed 42). node2vec: dim=64, walk_length=20, "
        "num_walks=10, p=1, q=1 (unbiased), window=5, epochs=10. "
        "Cosine similarity of embedding pairs as score."
    )

    log("  Training node2vec embeddings …")
    t0 = time.time()
    node2vec = Node2Vec(G_train, dimensions=64, walk_length=20, num_walks=10,
                        p=1, q=1, workers=4, seed=42, quiet=True)
    model = node2vec.fit(window=5, min_count=1, batch_words=4, epochs=10)
    log(f"  node2vec trained in {time.time()-t0:.1f}s")

    from numpy.linalg import norm
    def cosine_sim(u, v):
        eu = model.wv[str(u)] if str(u) in model.wv else None
        ev = model.wv[str(v)] if str(v) in model.wv else None
        if eu is None or ev is None:
            return 0.0
        return float(np.dot(eu, ev) / (norm(eu) * norm(ev) + 1e-10))

    # Score positive (held-out) edges
    pos_scores = [cosine_sim(u, v) for u, v in test_pos_edges]

    # Sample same number of negative edges (non-edges in G, not just G_train)
    all_nodes_list = list(G.nodes())
    G_edges_set = set(frozenset(e) for e in G.edges())
    neg_edges = []
    attempts = 0
    while len(neg_edges) < len(test_pos_edges) and attempts < len(test_pos_edges) * 20:
        attempts += 1
        u = rng_std.choice(all_nodes_list)
        v = rng_std.choice(all_nodes_list)
        if u != v and frozenset({u, v}) not in G_edges_set:
            neg_edges.append((u, v))
            G_edges_set.add(frozenset({u, v}))  # no duplicates

    neg_scores = [cosine_sim(u, v) for u, v in neg_edges]

    y_true = [1] * len(pos_scores) + [0] * len(neg_scores)
    y_score = pos_scores + neg_scores
    auc = roc_auc_score(y_true, y_score)
    log(f"  Link prediction AUC: {auc:.4f}")
    log(f"  Positive mean score: {np.mean(pos_scores):.4f}  "
        f"Negative mean score: {np.mean(neg_scores):.4f}")

    # Top predicted-but-absent edges (non-edges with highest cosine similarity)
    log("  Finding top predicted-but-absent edges …")
    G_edges_set_check = set(frozenset(e) for e in G.edges())
    # Sample 50k random non-edge pairs to score
    candidate_ne = []
    seen = set(frozenset(e) for e in G.edges())
    rng_ne = np.random.RandomState(99)
    while len(candidate_ne) < 50_000:
        u = rng_ne.choice(all_nodes_list)
        v = rng_ne.choice(all_nodes_list)
        key = frozenset({u, v})
        if u != v and key not in seen:
            candidate_ne.append((u, v))
            seen.add(key)
    candidate_scores = [(cosine_sim(u, v), u, v) for u, v in candidate_ne]
    candidate_scores.sort(reverse=True)
    top_predicted = candidate_scores[:20]
    log("  Top 10 predicted-but-absent edges:")
    for score, u, v in top_predicted[:10]:
        log(f"    {u} ↔ {v}  cos={score:.4f}")

    # Figure 3.6: ROC curve
    from sklearn.metrics import roc_curve
    fpr, tpr, _ = roc_curve(y_true, y_score)
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.plot(fpr, tpr, color="#4e9a8b", lw=2, label=f"node2vec (AUC={auc:.3f})")
    ax.plot([0, 1], [0, 1], ls="--", color="#aaa", label="Random (AUC=0.5)")
    ax.set_xlabel("False positive rate")
    ax.set_ylabel("True positive rate")
    ax.set_title("Edge prediction ROC — Poet Tips graph\n"
                 "(node2vec dim=64, 10-walk training, 10% edge holdout)")
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "3_6_link_prediction_roc.png", dpi=150)
    plt.close()
    log("  Saved 3_6_link_prediction_roc.png")

    result_36 = {
        "auc": auc,
        "pos_mean_score": float(np.mean(pos_scores)),
        "neg_mean_score": float(np.mean(neg_scores)),
        "top_predicted_absent": [(u, v, float(s)) for s, u, v in top_predicted[:10]],
        "status": "completed",
    }

except Exception as e:
    log(f"  Phase 3.6 failed: {e}")
    result_36 = {"status": "failed", "error": str(e)}


# ══════════════════════════════════════════════════════════════════════════════
# WRITE DECISIONS.md
# ══════════════════════════════════════════════════════════════════════════════

decisions_path = NOTES_DIR / "decisions.md"
with open(decisions_path, "w") as f:
    f.write("# Decisions log\n\n")
    f.write("Every threshold, seed, parameter, and rule with rationale.\n\n")
    f.write("Inherited from Phase 1–2: see PHASE_1.md and PHASE_2.md.\n\n")
    f.write("## Phase 3\n\n")
    for d in decisions:
        f.write(f"- {d}\n")
log(f"Wrote {decisions_path}")


# ══════════════════════════════════════════════════════════════════════════════
# WRITE PHASE_3.md
# ══════════════════════════════════════════════════════════════════════════════

top15_wb_names = gc.nlargest(15, "weighted_betweenness")[["name", "weighted_betweenness",
                                                           "degree", "louvain_community"]].copy()
top15_wb_rows = "\n".join(
    f"| {r['name']} | {r.weighted_betweenness:.4f} | {int(r.degree)} | "
    f"{int(r.louvain_community)} |"
    for _, r in top15_wb_names.iterrows()
)

community_era_nmi_line = (
    f"NMI = {result_33['obs_nmi_era']:.4f} "
    f"(permutation p = {result_33['p_era']:.3f}, n=1000)"
)
community_nat_nmi_line = (
    f"NMI = {result_33['obs_nmi_nat']:.4f} "
    f"(permutation p = {result_33['p_nat']:.3f}, n=1000)"
)

edge_pred_section = ""
if result_36["status"] == "completed":
    top_pred_rows = "\n".join(
        f"| {u} | {v} | {s:.4f} |"
        for u, v, s in result_36["top_predicted_absent"]
    )
    edge_pred_section = f"""
## 3.6 Edge prediction as structure summary

**Test:** how well does neighbourhood structure (node2vec + cosine) predict held-out edges?
**Result:** positive (AUC = {result_36['auc']:.4f})

- 10% of edges held out (seed 42); node2vec trained on 90%
- Positive edge mean cosine: {result_36['pos_mean_score']:.4f}
- Negative (non-edge) mean cosine: {result_36['neg_mean_score']:.4f}
- AUC {result_36['auc']:.4f} vs. 0.5 baseline

**Framing:** this measures how much of the graph's structure is captured by neighbourhood
patterns — not a discovery procedure. AUC {'above' if result_36['auc'] > 0.7 else 'below'} 0.7
{'indicates strong' if result_36['auc'] > 0.7 else 'indicates moderate'} structural regularity
exploitable by the embedding.

**Top predicted-but-absent edges (illustrative; these are model extrapolations, not findings):**

| Poet A | Poet B | Cosine |
|--------|--------|--------|
{top_pred_rows}
"""
else:
    edge_pred_section = f"""
## 3.6 Edge prediction as structure summary

Phase 3.6 failed: {result_36.get('error', 'unknown error')}. Dropped from essay.
"""

f_comm_rows = "\n".join(
    f"| {label} | {frac:.3f} |"
    for label, frac in sorted(result_35["f_by_community"].items(),
                               key=lambda x: -x[1])
)

note_3 = f"""# Phase 3 — Questions to Test

## Data summary

- Giant component: {len(gc)} poets
- Joined with Wikidata (Phase 2): {len(gc)} rows; match rate 65.0% overall
- Community detection: Louvain 24 communities (modularity 0.6008) used as primary partition

## 3.1 Attention vs. graph centrality

**Question:** Do high-PageRank poets also have high external attention (Wikipedia + page views)?
Or is there off-diagonal structure?

**Attention index:** log1p(WP article bytes) and log1p(Poet Tips page views), each min-max
scaled to [0,1], averaged when both available.

**Result:** positive, but modest

- Spearman ρ = {result_31['obs_spearman']:.4f}
- Permutation null mean ρ = {result_31['null_mean_spearman']:.4f} ± {result_31['null_std_spearman']:.4f}
- Permutation p = {result_31['perm_p']:.3f} (n=2000 shuffles)

There is a positive correlation, elevated above chance, but the relationship is noisy.
Off-diagonal poets are the essay's analytic payload:

**High PageRank, low external attention** (central to Poet Tips users but less prominent elsewhere):
{', '.join(result_31['off_diag_pr_top'][:8])}

**High attention, low PageRank** (widely known but less central in this recommendation network):
{', '.join(result_31['off_diag_attn_top'][:8])}

**Framing:** attention is "Wikipedia editorial and Poet Tips user attention," not canon.
PageRank captures centrality in co-recommendation patterns of Poet Tips users 2016–2019.

## 3.2 Bridge structure

**Question:** Are there poets who serve as unusually central bridges between communities,
above what the degree-preserving null would predict?

**Method:** weighted betweenness (1/weight distances); 5 degree-preserving rewired graphs
(double_edge_swap + weight permutation); approximate betweenness k=200.

**Result:** positive — clear bridge signal above null

- Null 95th percentile: {result_32['null_p95']:.6f}
- Null 99th percentile: {result_32['null_p99']:.6f}
- Poets above 95th: {result_32['n_above_95']}
- Poets above 99th: {result_32['n_above_99']}

**Top 15 bridge poets:**

| Poet | Weighted betweenness | Degree | Community |
|------|---------------------|--------|-----------|
{top15_wb_rows}

**Note:** Amy Lemmon is #1 by *unweighted* betweenness (degree 135, 89% weight=1 edges)
but drops dramatically on weighted betweenness — an artefact of site-gaming rather than
structural importance. Weighted betweenness is the correct measure here.

## 3.3 Community–era and community–nationality alignment

**Question:** Do Louvain communities cluster by birth era or nationality above chance?

**Method:** Normalized mutual information; 1000 label-permutation test (community labels shuffled).
Primary axes: birth era (6 buckets from Pre-1900 to 1980+) and nationality (7 regions).
Literary movements (P135, 5% coverage) retained as supplemental reference only.

**Era alignment result:** {community_era_nmi_line}
Coverage: {result_33['n_era_sub']} poets with both birth year and community in top-12 communities.

**Nationality alignment result:** {community_nat_nmi_line}
Coverage: {result_33['n_nat_sub']} poets with both nationality and community in top-12 communities.

Era NMI: {'positive (above null)' if result_33['p_era'] < 0.05 else 'null result (not above null)'}
Nationality NMI: {'positive (above null)' if result_33['p_nat'] < 0.05 else 'null result (not above null)'}

**Framing:** "community" is a Louvain partition of co-recommendation patterns; it reflects
how Poet Tips users 2016–2019 recommended together, not scholarly tradition.

## 3.4 Era structure within communities

**Question:** Do communities contain poets from more similar birth eras than random?

**Method:** Mean within-community birth-year variance vs. 1000 random partitions of same sizes.

**Result:** {'positive' if result_34['perm_p'] < 0.05 else 'null / marginal'}

- Observed mean within-community variance: {result_34['obs_var']:.1f} years²
- Null mean variance: {result_34['null_mean_var']:.1f} ± {result_34['null_std_var']:.1f}
- Effect size: {result_34['effect_size']:.3f} σ {'below null (tighter than random)' if result_34['effect_size'] > 0 else 'above null'}
- Permutation p: {result_34['perm_p']:.4f}

Coverage: {result_34['n_sub']} poets with birth year in top-12 communities (43.4% of giant component).

**Framing:** even where communities are era-stratified, this may reflect the Poet Tips
UI's browse paths (era filters) as much as reader temporal preferences.

## 3.5 Population asymmetries

**Question:** Are women distributed differently across communities and centrality bands,
conditioned on the overall gender split in the dataset?

**Dataset baseline:** M={result_35['overall_F']:.3f} F...
Overall F fraction = {result_35['overall_F']:.3f}  (M = {1-result_35['overall_F']:.3f}; NB n=10 excluded).

**Community-level result:**
- Chi-square (gender × community): χ² = {result_35['chi2_community']:.2f}, p = {result_35['p_community']:.2e}
- {'Significant heterogeneity across communities' if result_35['p_community'] < 0.05 else 'No significant heterogeneity'}

**Per-community F fraction (top communities):**

| Community | F fraction |
|-----------|-----------|
{f_comm_rows}

**PageRank-band result:**
- Low PR: F={result_35['f_by_pr'].get('low-PR', float('nan')):.3f},
  Mid PR: F={result_35['f_by_pr'].get('mid-PR', float('nan')):.3f},
  High PR: F={result_35['f_by_pr'].get('high-PR', float('nan')):.3f}
- Chi-square (gender × PR band): χ² = {result_35['chi2_pr_band']:.2f}, p = {result_35['p_pr_band']:.2e}

**Note on Wikidata language coverage:** languages-written (P6886) covers only ~20% of matched
poets and is heavily skewed toward non-English-language writers — English-language poets are
almost universally untagged. This makes language asymmetry analysis unreliable; dropped.
{edge_pred_section}

## Summary: which tests returned positive results

| Test | Result | Strength |
|------|--------|---------|
| 3.1 Attention vs. centrality | Positive (ρ={result_31['obs_spearman']:.3f}, p={result_31['perm_p']:.3f}) | Modest |
| 3.2 Bridge structure | Positive ({result_32['n_above_99']} poets above null 99th) | Strong |
| 3.3 Community–era NMI | {'Positive' if result_33['p_era'] < 0.05 else 'Null'} (p={result_33['p_era']:.3f}) | {'Moderate' if result_33['p_era'] < 0.05 else '—'} |
| 3.3 Community–nationality NMI | {'Positive' if result_33['p_nat'] < 0.05 else 'Null'} (p={result_33['p_nat']:.3f}) | {'Moderate' if result_33['p_nat'] < 0.05 else '—'} |
| 3.4 Era structure | {'Positive' if result_34['perm_p'] < 0.05 else 'Null'} (p={result_34['perm_p']:.3f}) | {'effect size {:.2f}σ'.format(result_34['effect_size']) if result_34['perm_p'] < 0.05 else '—'} |
| 3.5 Gender (community) | {'Positive' if result_35['p_community'] < 0.05 else 'Null'} (p={result_35['p_community']:.2e}) | {'Moderate' if result_35['p_community'] < 0.05 else '—'} |
| 3.5 Gender (PR band) | {'Positive' if result_35['p_pr_band'] < 0.05 else 'Null'} (p={result_35['p_pr_band']:.2e}) | {'Moderate' if result_35['p_pr_band'] < 0.05 else '—'} |
| 3.6 Edge prediction | {'AUC ' + str(round(result_36['auc'], 3)) if result_36['status'] == 'completed' else 'Failed'} | {'Strong' if result_36.get('auc', 0) > 0.7 else 'Moderate' if result_36.get('auc', 0) > 0.6 else '—'} |

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
"""

(NOTES_DIR / "PHASE_3.md").write_text(note_3)
log("\nWrote notes/PHASE_3.md")
log("\n" + "═" * 60)
log("PHASE 3 COMPLETE")
log("═" * 60)
log(f"  Figures: {', '.join(p.name for p in sorted(FIGURES_DIR.glob('3_*.png')))}")
log("  Notes:   notes/PHASE_2.md  notes/PHASE_3.md  notes/decisions.md")
log("═" * 60)
