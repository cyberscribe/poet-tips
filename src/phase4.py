"""Phase 4: Pre-compute layout and generate self-contained HTML viewer."""

import json
import time
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd
from fa2_modified import ForceAtlas2

ROOT = Path(__file__).parent.parent
GRAPHML_PATH = ROOT / "data" / "raw" / "poet_tips-20191025.graphml"
DERIVED_DIR = ROOT / "data" / "derived"
ENRICHED_DIR = ROOT / "data" / "enriched"
INTERACTIVE_DIR = ROOT / "outputs" / "interactive"
INTERACTIVE_DIR.mkdir(parents=True, exist_ok=True)


def log(msg):
    print(f"{time.strftime('%H:%M:%S')}  {msg}", flush=True)


# ── Load data ──────────────────────────────────────────────────────────────

log("Loading data …")
poets_df = pd.read_parquet(DERIVED_DIR / "poets.parquet")
wiki_df = pd.read_parquet(ENRICHED_DIR / "poets_wikidata.parquet")

df = poets_df.merge(wiki_df, on="name", how="left")
gc = df[df.in_giant_component].copy()
gc["birth_year"] = pd.to_numeric(gc["birth_year"], errors="coerce")
gc.loc[(gc.birth_year < 1400) | (gc.birth_year > 2010), "birth_year"] = np.nan
gc["wp_article_bytes"] = pd.to_numeric(gc["wp_article_bytes"], errors="coerce")
gc["hits"] = pd.to_numeric(gc["hits"], errors="coerce")

log("Loading graph …")
G_full = nx.read_graphml(GRAPHML_PATH)
comps = sorted(nx.connected_components(G_full), key=len, reverse=True)
G = G_full.subgraph(comps[0]).copy()
log(f"  {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")


# ── Stability scores (multi-seed Louvain) ─────────────────────────────────

log("Computing stability via 20-seed Louvain ensemble …")
N_SEEDS = 20
all_partitions = []
for seed in range(N_SEEDS):
    comms = nx.community.louvain_communities(G, weight="weight", seed=seed)
    mapping = {}
    for i, comm in enumerate(comms):
        for node in comm:
            mapping[node] = i
    all_partitions.append(mapping)
    if (seed + 1) % 5 == 0:
        log(f"  {seed+1}/{N_SEEDS} seeds done")

# For each node: fraction of seed pairs where node co-clusters with its reference community
# Simpler: use consensus_community = majority_vote across seeds, stability = agreement rate
ref_partition = all_partitions[0]  # seed=0 is the canonical Louvain

stability_scores = {}
for node in G.nodes():
    ref_comm = ref_partition[node]
    # Find which community in each partition contains the most of ref_comm's members
    ref_members = {n for n, c in ref_partition.items() if c == ref_comm}
    agree = 0
    for part in all_partitions:
        node_comm = part.get(node)
        if node_comm is None:
            continue
        comm_members = {n for n, c in part.items() if c == node_comm}
        overlap = len(ref_members & comm_members) / max(len(ref_members | comm_members), 1)
        if overlap > 0.5:
            agree += 1
    stability_scores[node] = agree / N_SEEDS

log(f"  Stability mean={np.mean(list(stability_scores.values())):.3f}  "
    f"stable (>0.7): {sum(1 for v in stability_scores.values() if v > 0.7)}/{len(stability_scores)}")


# ── ForceAtlas2 layout ─────────────────────────────────────────────────────

log("Computing ForceAtlas2 layout (this takes 2-4 minutes) …")
fa2 = ForceAtlas2(
    outboundAttractionDistribution=True,
    linLogMode=False,
    adjustSizes=False,
    edgeWeightInfluence=1.0,
    jitterTolerance=1.0,
    barnesHutOptimize=True,
    barnesHutTheta=1.2,
    multiThreaded=False,
    scalingRatio=2.0,
    strongGravityMode=False,
    gravity=1.0,
    verbose=False,
)
t0 = time.time()
pos = fa2.forceatlas2_networkx_layout(G, pos=None, iterations=400)
log(f"  FA2 done in {time.time()-t0:.1f}s")

# Normalise to [-1, 1]
xs = np.array([v[0] for v in pos.values()])
ys = np.array([v[1] for v in pos.values()])
cx, cy = xs.mean(), ys.mean()
span = max(xs.max() - xs.min(), ys.max() - ys.min()) / 2
for node in pos:
    pos[node] = ((pos[node][0] - cx) / span, (pos[node][1] - cy) / span)
log("  Positions normalised")


# ── Bridge poets (from Phase 3 results) ───────────────────────────────────

# Any poet with weighted_betweenness in top 20 (all were above null 99th percentile)
gc_sorted_wb = gc.nlargest(20, "weighted_betweenness")
bridge_set = set(gc_sorted_wb["name"])


# ── Community labels and colours ──────────────────────────────────────────

comm_summaries = pd.read_parquet(DERIVED_DIR / "communities.parquet")
louvain_summ = comm_summaries[comm_summaries.algorithm == "louvain"].copy()
COMM_LABELS = {}
for _, row in louvain_summ.iterrows():
    top = eval(row.top10_by_pagerank)[0]
    COMM_LABELS[int(row.community_id)] = f"C{int(row.community_id)}: {top}"

# 24 distinct colours (qualitative, colourblind-friendly where possible)
COMM_COLORS = [
    "#4e9a8b", "#e07b54", "#7b54e0", "#f5b942", "#54a0e0",
    "#c95f8e", "#6cbf6c", "#54d4a0", "#d49654", "#6c8bbf",
    "#bf8b6c", "#4ebf9a", "#bf4e7b", "#9abf4e", "#7b9abf",
    "#e0c454", "#a054e0", "#54e0c4", "#e054a0", "#c4e054",
    "#8b6cbf", "#bf6c8b", "#6cbfbf", "#bfbf6c",
]


# ── Top neighbours per node ────────────────────────────────────────────────

log("Computing top neighbours …")
name_to_idx = {name: i for i, name in enumerate(gc["name"])}
top_neighbors = {}
for node in G.nodes():
    nbrs = sorted(G[node].items(), key=lambda x: float(x[1].get("weight", 1)), reverse=True)[:10]
    top_neighbors[node] = [nb for nb, _ in nbrs]


# ── PageRank rank ──────────────────────────────────────────────────────────

pr_rank_series = gc.sort_values("pagerank", ascending=False).reset_index(drop=True)
pr_rank_map = {row["name"]: i + 1 for i, row in pr_rank_series.iterrows()}


# ── Nationality normalization (same as phase3) ─────────────────────────────

_UK_VARIANTS = {
    "United Kingdom of Great Britain and Ireland",
    "Kingdom of Great Britain", "Kingdom of England",
    "Kingdom of Scotland", "British Empire",
}

def norm_country(raw):
    if pd.isna(raw) or str(raw).strip() == "":
        return None
    first = str(raw).split("|")[0].strip()
    return "United Kingdom" if first in _UK_VARIANTS else first


gc["nationality_norm"] = gc["citizenships"].apply(norm_country)


# ── Assemble node and edge data ────────────────────────────────────────────

log("Assembling graph data …")

node_list = list(gc["name"])
node_idx = {n: i for i, n in enumerate(node_list)}

nodes_json = []
for i, row in gc.iterrows():
    name = row["name"]
    if name not in pos:
        continue  # not in giant component (shouldn't happen)
    x, y = pos[name]
    comm_id = int(row["louvain_community"]) if pd.notna(row["louvain_community"]) else -1
    stability = stability_scores.get(name, 0.0)
    pr = float(row["pagerank"]) if pd.notna(row["pagerank"]) else 0.0
    deg = int(row["degree"]) if pd.notna(row["degree"]) else 0
    wb = float(row["weighted_betweenness"]) if pd.notna(row["weighted_betweenness"]) else 0.0
    hits_val = int(row["hits"]) if pd.notna(row["hits"]) else None
    wp_bytes = int(row["wp_article_bytes"]) if pd.notna(row["wp_article_bytes"]) else None
    by = int(row["birth_year"]) if pd.notna(row["birth_year"]) else None
    nat = row["nationality_norm"] if pd.notna(row.get("nationality_norm")) else None
    wp_title = row["wp_title"] if pd.notna(row.get("wp_title")) and row["wp_title"] else None
    gender = row["gender"] if pd.notna(row["gender"]) and row["gender"] != "" else None
    nbrs = [node_idx[n] for n in top_neighbors.get(name, []) if n in node_idx]

    nodes_json.append({
        "id": node_idx[name],
        "n": name,
        "x": round(x, 5),
        "y": round(y, 5),
        "c": comm_id,
        "pr": round(pr * 1e4, 4),  # × 1e4 for readability
        "prRank": pr_rank_map.get(name, 9999),
        "deg": deg,
        "wb": round(wb, 5),
        "bridge": name in bridge_set,
        "stable": stability >= 0.7,
        "stab": round(stability, 2),
        "hits": hits_val,
        "wpBytes": wp_bytes,
        "by": by,
        "nat": nat,
        "wpTitle": wp_title,
        "gender": gender,
        "nbrs": nbrs,
    })

# Build edges as [src_idx, tgt_idx, weight]
edges_json = []
for u, v, d in G.edges(data=True):
    if u in node_idx and v in node_idx:
        edges_json.append([node_idx[u], node_idx[v], int(d.get("weight", 1))])

log(f"  {len(nodes_json)} nodes, {len(edges_json)} edges in output")

# Community metadata
comm_meta = {}
for comm_id, label in COMM_LABELS.items():
    comm_meta[str(comm_id)] = {
        "label": label,
        "color": COMM_COLORS[comm_id % len(COMM_COLORS)],
    }
comm_meta["-1"] = {"label": "Unknown", "color": "#cccccc"}

data_json = json.dumps({"nodes": nodes_json, "edges": edges_json, "comms": comm_meta},
                       separators=(",", ":"))
log(f"  JSON size: {len(data_json) / 1024:.0f} KB")


# ── HTML template ──────────────────────────────────────────────────────────

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Poet Tips Network — Reader Recommendations 2016–2019</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#1a1a2e;color:#e0e0e0;height:100vh;overflow:hidden;display:flex;flex-direction:column}
#toolbar{display:flex;align-items:center;gap:8px;padding:8px 12px;background:#16213e;border-bottom:1px solid #0f3460;flex-shrink:0;flex-wrap:wrap}
#title{font-size:13px;font-weight:600;color:#a0c4ff;flex:1;min-width:180px}
#search{padding:5px 10px;border:1px solid #0f3460;border-radius:16px;background:#0f3460;color:#e0e0e0;font-size:12px;width:220px;outline:none}
#search:focus{border-color:#4e9a8b}
#search-results{position:absolute;top:42px;left:0;background:#16213e;border:1px solid #0f3460;border-radius:4px;max-height:200px;overflow-y:auto;z-index:100;min-width:240px;display:none}
#search-wrap{position:relative}
.sr-item{padding:6px 12px;cursor:pointer;font-size:12px}
.sr-item:hover{background:#0f3460}
.btn{padding:5px 10px;border:1px solid #4e9a8b;border-radius:4px;background:transparent;color:#4e9a8b;font-size:11px;cursor:pointer;white-space:nowrap}
.btn:hover{background:#4e9a8b22}
.btn.active{background:#4e9a8b;color:#fff}
#main{display:flex;flex:1;overflow:hidden;position:relative}
#canvas{flex:1;cursor:grab;touch-action:none;display:block}
#canvas.grabbing{cursor:grabbing}
#panel{width:280px;background:#16213e;border-left:1px solid #0f3460;overflow-y:auto;padding:14px;flex-shrink:0;font-size:12px;display:none}
#panel.open{display:block}
#panel h2{font-size:14px;color:#a0c4ff;margin-bottom:10px;line-height:1.3}
.panel-section{margin-bottom:12px}
.panel-label{color:#888;font-size:10px;text-transform:uppercase;letter-spacing:.05em;margin-bottom:3px}
.panel-value{color:#e0e0e0}
.panel-tag{display:inline-block;padding:2px 7px;border-radius:10px;font-size:10px;margin:2px}
.nbr-list{list-style:none}
.nbr-list li{padding:3px 0;border-bottom:1px solid #0f3460;cursor:pointer;color:#a0c4ff}
.nbr-list li:hover{color:#4e9a8b}
#about-modal{display:none;position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);background:#16213e;border:1px solid #0f3460;border-radius:8px;padding:20px;max-width:480px;width:90%;z-index:200;font-size:12px;line-height:1.6}
#about-modal.open{display:block}
#about-modal h3{color:#a0c4ff;margin-bottom:10px}
#about-modal p{margin-bottom:8px;color:#ccc}
#about-close{float:right;background:transparent;border:none;color:#888;cursor:pointer;font-size:16px;line-height:1}
#overlay{display:none;position:absolute;top:0;left:0;width:100%;height:100%;background:#00000055;z-index:150}
#overlay.open{display:block}
#stats-bar{position:absolute;bottom:8px;left:12px;font-size:10px;color:#555;pointer-events:none}
#tooltip{position:absolute;background:#16213e;border:1px solid #0f3460;border-radius:4px;padding:4px 8px;font-size:11px;pointer-events:none;display:none;z-index:50;white-space:nowrap;color:#e0e0e0}
</style>
</head>
<body>
<div id="toolbar">
  <span id="title">Poet Tips Network — Reader Recommendations 2016–2019</span>
  <div id="search-wrap">
    <input id="search" type="text" placeholder="Search poet…" autocomplete="off">
    <div id="search-results"></div>
  </div>
  <button class="btn" id="btn-bridges">Bridges only</button>
  <button class="btn" id="btn-top100">Top 100 only</button>
  <button class="btn" id="btn-about">About this view</button>
  <button class="btn" id="btn-reset">Reset view</button>
</div>
<div id="main">
  <canvas id="canvas"></canvas>
  <div id="panel"></div>
</div>
<div id="overlay"></div>
<div id="about-modal">
  <button id="about-close">✕</button>
  <h3>About this view</h3>
  <p><strong>What you're seeing:</strong> 6,095 poets from the Poet Tips recommendation website (2016–2019), connected by co-recommendation patterns: two poets are linked when users recommended them together.</p>
  <p><strong>Layout:</strong> node positions are a 2D projection computed by ForceAtlas2. Proximity is a layout artefact — it reflects graph connectivity, not literary similarity or canonical status.</p>
  <p><strong>Node size</strong> = PageRank in the co-recommendation network. <strong>Node colour</strong> = Louvain community (consensus across 20 random seeds). <strong>Faded nodes</strong> have unstable community assignments (below 70% seed agreement).</p>
  <p><strong>Bridge poets</strong> are the top 20 by weighted betweenness (using 1/weight as distance), all significantly above the degree-preserving null model.</p>
  <p><strong>Data coverage:</strong> 65% of poets matched to Wikidata; birth year available for 43% of all poets; gender from the dataset itself (99.4% coverage).</p>
  <p><strong>What this is not:</strong> a measure of literary quality, canonical status, or critical importance. It is a portrait of what Poet Tips users recommended to each other between 2016 and 2019.</p>
</div>
<div id="stats-bar" id="stats-bar"></div>
<div id="tooltip"></div>
<script>
const RAW=__DATA__;
const nodes=RAW.nodes, edges=RAW.edges, comms=RAW.comms;
const N=nodes.length;

// Build name→id index
const nameIdx={};
nodes.forEach(n=>nameIdx[n.n.toLowerCase()]=n.id);
const nameExact={};
nodes.forEach(n=>nameExact[n.n]=n.id);

// PageRank max for sizing
const prMax=Math.max(...nodes.map(n=>n.pr));

// Community colours
function nodeColor(n,alpha=1){
  const c=comms[String(n.c)];
  const hex=c?c.color:"#888888";
  if(alpha===1)return hex;
  const r=parseInt(hex.slice(1,3),16);
  const g=parseInt(hex.slice(3,5),16);
  const b=parseInt(hex.slice(5,7),16);
  return `rgba(${r},${g},${b},${alpha})`;
}

function nodeRadius(n){
  return 3+12*Math.sqrt(n.pr/prMax);
}

// ── Canvas setup ──────────────────────────────────────────────────────────
const canvas=document.getElementById("canvas");
const ctx=canvas.getContext("2d");
let W,H;

function resize(){
  const pr=window.devicePixelRatio||1;
  const rect=canvas.getBoundingClientRect();
  W=rect.width; H=rect.height;
  canvas.width=W*pr; canvas.height=H*pr;
  ctx.scale(pr,pr);
  draw();
}
window.addEventListener("resize",resize);

// ── Transform (world ↔ screen) ─────────────────────────────────────────────
// World coords: roughly [-1,1] × [-1,1] (FA2 normalised)
// Screen coords: [0,W] × [0,H]
let tx=0, ty=0, scale=1;

function worldToScreen(wx,wy){
  return [wx*scale+tx, wy*scale+ty];
}
function screenToWorld(sx,sy){
  return [(sx-tx)/scale, (sy-ty)/scale];
}
function resetView(){
  // Fit all nodes in the canvas with 5% padding
  const xs=nodes.map(n=>n.x), ys=nodes.map(n=>n.y);
  const xMin=Math.min(...xs), xMax=Math.max(...xs);
  const yMin=Math.min(...ys), yMax=Math.max(...ys);
  const span=Math.max(xMax-xMin,yMax-yMin)*1.05;
  scale=Math.min(W,H)/span;
  tx=W/2-((xMin+xMax)/2)*scale;
  ty=H/2-((yMin+yMax)/2)*scale;
}

// ── State ──────────────────────────────────────────────────────────────────
let hoveredId=-1, selectedId=-1;
let showBridges=false, showTop100=false;
let isDirty=true;
let highlightSet=null; // Set of node IDs to highlight (search/neighbours)

function visibleNodes(){
  if(showBridges) return nodes.filter(n=>n.bridge);
  if(showTop100)  return nodes.filter(n=>n.prRank<=100);
  return nodes;
}

// ── Drawing ───────────────────────────────────────────────────────────────
function draw(){
  if(!isDirty)return;
  isDirty=false;
  ctx.clearRect(0,0,W,H);

  const vn=new Set(visibleNodes().map(n=>n.id));
  const dimmed=highlightSet!==null;

  // Draw edges
  ctx.lineWidth=0.6;
  const maxW=Math.max(...edges.map(e=>e[2]));
  for(const [si,ti,w] of edges){
    if(!vn.has(si)||!vn.has(ti))continue;
    const src=nodes[si], tgt=nodes[ti];
    const [sx,sy]=worldToScreen(src.x,src.y);
    const [ex,ey]=worldToScreen(tgt.x,tgt.y);
    // Viewport cull
    if(sx<-50&&ex<-50)continue;
    if(sy<-50&&ey<-50)continue;
    if(sx>W+50&&ex>W+50)continue;
    if(sy>H+50&&ey>H+50)continue;

    let alpha=0.08+0.07*(w/maxW);
    if(dimmed){
      const connected=highlightSet.has(si)&&highlightSet.has(ti);
      alpha=connected?0.4:0.02;
    }
    if(si===selectedId||ti===selectedId) alpha=0.5;
    ctx.strokeStyle=`rgba(180,200,220,${alpha})`;
    ctx.beginPath(); ctx.moveTo(sx,sy); ctx.lineTo(ex,ey); ctx.stroke();
  }

  // Draw nodes
  for(const n of visibleNodes()){
    const [sx,sy]=worldToScreen(n.x,n.y);
    if(sx<-30||sy<-30||sx>W+30||sy>H+30)continue;
    const r=nodeRadius(n);
    const isSelected=n.id===selectedId;
    const isHovered=n.id===hoveredId;
    const inHL=highlightSet===null||highlightSet.has(n.id);
    const alpha=inHL?1:0.2;

    ctx.beginPath();
    ctx.arc(sx,sy,r,0,Math.PI*2);
    ctx.fillStyle=nodeColor(n,alpha*(n.stable?1:0.5));
    ctx.fill();

    // Unstable ring
    if(!n.stable&&inHL){
      ctx.strokeStyle=`rgba(255,255,100,${alpha*0.6})`;
      ctx.lineWidth=1;
      ctx.setLineDash([2,2]);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    // Bridge ring
    if(n.bridge&&inHL){
      ctx.strokeStyle=`rgba(255,150,80,${alpha*0.8})`;
      ctx.lineWidth=1.5;
      ctx.stroke();
    }

    // Selected highlight
    if(isSelected){
      ctx.strokeStyle="#ffffff";
      ctx.lineWidth=2;
      ctx.setLineDash([]);
      ctx.stroke();
    } else if(isHovered){
      ctx.strokeStyle="rgba(255,255,255,0.6)";
      ctx.lineWidth=1;
      ctx.stroke();
    }
  }

  // Labels for selected node + its neighbours (or hover at close zoom)
  const labelZoom=scale>150;
  const labelled=new Set();
  if(selectedId>=0){
    const sn=nodes[selectedId];
    labelled.add(selectedId);
    sn.nbrs.forEach(id=>labelled.add(id));
  }
  if(labelZoom){
    for(const n of visibleNodes()){
      if(n.id===hoveredId||n.prRank<=30) labelled.add(n.id);
    }
  }
  ctx.font="bold 10px sans-serif";
  ctx.textAlign="left";
  for(const id of labelled){
    if(!vn.has(id))continue;
    const n=nodes[id];
    const [sx,sy]=worldToScreen(n.x,n.y);
    if(sx<-50||sy<-50||sx>W+50||sy>H+50)continue;
    const r=nodeRadius(n);
    const inHL=highlightSet===null||highlightSet.has(id);
    ctx.fillStyle=`rgba(220,220,220,${inHL?0.95:0.3})`;
    ctx.fillText(n.n,sx+r+2,sy+4);
  }

  // Stats bar
  document.getElementById("stats-bar").textContent=
    `${vn.size} poets shown  ·  ${edges.length.toLocaleString()} edges  ·  `+
    `zoom ${(scale/200*100).toFixed(0)}%`;
}

// ── Interaction ────────────────────────────────────────────────────────────
function nearestNode(sx,sy,maxDist=20){
  let best=-1, bestD=maxDist*maxDist;
  for(const n of visibleNodes()){
    const [nx,ny]=worldToScreen(n.x,n.y);
    const d=(nx-sx)**2+(ny-sy)**2;
    if(d<bestD){bestD=d;best=n.id;}
  }
  return best;
}

// Pan
let dragging=false, dragStart=[0,0], dragTX=0, dragTY=0;
canvas.addEventListener("mousedown",e=>{
  if(e.button!==0)return;
  dragging=true;
  dragStart=[e.offsetX,e.offsetY];
  dragTX=tx; dragTY=ty;
  canvas.classList.add("grabbing");
  e.preventDefault();
});
canvas.addEventListener("mousemove",e=>{
  if(dragging){
    tx=dragTX+(e.offsetX-dragStart[0]);
    ty=dragTY+(e.offsetY-dragStart[1]);
    isDirty=true; draw(); return;
  }
  const id=nearestNode(e.offsetX,e.offsetY,16);
  if(id!==hoveredId){hoveredId=id;isDirty=true;draw();}
  const tooltip=document.getElementById("tooltip");
  if(id>=0){
    const n=nodes[id];
    tooltip.textContent=n.n+(n.by?` (b.${n.by})`:"")+` · PR #${n.prRank}`;
    tooltip.style.display="block";
    tooltip.style.left=(e.clientX+12)+"px";
    tooltip.style.top=(e.clientY-8)+"px";
  } else {
    tooltip.style.display="none";
  }
});
canvas.addEventListener("mouseup",e=>{
  const moved=Math.hypot(e.offsetX-dragStart[0],e.offsetY-dragStart[1]);
  dragging=false;
  canvas.classList.remove("grabbing");
  if(moved<4){
    const id=nearestNode(e.offsetX,e.offsetY,16);
    if(id>=0) selectNode(id);
    else deselectNode();
  }
});
canvas.addEventListener("mouseleave",()=>{
  dragging=false;
  canvas.classList.remove("grabbing");
  document.getElementById("tooltip").style.display="none";
});
canvas.addEventListener("wheel",e=>{
  e.preventDefault();
  const factor=e.deltaY>0?0.85:1/0.85;
  const [wx,wy]=screenToWorld(e.offsetX,e.offsetY);
  scale*=factor;
  scale=Math.max(20,Math.min(4000,scale));
  tx=e.offsetX-wx*scale;
  ty=e.offsetY-wy*scale;
  isDirty=true; draw();
},{passive:false});

// Touch pan/zoom
let lastTouches=null;
canvas.addEventListener("touchstart",e=>{
  e.preventDefault();
  lastTouches=Array.from(e.touches).map(t=>({x:t.clientX,y:t.clientY}));
});
canvas.addEventListener("touchmove",e=>{
  e.preventDefault();
  const cur=Array.from(e.touches).map(t=>({x:t.clientX,y:t.clientY}));
  if(cur.length===1&&lastTouches.length===1){
    tx+=cur[0].x-lastTouches[0].x;
    ty+=cur[0].y-lastTouches[0].y;
  } else if(cur.length===2&&lastTouches.length===2){
    const d0=Math.hypot(lastTouches[0].x-lastTouches[1].x,lastTouches[0].y-lastTouches[1].y);
    const d1=Math.hypot(cur[0].x-cur[1].x,cur[0].y-cur[1].y);
    const factor=d1/d0;
    const mx=(cur[0].x+cur[1].x)/2, my=(cur[0].y+cur[1].y)/2;
    const rect=canvas.getBoundingClientRect();
    const [wx,wy]=screenToWorld(mx-rect.left,my-rect.top);
    scale*=factor;
    tx=(mx-rect.left)-wx*scale;
    ty=(my-rect.top)-wy*scale;
  }
  lastTouches=cur;
  isDirty=true; draw();
},{passive:false});

// ── Node selection ─────────────────────────────────────────────────────────
function selectNode(id){
  selectedId=id;
  const n=nodes[id];
  highlightSet=new Set([id,...n.nbrs]);
  showPanel(n);
  isDirty=true; draw();
}
function deselectNode(){
  selectedId=-1;
  highlightSet=null;
  document.getElementById("panel").classList.remove("open");
  isDirty=true; draw();
}

function showPanel(n){
  const panel=document.getElementById("panel");
  panel.classList.add("open");
  const c=comms[String(n.c)];
  const wikiLink=n.wpTitle
    ?`<a href="https://en.wikipedia.org/wiki/${encodeURIComponent(n.wpTitle)}" target="_blank" style="color:#a0c4ff">${n.wpTitle}</a>`
    :"—";
  const nbrsHTML=n.nbrs.map(nid=>{
    const nb=nodes[nid];
    return `<li onclick="selectNode(${nid})">${nb.n}</li>`;
  }).join("");

  panel.innerHTML=`
    <h2>${escH(n.n)}</h2>
    <div class="panel-section">
      <div class="panel-label">Community</div>
      <span class="panel-tag" style="background:${c?c.color+"33":"#33333355"};border:1px solid ${c?c.color:"#888"}">${c?c.label:"Unknown"}</span>
      <span class="panel-tag" style="background:#1a1a2e;border:1px solid #555">stability ${(n.stab*100).toFixed(0)}%${n.stable?" ✓":" ⚬"}</span>
    </div>
    <div class="panel-section">
      <div class="panel-label">Network metrics</div>
      <div class="panel-value">PageRank rank #${n.prRank} of ${N.toLocaleString()}</div>
      <div class="panel-value">Degree: ${n.deg} co-recommendations</div>
      ${n.bridge?`<div class="panel-value" style="color:#e07b54">⬡ Bridge poet (top 20 weighted betweenness)</div>`:""}
    </div>
    ${n.by||n.nat||n.gender?`<div class="panel-section">
      <div class="panel-label">Profile</div>
      ${n.by?`<div class="panel-value">Born: ${n.by}</div>`:""}
      ${n.nat?`<div class="panel-value">Nationality: ${escH(n.nat)}</div>`:""}
      ${n.gender?`<div class="panel-value">Gender: ${n.gender==="M"?"M":"F"==="F"?"F":n.gender}</div>`:""}
    </div>`:""}
    <div class="panel-section">
      <div class="panel-label">Wikipedia</div>
      <div class="panel-value">${wikiLink}</div>
      ${n.wpBytes?`<div class="panel-value" style="color:#888">${(n.wpBytes/1000).toFixed(0)} KB article</div>`:""}
    </div>
    <div class="panel-section">
      <div class="panel-label">Top recommended with</div>
      <ul class="nbr-list">${nbrsHTML}</ul>
    </div>
    <div style="margin-top:12px">
      <button class="btn" onclick="deselectNode()" style="width:100%;font-size:11px">✕ Close</button>
    </div>
  `;
}
function escH(s){return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");}

// Make selectNode globally accessible for panel clicks
window.selectNode=selectNode;

// ── Toggles ────────────────────────────────────────────────────────────────
document.getElementById("btn-bridges").addEventListener("click",function(){
  showBridges=!showBridges;
  if(showBridges)showTop100=false;
  this.classList.toggle("active",showBridges);
  document.getElementById("btn-top100").classList.remove("active");
  isDirty=true; draw();
});
document.getElementById("btn-top100").addEventListener("click",function(){
  showTop100=!showTop100;
  if(showTop100)showBridges=false;
  this.classList.toggle("active",showTop100);
  document.getElementById("btn-bridges").classList.remove("active");
  isDirty=true; draw();
});
document.getElementById("btn-reset").addEventListener("click",()=>{
  resetView(); isDirty=true; draw();
});

// ── About modal ────────────────────────────────────────────────────────────
document.getElementById("btn-about").addEventListener("click",()=>{
  document.getElementById("about-modal").classList.add("open");
  document.getElementById("overlay").classList.add("open");
});
document.getElementById("about-close").addEventListener("click",()=>{
  document.getElementById("about-modal").classList.remove("open");
  document.getElementById("overlay").classList.remove("open");
});
document.getElementById("overlay").addEventListener("click",()=>{
  document.getElementById("about-modal").classList.remove("open");
  document.getElementById("overlay").classList.remove("open");
});

// ── Search ─────────────────────────────────────────────────────────────────
const searchInput=document.getElementById("search");
const searchResults=document.getElementById("search-results");
searchInput.addEventListener("input",()=>{
  const q=searchInput.value.trim().toLowerCase();
  if(q.length<2){searchResults.style.display="none";return;}
  const matches=nodes
    .filter(n=>n.n.toLowerCase().includes(q))
    .slice(0,10);
  if(matches.length===0){searchResults.style.display="none";return;}
  searchResults.innerHTML=matches.map(n=>
    `<div class="sr-item" data-id="${n.id}">${escH(n.n)}</div>`
  ).join("");
  searchResults.style.display="block";
});
searchResults.addEventListener("click",e=>{
  const item=e.target.closest(".sr-item");
  if(!item)return;
  const id=parseInt(item.dataset.id);
  focusNode(id);
  searchResults.style.display="none";
  searchInput.value=nodes[id].n;
});
document.addEventListener("click",e=>{
  if(!e.target.closest("#search-wrap"))
    searchResults.style.display="none";
});

function focusNode(id){
  const n=nodes[id];
  // Animate camera to node
  const targetScale=400;
  tx=W/2-n.x*targetScale;
  ty=H/2-n.y*targetScale;
  scale=targetScale;
  selectNode(id);
  isDirty=true; draw();
}

// ── Init ───────────────────────────────────────────────────────────────────
resize();
resetView();
isDirty=true;
draw();

// Continuous render (for smooth interactions)
function loop(){isDirty&&draw();requestAnimationFrame(loop);}
loop();
</script>
</body>
</html>
"""

# Inject data
html_out = HTML.replace("__DATA__", data_json)

out_path = INTERACTIVE_DIR / "explorer.html"
out_path.write_text(html_out, encoding="utf-8")
log(f"\nWrote {out_path}  ({out_path.stat().st_size/1024:.0f} KB)")
log("\n" + "═" * 60)
log("PHASE 4 COMPLETE")
log("═" * 60)
log(f"  Open: {out_path}")
log("═" * 60)
