import os
import json

def load_system_config(file_path=None):
    defaults = {
        "bot_settings": {},
        "monitor_base_dir": [],
        "destinations": []
    }

    # ファイルパスが指定されていない場合は、このスクリプトの位置を基準に一つ上の階層の config.json を狙う
    if file_path is None:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # system フォルダ内にある想定なので、一つ上のプロジェクトルートにある config.json を指定
        file_path = os.path.normpath(os.path.join(current_dir, "..", "config.json"))

    config = defaults.copy()
    
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                config.update(json.load(f))
        except Exception as e:
            print(f"[Warning] config.json の読み込みに失敗しました ({file_path}): {e}")
    else:
        print(f"[Notice] config.json が見つからないため、デフォルト設定で動作します: {file_path}")

    return config