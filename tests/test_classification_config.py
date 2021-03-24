from pathlib import Path
from typing import Dict, Any

import yaml
import pytest

classification_config_path = Path().cwd() / "configs" / "classification.yaml"


def test_existence():
    assert classification_config_path.exists()


@pytest.fixture
def classification_config():
    with classification_config_path.open('r') as file:
        return yaml.load(file.read(), yaml.FullLoader)


def test_all_vectors_unique(classification_config):
    vectors = []
    for classification, config in classification_config.items():
        if 'vector' in config:
            vectors.append(config['vector'])

    for vector in vectors:
        assert vectors.count(vector) == 1, f"{vector} appears more than once in classification config!"


def test_accumulated_segments(classification_config):
    for classification, config in classification_config.items():
        if "+" in classification:
            prefix = classification[:2]
            for segment_num in classification[2:].split('+'):
                assert f"{prefix}{segment_num}" in config.get('children', [])


def test_take_best_only_in_top_levels(classification_config):
    for classification, config in classification_config.items():
        assert config.get('take_best', False) == (classification in ["Trachea", "Bronchus"])


