"""Phase 2: Enrich poet nodes with Wikidata metadata.

Reconciliation strategy
-----------------------
1. wbsearchentities (REST) for name lookup — up to 5 candidates per poet.
2. Score candidates by description: "poet" terms score high, profession mismatches
   score negative. The description alone resolves ~85% of cases without extra calls.
3. SPARQL batch-query for properties once QIDs are confirmed.
4. Wikipedia Action API for article lengths in batches of 50.
5. All API responses are cached to disk; re-runs are free.

Usage
-----
    python src/phase2.py              # full run (6095 poets)
    python src/phase2.py --sample 300 # random sample for viability check
    python src/phase2.py --sample 300 --seed 42
"""

import argparse
import hashlib
import json
import logging
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import unquote

import networkx as nx
import pandas as pd

ROOT = Path(__file__).parent.parent
RAW_DIR = ROOT / "data" / "raw"
ENRICHED_DIR = ROOT / "data" / "enriched"
CACHE_DIR = ENRICHED_DIR / "cache"
GRAPHML_PATH = RAW_DIR / "poet_tips-20191025.graphml"

for d in [ENRICHED_DIR, CACHE_DIR / "search", CACHE_DIR / "sparql", CACHE_DIR / "wp"]:
    d.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s", stream=sys.stdout)
log = logging.getLogger(__name__)

try:
    import requests
except ImportError:
    sys.exit("requests not installed — run: pip install requests")

HEADERS = {
    "User-Agent": (
        "PoetTipsNetworkAnalysis/1.0 "
        "(academic research; contact: robert@peakepro.com)"
    )
}
WD_API = "https://www.wikidata.org/w/api.php"
SPARQL_URL = "https://query.wikidata.org/sparql"
WP_API = "https://en.wikipedia.org/w/api.php"


# ── Cache ──────────────────────────────────────────────────────────────────

def _ck(s: str) -> str:
    return hashlib.md5(s.encode()).hexdigest()

def _cache_get(subdir: str, key: str):
    p = CACHE_DIR / subdir / f"{key}.json"
    return json.loads(p.read_text()) if p.exists() else None

def _cache_set(subdir: str, key: str, data) -> None:
    (CACHE_DIR / subdir / f"{key}.json").write_text(json.dumps(data))


# ── Wikidata search ─────────────────────────────────────────────────────────

def _search(name: str) -> list[dict]:
    ck = _ck(name)
    hit = _cache_get("search", ck)
    if hit is not None:
        time.sleep(0.5)  # pace cache hits so they don't let real calls stack up
        return hit
    for attempt in range(4):
        try:
            r = requests.get(
                WD_API,
                params={
                    "action": "wbsearchentities",
                    "search": name,
                    "language": "en",
                    "limit": 5,
                    "format": "json",
                },
                headers=HEADERS,
                timeout=15,
            )
            if r.status_code == 429:
                wait = 10 * (2 ** attempt)
                log.warning(f"429 rate-limited on {name!r}; waiting {wait}s")
                time.sleep(wait)
                continue
            r.raise_for_status()
            results = r.json().get("search", [])
            _cache_set("search", ck, results)  # only cache real results
            time.sleep(5.0)                    # ~0.2 req/sec — well within Wikidata limits
            return results
        except Exception as e:
            log.debug(f"search attempt {attempt+1} failed {name!r}: {e}")
            time.sleep(2)
    return []  # not cached — will retry next run


def _score(candidate: dict, name: str) -> float:
    score = 0.0
    desc = candidate.get("description", "").lower()
    label = candidate.get("label", "").lower()
    name_lc = name.lower()

    # Label match
    if label == name_lc:
        score += 10.0
    elif name_lc in label or label in name_lc:
        score += 4.0

    # Strong positive: poet/poetry in description
    if any(t in desc for t in ["poet", "poetry", "lyric poet", "verse"]):
        score += 5.0
    # Weaker positive: author/writer/lyricist
    elif any(t in desc for t in ["author", "writer", "novelist", "playwright",
                                  "essayist", "lyricist", "rapper", "musician"]):
        score += 2.0

    # Mild positive: nationality/era context in description (suggests a person)
    if any(t in desc for t in ["american", "british", "canadian", "australian",
                                "irish", "scottish", "english", "french",
                                "born", "century"]):
        score += 0.5

    # Disqualifying professions
    if any(t in desc for t in ["politician", "footballer", "basketball player",
                                "baseball player", "tennis player", "swimmer",
                                "mathematician", "physicist", "chemist",
                                "painter", "sculptor", "architect",
                                "film director", "actor", "actress",
                                "businessperson", "entrepreneur",
                                "military officer", "general", "admiral"]):
        score -= 8.0

    return score


def match_poet(name: str) -> dict:
    candidates = _search(name)
    if not candidates:
        return {"qid": None, "status": "no_results"}

    scored = sorted(
        [(_score(c, name), c) for c in candidates],
        key=lambda x: x[0],
        reverse=True,
    )
    best_score, best = scored[0]
    second_score = scored[1][0] if len(scored) > 1 else -999.0

    if best_score < 3.0:
        return {
            "qid": None,
            "status": "low_confidence",
            "candidates": [(s, c.get("id"), c.get("description", "")) for s, c in scored[:3]],
        }

    ambiguous = second_score > 0.0 and (best_score - second_score) < 2.5
    return {
        "qid": best["id"],
        "wd_label": best.get("label", ""),
        "wd_description": best.get("description", ""),
        "match_score": round(best_score, 1),
        "ambiguous": ambiguous,
        "status": "ambiguous" if ambiguous else "matched",
    }


# ── SPARQL enrichment ───────────────────────────────────────────────────────

_SPARQL_TMPL = """\
SELECT ?item
       (YEAR(?dob) AS ?birth_year)
       (YEAR(?dod) AS ?death_year)
       ?genderLabel
       ?citizenshipLabel
       ?movementLabel
       ?languageLabel
       ?wp_title
WHERE {{
  VALUES ?item {{ {qids} }}
  OPTIONAL {{ ?item wdt:P569 ?dob }}
  OPTIONAL {{ ?item wdt:P570 ?dod }}
  OPTIONAL {{ ?item wdt:P21 ?gender }}
  OPTIONAL {{ ?item wdt:P27 ?citizenship }}
  OPTIONAL {{ ?item wdt:P135 ?movement }}
  OPTIONAL {{ ?item wdt:P6886 ?language }}
  OPTIONAL {{
    ?enwiki schema:about ?item ;
            schema:inLanguage "en" ;
            schema:isPartOf <https://en.wikipedia.org/> .
    BIND(REPLACE(STR(?enwiki), "https://en.wikipedia.org/wiki/", "") AS ?wp_title)
  }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" }}
}}
"""


def _sparql_batch(qids: list[str]) -> dict[str, dict]:
    """Return a dict mapping QID → aggregated property dict."""
    ck = _ck("|".join(sorted(qids)))
    hit = _cache_get("sparql", ck)
    if hit is not None:
        return hit

    qid_str = " ".join(f"wd:{q}" for q in qids)
    query = _SPARQL_TMPL.format(qids=qid_str)

    for attempt in range(3):
        try:
            r = requests.get(
                SPARQL_URL,
                params={"query": query, "format": "json"},
                headers={**HEADERS, "Accept": "application/sparql-results+json"},
                timeout=60,
            )
            if r.status_code == 429:
                wait = 15 * (2 ** attempt)
                log.warning(f"SPARQL 429; waiting {wait}s")
                time.sleep(wait)
                continue
            r.raise_for_status()
            bindings = r.json()["results"]["bindings"]
            break
        except Exception as e:
            log.warning(f"SPARQL attempt {attempt+1} failed: {e}")
            bindings = []
            time.sleep(5)

    # Aggregate multi-valued properties across rows per QID
    agg: dict[str, dict] = {}
    for b in bindings:
        qid = b["item"]["value"].rsplit("/", 1)[-1]
        if qid not in agg:
            agg[qid] = {
                "qid": qid,
                "birth_year": b.get("birth_year", {}).get("value"),
                "death_year": b.get("death_year", {}).get("value"),
                "genderLabel": b.get("genderLabel", {}).get("value"),
                "wp_title": b.get("wp_title", {}).get("value"),
                "citizenships": set(),
                "movements": set(),
                "languages": set(),
            }
        for multi, key in [("citizenships", "citizenshipLabel"),
                            ("movements", "movementLabel"),
                            ("languages", "languageLabel")]:
            val = b.get(key, {}).get("value")
            if val:
                agg[qid][multi].add(val)

    # Convert sets to "|"-joined strings for consistent output
    result = {}
    for qid, row in agg.items():
        result[qid] = {
            **{k: v for k, v in row.items() if k not in ("citizenships", "movements", "languages")},
            "citizenships": "|".join(sorted(row["citizenships"])),
            "movements": "|".join(sorted(row["movements"])),
            "languages": "|".join(sorted(row["languages"])),
        }

    _cache_set("sparql", ck, result)
    time.sleep(1.2)
    return result


# ── Wikipedia article lengths ───────────────────────────────────────────────

def _wp_lengths(titles: list[str]) -> dict[str, int]:
    if not titles:
        return {}
    decoded = [unquote(t).replace("_", " ") for t in titles]
    ck = _ck("|".join(sorted(decoded)))
    hit = _cache_get("wp", ck)
    if hit is not None:
        return hit

    try:
        r = requests.get(
            WP_API,
            params={
                "action": "query",
                "titles": "|".join(decoded[:50]),
                "prop": "info",
                "format": "json",
            },
            headers=HEADERS,
            timeout=30,
        )
        r.raise_for_status()
        pages = r.json()["query"]["pages"]
        result = {
            p["title"]: p.get("length", 0)
            for p in pages.values()
            if "missing" not in p
        }
        _cache_set("wp", ck, result)
        time.sleep(0.5)
        return result
    except Exception as e:
        log.warning(f"Wikipedia API failed: {e}")
        return {}


# ── Main ────────────────────────────────────────────────────────────────────

def run(names: list[str]) -> pd.DataFrame:
    total = len(names)
    checkpoint_path = ENRICHED_DIR / "checkpoint_search.json"

    # Resume from checkpoint if present — skip names already resolved
    import json as _json
    matches: dict[str, dict] = {}
    if checkpoint_path.exists():
        matches = _json.loads(checkpoint_path.read_text())
        skipped = sum(1 for n in names if n in matches)
        if skipped:
            log.info(f"Resuming from checkpoint: {skipped}/{total} already resolved, "
                     f"{total - skipped} remaining")
    names_todo = [n for n in names if n not in matches]

    log.info(f"Matching {len(names_todo)} poet names against Wikidata …")

    done = 0
    cache_hits = 0

    def _do(name):
        cached_before = _cache_get("search", _ck(name)) is not None
        result = match_poet(name)
        return name, result, cached_before

    with ThreadPoolExecutor(max_workers=1) as pool:
        futures = {pool.submit(_do, n): n for n in names_todo}
        for fut in as_completed(futures):
            name, result, was_cached = fut.result()
            matches[name] = result
            done += 1
            if was_cached:
                cache_hits += 1
            if done % 50 == 0 or done == len(names_todo):
                matched_so_far = sum(1 for v in matches.values() if v.get("qid"))
                pct = matched_so_far / len(matches) * 100
                log.info(f"  {done}/{len(names_todo)} new  ({len(matches)} total)  "
                         f"matched {matched_so_far} ({pct:.1f}%)  "
                         f"cache hits {cache_hits}/{done}")
            # Persist checkpoint every 200 new entries so progress survives interruption
            if done % 200 == 0:
                checkpoint_path.write_text(_json.dumps(matches, ensure_ascii=False))

    # Final checkpoint save
    checkpoint_path.write_text(_json.dumps(matches, ensure_ascii=False))
    log.info(f"Search checkpoint saved ({len(matches)} entries)")

    matched_names = [n for n, v in matches.items() if v.get("qid")]
    qid_map = {v["qid"]: n for n, v in matches.items() if v.get("qid")}
    qids = list(qid_map.keys())

    log.info(f"\nSearch phase done. {len(matched_names)}/{total} matched "
             f"({len(matched_names)/total*100:.1f}%)")

    # ── SPARQL enrichment ──────────────────────────────────────────────────
    log.info(f"Fetching Wikidata properties for {len(qids)} QIDs (batches of 50) …")
    sparql_by_qid: dict[str, dict] = {}
    BATCH = 50
    for i in range(0, len(qids), BATCH):
        batch = qids[i : i + BATCH]
        sparql_by_qid.update(_sparql_batch(batch))
        if (i // BATCH + 1) % 5 == 0:
            log.info(f"  SPARQL {min(i+BATCH, len(qids))}/{len(qids)}")

    log.info(f"SPARQL returned data for {len(sparql_by_qid)} QIDs")

    # ── Wikipedia article lengths ──────────────────────────────────────────
    wp_titles = [
        r["wp_title"] for r in sparql_by_qid.values() if r.get("wp_title")
    ]
    log.info(f"Fetching Wikipedia article lengths for {len(wp_titles)} articles …")
    wp_len_map: dict[str, int] = {}
    for i in range(0, len(wp_titles), 50):
        wp_len_map.update(_wp_lengths(wp_titles[i : i + 50]))

    log.info(f"Wikipedia lengths retrieved for {len(wp_len_map)} articles")

    # ── Assemble output dataframe ──────────────────────────────────────────
    rows = []
    for name in names:
        m = matches[name]
        qid = m.get("qid")
        row: dict = {
            "name": name,
            "qid": qid,
            "match_status": m.get("status", "unmatched"),
            "match_score": m.get("match_score"),
            "wd_label": m.get("wd_label"),
            "wd_description": m.get("wd_description"),
            "ambiguous": m.get("ambiguous", False),
        }

        if qid and qid in sparql_by_qid:
            s = sparql_by_qid[qid]
            row["birth_year"] = s.get("birth_year")
            row["death_year"] = s.get("death_year")
            row["wd_gender"] = s.get("genderLabel")
            row["citizenships"] = s.get("citizenships") or ""
            row["movements"] = s.get("movements") or ""
            row["languages"] = s.get("languages") or ""
            wp_t = s.get("wp_title")
            row["wp_title"] = unquote(wp_t).replace("_", " ") if wp_t else None
            if row["wp_title"] and row["wp_title"] in wp_len_map:
                row["wp_article_bytes"] = wp_len_map[row["wp_title"]]
            elif row["wp_title"]:
                # Title casing mismatch — try a loose lookup
                for k, v in wp_len_map.items():
                    if k.lower() == row["wp_title"].lower():
                        row["wp_article_bytes"] = v
                        break
                else:
                    row["wp_article_bytes"] = None
            else:
                row["wp_article_bytes"] = None
        else:
            for f in ["birth_year", "death_year", "wd_gender", "citizenships",
                      "movements", "languages", "wp_title", "wp_article_bytes"]:
                row[f] = None

        rows.append(row)

    df = pd.DataFrame(rows)

    # ── Unmatched log ──────────────────────────────────────────────────────
    unmatched = df[df["qid"].isna()][["name", "match_status"]].copy()
    unmatched.to_csv(ENRICHED_DIR / "unmatched.csv", index=False)

    return df


def summarise(df: pd.DataFrame) -> None:
    n = len(df)
    matched = df["qid"].notna().sum()
    ambig = (df["match_status"] == "ambiguous").sum()
    no_results = (df["match_status"] == "no_results").sum()
    low_conf = (df["match_status"] == "low_confidence").sum()

    has_birth = df["birth_year"].notna().sum()
    has_movement = (df["movements"].fillna("") != "").sum()
    has_wp = df["wp_article_bytes"].notna().sum()
    has_lang = (df["languages"].fillna("") != "").sum()

    print("\n" + "═" * 60)
    print("PHASE 2 SUMMARY")
    print("═" * 60)
    print(f"  Poets queried          : {n:>6}")
    print(f"  Matched                : {matched:>6}  ({matched/n*100:.1f}%)")
    print(f"    of which ambiguous   : {ambig:>6}")
    print(f"  No Wikidata results    : {no_results:>6}  ({no_results/n*100:.1f}%)")
    print(f"  Low-confidence         : {low_conf:>6}  ({low_conf/n*100:.1f}%)")
    print()
    print("  Coverage among ALL poets queried:")
    print(f"    Birth year           : {has_birth:>6}  ({has_birth/n*100:.1f}%)")
    print(f"    Literary movements   : {has_movement:>6}  ({has_movement/n*100:.1f}%)")
    print(f"    Wikipedia article    : {has_wp:>6}  ({has_wp/n*100:.1f}%)")
    print(f"    Languages written    : {has_lang:>6}  ({has_lang/n*100:.1f}%)")

    if matched > 0:
        matched_df = df[df["qid"].notna()]
        birth_of_matched = matched_df["birth_year"].notna().sum()
        move_of_matched = (matched_df["movements"].fillna("") != "").sum()
        wp_of_matched = matched_df["wp_article_bytes"].notna().sum()
        print()
        print("  Coverage among MATCHED poets only:")
        print(f"    Birth year           : {birth_of_matched:>6}  ({birth_of_matched/matched*100:.1f}%)")
        print(f"    Literary movements   : {move_of_matched:>6}  ({move_of_matched/matched*100:.1f}%)")
        print(f"    Wikipedia article    : {wp_of_matched:>6}  ({wp_of_matched/matched*100:.1f}%)")

    print()
    print("  Top 10 movements (across all matched poets):")
    movements = (
        df["movements"]
        .dropna()
        .str.split("|")
        .explode()
        .str.strip()
        .loc[lambda s: s != ""]
        .value_counts()
        .head(10)
    )
    for mv, cnt in movements.items():
        print(f"    {cnt:>4}  {mv}")

    print()
    print("  Sample matched poets:")
    sample = df[df["qid"].notna()].head(10)[
        ["name", "wd_description", "birth_year", "movements", "wp_article_bytes"]
    ]
    for _, r in sample.iterrows():
        mv = (r["movements"] or "")[:40]
        print(f"    {r['name'][:30]:<30}  {str(r['birth_year'] or ''):<6}  "
              f"wp={r['wp_article_bytes'] or '—':>7}  {mv}")

    print("═" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=int, default=0,
                        help="Run on N random poets (0 = full dataset)")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    G = nx.read_graphml(GRAPHML_PATH)
    all_names = list(G.nodes())

    if args.sample:
        rng = random.Random(args.seed)
        # Stratified: mix high-degree and low-degree nodes
        degrees = dict(G.degree())
        sorted_names = sorted(all_names, key=lambda n: degrees[n], reverse=True)
        top = sorted_names[: args.sample // 3]
        rest = sorted_names[args.sample // 3 :]
        rng.shuffle(rest)
        names = top + rest[: args.sample - len(top)]
        log.info(f"Sample: {len(names)} poets (top-{len(top)} by degree + random)")
    else:
        names = all_names

    df = run(names)

    is_sample = bool(args.sample)
    if not is_sample:
        out_path = ENRICHED_DIR / "poets_wikidata.parquet"
        df.to_parquet(out_path, index=False)
        log.info(f"Saved → {out_path}")

        unmatched_path = ENRICHED_DIR / "unmatched.csv"
        log.info(f"Unmatched log → {unmatched_path}")

    summarise(df)

    if is_sample:
        print(f"\n(Sample run — {len(names)} poets. "
              "Run without --sample to process all 6,095 and save parquet.)")
