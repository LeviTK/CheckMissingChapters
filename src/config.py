import json
import os
import re

from num_utils import NUM_PATTERNS


CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

DEFAULT_VOL_REGEX = rf"第\s*({NUM_PATTERNS['mixed']})\s*[卷部册辑篇集幕]"

DEFAULT_CONFIG = {
    "chap_prefix": "第",
    "chap_num_type": "mixed",
    "chap_suffix": "章",
    "custom_suffixes": ["章", "回", "节", "话", "集"],
    "enable_volume": False,
    "vol_regex": DEFAULT_VOL_REGEX,
    "chap_reset_mode": "reset_1",
    "auto_detect_reset": False,
}


def load_or_create_config():
    config = DEFAULT_CONFIG.copy()
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                user_config = json.load(f)
                for k, v in user_config.items():
                    config[k] = v
        except Exception:
            pass
    else:
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_CONFIG, f, indent=4, ensure_ascii=False)
        except Exception:
            pass
    return config


def save_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception:
        pass


def build_chapter_regex_str(config):
    prefix = config["chap_prefix"]
    num_type = config.get("chap_num_type", "mixed")
    num_pat = NUM_PATTERNS.get(num_type, NUM_PATTERNS["mixed"])
    suffix = config["chap_suffix"]

    escaped_prefix = re.escape(prefix)
    if "|" in suffix:
        parts = [re.escape(p.strip()) for p in suffix.split("|") if p.strip()]
        real_suffix = f"(?:{'|'.join(parts)})"
    else:
        real_suffix = re.escape(suffix)

    return f"{escaped_prefix}\\s*({num_pat})\\s*{real_suffix}"
