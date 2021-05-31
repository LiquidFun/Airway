import subprocess
import sys
from pathlib import Path
from typing import List

import networkx as nx

from airway.classification.split_classification import is_valid_tree
from airway.util.config_parsers import parse_classification_config
from airway.util.util import get_data_paths_from_args, generate_pdf_report, get_ignored_patients

file_name = "data_quality_evaluation"


def get_input():
    output_data_path, tree_input_path, render_path = get_data_paths_from_args(inputs=2)
    classification_config = parse_classification_config()
    trees: List[nx.Graph] = []
    for tree_path in Path(tree_input_path).glob("*/tree.graphml"):
        trees.append(nx.read_graphml(tree_path))
    return output_data_path, trees, classification_config, render_path


def main():
    output_path, trees, classification_config, render_path = get_input()
    ignored_patients = get_ignored_patients()
    if sys.argv[4].lower() == "true":
        subprocess.Popen(["xdg-open", f"{output_path / f'{file_name}.pdf'}"])
        sys.exit()

    clustering_end_nodes = [
        c for c, k in classification_config.items() if "clustering_endnode" in k and k["clustering_endnode"]
    ]
    content = ["# Airway Auto-Generated Data Quality Evaluation\n"]
    for index, tree in enumerate(trees, 1):
        patient = str(tree.graph["patient"])
        successors = dict(nx.bfs_successors(tree, "0"))
        img_path = Path(render_path) / patient / "bronchus0.png"
        content.append(f"![{patient}]({img_path})\n\n")
        formatting_if_ignored = "(ignored due to bad data)" if patient in ignored_patients else ""
        content.append(f"#### {index}. Patient {patient} {formatting_if_ignored}\n\n")

        total_cost = sum(tree.nodes[node_id]["cost"] for node_id in tree.nodes)
        content.append(f"Total cost: {total_cost:.2f}\n\n")

        content.append(f"Total nodes: {len(tree.nodes)}\n\n")

        is_valid = is_valid_tree(tree, classification_config, successors)
        content.append(f"Tree is **{'valid' if is_valid else 'invalid'}** (follows given rule-set)\n\n")

        classifications_in_tree = {tree.nodes[node_id]["split_classification"] for node_id in tree.nodes}
        missing_end_node = set(clustering_end_nodes) - classifications_in_tree
        content.append(f"Missing segments: {', '.join(missing_end_node)}\n\n")

        content.append("\n")

    generate_pdf_report(output_path, file_name, "".join(content))


if __name__ == "__main__":
    main()
