"""Group snakemake's --rulegraph into labelled phase clusters for a readable DAG.

Reads the DOT that `snakemake --rulegraph` writes on stdin and re-emits it with the rule
nodes wrapped in subgraph clusters (ingest -> per-scan analysis -> combine). FAITHFUL: it
only reshuffles snakemake's own nodes/edges -- the rule set and dependency edges are whatever
snakemake emits, so the picture cannot drift from the real Snakefile. A rule not in PHASES
still renders, just unclustered.

Readability tweaks (cosmetic only):
  * `outputorder=edgesfirst` + white-filled rule nodes -> edges run BEHIND the nodes;
  * each phase label is a FILLED header node (not the cluster's own label), so it is drawn
    on top of the edges -- arrows pass behind the title text;
  * the `all` meta-target is dropped (pure fan-in clutter, no information).

Invoked by `pixi run dag`:  snakemake --rulegraph | python workflow/cluster_dag.py | dot ...
"""
import re
import sys

# (key, header label, rules in this phase) -- ordered top to bottom
PHASES = [
    ("ingest",    "1 · fetch inputs",       ["download"]),
    ("perscan",   "2 · per-scan analysis",  ["parse_slha", "merge_exclusion", "analyze", "sensitivity", "plots"]),
    ("aggregate", "3 · combine all scans",  ["report", "validate"]),
]
FILL = {"ingest": "#e8f1fb", "perscan": "#e8f7ea", "aggregate": "#fce8ee"}
DROP = {"all"}                       # meta-target: drop it and every edge touching it

node_re = re.compile(r'^\s*(\d+)\[label = "([^"]+)"')
header, edges, node_line, id_of = [], [], {}, {}
for ln in sys.stdin.read().splitlines():
    m = node_re.match(ln)
    if m:
        nid, name = m.group(1), m.group(2)
        id_of[name] = nid
        if name not in DROP:
            # white fill so edges (drawn first) run behind the node body
            node_line[name] = ln.strip().replace('style="rounded"', 'style="rounded,filled", fillcolor="white"')
    elif "->" in ln:
        edges.append(ln.rstrip())
    elif ln.strip() != "}":
        header.append(ln)

drop_ids = {id_of[n] for n in DROP if n in id_of}
edges = [e for e in edges if not (set(re.findall(r"\d+", e)) & drop_ids)]

out = list(header)
out.insert(1, "  compound=true; newrank=true; rankdir=TB; outputorder=edgesfirst; "
              "nodesep=0.35; ranksep=0.55;")
rank_edges, clustered = [], set()
for key, label, rules in PHASES:
    present = [r for r in rules if r in node_line]
    if not present:
        continue
    hdr = f"_hdr_{key}"
    out.append(f"  subgraph cluster_{key} {{")
    # fill-only region (no border): a border is drawn as background, so every edge/node
    # crossing it punches a visible gap. The fill + header title delineate the phase instead.
    out.append(f'    style="rounded,filled"; color="{FILL[key]}"; pencolor="{FILL[key]}"; '
               f'penwidth=0; fillcolor="{FILL[key]}"; margin=14;')
    # filled header node = the phase title, drawn on top of the edges
    out.append(f'    {hdr} [label="{label}", shape=box, style=filled, fillcolor="{FILL[key]}", '
               f'color="{FILL[key]}", fontname="Helvetica-Bold", fontsize=12, margin="0.18,0.04"];')
    for r in present:
        out.append("    " + node_line[r])
        clustered.add(r)
    out.append("  }")
    rank_edges.append(f"  {hdr} -> {id_of[present[0]]} [style=invis];")   # pin title to the top

for r, ln in node_line.items():        # any future rule not assigned to a phase
    if r not in clustered:
        out.append("  " + ln)
out += rank_edges
out += edges
out.append("}")
print("\n".join(out))
