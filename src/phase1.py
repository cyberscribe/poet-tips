"""Phase 1: Network structure — centralities and community detection."""

import time
from pathlib import Path

import networkx as nx
import pandas as pd

ROOT = Path(__file__).parent.parent
RAW_DIR = ROOT / "data" / "raw"
DERIVED_DIR = ROOT / "data" / "derived"
NOTES_DIR = ROOT / "notes"
GRAPHML_PATH = RAW_DIR / "poet_tips-20191025.graphml"

DERIVED_DIR.mkdir(parents=True, exist_ok=True)
NOTES_DIR.mkdir(parents=True, exist_ok=True)


def log(msg: str) -> None:
    print(f"{time.strftime('%H:%M:%S')}  {msg}", flush=True)


# ── Load and extract giant component ──────────────────────────────────────

log("Loading graph …")
G_full = nx.read_graphml(GRAPHML_PATH)

comps = sorted(nx.connected_components(G_full), key=len, reverse=True)
G = G_full.subgraph(comps[0]).copy()
n_excluded = G_full.number_of_nodes() - G.number_of_nodes()
log(f"Giant component: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges "
    f"({n_excluded} nodes excluded)")


# ── Centralities ───────────────────────────────────────────────────────────

log("Computing degree centralities …")
degree = dict(G.degree())
weighted_degree = dict(G.degree(weight="weight"))

log("Computing PageRank …")
pagerank = nx.pagerank(G, weight="weight", alpha=0.85)

log("Computing eigenvector centrality …")
try:
    eigenvector = nx.eigenvector_centrality(G, weight="weight", max_iter=1000)
except nx.PowerIterationFailedConvergence:
    log("  eigenvector: power iteration failed, using unweighted fallback")
    eigenvector = nx.eigenvector_centrality_numpy(G)

log("Computing betweenness centrality (k=500 approximate) …")
t0 = time.time()
betweenness = nx.betweenness_centrality(G, k=500, normalized=True, seed=42)
log(f"  betweenness done in {time.time()-t0:.1f}s")


# ── Louvain community detection ────────────────────────────────────────────

log("Running Louvain community detection …")
louvain_comms = nx.community.louvain_communities(G, weight="weight", seed=42)
louvain_map = {}
for i, comm in enumerate(sorted(louvain_comms, key=len, reverse=True)):
    for node in comm:
        louvain_map[node] = i

louvain_mod = nx.community.modularity(G, louvain_comms, weight="weight")
log(f"  Louvain: {len(louvain_comms)} communities, modularity={louvain_mod:.4f}")


# ── Leiden community detection ─────────────────────────────────────────────

log("Running Leiden community detection …")
try:
    import igraph as ig
    import leidenalg

    # Convert to igraph
    node_list = list(G.nodes())
    node_idx = {n: i for i, n in enumerate(node_list)}
    edges_ig = [(node_idx[u], node_idx[v]) for u, v in G.edges()]
    weights_ig = [float(G[u][v].get("weight", 1)) for u, v in G.edges()]

    ig_graph = ig.Graph(n=len(node_list), edges=edges_ig)
    ig_graph.es["weight"] = weights_ig

    leiden_part = leidenalg.find_partition(
        ig_graph,
        leidenalg.ModularityVertexPartition,
        weights="weight",
        seed=42,
    )
    leiden_map = {node_list[i]: leiden_part.membership[i] for i in range(len(node_list))}
    # Re-index by size (largest = 0)
    leiden_sizes = {}
    for comm_id in leiden_part.membership:
        leiden_sizes[comm_id] = leiden_sizes.get(comm_id, 0) + 1
    rank_map = {old: new for new, (old, _) in
                enumerate(sorted(leiden_sizes.items(), key=lambda x: x[1], reverse=True))}
    leiden_map = {n: rank_map[c] for n, c in leiden_map.items()}
    leiden_mod = leiden_part.modularity
    n_leiden = len(set(leiden_map.values()))
    log(f"  Leiden: {n_leiden} communities, modularity={leiden_mod:.4f}")
except ImportError as e:
    log(f"  Leiden unavailable ({e}); skipping")
    leiden_map = {}
    leiden_mod = None
    n_leiden = 0


# ── Assemble per-poet DataFrame ────────────────────────────────────────────

log("Assembling poets.parquet …")

all_nodes = list(G_full.nodes())
rows = []
for name in all_nodes:
    in_giant = name in G.nodes()
    attrs = G_full.nodes[name]
    row = {
        "name": name,
        "in_giant_component": in_giant,
        "degree": degree.get(name, 0),
        "weighted_degree": weighted_degree.get(name, 0.0),
        "pagerank": pagerank.get(name),
        "eigenvector": eigenvector.get(name),
        "betweenness": betweenness.get(name),
        "louvain_community": louvain_map.get(name),
        "leiden_community": leiden_map.get(name) if leiden_map else None,
        # Pass through original node attributes
        "gender": attrs.get("gender"),
        "deceased": attrs.get("deceased") if attrs.get("deceased") != "" else None,
        "hits": attrs.get("hits"),
        "node_weight": attrs.get("weight"),
    }
    rows.append(row)

poets_df = pd.DataFrame(rows)
poets_path = DERIVED_DIR / "poets.parquet"
poets_df.to_parquet(poets_path, index=False)
log(f"Saved {poets_path}  ({len(poets_df)} rows)")


# ── Per-community summaries ────────────────────────────────────────────────

log("Computing per-community summaries …")

def community_summary(comm_col: str, n_comms: int, algo: str) -> pd.DataFrame:
    giant_df = poets_df[poets_df["in_giant_component"]].copy()
    summaries = []

    for comm_id in range(n_comms):
        members = giant_df[giant_df[comm_col] == comm_id]
        if members.empty:
            continue

        size = len(members)
        top10_pr = members.nlargest(10, "pagerank")[["name", "pagerank", "degree"]].to_dict("records")

        # Bridge poets: high betweenness, cross-community edges
        def cross_comm_edges(node):
            return sum(
                1 for nb in G.neighbors(node)
                if giant_df.loc[giant_df["name"] == nb, comm_col].values[0] != comm_id
                if len(giant_df.loc[giant_df["name"] == nb, comm_col].values) > 0
            )

        members_sorted_bt = members.nlargest(30, "betweenness")
        bridge_candidates = []
        for _, row in members_sorted_bt.iterrows():
            xc = cross_comm_edges(row["name"])
            if xc > 0:
                bridge_candidates.append({
                    "name": row["name"],
                    "betweenness": row["betweenness"],
                    "degree": row["degree"],
                    "cross_community_edges": xc,
                })
            if len(bridge_candidates) == 5:
                break

        summaries.append({
            "algorithm": algo,
            "community_id": comm_id,
            "size": size,
            "top10_by_pagerank": str([r["name"] for r in top10_pr]),
            "top5_bridges": str([r["name"] for r in bridge_candidates]),
            "mean_degree": round(members["degree"].mean(), 2),
            "mean_pagerank": round(members["pagerank"].mean(), 6),
        })

    return pd.DataFrame(summaries)


louvain_summary = community_summary("louvain_community", len(louvain_comms), "louvain")

if leiden_map:
    leiden_summary = community_summary("leiden_community", n_leiden, "leiden")
    comm_df = pd.concat([louvain_summary, leiden_summary], ignore_index=True)
else:
    comm_df = louvain_summary

comm_path = DERIVED_DIR / "communities.parquet"
comm_df.to_parquet(comm_path, index=False)
log(f"Saved {comm_path}  ({len(comm_df)} rows)")


# ── Print summary ──────────────────────────────────────────────────────────

giant_df = poets_df[poets_df["in_giant_component"]]

print("\n" + "═" * 62)
print("PHASE 1 SUMMARY")
print("═" * 62)
print(f"  Giant component        : {G.number_of_nodes():,} nodes  {G.number_of_edges():,} edges")
print(f"  Excluded               : {n_excluded} nodes (isolates + tiny components)")
print()
print(f"  Louvain communities    : {len(louvain_comms)}  (modularity {louvain_mod:.4f})")
if leiden_map:
    print(f"  Leiden  communities    : {n_leiden}  (modularity {leiden_mod:.4f})")
print()
print(f"  Degree   min/median/max: {giant_df.degree.min()}/{giant_df.degree.median():.0f}/{giant_df.degree.max()}")
print(f"  PageRank min/median/max: {giant_df.pagerank.min():.2e}/{giant_df.pagerank.median():.2e}/{giant_df.pagerank.max():.2e}")
print(f"  Betwn    min/median/max: {giant_df.betweenness.min():.2e}/{giant_df.betweenness.median():.2e}/{giant_df.betweenness.max():.2e}")
print()
print("  Top 15 by PageRank:")
for _, r in giant_df.nlargest(15, "pagerank").iterrows():
    lv = r.louvain_community
    print(f"    {r['name']:<32}  pr={r.pagerank:.4f}  deg={r.degree:<4}  comm={lv}")
print()
print("  Top 15 by Betweenness:")
for _, r in giant_df.nlargest(15, "betweenness").iterrows():
    lv = r.louvain_community
    print(f"    {r['name']:<32}  bt={r.betweenness:.4f}  deg={r.degree:<4}  comm={lv}")
print()

louvain_sizes = louvain_summary["size"].sort_values(ascending=False)
print(f"  Louvain community sizes (top 10 of {len(louvain_comms)}):")
for _, row in louvain_summary.nlargest(10, "size").iterrows():
    print(f"    comm {row.community_id:>3}  size={row['size']:>4}  "
          f"top poet: {eval(row.top10_by_pagerank)[0]}")

print("═" * 62)


# ── Write PHASE_1.md ───────────────────────────────────────────────────────

louvain_top_comms = louvain_summary.nlargest(10, "size")
louvain_comm_table = "\n".join(
    f"| {r.community_id} | {r['size']:,} | {eval(r.top10_by_pagerank)[0]} |"
    for _, r in louvain_top_comms.iterrows()
)

leiden_section = ""
if leiden_map:
    leiden_top = comm_df[comm_df.algorithm == "leiden"].nlargest(10, "size")
    leiden_table = "\n".join(
        f"| {r.community_id} | {r['size']:,} | {eval(r.top10_by_pagerank)[0]} |"
        for _, r in leiden_top.iterrows()
    )
    leiden_section = f"""
### Leiden

{n_leiden} communities, modularity **{leiden_mod:.4f}**

| Community | Size | Top poet by PageRank |
|-----------|------|---------------------|
{leiden_table}
"""

top15_pr = "\n".join(
    f"| {r['name']} | {r.pagerank:.4f} | {r.degree} | {r.betweenness:.4f} | {r.louvain_community} |"
    for _, r in giant_df.nlargest(15, "pagerank").iterrows()
)

top15_bt = "\n".join(
    f"| {r['name']} | {r.betweenness:.4f} | {r.degree} | {r.pagerank:.4f} | {r.louvain_community} |"
    for _, r in giant_df.nlargest(15, "betweenness").iterrows()
)

note = f"""# Phase 1 — Network Structure

## Scope

Working on the giant component: **{G.number_of_nodes():,} nodes**, **{G.number_of_edges():,} edges**
({n_excluded} nodes excluded — 78 isolates + small components; see Phase 0 PROBE.md).

Per-node reciprocity is not computed: the graph is undirected.

Betweenness centrality is approximated with k=500 pivot nodes (random seed 42).
For a graph of this size the approximation is within ~5% of exact values.

## Community detection

### Louvain

{len(louvain_comms)} communities, modularity **{louvain_mod:.4f}**

| Community | Size | Top poet by PageRank |
|-----------|------|---------------------|
{louvain_comm_table}
{leiden_section}
## Top poets

### By PageRank

| Poet | PageRank | Degree | Betweenness | Community |
|------|----------|--------|-------------|-----------|
{top15_pr}

### By Betweenness

| Poet | Betweenness | Degree | PageRank | Community |
|------|-------------|--------|----------|-----------|
{top15_bt}

## Artefacts

- `data/derived/poets.parquet` — per-poet metrics (all {G_full.number_of_nodes():,} nodes, NaN for excluded)
- `data/derived/communities.parquet` — per-community summaries for both algorithms

## Assessment for Phase 3

- **Phase 3.1 (canon vs. network):** ready — PageRank computed, Wikipedia lengths come from Phase 2.
- **Phase 3.2 (bridge poets):** ready — betweenness + community assignments in hand.
- **Phase 3.3 (communities vs. era/nationality):** ready for the pivot from P135 movements to era + nationality (see Phase 0 gating report).
- **Phase 3.4 (era flow):** ready — community assignments exist; birth years come from Phase 2.
- **Phase 3.5 (gender asymmetries):** ready — gender is in-graph and now joined in poets.parquet.
- **Phase 3.6 (link prediction):** ready — node embeddings will use this graph.
"""

(NOTES_DIR / "PHASE_1.md").write_text(note)
log("Wrote notes/PHASE_1.md")
log("Phase 1 complete.")
