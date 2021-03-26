import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import List

import networkx as nx
import yaml

from airway.util.util import get_data_paths_from_args, generate_pdf_report, get_ignored_patients

# classify_for = ["Trachea"]
classify_for = ["LLowerLobe", "LUpperLobe", "RMiddleLobe", "RUpperLobe", "RLowerLobe"]
# classify_for = ["LLowerLobe", "LUpperLobe"]


def get_input():
    output_data_path, tree_input_path, render_path = get_data_paths_from_args(inputs=2)
    config_path = Path("configs") / "classification.yaml"
    with open(config_path) as config_file:
        classification_config = yaml.load(config_file, yaml.FullLoader)
        for cc_dict in classification_config.values():
            if "clustering_endnode" not in cc_dict:
                cc_dict["clustering_endnode"] = False
    trees: List[nx.Graph] = []
    ignored_patients = get_ignored_patients()
    for tree_path in Path(tree_input_path).glob('*/tree.graphml'):
        if tree_path.parent.name not in ignored_patients:
            trees.append(nx.read_graphml(tree_path))
    return output_data_path, trees, classification_config, render_path


def main():
    output_path, trees, classification_config, render_path = get_input()
    print(render_path)
    print(sys.argv)
    if sys.argv[4].lower() == "true":
        subprocess.Popen(["xdg-open", f"{output_path / 'clustering_report.pdf'}"])
        sys.exit()
    clustering = {c: defaultdict(lambda: []) for c in classify_for}
    content = ["# Airway Auto-Generated Clustering Report\n"]
    for tree in trees:
        successors = dict(nx.bfs_successors(tree, '0'))
        clusters = cluster(tree, successors, classification_config)
        for start_node, curr_cluster in clusters.items():
            clustering[start_node][curr_cluster].append(tree)
    for start_node, curr_clustering in clustering.items():
        content.append(f"## Clustering of {start_node}\n")
        for key, trees_in_cluster in sorted(curr_clustering.items(), key=lambda k: -len(k[1])):
            for tree in trees_in_cluster:
                patient = tree.graph['patient']
                img_path = Path(render_path) / str(patient) / 'bronchus0.png'
                content.append(f"![{patient}]({img_path})\n")
                content.append(f"### ^ Example patient {patient}\n")
                break
            percent = f"{len(trees_in_cluster)/len(trees)*100:.1f}%"
            content.append(f"### {len(trees_in_cluster)} ({percent}) patients with this structure:\n")
            content.append(key + "\n")
    generate_pdf_report(output_path, "clustering_report", "".join(content))


def cluster(tree, successors, classification_config):
    cluster_start_nodes = [n for n in tree.nodes if tree.nodes[n]["split_classification"] in classify_for]

    def rec_cluster(curr_id, tabs=1):
        nonlocal cluster_name
        try:
            classification = tree.nodes[curr_id]["split_classification"]
            if classification not in classification_config:
                return
            cluster_name += ('    ' * tabs) + classification + '\n'
            if classification_config[classification]['clustering_endnode']:
                return
        except KeyError:
            return
        classification_id_pairs = []
        for succ in successors.get(curr_id, []):
            classification_id_pairs.append((tree.nodes[succ]['split_classification'], succ))
        for _, child_id in sorted(classification_id_pairs):
            rec_cluster(child_id, tabs+1)

    cluster_names = {}
    for start_node in cluster_start_nodes:
        cluster_name = ""
        rec_cluster(start_node)
        cluster_names[tree.nodes[start_node]['split_classification']] = cluster_name
    return cluster_names


if __name__ == "__main__":

    main()
