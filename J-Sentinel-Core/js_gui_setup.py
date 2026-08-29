from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import tkinter as tk
from tkinter import messagebox, ttk

# --- 動的パスの基準設定 ---
BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"
ICON_PATH = BASE_DIR / "icon.ico"
CODEMASTER_DIR = BASE_DIR / "codemaster"


class JSentinelSetupApp:

  def __init__(self, root):
    self.root = root
    self.root.title("J-Sentinel Core Setup")
    self.root.geometry("480x610")
    self.root.resizable(False, False)

    # アイコンの設定（存在する場合のみ適用）
    if ICON_PATH.exists():
      try:
        self.root.iconbitmap(str(ICON_PATH))
      except Exception:
        pass

    # 設定のロード
    self.config = self.load_config()

    # GUIパーツの構築
    self.create_widgets()
    self.load_to_widgets()

  def load_config(self) -> dict:
    """config.jsonを読み込む。なければデフォルトを返す"""
    default_config = {
        "debug_mode": True,
        "interval_seconds": 60,
        "tasks": {
            "info": {"enabled": True, "script": "fetch_info.py"},
            "quake": {"enabled": True, "script": "fetch_quake.py"},
            "warning": {"enabled": True, "script": "fetch_warning.py"},
        },
        "retention": {"auto_clean_enabled": False, "keep_days": 90},
    }

    if CONFIG_PATH.exists():
      try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
          return json.load(f)
      except Exception as e:
        messagebox.showwarning(
            "警告",
            f"config.json の読み込みに失敗しました。\n初期設定を使用します。\nエラー: {e}",
        )
    return default_config

  def save_config(self):
    """GUI上の値を config.json に書き込む"""
    try:
      # インターバルのバリデーション
      try:
        interval = int(self.interval_var.get())
        if interval < 1:
          raise ValueError("インターバルは1秒以上にしてください。")
      except ValueError as ve:
        messagebox.showerror(
            "入力エラー", f"巡回インターバルには有効な数値を入力してください。\n{ve}"
        )
        return

      # 保持日数のバリデーション
      try:
        keep_days = int(self.keep_days_var.get())
        if keep_days < 1:
          raise ValueError("保持日数は1日以上にしてください。")
      except ValueError as ve:
        messagebox.showerror(
            "入力エラー", f"保持日数には有効な数値を入力してください。\n{ve}"
        )
        return

      # 辞書の構築
      self.config["debug_mode"] = self.debug_var.get()
      self.config["interval_seconds"] = interval

      self.config["tasks"]["info"]["enabled"] = self.task_info_var.get()
      self.config["tasks"]["quake"]["enabled"] = self.task_quake_var.get()
      self.config["tasks"]["warning"]["enabled"] = self.task_warning_var.get()

      self.config["retention"][
          "auto_clean_enabled"
      ] = self.auto_clean_var.get()
      self.config["retention"]["keep_days"] = keep_days

      # ファイル保存
      with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(self.config, f, ensure_ascii=False, indent=2)

      messagebox.showinfo("成功", "config.json を正常に保存しました！")
    except Exception as e:
      messagebox.showerror("エラー", f"保存に失敗しました:\n{e}")

  def load_to_widgets(self):
    """読み込んだconfigの内容を各ウィジェットに反映する"""
    self.debug_var.set(self.config.get("debug_mode", True))
    self.interval_var.set(str(self.config.get("interval_seconds", 60)))

    tasks = self.config.get("tasks", {})
    self.task_info_var.set(tasks.get("info", {}).get("enabled", True))
    self.task_quake_var.set(tasks.get("quake", {}).get("enabled", True))
    self.task_warning_var.set(tasks.get("warning", {}).get("enabled", True))

    retention = self.config.get("retention", {})
    self.auto_clean_var.set(retention.get("auto_clean_enabled", False))
    self.keep_days_var.set(str(retention.get("keep_days", 90)))

  def open_csv(self, filename: str):
    """指定されたCSVファイル（codemaster内）を関連付けアプリで開く"""
    csv_path = CODEMASTER_DIR / filename
    if not csv_path.exists():
      messagebox.showerror(
          "エラー", f"ファイルが見つかりません:\n{csv_path}"
      )
      return
    try:
      os.startfile(str(csv_path))
    except Exception as e:
      messagebox.showerror("エラー", f"ファイルを開けませんでした:\n{e}")

  def create_desktop_shortcut(self):
    """デスクトップに run_sentinel.bat のショートカットを作成する"""
    target_bat = BASE_DIR / "run_sentinel.bat"
    if not target_bat.exists():
      messagebox.showerror(
          "エラー", f"起動用バッチが見つかりません:\n{target_bat}"
      )
      return

    try:
      desktop_dir = Path(os.path.expanduser("~")) / "Desktop"
      shortcut_path = desktop_dir / "J-Sentinel Core.lnk"

      # PowerShellを使わず、Pythonの標準機能（comtypes もしくは ctypes経由のWScript.Shell）で作成する
      # Python標準の win32com が入っていれば一番良いですが、標準ライブラリだけでやるため
      # 一時的な .vbs スクリプトを生成して実行して即消す、という最も確実で確実な手を使います。
      vbs_path = BASE_DIR / "make_shortcut.vbs"
      ico_str = str(ICON_PATH) if ICON_PATH.exists() else ""

      vbs_content = f'''Set ws = CreateObject("WScript.Shell")
Set sc = ws.CreateShortcut("{shortcut_path}")
sc.TargetPath = "{target_bat}"
sc.WorkingDirectory = "{BASE_DIR}"
'''
      if ico_str:
        vbs_content += f'sc.IconLocation = "{ico_str}"\n'
      vbs_content += "sc.Save()\n"

      # VBSファイルを書き出して実行
      with open(vbs_path, "w", encoding="cp932") as f:
        f.write(vbs_content)

      subprocess.run(["cscript", "//nologo", str(vbs_path)], check=True)

      # 用済みのVBSファイルを削除
      if vbs_path.exists():
        vbs_path.unlink()

      messagebox.showinfo(
          "完了",
          "デスクトップにショートカットを作成しました！\n"
          f"({shortcut_path.name})",
      )
    except Exception as e:
      # 念のため例外時もVBSが残らないように掃除
      if "vbs_path" in locals() and vbs_path.exists():
        try:
          vbs_path.unlink()
        except:
          pass
      messagebox.showerror(
          "エラー", f"ショートカットの作成に失敗しました:\n{e}"
      )

  def create_widgets(self):
    main_frame = ttk.Frame(self.root, padding=15)
    main_frame.pack(fill=tk.BOTH, expand=True)

    # --- 1. 基本・デバッグ設定 ---
    basic_frame = ttk.LabelFrame(
        main_frame, text=" 動作・基本設定 ", padding=10
    )
    basic_frame.pack(fill=tk.X, pady=5)

    self.debug_var = tk.BooleanVar()
    ttk.Checkbutton(
        basic_frame, text="デバッグモード有効 (詳細ログ出力)", variable=self.debug_var
    ).pack(anchor=tk.W, pady=2)

    interval_frame = ttk.Frame(basic_frame)
    interval_frame.pack(fill=tk.X, pady=5)
    ttk.Label(interval_frame, text="巡回インターバル (秒):").pack(
        side=tk.LEFT, padx=(0, 10)
    )
    self.interval_var = tk.StringVar()
    ttk.Entry(interval_frame, textvariable=self.interval_var, width=10).pack(
        side=tk.LEFT
    )

    # --- 2. タスク有効/無効設定 ---
    task_frame = ttk.LabelFrame(
        main_frame, text=" タスク有効/無効 設定 ", padding=10
    )
    task_frame.pack(fill=tk.X, pady=5)

    self.task_info_var = tk.BooleanVar()
    ttk.Checkbutton(
        task_frame,
        text="気象庁総合情報タスク (fetch_info.py)",
        variable=self.task_info_var,
    ).pack(anchor=tk.W, pady=2)

    self.task_quake_var = tk.BooleanVar()
    ttk.Checkbutton(
        task_frame,
        text="地震情報タスク (fetch_quake.py)",
        variable=self.task_quake_var,
    ).pack(anchor=tk.W, pady=2)

    self.task_warning_var = tk.BooleanVar()
    ttk.Checkbutton(
        task_frame,
        text="気象警報タスク (fetch_warning.py)",
        variable=self.task_warning_var,
    ).pack(anchor=tk.W, pady=2)

    # --- 3. データ保持 (リテンション) 設定 ---
    retention_frame = ttk.LabelFrame(
        main_frame, text=" データ保持 (クリーンアップ) 設定 ", padding=10
    )
    retention_frame.pack(fill=tk.X, pady=5)

    self.auto_clean_var = tk.BooleanVar()
    ttk.Checkbutton(
        retention_frame,
        text="古いデータの自動クリーンアップを有効にする",
        variable=self.auto_clean_var,
    ).pack(anchor=tk.W, pady=2)

    keep_frame = ttk.Frame(retention_frame)
    keep_frame.pack(fill=tk.X, pady=5)
    ttk.Label(keep_frame, text="保持日数 (日):").pack(
        side=tk.LEFT, padx=(0, 10)
    )
    self.keep_days_var = tk.StringVar()
    ttk.Entry(keep_frame, textvariable=self.keep_days_var, width=10).pack(
        side=tk.LEFT
    )

    # --- 4. CSVマスター編集エリア ---
    csv_frame = ttk.LabelFrame(
        main_frame, text=" マスターCSV振り分け設定 (表計算ソフトで編集) ", padding=10
    )
    csv_frame.pack(fill=tk.X, pady=5)

    csv_btn_frame = ttk.Frame(csv_frame)
    csv_btn_frame.pack(fill=tk.X, pady=2)

    ttk.Button(
        csv_btn_frame,
        text="infosorter.csv を開く",
        command=lambda: self.open_csv("infosorter.csv"),
    ).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
    ttk.Button(
        csv_btn_frame,
        text="quakesorter.csv を開く",
        command=lambda: self.open_csv("quakesorter.csv"),
    ).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

    # --- 5. ユーティリティ・保存ボタン ---
    util_frame = ttk.Frame(main_frame, padding=5)
    util_frame.pack(fill=tk.X, pady=5)

    ttk.Button(
        util_frame,
        text="📌 デスクトップショートカット作成",
        command=self.create_desktop_shortcut,
    ).pack(fill=tk.X, pady=3)

    # 保存ボタン（目立つように配置）
    ttk.Button(
        main_frame,
        text="💾 設定を保存 (config.json)",
        command=self.save_config,
    ).pack(fill=tk.X, ipady=5, pady=(5, 0))


if __name__ == "__main__":
  root = tk.Tk()
  app = JSentinelSetupApp(root)
  root.mainloop()