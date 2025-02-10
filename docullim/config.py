import json
import os

DEFAULT_CONFIG = {
    "model": "gpt-4",
    "max_concurrency": 1,
    "prompts": {
        "default": "Generate short and simple documentation explaing the code and include sample usage. don't add the word documentation in the begining and also don't explain the example usage."
    },
}


def load_config(config_path=None):
    """
    Load configuration from a JSON file and merge it with the default configuration.

    If no config file is provided (i.e. config_path is None), the function will look
    for a file named 'docullim.json' in the current working directory.
    If the file exists, it is loaded; otherwise, the default configuration is used.
    """
    # If no explicit config path is provided, try to use the default "docullim.json"
    if config_path is None:
        default_config_path = os.path.join(os.getcwd(), "docullim.json")
        if os.path.exists(default_config_path):
            config_path = default_config_path

    # Start with the default configuration.
    config = DEFAULT_CONFIG.copy()

    # If a configuration file path was found or provided, try to load and merge it.
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                user_config = json.load(f)
            config.update(user_config)
        except Exception as e:
            print(f"Error loading config file {config_path}: {e}")
    else:
        if config_path:
            print(
                f"Configuration file {config_path} not found. Using default configuration."
            )

    return config
