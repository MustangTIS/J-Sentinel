# config_manager.py
import os
import json

def load_system_config(file_path="config.json"):
    defaults = {
        "bot_settings": {},
        "monitor_base_dir": [],
        "destinations": []
    }

    config = defaults.copy()
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                config.update(json.load(f))
        except Exception as e:
            print(f"[Warning] config.json の読み込みに失敗しました: {e}")

    return config