import yaml


def load_config(env: str = "prod") -> dict | None:
    """
    Loads the configuration from the file specified for the environment.
    Args:
        env (str): The environment to load the config for. Defaults to 'prod'
    Returns:
        dict: A dictionary containing the configuration, or None if there was an error.
    Raises:
        RuntimeError: If there was an error loading the configuration file.
    """
    file_name = __get_filename(env)
    try:
        with open(file_name, "r", encoding="utf-8") as stream:
            return yaml.safe_load(stream)
        
    except FileNotFoundError:
        raise RuntimeError(f"Config file {file_name} not found")
    
    except PermissionError:
        raise RuntimeError(f"Permission denied to read config file {file_name}")
    
    except OSError as e:
        raise RuntimeError(f"Error reading config file {file_name}: {e}")
    
    except yaml.YAMLError as e:
        raise RuntimeError(f"Error parsing config file {file_name}: {e}")

def __get_filename(env: str) -> str:
    """
    Returns the appropriate file for the environment.
    Args:
        env (str): The environment to load the config for.
    Returns:
        str: The specific file name for the environment.
    """
    if env == "dev":
        return "config/config_dev.yaml"
    else:
        return "config/config.yaml"