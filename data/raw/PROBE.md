# PROBE.md — Poet Tips Dataset

## Graph basics

| Property | Value |
|----------|-------|
| Node count | 6,095 |
| Edge count | 20,526 |
| Directed | False |
| Multigraph | False |

## Node attributes

**deceased** — 17.9% coverage  ⚠ <50% coverage
  range [0, 1]  median 0  mean 0.4386

**gender** — 99.4% coverage
  3 unique values; top 10:
      3197  M
      2852  F
        10  NB

**hits** — 100.0% coverage
  range [11, 1.78e+04]  median 893  mean 904.9

**url** — 100.0% coverage
  6095 unique values; top 10:
         1  http://poet.tips/poet/andr%C3%A9_3000
         1  http://poet.tips/poet/big_boi
         1  http://poet.tips/poet/frank_ocean
         1  http://poet.tips/poet/chris_abani
         1  http://poet.tips/poet/kobena_eyi_acquah
         1  http://poet.tips/poet/d.m._aderibigbe
         1  http://poet.tips/poet/patience_agbabi
         1  http://poet.tips/poet/kofi_awoonor
         1  http://poet.tips/poet/david_campos
         1  http://poet.tips/poet/kwame_dawes

**weight** — 100.0% coverage
  range [0.00011, 2.91]  median 0.01212  mean 0.08966

## Edge attributes

**weight** — 100.0% coverage
  range [1, 44]  median 1  mean 2.176

## Five sample nodes (full attributes)

```
  id='André 3000'  attrs={'gender': 'M', 'deceased': '', 'weight': 0.000151597, 'hits': 861, 'url': 'http://poet.tips/poet/andr%C3%A9_3000'}
  id='Big Boi'  attrs={'gender': 'M', 'deceased': '', 'weight': 0.0109999, 'hits': 826, 'url': 'http://poet.tips/poet/big_boi'}
  id='Frank Ocean'  attrs={'gender': 'M', 'deceased': '', 'weight': 0.0207988, 'hits': 902, 'url': 'http://poet.tips/poet/frank_ocean'}
  id='Chris Abani'  attrs={'gender': 'M', 'deceased': 0, 'weight': 0.306731, 'hits': 1710, 'url': 'http://poet.tips/poet/chris_abani'}
  id='Kobena Eyi Acquah'  attrs={'gender': 'M', 'deceased': 0, 'weight': 0.000235438, 'hits': 902, 'url': 'http://poet.tips/poet/kobena_eyi_acquah'}
```

## Ten sample edges (full attributes)

```
  'André 3000' → 'Big Boi'  attrs={'weight': 1.0}
  'André 3000' → 'Frank Ocean'  attrs={'weight': 1.0}
  'Frank Ocean' → 'Tyler, The Creator'  attrs={'weight': 1.0}
  'Frank Ocean' → 'Jay Z'  attrs={'weight': 1.0}
  'Frank Ocean' → 'Kanye West'  attrs={'weight': 1.0}
  'Chris Abani' → 'Kobena Eyi Acquah'  attrs={'weight': 1.0}
  'Chris Abani' → 'D.M. Aderibigbe'  attrs={'weight': 4.0}
  'Chris Abani' → 'Patience Agbabi'  attrs={'weight': 1.0}
  'Chris Abani' → 'Kofi Awoonor'  attrs={'weight': 1.0}
  'Chris Abani' → 'David Campos'  attrs={'weight': 2.0}
```

## Connected components

Component type: **connected**

Total component count: 157

Top 5 by size:

| Rank | Size |
|------|------|
| 1 | 5,841 |
| 2 | 5 |
| 3 | 5 |
| 4 | 5 |
| 5 | 4 |

## Degree distribution

| Stat | Value |
|------|-------|
| Min | 0 |
| Median | 3.0 |
| Mean | 6.74 |
| 95th percentile | 26.0 |
| Max | 135 |

Top 20 nodes by total degree:

| Node ID | Label | Degree |
|---------|-------|--------|
| `Amy Lemmon` |  | 135 |
| `Richard Siken` |  | 111 |
| `Anne Carson` |  | 101 |
| `Sharon Olds` |  | 93 |
| `John Ashbery` |  | 92 |
| `Frank O'Hara` |  | 89 |
| `Sylvia Plath` |  | 87 |
| `Elizabeth Bishop` |  | 87 |
| `Trace Peterson` |  | 86 |
| `Wallace Stevens` |  | 79 |
| `Anne Sexton` |  | 77 |
| `Melissa Studdard` |  | 73 |
| `Meg Johnson` |  | 70 |
| `Gerard Manley Hopkins` |  | 69 |
| `C.D. Wright` |  | 69 |
| `Cecilia Llompart` |  | 68 |
| `Alice Notley` |  | 65 |
| `Larry Levis` |  | 65 |
| `Catherine Daly` |  | 63 |
| `Dean Young` |  | 62 |

## Edge-weight distribution

| Stat | Value |
|------|-------|
| Min | 1 |
| Median | 1 |
| Mean | 2.176 |
| 95th percentile | 6 |
| Max | 44 |

## Data-quality issues

- Self-loops: **0**
- Isolates (degree-0 nodes): **78**
- Duplicate labels: **0** label(s) appear on more than one node
