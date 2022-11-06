from pathlib import Path

# Root package path
PACKAGE_PATH = Path(__file__).parents[2]

# Configs path
CONFIGS_PATH = PACKAGE_PATH / "airway" / "configs"
LOGS_PATH = PACKAGE_PATH / "logs"

# Actual files
STAGE_CONFIGS_PATH = CONFIGS_PATH / "stage_configs.yaml"
CLASSIFICATION_CONFIG_PATH = CONFIGS_PATH / "classification.yaml"
ARRAY_ENCODING_PATH = CONFIGS_PATH / "array_encoding.yaml"
LOG_LN_PATH = PACKAGE_PATH / "log"

# Stages
ROOT_STAGE = "raw_airway"
