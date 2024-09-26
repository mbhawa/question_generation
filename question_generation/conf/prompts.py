import json
import os
from pathlib import Path
from typing import Dict

import yaml


def load_yaml(path: Path) -> Dict:
    """
    Read the yaml file

    Args:
        path (pathlib.Path): yaml path

    Returns:
        Dict: the data loaded from the yaml file
    """
    try:
        with open(path, "r") as yaml_file:
            data = yaml_file.read()
            if data.strip():
                data_dict = yaml.load(data, Loader=yaml.SafeLoader)
                return data_dict
    except FileNotFoundError:
        raise "YAML File not in path"


def load_json(path: Path) -> Dict:
    """_summary_

    Args:
        path (Path): _description_

    Returns:
        Dict: _description_
    """
    try:
        with open(path, "r") as f:
            json_object = json.load(f)
        return json_object
    except FileNotFoundError:
        raise "JSON File not in the path"


current_directory = Path(__file__).parent

# Load the configs of prompt from the JSON File
prompts_config = load_json(os.path.join(current_directory, "prompts_config.json"))
output_format = prompts_config.get("output_format")

system_prompt_version = prompts_config.get("SystemMessageTemplateVersion")
human_prompt_version = prompts_config.get("HumanMessageTemplateVersion")


# Load the final prompt from the YAML file
yaml_contents = load_yaml(os.path.join(current_directory, "prompts.yaml"))

SYSTEM_MESSAGE_TEMPLATE = yaml_contents.get("SystemMessageTemplate").get(
    system_prompt_version
)
SYSTEM_MESSAGE = SYSTEM_MESSAGE_TEMPLATE.format(
    output_format=json.dumps(output_format),
)

HUMAN_MESSAGE_TEMPLATE = yaml_contents.get("HumanMessageTemplate").get(
    human_prompt_version
)
