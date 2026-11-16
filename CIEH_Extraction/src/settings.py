from pathlib import Path
import yaml

BASE_DIR = Path(__file__).resolve().parents[1]


def load_settings(path=None):
    path = Path(path or BASE_DIR / "config.yaml").resolve()
    with path.open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    columns = config["master"]["columns"]
    if not isinstance(columns, list) or not columns or not all(isinstance(c, str) and c.strip() for c in columns) or len(columns) != len(set(columns)):
        raise ValueError("master.columns must contain unique column names")
    definitions = config["master"].get("column_definitions", {})
    output = config["master"].get("output_columns", columns)
    if not isinstance(output, list) or not output or not all(isinstance(c, str) and c in columns for c in output) or len(output) != len(set(output)):
        raise ValueError("master.output_columns must be unique names from master.columns")
    if not isinstance(definitions, dict) or set(definitions) - set(columns):
        raise ValueError("column_definitions must describe only names in master.columns")
    for name, definition in definitions.items():
        if not isinstance(definition, dict):
            raise ValueError(f"Column definition for {name} must be a mapping")
        if "description" in definition and not isinstance(definition["description"], str):
            raise ValueError(f"Description for {name} must be text")
        for key in ("aliases", "allowed_values"):
            if key in definition and not isinstance(definition[key], list):
                raise ValueError(f"{name}.{key} must be a list")
    extraction = config.get("extraction", {})
    if not isinstance(extraction, dict):
        raise ValueError("extraction must be a mapping")
    for key in ("context", "record_definition"):
        if key in extraction and not isinstance(extraction[key], str):
            raise ValueError(f"extraction.{key} must be text")
    if "rules" in extraction and (not isinstance(extraction["rules"], list) or not all(isinstance(rule, str) for rule in extraction["rules"])):
        raise ValueError("extraction.rules must be a list of instructions")
    size = config["json"]["lines_per_chunk"]
    if type(size) is not int or size < 1:
        raise ValueError("json.lines_per_chunk must be a positive integer")
    overlap = config["json"].get("context_overlap_lines", 5)
    if type(overlap) is not int or overlap < 0:
        raise ValueError("json.context_overlap_lines must be a nonnegative integer")
    config["paths"] = {key: (path.parent / value).resolve() for key, value in config["paths"].items()}
    return config
