from collections import defaultdict
from pathlib import Path
from typing import Tuple, List, Dict

import markdown
import networkx as nx
import yaml
from weasyprint import HTML

from util.util import get_data_paths_from_args


# classify_for = ["Trachea"]
# classify_for = ["LLowerLobe", "LUpperLobe", "RMiddleLobe", "RUpperLobe", "RLowerLobe"]
classify_for = ["LLowerLobe", "LUpperLobe"]


def get_input():
    output_data_path, tree_input_path, render_path = get_data_paths_from_args(inputs=2)
    config_path = Path("configs") / "classification.yaml"
    with open(config_path) as config_file:
        classification_config = yaml.load(config_file, yaml.FullLoader)
        for cc_dict in classification_config.values():
            if "clustering_endnode" not in cc_dict:
                cc_dict["clustering_endnode"] = False
    trees: List[nx.Graph] = []
    for tree_path in Path(tree_input_path).glob('*/tree.graphml'):
        trees.append(nx.read_graphml(tree_path))
    return output_data_path, trees, classification_config, render_path


def main():
    output_path, trees, classification_config, render_path = get_input()
    print(render_path)
    clustering = {c: defaultdict(lambda: []) for c in classify_for}
    with open(Path(output_path) / "clustering_report.md", 'w') as file:
        file.write("# Airway Auto-Generated Clustering Report\n")
        for tree in trees:
            successors = dict(nx.bfs_successors(tree, '0'))
            clusters = cluster(tree, successors, classification_config)
            # patient = tree.graph['patient']
            # print(patient)
            # print(cluster_name)
            for start_node, curr_cluster in clusters.items():
                clustering[start_node][curr_cluster].append(tree)
        for start_node, curr_clustering in clustering.items():
            file.write(f"## Clustering of {start_node}\n")
            for key, trees in sorted(curr_clustering.items(), key=lambda k: -len(k[1])):
                for tree in trees:
                    patient = tree.graph['patient']
                    img_path = Path(render_path) / str(patient) / 'left_upper_lobe0.png'
                    file.write(f"![{patient}]({img_path})\n")
                    file.write(f"### ^ Example patient {patient}\n")
                    break
                file.write(f"### {len(trees)} patients with this structure:\n")
                file.write(key + "\n")

    with open(Path(output_path) / "clustering_report.md", 'r') as file:
        md = markdown.markdown(file.read())
        md = md.replace('<img', '<img width="600"')
        # for cc_key, cc in classification_config.items():
        #     if "color" in cc:
        #         col = cc["color"]
        #         md = md.replace(cc_key, f'<p style="color:{col}>"{cc_key}</p>')
        with open(Path(output_path) / "clustering_report.html", "w", encoding="utf-8", errors="xmlcharrefreplace") as html_file:
            html_file.write(md)

    a = HTML(Path(output_path) / "clustering_report.html")
    a.write_pdf(Path(output_path) / "clustering_report.pdf", presentational_hints=True)


def cluster(tree, successors, classification_config):
    cluster_start_nodes = [n for n in tree.nodes if tree.nodes[n]["split_classification"] in classify_for]

    def rec_cluster(curr_id, tabs=1):
        nonlocal cluster_name
        try:
            classification = tree.nodes[curr_id]["split_classification"]
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
