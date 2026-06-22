"""Group snakemake's --rulegraph into labelled phase clusters for a readable DAG.

Reads the DOT that `snakemake --rulegraph` writes on stdin and re-emits it with the rule
nodes wrapped in subgraph clusters (ingest -> per-scan pipeline -> per-scan branches ->
combine). FAITHFUL: it only reshuffles snakemake's own nodes and edges into clusters --
the rule set and the dependency edges are whatever snakemake emits, so the picture cannot
drift from the real Snakefile. A rule not listed in PHASES still renders, just uncluttered.

Invoked by `pixi run dag`:  snakemake --rulegraph | python workflow/cluster_dag.py | dot ...
"""
import re
import sys

# (key, cluster label, rules in this phase) -- ordered top to bottom.
# Three phases only: the per-scan work (the linear parse->classify spine AND the holes/
# sensitivity/plots branches that sprout off it) is ONE conceptual block -- splitting the
# spine from its branches is a purely topological distinction that just makes edges cross.
PHASES = [
    ("ingest",    "1 · fetch inputs",                 ["download"]),
    ("perscan",   "2 · per-scan analysis (per scan)",  ["parse_slha", "merge_exclusion", "project",
                                                        "classify", "holes", "sensitivity", "plots"]),
    ("aggregate", "3 · combine all scans",            ["report", "validate", "all"]),
]
FILL = {"ingest": "#eef6ff", "perscan": "#eefcf0", "aggregate": "#fdeef2"}

node_re = re.compile(r'^\s*(\d+)\[label = "([^"]+)"')
header, edges, node_line = [], [], {}
for ln in sys.stdin.read().splitlines():
    m = node_re.match(ln)
    if m:
        node_line[m.group(2)] = ln.strip()
    elif "->" in ln:
        edges.append(ln.rstrip())
    elif ln.strip() != "}":
        header.append(ln)

out = list(header)
out.insert(1, "  compound=true; newrank=true; rankdir=TB;")
clustered = set()
for key, label, rules in PHASES:
    present = [r for r in rules if r in node_line]
    if not present:
        continue
    out.append(f"  subgraph cluster_{key} {{")
    out.append(f'    label="{label}"; labelloc=t; fontname=sans; fontsize=11; '
               f'style="rounded,filled"; color="#bbbbbb"; fillcolor="{FILL[key]}";')
    for r in present:
        out.append("    " + node_line[r])
        clustered.add(r)
    out.append("  }")
for r, ln in node_line.items():          # any future rule not assigned to a phase
    if r not in clustered:
        out.append("  " + ln)
out += edges
out.append("}")
print("\n".join(out))
