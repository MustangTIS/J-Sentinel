import os
import time

class LogMonitor:
    def __init__(self, target_dirs):
        """
        指定されたディレクトリのリスト（または単一の文字列）を再帰的に監視対象にする
        """
        # 単一の文字列で渡された場合でもリストに変換して安全に扱う
        if isinstance(target_dirs, str):
            self.target_dirs = [target_dirs]
        else:
            self.target_dirs = target_dirs or []
            
        self.known_files = set()
        
        for target_dir in self.target_dirs:
            if os.path.exists(target_dir):
                for root, _, files in os.walk(target_dir):
                    normalized_root = root.replace("\\", "/")
                    if "keiho" in normalized_root or "warning" in normalized_root:
                        continue
                        
                    for file in files:
                        file_path = os.path.abspath(os.path.join(root, file))
                        self.known_files.add(file_path)

    def check_new_logs(self):
        """
        監視ディレクトリのリストを順次走査し、新しく追加されたファイルのリストを返す
        """
        new_files = []
        current_files = set()

        for target_dir in self.target_dirs:
            if not os.path.exists(target_dir):
                continue

            for root, _, files in os.walk(target_dir):
                normalized_root = root.replace("\\", "/")
                if "keiho" in normalized_root or "warning" in normalized_root:
                    continue

                for file in files:
                    file_path = os.path.abspath(os.path.join(root, file))
                    current_files.add(file_path)

                    # 新着ファイルの検知
                    if file_path not in self.known_files:
                        new_files.append(file_path)

        # 既存ファイルのトラッキングを更新
        self.known_files = current_files
        return new_files if new_files else None