"""Load the single editable settings file (`~/.lifeboard/config.json`), deep-merged
over defaults shipped in the example template. Nothing personal lives in code."""
import copy
import json
import os
import pathlib

CONFIG_PATH = pathlib.Path(os.path.expanduser("~/.lifeboard/config.json"))
_EXAMPLE = pathlib.Path(__file__).parent / "data" / "lifeboard.config.example.json"
DEFAULTS = json.loads(_EXAMPLE.read_text())


def _deep_merge(base, over):
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config():
    user = {}
    if CONFIG_PATH.exists():
        try:
            user = json.loads(CONFIG_PATH.read_text())
        except Exception:
            user = {}
    cfg = _deep_merge(DEFAULTS, user)
    if cfg["trading"].get("jarvis_dir"):
        cfg["trading"]["jarvis_dir"] = os.path.expanduser(cfg["trading"]["jarvis_dir"])
    cfg["claude"]["projects_dir"] = os.path.expanduser(cfg["claude"]["projects_dir"])
    return cfg
