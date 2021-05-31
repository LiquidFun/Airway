import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import List, Tuple
import re

import networkx as nx
import yaml

from airway.util.config_parsers import parse_classification_config
from airway.util.util import get_data_paths_from_args, generate_pdf_report, get_ignored_patients

classify_for = ["LLowerLobe", "LUpperLobe", "RMiddleLobe", "RUpperLobe", "RLowerLobe"]
latex_tables_for = ["LUpperLobe", "RUpperLobe"]
assert all(lobe in classify_for for lobe in latex_tables_for)


def get_input():
    output_data_path, tree_input_path, render_path = get_data_paths_from_args(inputs=2)
    classification_config = parse_classification_config()
    for cc_dict in classification_config.values():
        if "clustering_endnode" not in cc_dict:
            cc_dict["clustering_endnode"] = False
    trees: List[nx.Graph] = []
    ignored_patients = get_ignored_patients()
    for tree_path in Path(tree_input_path).glob("*/tree.graphml"):
        if tree_path.parent.name not in ignored_patients:
            trees.append(nx.read_graphml(tree_path))
    return output_data_path, trees, classification_config, render_path


def get_latex_table(cluster_trees: List[Tuple[str, List[nx.Graph]]], patient_count: int):
    table = ""

    class LatexBlock:
        def __init__(self, block_type: str, after_begin: str = ""):
            self.block_type = block_type
            self.after_begin = after_begin

        def __enter__(self):
            nonlocal table
            table += f"\\begin{{{self.block_type}}}{self.after_begin}\n"

        def __exit__(self, exc_type, exc_value, exc_traceback):
            nonlocal table
            table += f"\\end{{{self.block_type}}}\n"

    with LatexBlock("table", "[hbpt]"):
        table += "\\centering\n"
        formatted_key = "_".join(re.findall("[A-Z][a-z]*", cluster_trees[0][0].split("\n")[0].strip())).lower()
        formatted_key = ("left" if formatted_key[0] == "l" else "right") + formatted_key[1:]
        table += f"\\caption{{The three most common clusters for the \\textbf{{{formatted_key.replace('_', ' ')}}}.}}\n"
        table += f"\\label{{tab:{formatted_key}}}\n"
        with LatexBlock("tabular", f"{{{'|'.join(['c']*len(cluster_trees))}}}"):
            table += (
                " & ".join(
                    [f"{len(trees)} ({len(trees) / patient_count * 100:.1f}\\%) patients" for _, trees in cluster_trees]
                )
                + "\\\\\n"
                + "\\hline\n"
            )
            for index, (clustering, _) in enumerate(cluster_trees, 1):
                with LatexBlock("minipage", "[t]{1.65in}"):
                    with LatexBlock("verbatim"):
                        table += clustering
                table += "&\n" if index != len(cluster_trees) else "\\\\\n"
    return table


def main():
    output_path, trees, classification_config, render_path = get_input()
    print(render_path)
    print(sys.argv)
    if sys.argv[4].lower() == "true":
        subprocess.Popen(["xdg-open", f"{output_path / 'clustering_report.pdf'}"])
        sys.exit()
    clustering = {c: defaultdict(lambda: []) for c in classify_for}
    html_content = ["# Auto-Generated Clustering Report\n"]
    latex_content = []
    for index, tree in enumerate(trees, 1):
        successors = dict(nx.bfs_successors(tree, "0"))
        clusters = cluster(tree, successors, classification_config)
        print("===", index, tree.graph["patient"], "===")
        for c, k in clusters.items():
            if c == "LUpperLobe":
                print(k)
        print()
        for start_node, curr_cluster in clusters.items():
            clustering[start_node][curr_cluster].append(tree)
    for start_node, curr_clustering in clustering.items():
        html_content.append(f"## Clustering of {start_node}\n")
        sorted_curr_clustering = sorted(curr_clustering.items(), key=lambda k: -len(k[1]))
        if start_node in latex_tables_for:
            latex_content.append(get_latex_table(sorted_curr_clustering[:3], patient_count=len(trees)))
        for key, trees_in_cluster in sorted_curr_clustering:
            patient = trees_in_cluster[0].graph["patient"]
            img_path = Path(render_path) / str(patient) / "bronchus0.png"
            html_content.append(f"![{patient}]({img_path})\n")
            html_content.append(f"### ^ Example patient {patient}\n")
            percent = f"{len(trees_in_cluster)/len(trees)*100:.1f}%"
            html_content.append(f"### {len(trees_in_cluster)} ({percent}) patients with this structure:\n")
            html_content.append(key + "\n")
    generate_pdf_report(output_path, "clustering_report", "".join(html_content))

    with open(output_path / "clustering_tables.tex", "w") as file:
        for table in latex_content:
            file.write(table)


def cluster(tree, successors, classification_config):
    cluster_start_nodes = [n for n in tree.nodes if tree.nodes[n]["split_classification"] in classify_for]

    def rec_cluster(curr_id, tabs=1):
        nonlocal cluster_name
        try:
            classification = tree.nodes[curr_id]["split_classification"]
            if classification not in classification_config:
                return
            cluster_name += ("    " * tabs) + classification + "\n"
            if classification_config[classification]["clustering_endnode"]:
                return
        except KeyError:
            return
        classification_id_pairs = []
        for succ in successors.get(curr_id, []):
            classification_id_pairs.append((tree.nodes[succ]["split_classification"], succ))
        for _, child_id in sorted(classification_id_pairs):
            rec_cluster(child_id, tabs + 1)

    cluster_names = {}
    for start_node in cluster_start_nodes:
        cluster_name = ""
        rec_cluster(start_node)
        cluster_names[tree.nodes[start_node]["split_classification"]] = cluster_name
    return cluster_names


if __name__ == "__main__":

    main()
