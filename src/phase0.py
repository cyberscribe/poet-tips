"""Phase 0: Acquire, probe, and gate the Poet Tips GraphML dataset."""

import hashlib
from collections import Counter
from pathlib import Path

import networkx as nx
import numpy as np

ROOT = Path(__file__).parent.parent
RAW_DIR = ROOT / "data" / "raw"
NOTES_DIR = ROOT / "notes"
GRAPHML_PATH = RAW_DIR / "poet_tips-20191025.graphml"

PROVENANCE_URL = "https://archive.org/details/poet_tips-20191025"
NOTES_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def describe_attribute(values: list, name: str, indent: str = "") -> str:
    non_null = [v for v in values if v not in (None, "", "null", "NULL")]
    coverage = len(non_null) / len(values) if values else 0
    coverage_flag = "  ⚠ <50% coverage" if coverage < 0.5 else ""
    lines = [f"{indent}**{name}** — {coverage:.1%} coverage{coverage_flag}"]

    if not non_null:
        lines.append(f"{indent}  (no non-null values)")
        return "\n".join(lines)

    # Try numeric
    nums = []
    for v in non_null:
        try:
            nums.append(float(v))
        except (ValueError, TypeError):
            break

    if len(nums) == len(non_null):
        arr = np.array(nums)
        lines.append(
            f"{indent}  range [{arr.min():.4g}, {arr.max():.4g}]  "
            f"median {np.median(arr):.4g}  mean {arr.mean():.4g}"
        )
    else:
        counts = Counter(str(v) for v in non_null)
        top = counts.most_common(10)
        lines.append(f"{indent}  {len(counts)} unique values; top 10:")
        for val, cnt in top:
            short = val[:80]
            lines.append(f"{indent}    {cnt:>6}  {short}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------

print("Loading graph …")
G = nx.read_graphml(GRAPHML_PATH)
print(f"  nodes={G.number_of_nodes()}  edges={G.number_of_edges()}")

is_directed = G.is_directed()
is_multigraph = G.is_multigraph()

# ---------------------------------------------------------------------------
# PROVENANCE.md
# ---------------------------------------------------------------------------

sha = file_sha256(GRAPHML_PATH)
size_bytes = GRAPHML_PATH.stat().st_size

provenance_text = f"""# Provenance

| Field | Value |
|-------|-------|
| Source URL | {PROVENANCE_URL} |
| File | poet_tips-20191025.graphml |
| Size | {size_bytes:,} bytes ({size_bytes / 1e6:.2f} MB) |
| SHA-256 | `{sha}` |
| Downloaded | already present in working directory (file dated 2019-10-25) |
| Notes | Plain XML GraphML, UTF-8, no compression wrapper needed |
"""
(RAW_DIR / "PROVENANCE.md").write_text(provenance_text)
print("Wrote PROVENANCE.md")

# ---------------------------------------------------------------------------
# Node attributes
# ---------------------------------------------------------------------------

all_node_attrs: dict[str, list] = {}
for _nid, attrs in G.nodes(data=True):
    for k, v in attrs.items():
        all_node_attrs.setdefault(k, []).append(v)

# Pad missing to total node count so coverage is accurate
n_nodes = G.number_of_nodes()
for k in all_node_attrs:
    if len(all_node_attrs[k]) < n_nodes:
        all_node_attrs[k] += [None] * (n_nodes - len(all_node_attrs[k]))

# ---------------------------------------------------------------------------
# Edge attributes
# ---------------------------------------------------------------------------

all_edge_attrs: dict[str, list] = {}
for _u, _v, attrs in G.edges(data=True):
    for k, v in attrs.items():
        all_edge_attrs.setdefault(k, []).append(v)

n_edges = G.number_of_edges()
for k in all_edge_attrs:
    if len(all_edge_attrs[k]) < n_edges:
        all_edge_attrs[k] += [None] * (n_edges - len(all_edge_attrs[k]))

# ---------------------------------------------------------------------------
# Degree distribution
# ---------------------------------------------------------------------------

if is_directed:
    degrees = dict(G.degree())
else:
    degrees = dict(G.degree())

deg_vals = list(degrees.values())
deg_arr = np.array(deg_vals)

top20 = sorted(degrees.items(), key=lambda x: x[1], reverse=True)[:20]

# ---------------------------------------------------------------------------
# Connected components
# ---------------------------------------------------------------------------

if is_directed:
    comps = sorted(nx.weakly_connected_components(G), key=len, reverse=True)
    comp_type = "weakly connected"
else:
    comps = sorted(nx.connected_components(G), key=len, reverse=True)
    comp_type = "connected"

isolates = list(nx.isolates(G))

# ---------------------------------------------------------------------------
# Self-loops & duplicates
# ---------------------------------------------------------------------------

self_loops = list(nx.selfloop_edges(G))

node_labels = [data.get("label", "") for _, data in G.nodes(data=True)]
dup_labels = {
    lbl: cnt for lbl, cnt in Counter(node_labels).items() if cnt > 1 and lbl
}

# ---------------------------------------------------------------------------
# Sample nodes and edges
# ---------------------------------------------------------------------------

sample_nodes = list(G.nodes(data=True))[:5]
sample_edges = list(G.edges(data=True))[:10]

# ---------------------------------------------------------------------------
# Edge weight distribution (if present)
# ---------------------------------------------------------------------------

weight_vals = all_edge_attrs.get("weight", [])
numeric_weights = []
if weight_vals:
    for v in weight_vals:
        try:
            numeric_weights.append(float(v))
        except (TypeError, ValueError):
            pass

# ---------------------------------------------------------------------------
# Assemble PROBE.md
# ---------------------------------------------------------------------------

probe_lines = [
    "# PROBE.md — Poet Tips Dataset",
    "",
    "## Graph basics",
    "",
    "| Property | Value |",
    "|----------|-------|",
    f"| Node count | {n_nodes:,} |",
    f"| Edge count | {n_edges:,} |",
    f"| Directed | {is_directed} |",
    f"| Multigraph | {is_multigraph} |",
    "",
    "## Node attributes",
    "",
]

if all_node_attrs:
    for k, vals in sorted(all_node_attrs.items()):
        probe_lines.append(describe_attribute(vals, k))
        probe_lines.append("")
else:
    probe_lines += ["(no node attributes found)", ""]

probe_lines += [
    "## Edge attributes",
    "",
]

if all_edge_attrs:
    for k, vals in sorted(all_edge_attrs.items()):
        probe_lines.append(describe_attribute(vals, k))
        probe_lines.append("")
else:
    probe_lines += ["(no edge attributes found)", ""]

probe_lines += [
    "## Five sample nodes (full attributes)",
    "",
    "```",
]
for nid, attrs in sample_nodes:
    probe_lines.append(f"  id={nid!r}  attrs={attrs}")
probe_lines += ["```", ""]

probe_lines += [
    "## Ten sample edges (full attributes)",
    "",
    "```",
]
for u, v, attrs in sample_edges:
    probe_lines.append(f"  {u!r} → {v!r}  attrs={attrs}")
probe_lines += ["```", ""]

probe_lines += [
    "## Connected components",
    "",
    f"Component type: **{comp_type}**",
    "",
    f"Total component count: {len(comps):,}",
    "",
    "Top 5 by size:",
    "",
    "| Rank | Size |",
    "|------|------|",
]
for i, comp in enumerate(comps[:5], 1):
    probe_lines.append(f"| {i} | {len(comp):,} |")
probe_lines += [""]

probe_lines += [
    "## Degree distribution",
    "",
    "| Stat | Value |",
    "|------|-------|",
    f"| Min | {deg_arr.min()} |",
    f"| Median | {np.median(deg_arr):.1f} |",
    f"| Mean | {deg_arr.mean():.2f} |",
    f"| 95th percentile | {np.percentile(deg_arr, 95):.1f} |",
    f"| Max | {deg_arr.max()} |",
    "",
    "Top 20 nodes by total degree:",
    "",
    "| Node ID | Label | Degree |",
    "|---------|-------|--------|",
]
for nid, deg in top20:
    lbl = G.nodes[nid].get("label", "")
    probe_lines.append(f"| `{nid}` | {lbl} | {deg} |")
probe_lines += [""]

if numeric_weights:
    wt = np.array(numeric_weights)
    probe_lines += [
        "## Edge-weight distribution",
        "",
        "| Stat | Value |",
        "|------|-------|",
        f"| Min | {wt.min():.4g} |",
        f"| Median | {np.median(wt):.4g} |",
        f"| Mean | {wt.mean():.4g} |",
        f"| 95th percentile | {np.percentile(wt, 95):.4g} |",
        f"| Max | {wt.max():.4g} |",
        "",
    ]

probe_lines += [
    "## Data-quality issues",
    "",
    f"- Self-loops: **{len(self_loops)}**",
    f"- Isolates (degree-0 nodes): **{len(isolates)}**",
    f"- Duplicate labels: **{len(dup_labels)}** label(s) appear on more than one node",
]
if dup_labels:
    for lbl, cnt in list(dup_labels.items())[:10]:
        probe_lines.append(f"  - {lbl!r}: {cnt} nodes")
probe_lines += [""]

probe_text = "\n".join(probe_lines)
(RAW_DIR / "PROBE.md").write_text(probe_text)
print("Wrote PROBE.md")

# ---------------------------------------------------------------------------
# Print key facts for the gating report
# ---------------------------------------------------------------------------

print("\n--- Key facts for gating report ---")
print(f"Nodes: {n_nodes}, Edges: {n_edges}, Directed: {is_directed}")
print(f"Components: {len(comps)}, largest: {len(comps[0])}")
print(f"Isolates: {len(isolates)}")
print(f"Self-loops: {len(self_loops)}")
print(f"Node attrs: {list(all_node_attrs.keys())}")
print(f"Edge attrs: {list(all_edge_attrs.keys())}")
print(f"Has weights: {bool(numeric_weights)}")
print(f"Top node by degree: {top20[0]}")
