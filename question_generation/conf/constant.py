import json
import os
from pathlib import Path
from typing import Dict


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
constant_config = load_json(os.path.join(current_directory, "constant.json"))


# print(constant_config.get("supported_media_format"))
