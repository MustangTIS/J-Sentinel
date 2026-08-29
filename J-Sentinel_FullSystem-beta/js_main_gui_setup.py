# -*- coding: utf-8 -*-
import os
import json
import csv
import sys
import subprocess
import customtkinter as ctk
from tkinter import messagebox

class JSentinelSetup(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_path = os.path.join(self.base_dir, "config.json")
        
        # CSVファイルのパス
        self.info_csv_path = os.path.join(self.base_dir, "js_core", "codemaster", "infosorter.csv")
        self.quake_csv_path = os.path.join(self.base_dir, "js_core", "codemaster", "quakesorter.csv")

        # ウィンドウ基本設定（ワイド画面）
        self.title("J-Sentinel 初期設定セットアップ (完全版)")
        self.geometry("1150x950")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # 状態変数
        self.checkbox_vars = {}  
        self.csv_data_map = {}   
        self.destination_rows = [] 

        self.create_widgets()
        self.load_all_csvs()
        self.load_existing_config()

    def create_widgets(self):
        # --- タイトル ---
        self.label_title = ctk.CTkLabel(self, text="J-Sentinel 初期設定・マルチ配信マネージャー", font=("Yu Gothic", 20, "bold"))
        self.label_title.pack(pady=(10, 5))

        # --- Discord Bot 共通設定エリア ---
        self.bot_setting_frame = ctk.CTkFrame(self)
        self.bot_setting_frame.pack(pady=5, padx=15, fill="x")
        
        ctk.CTkLabel(self.bot_setting_frame, text="Discord Bot 共通設定 (bot_settings)", font=("Yu Gothic", 11, "bold")).pack(pady=(6, 2), padx=10, anchor="w")
        
        bot_input_row = ctk.CTkFrame(self.bot_setting_frame, fg_color="transparent")
        bot_input_row.pack(fill="x", padx=10, pady=(0, 8))
        
        ctk.CTkLabel(bot_input_row, text="Bot Token:", font=("Yu Gothic", 10)).pack(side="left", padx=(0, 5))
        self.entry_bot_token = ctk.CTkEntry(bot_input_row, placeholder_text="Discord Bot Token を入力", height=28, show="*")
        self.entry_bot_token.pack(side="left", fill="x", expand=True, padx=5)

        # --- 全体を左右に大きく二分割するメインコンテナ ---
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(pady=5, padx=15, fill="both", expand=True)
        main_container.grid_columnconfigure(0, weight=4)  # 左: 監視対象
        main_container.grid_columnconfigure(1, weight=5)  # 右: 配信先・SNS連携
        main_container.grid_rowconfigure(0, weight=1)

        # ==========================================
        # 【左カラム】 監視対象の選択 (気象・地震)
        # ==========================================
        left_main_frame = ctk.CTkFrame(main_container)
        left_main_frame.grid(row=0, column=0, padx=(0, 8), sticky="nsew")
        left_main_frame.grid_rowconfigure(1, weight=1)
        left_main_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(left_main_frame, text="1. 監視対象の選択 (CSV + その他枠)", font=("Yu Gothic", 12, "bold")).grid(row=0, column=0, pady=8, padx=10, sticky="w")

        sub_left_container = ctk.CTkFrame(left_main_frame, fg_color="transparent")
        sub_left_container.grid(row=1, column=0, sticky="nsew", padx=5, pady=(0, 5))
        sub_left_container.grid_rowconfigure((0, 1), weight=1)
        sub_left_container.grid_columnconfigure(0, weight=1)

        # 気象・情報系ボックス
        info_box = ctk.CTkFrame(sub_left_container)
        info_box.grid(row=0, column=0, sticky="nsew", pady=(0, 4))
        info_box.grid_rowconfigure(1, weight=1)
        info_box.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(info_box, text="氣象・情報系 (infosorter)", font=("Yu Gothic", 11, "bold")).grid(row=0, column=0, sticky="w", padx=8, pady=4)
        self.scroll_info = ctk.CTkScrollableFrame(info_box, fg_color="transparent")
        self.scroll_info.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)

        # 地震系ボックス
        quake_box = ctk.CTkFrame(sub_left_container)
        quake_box.grid(row=1, column=0, sticky="nsew", pady=(4, 0))
        quake_box.grid_rowconfigure(1, weight=1)
        quake_box.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(quake_box, text="地震系 (quakesorter)", font=("Yu Gothic", 11, "bold")).grid(row=0, column=0, sticky="w", padx=8, pady=4)
        self.scroll_quake = ctk.CTkScrollableFrame(quake_box, fg_color="transparent")
        self.scroll_quake.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)

        # ==========================================
        # 【右カラム】 SNS連携・マルチ配信先設定
        # ==========================================
        right_main_frame = ctk.CTkFrame(main_container)
        right_main_frame.grid(row=0, column=1, padx=(8, 0), sticky="nsew")
        right_main_frame.grid_rowconfigure(1, weight=1)
        right_main_frame.grid_columnconfigure(0, weight=1)

        dest_header_frame = ctk.CTkFrame(right_main_frame, fg_color="transparent")
        dest_header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=8)
        
        ctk.CTkLabel(dest_header_frame, text="2. 配信先・SNS連携設定 (マルチ)", font=("Yu Gothic", 12, "bold")).pack(side="left", anchor="w")
        
        self.btn_add_dest = ctk.CTkButton(dest_header_frame, text="＋ 配信先を追加", width=110, height=26, fg_color="#28a745", hover_color="#218838", font=("Yu Gothic", 11, "bold"), command=lambda: self.add_destination_card())
        self.btn_add_dest.pack(side="right")

        self.scroll_dest = ctk.CTkScrollableFrame(right_main_frame, fg_color="transparent")
        self.scroll_dest.grid(row=1, column=0, sticky="nsew", padx=5, pady=(0, 5))

        # --- 3. オプション＆保存・連携エリア (下部) ---
        option_frame = ctk.CTkFrame(self, fg_color="transparent")
        option_frame.pack(pady=(5, 0), padx=15, fill="x")

        self.var_create_desktop = ctk.BooleanVar(value=False)
        self.chk_desktop = ctk.CTkCheckBox(option_frame, text="デスクトップにショートカットを作成する", variable=self.var_create_desktop, font=("Yu Gothic", 11))
        self.chk_desktop.pack(anchor="w", padx=5, pady=2)

        self.var_create_startup = ctk.BooleanVar(value=False)
        self.chk_startup = ctk.CTkCheckBox(option_frame, text="スタートアップに登録する", variable=self.var_create_startup, font=("Yu Gothic", 11))
        self.chk_startup.pack(anchor="w", padx=5, pady=2)

        # ボタン配置用コンテナ
        action_row = ctk.CTkFrame(self, fg_color="transparent")
        action_row.pack(pady=10, padx=15, fill="x")

        self.btn_save = ctk.CTkButton(action_row, text="設定を保存", fg_color="#1f538d", hover_color="#14375e", height=42,
                                      font=("Yu Gothic", 14, "bold"), command=self.save_config)
        self.btn_save.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.btn_open_core_gui = ctk.CTkButton(action_row, text="Core設定を開く (js_gui_setup.py)", fg_color="#444444", hover_color="#555555", height=42,
                                               font=("Yu Gothic", 12, "bold"), command=self.open_core_gui)
        self.btn_open_core_gui.pack(side="right", padx=(5, 0))

    def add_destination_card(self, data=None):
        if data is None:
            data = {"platform": "disembed", "url": "", "matrix_room": "", "token": "", "handle": "", "password": ""}

        card = ctk.CTkFrame(self.scroll_dest, fg_color="#2b2b2b", corner_radius=6)
        card.pack(pady=6, padx=4, fill="x")

        top_row = ctk.CTkFrame(card, fg_color="transparent")
        top_row.pack(fill="x", padx=8, pady=(6, 2))

        ctk.CTkLabel(top_row, text="形式:", font=("Yu Gothic", 10)).pack(side="left", padx=(0, 4))
        
        platform_var = ctk.StringVar(value=data.get("platform", data.get("style", "disembed")))

        def remove_card():
            card.destroy()
            if card_data in self.destination_rows:
                self.destination_rows.remove(card_data)

        btn_del = ctk.CTkButton(top_row, text="削除", width=50, height=24, fg_color="#d9534f", hover_color="#c9302c", command=remove_card)
        btn_del.pack(side="right")

        fields_frame = ctk.CTkFrame(card, fg_color="transparent")
        fields_frame.pack(fill="x", padx=8, pady=(2, 8))

        url_entry = ctk.CTkEntry(fields_frame, placeholder_text="Webhook URL (Discord / Slack)", height=28)
        room_entry = ctk.CTkEntry(fields_frame, placeholder_text="Matrix Room ID (例: !xxx:matrix.org)", height=28)
        token_entry = ctk.CTkEntry(fields_frame, placeholder_text="Matrix Access Token", height=28, show="*")
        handle_entry = ctk.CTkEntry(fields_frame, placeholder_text="Bluesky Handle (例: user.bsky.social)", height=28)
        pass_entry = ctk.CTkEntry(fields_frame, placeholder_text="Bluesky App Password", height=28, show="*")

        if data.get("url"): url_entry.insert(0, data.get("url"))
        if data.get("matrix_room"): room_entry.insert(0, data.get("matrix_room"))
        if data.get("token"): token_entry.insert(0, data.get("token"))
        if data.get("handle"): handle_entry.insert(0, data.get("handle"))
        if data.get("password"): pass_entry.insert(0, data.get("password"))

        def update_fields(*args):
            for widget in (url_entry, room_entry, token_entry, handle_entry, pass_entry):
                widget.pack_forget()

            sel = platform_var.get()
            if sel in ["disembed", "dissimple", "slack"]:
                url_entry.configure(placeholder_text="Webhook URL")
                url_entry.pack(fill="x", pady=2)
            elif sel == "matrix":
                url_entry.configure(placeholder_text="Matrix Base URL (省略時はデフォルト)")
                url_entry.pack(fill="x", pady=2)
                room_entry.pack(fill="x", pady=2)
                token_entry.pack(fill="x", pady=2)
            elif sel == "bluesky":
                url_entry.configure(placeholder_text="PDS URL (省略時は https://bsky.social)")
                url_entry.pack(fill="x", pady=2)
                handle_entry.pack(fill="x", pady=2)
                pass_entry.pack(fill="x", pady=2)

        platform_var.trace_add("write", update_fields)
        platform_menu = ctk.CTkOptionMenu(top_row, values=["disembed", "dissimple", "slack", "matrix", "bluesky"], variable=platform_var, width=110, height=24)
        platform_menu.pack(side="left", padx=4)

        update_fields()

        card_data = {
            "card": card,
            "platform_var": platform_var,
            "url_entry": url_entry,
            "room_entry": room_entry,
            "token_entry": token_entry,
            "handle_entry": handle_entry,
            "pass_entry": pass_entry
        }
        self.destination_rows.append(card_data)

    def load_info_csv(self, csv_path, scroll_parent):
        etc_key = "[その他未分類] info/etc"
        etc_rel = "js_core/database/info/etc"
        self.csv_data_map[etc_key] = etc_rel
        etc_var = ctk.BooleanVar(value=False)
        self.checkbox_vars[etc_key] = etc_var
        ctk.CTkCheckBox(scroll_parent, text="【その他未分類】 [info/etc]", variable=etc_var, font=("Yu Gothic", 10, "bold"), text_color="#ffcc00").pack(pady=2, padx=2, anchor="w")

        if not os.path.exists(csv_path):
            ctk.CTkLabel(scroll_parent, text="CSV未検出", text_color="orange").pack(anchor="w", padx=5, pady=5)
            return
        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    cleaned = {k.strip(): v for k, v in row.items() if k is not None}
                    kw, tf = cleaned.get("Keyword"), cleaned.get("Target Folder")
                    if kw and tf:
                        rel = os.path.join("js_core", "database", "info", tf).replace("\\", "/")
                        self.csv_data_map[kw] = rel
                        var = ctk.BooleanVar(value=False)
                        self.checkbox_vars[kw] = var
                        ctk.CTkCheckBox(scroll_parent, text=f"{kw} [{tf}]", variable=var, font=("Yu Gothic", 10)).pack(pady=2, padx=2, anchor="w")
        except Exception as e:
            print(f"Info CSV error: {e}")

    def load_quake_csv(self, csv_path, scroll_parent):
        etc_key = "[その他未分類] quake/etc"
        etc_rel = "js_core/database/quake/etc"
        self.csv_data_map[etc_key] = etc_rel
        etc_var = ctk.BooleanVar(value=False)
        self.checkbox_vars[etc_key] = etc_var
        ctk.CTkCheckBox(scroll_parent, text="【その他未分類】 [quake/etc]", variable=etc_var, font=("Yu Gothic", 10, "bold"), text_color="#ffcc00").pack(pady=2, padx=2, anchor="w")

        if not os.path.exists(csv_path):
            ctk.CTkLabel(scroll_parent, text="CSV未検出", text_color="orange").pack(anchor="w", padx=5, pady=5)
            return
        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    cleaned = {k.strip(): v for k, v in row.items() if k is not None}
                    kw, cat = cleaned.get("keyword"), cleaned.get("category")
                    if kw:
                        sub = f"quake/{cat}" if cat else "quake"
                        rel = os.path.join("js_core", "database", sub).replace("\\", "/")
                        self.csv_data_map[kw] = rel
                        var = ctk.BooleanVar(value=False)
                        self.checkbox_vars[kw] = var
                        ctk.CTkCheckBox(scroll_parent, text=f"{kw} [{cat}]", variable=var, font=("Yu Gothic", 10)).pack(pady=2, padx=2, anchor="w")
        except Exception as e:
            print(f"Quake CSV error: {e}")

    def load_all_csvs(self):
        self.load_info_csv(self.info_csv_path, self.scroll_info)
        self.load_quake_csv(self.quake_csv_path, self.scroll_quake)

    def load_existing_config(self):
        if not os.path.exists(self.config_path):
            self.add_destination_card()
            return

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            bot_settings = config.get("bot_settings", {})
            if "token" in bot_settings:
                self.entry_bot_token.insert(0, bot_settings["token"])

            destinations = config.get("destinations", [])
            if destinations:
                for dest in destinations:
                    self.add_destination_card({
                        "platform": dest.get("style", dest.get("platform", "disembed")),
                        "url": dest.get("url", ""),
                        "matrix_room": dest.get("matrix_room", ""),
                        "token": dest.get("token", ""),
                        "handle": dest.get("handle", ""),
                        "password": dest.get("password", "")
                    })
            else:
                self.add_destination_card()

            if "monitor_base_dir" in config:
                saved_paths = [p.replace("\\", "/") for p in config["monitor_base_dir"]]
                for kw, path in self.csv_data_map.items():
                    if path in saved_paths:
                        self.checkbox_vars[kw].set(True)
        except Exception as e:
            print(f"Config load error: {e}")
            self.add_destination_card()

    def create_shortcut_file(self, target_script, shortcut_name, dest_dir):
        """標準の VBScript を一時生成して指定ディレクトリにショートカットを作成する"""
        try:
            if not os.path.exists(dest_dir):
                os.makedirs(dest_dir, exist_ok=True)
                
            path = os.path.join(dest_dir, f"{shortcut_name}.lnk")
            target_path = os.path.join(self.base_dir, target_script)
            python_w_path = sys.executable.replace("python.exe", "pythonw.exe")
            if not os.path.exists(python_w_path):
                python_w_path = sys.executable

            vbs_path = os.path.join(self.base_dir, "temp_create_shortcut.vbs")
            vbs_content = f"""
Set ws = CreateObject("WScript.Shell")
Set lnk = ws.CreateShortcut("{path}")
lnk.TargetPath = "{python_w_path}"
lnk.Arguments = "\"{target_path}\""
lnk.WorkingDirectory = "{self.base_dir}"
lnk.IconLocation = "{python_w_path}"
lnk.Save
"""
            with open(vbs_path, "w", encoding="cp932") as f:
                f.write(vbs_content)

            subprocess.run(["cscript", "//nologo", vbs_path], check=True)
            
            if os.path.exists(vbs_path):
                os.remove(vbs_path)
                
            return True
        except Exception as e:
            print(f"Shortcut creation error for {shortcut_name} in {dest_dir}: {e}")
            return False

    def open_core_gui(self):
        """\js_core\js_gui_setup.py を別プロセスで起動する"""
        core_gui_path = os.path.join(self.base_dir, "js_core", "js_gui_setup.py")
        if os.path.exists(core_gui_path):
            try:
                subprocess.Popen([sys.executable, core_gui_path])
            except Exception as e:
                messagebox.showerror("起動エラー", f"Core設定の起動に失敗しました:\n{e}")
        else:
            messagebox.showwarning("ファイル未検出", f"指定されたパスにファイルが見つかりません:\n{core_gui_path}")

    def save_config(self):
        selected_dirs = [self.csv_data_map[kw] for kw, var in self.checkbox_vars.items() if var.get()]

        destinations_list = []
        for row in self.destination_rows:
            destinations_list.append({
                "style": row["platform_var"].get(),
                "url": row["url_entry"].get().strip(),
                "matrix_room": row["room_entry"].get().strip(),
                "token": row["token_entry"].get().strip(),
                "handle": row["handle_entry"].get().strip(),
                "password": row["pass_entry"].get().strip()
            })

        config_data = {
            "bot_settings": {
                "token": self.entry_bot_token.get().strip()
            },
            "monitor_base_dir": selected_dirs,
            "destinations": destinations_list
        }

        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4, ensure_ascii=False)

            msg = "設定を config.json に保存しました！\n" + f"監視項目: {len(selected_dirs)}件 / 配信先: {len(destinations_list)}件"

            created_actions = []

            # 1. デスクトップショートカット作成
            if self.var_create_desktop.get():
                desktop = os.path.join(os.path.expanduser("~"), "Desktop")
                if not os.path.exists(desktop):
                    desktop = os.path.join(os.environ["USERPROFILE"], "Desktop")
                
                sc_main = self.create_shortcut_file("J-Sentinel_main.py", "J-Sentinel_Alert", desktop)
                sc_bot = self.create_shortcut_file("bot.py", "J-Sentinel_CallBack", desktop)
                if sc_main and sc_bot:
                    created_actions.append("デスクトップショートカット作成完了")

            # 2. スタートアップ登録
            if self.var_create_startup.get():
                startup_dir = os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs", "Startup")
                sc_main_su = self.create_shortcut_file("J-Sentinel_main.py", "J-Sentinel_Alert", startup_dir)
                sc_bot_su = self.create_shortcut_file("bot.py", "J-Sentinel_CallBack", startup_dir)
                if sc_main_su and sc_bot_su:
                    created_actions.append("スタートアップ登録完了")

            if created_actions:
                msg += "\n\n[" + " / ".join(created_actions) + "]"

            messagebox.showinfo("保存完了", msg)
        except Exception as e:
            messagebox.showerror("保存エラー", f"保存に失敗しました:\n{e}")

if __name__ == "__main__":
    JSentinelSetup().mainloop()