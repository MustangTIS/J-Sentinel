# -*- coding: utf-8 -*-
import os
import json
import csv
import sys
import subprocess
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox

class JSentinelSetup(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_path = os.path.join(self.base_dir, "config.json")
        
        self.info_csv_path = os.path.join(self.base_dir, "js_core", "codemaster", "infosorter.csv")
        self.quake_csv_path = os.path.join(self.base_dir, "js_core", "codemaster", "quakesorter.csv")
        self.volcano_csv_path = os.path.join(self.base_dir, "js_core", "codemaster", "volcanosorter.csv")

        self.title("J-Sentinel 初期設定セットアップ")
        self.geometry("1280x850")
        self.minsize(1100, 700)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        if os.path.exists(os.path.join(self.base_dir, "icon.ico")):
            self.iconbitmap(os.path.join(self.base_dir, "icon.ico"))

        self.checkbox_vars = {}  
        self.checkbox_widgets = {} 
        self.csv_data_map = {}   
        self.destination_rows = []

        self.platform_map = {
            "Discord (Embed)": "disembed",
            "Discord (Simple)": "dissimple",
            "Slack": "slack",
            "Matrix": "matrix",
            "Bluesky": "bluesky",
            "Generic Webhook": "webhook"
        }
        self.reverse_platform_map = {v: k for k, v in self.platform_map.items()}

        self.mode_map = {
            "全文転送": "full",
            "文字数制限 (概要)": "limit"
        }
        self.reverse_mode_map = {v: k for k, v in self.mode_map.items()}

        self.create_widgets()
        self.load_all_csvs()
        self.load_existing_config()

    def bind_entry_context_menu(self, entry_widget):
        menu = tk.Menu(entry_widget, tearoff=0, bg="#2b2b2b", fg="#ffffff", activebackground="#1f538d", activeforeground="#ffffff")
        
        def do_cut():
            try: entry_widget.event_generate("<<Cut>>")
            except Exception: pass

        def do_copy():
            try: entry_widget.event_generate("<<Copy>>")
            except Exception: pass

        def do_paste():
            try:
                clip_text = entry_widget.clipboard_get()
                try:
                    sel_first = entry_widget.index("sel.first")
                    sel_last = entry_widget.index("sel.last")
                    entry_widget.delete(sel_first, sel_last)
                except tk.TclError: pass
                entry_widget.insert("insert", clip_text)
            except Exception:
                try: entry_widget.event_generate("<<Paste>>")
                except Exception: pass

        def do_select_all():
            try:
                entry_widget.select_range(0, 'end')
                entry_widget.icursor('end')
            except Exception: pass

        menu.add_command(label="切り取り", command=do_cut)
        menu.add_command(label="コピー", command=do_copy)
        menu.add_command(label="貼り付け", command=do_paste)
        menu.add_separator()
        menu.add_command(label="すべて選択", command=do_select_all)

        def r_click(event):
            try:
                entry_widget.focus_set()
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()

        entry_widget.bind("<Button-3>", r_click)

    def create_widgets(self):
        self.label_title = ctk.CTkLabel(self, text="J-Sentinel ～高度防災システム 初期設定マネージャー", font=("Yu Gothic", 18, "bold"))
        self.label_title.pack(pady=(10, 2))

        self.bot_setting_frame = ctk.CTkFrame(self)
        self.bot_setting_frame.pack(pady=4, padx=12, fill="x")
        
        bot_input_row = ctk.CTkFrame(self.bot_setting_frame, fg_color="transparent")
        bot_input_row.pack(fill="x", padx=10, pady=4)
        
        ctk.CTkLabel(bot_input_row, text="Discord Bot Token (共通):", font=("Yu Gothic", 11, "bold")).pack(side="left", padx=(0, 5))
        self.entry_bot_token = ctk.CTkEntry(bot_input_row, placeholder_text="Bot Token を入力", height=28, show="*")
        self.entry_bot_token.pack(side="left", fill="x", expand=True, padx=5)
        self.bind_entry_context_menu(self.entry_bot_token)

        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(pady=4, padx=12, fill="both", expand=True)
        
        main_container.grid_columnconfigure(0, weight=4)
        main_container.grid_columnconfigure(1, weight=3)
        main_container.grid_columnconfigure(2, weight=4)
        main_container.grid_rowconfigure(0, weight=1)

        # カラム1: 気象
        col1_frame = ctk.CTkFrame(main_container)
        col1_frame.grid(row=0, column=0, padx=(0, 4), sticky="nsew")
        col1_frame.grid_rowconfigure(1, weight=1)
        col1_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(col1_frame, text="1. 氣象・情報系 (infosorter)", font=("Yu Gothic", 12, "bold")).grid(row=0, column=0, pady=6, padx=8, sticky="w")
        self.scroll_info = ctk.CTkScrollableFrame(col1_frame, fg_color="transparent")
        self.scroll_info.grid(row=1, column=0, sticky="nsew", padx=4, pady=(0, 4))

        # カラム2: 地震・火山
        col2_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        col2_frame.grid(row=0, column=1, padx=4, sticky="nsew")
        col2_frame.grid_rowconfigure((0, 1), weight=1)
        col2_frame.grid_columnconfigure(0, weight=1)

        quake_box = ctk.CTkFrame(col2_frame)
        quake_box.grid(row=0, column=0, sticky="nsew", pady=(0, 3))
        quake_box.grid_rowconfigure(1, weight=1)
        quake_box.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(quake_box, text="2. 地震系 (quakesorter)", font=("Yu Gothic", 12, "bold")).grid(row=0, column=0, sticky="w", padx=8, pady=4)
        self.scroll_quake = ctk.CTkScrollableFrame(quake_box, fg_color="transparent")
        self.scroll_quake.grid(row=1, column=0, sticky="nsew", padx=4, pady=(0, 4))

        volcano_box = ctk.CTkFrame(col2_frame)
        volcano_box.grid(row=1, column=0, sticky="nsew", pady=(3, 0))
        volcano_box.grid_rowconfigure(1, weight=1)
        volcano_box.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(volcano_box, text="3. 火山系 (volcanosorter)", font=("Yu Gothic", 12, "bold")).grid(row=0, column=0, sticky="w", padx=8, pady=4)
        self.scroll_volcano = ctk.CTkScrollableFrame(volcano_box, fg_color="transparent")
        self.scroll_volcano.grid(row=1, column=0, sticky="nsew", padx=4, pady=(0, 4))

        # カラム3: 配信先設定
        col3_frame = ctk.CTkFrame(main_container)
        col3_frame.grid(row=0, column=2, padx=(4, 0), sticky="nsew")
        col3_frame.grid_rowconfigure(1, weight=1)
        col3_frame.grid_columnconfigure(0, weight=1)

        dest_header = ctk.CTkFrame(col3_frame, fg_color="transparent")
        dest_header.grid(row=0, column=0, sticky="ew", padx=8, pady=6)
        
        ctk.CTkLabel(dest_header, text="4. 配信先設定 (senders)", font=("Yu Gothic", 12, "bold")).pack(side="left", anchor="w")
        self.btn_add_dest = ctk.CTkButton(dest_header, text="＋ 追加", width=70, height=24, fg_color="#28a745", hover_color="#218838", font=("Yu Gothic", 11, "bold"), command=lambda: self.add_destination_card())
        self.btn_add_dest.pack(side="right")

        self.scroll_dest = ctk.CTkScrollableFrame(col3_frame, fg_color="transparent")
        self.scroll_dest.grid(row=1, column=0, sticky="nsew", padx=4, pady=(0, 4))

        # フッター
        footer_frame = ctk.CTkFrame(self, fg_color="transparent")
        footer_frame.pack(pady=(4, 8), padx=12, fill="x")

        opt_row = ctk.CTkFrame(footer_frame, fg_color="transparent")
        opt_row.pack(fill="x", pady=(0, 4))

        self.var_create_desktop = ctk.BooleanVar(value=False)
        self.chk_desktop = ctk.CTkCheckBox(opt_row, text="デスクトップにショートカットを作成", variable=self.var_create_desktop, font=("Yu Gothic", 11))
        self.chk_desktop.pack(side="left", padx=(5, 15))

        self.var_create_startup = ctk.BooleanVar(value=False)
        self.chk_startup = ctk.CTkCheckBox(opt_row, text="スタートアップに登録", variable=self.var_create_startup, font=("Yu Gothic", 11))
        self.chk_startup.pack(side="left")

        action_row = ctk.CTkFrame(footer_frame, fg_color="transparent")
        action_row.pack(fill="x")

        self.btn_save = ctk.CTkButton(action_row, text="設定を保存", fg_color="#1f538d", hover_color="#14375e", height=38,
                                     font=("Yu Gothic", 13, "bold"), command=self.save_config)
        self.btn_save.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self.btn_open_core_gui = ctk.CTkButton(action_row, text="Core設定を開く (js_gui_setup.py)", fg_color="#444444", hover_color="#555555", height=38,
                                               font=("Yu Gothic", 11, "bold"), command=self.open_core_gui)
        self.btn_open_core_gui.pack(side="right", padx=(4, 0))

    def update_duplicate_states(self, *args):
        path_counts = {}
        for kw, var in self.checkbox_vars.items():
            if var.get():
                path = self.csv_data_map.get(kw)
                if path:
                    path_counts[path] = path_counts.get(path, 0) + 1

        for kw, widget in self.checkbox_widgets.items():
            path = self.csv_data_map.get(kw)
            is_checked = self.checkbox_vars[kw].get()
            
            if path and path_counts.get(path, 0) > 1:
                if is_checked:
                    widget.configure(text_color="#888888")
                else:
                    widget.configure(text_color="#555555")
            else:
                if "その他未分類" in kw:
                    widget.configure(text_color="#ffcc00")
                else:
                    widget.configure(text_color="#DCE4EE")

    def add_destination_card(self, data=None):
        if data is None:
            data = {"platform": "disembed", "mode": "full", "url": "", "room": "", "token": "", "handle": "", "password": ""}

        card = ctk.CTkFrame(self.scroll_dest, fg_color="#2b2b2b", corner_radius=6)
        card.pack(pady=4, padx=2, fill="x")

        top_row = ctk.CTkFrame(card, fg_color="transparent")
        top_row.pack(fill="x", padx=6, pady=(4, 2))

        # --- プラットフォーム選択 ---
        ctk.CTkLabel(top_row, text="形式:", font=("Yu Gothic", 10)).pack(side="left", padx=(0, 2))
        
        raw_platform = data.get("platform", data.get("style", "disembed"))
        initial_display = self.reverse_platform_map.get(raw_platform, "Discord (Embed)")
        platform_var = ctk.StringVar(value=initial_display)

        platform_menu = ctk.CTkOptionMenu(
            top_row, 
            values=list(self.platform_map.keys()), 
            variable=platform_var, 
            width=130, 
            height=22,
            font=("Yu Gothic", 10)
        )
        platform_menu.pack(side="left", padx=2)

        # --- 転送モード選択 ---
        ctk.CTkLabel(top_row, text="モード:", font=("Yu Gothic", 10)).pack(side="left", padx=(6, 2))
        
        raw_mode = data.get("mode", "full")
        initial_mode_display = self.reverse_mode_map.get(raw_mode, "全文転送")
        mode_var = ctk.StringVar(value=initial_mode_display)

        mode_menu = ctk.CTkOptionMenu(
            top_row,
            values=list(self.mode_map.keys()),
            variable=mode_var,
            width=120,
            height=22,
            font=("Yu Gothic", 10)
        )
        mode_menu.pack(side="left", padx=2)

        card_data = {}

        def delete_card():
            card.destroy()
            if card_data in self.destination_rows:
                self.destination_rows.remove(card_data)

        btn_del = ctk.CTkButton(top_row, text="削除", width=40, height=22, fg_color="#d9534f", hover_color="#c9302c",
                                font=("Yu Gothic", 10, "bold"), command=delete_card)
        btn_del.pack(side="right")

        fields_frame = ctk.CTkFrame(card, fg_color="transparent")
        fields_frame.pack(fill="x", padx=6, pady=(2, 6))

        url_entry = ctk.CTkEntry(fields_frame, placeholder_text="Webhook URL / API Endpoint", height=26)
        room_entry = ctk.CTkEntry(fields_frame, placeholder_text="Room / Channel ID", height=26)
        token_entry = ctk.CTkEntry(fields_frame, placeholder_text="Access Token / Bot Token", height=26, show="*")
        handle_entry = ctk.CTkEntry(fields_frame, placeholder_text="User Handle", height=26)
        pass_entry = ctk.CTkEntry(fields_frame, placeholder_text="App Password", height=26, show="*")

        for entry in (url_entry, room_entry, token_entry, handle_entry, pass_entry):
            self.bind_entry_context_menu(entry)
        
        def update_fields(*args):
            for widget in (url_entry, room_entry, token_entry, handle_entry, pass_entry):
                widget.pack_forget()

            display_name = platform_var.get()
            sel = self.platform_map.get(display_name, display_name)

            if sel in ["disembed", "dissimple", "slack", "webhook"]:
                url_entry.configure(placeholder_text="Webhook URL")
                url_entry.pack(fill="x", pady=2)
            elif sel == "matrix":
                url_entry.configure(placeholder_text="Matrix Base URL (省略可)")
                url_entry.pack(fill="x", pady=2)
                room_entry.configure(placeholder_text="Room ID (!xxx:server)")
                room_entry.pack(fill="x", pady=2)
                token_entry.configure(placeholder_text="Access Token")
                token_entry.pack(fill="x", pady=2)
            elif sel == "bluesky":
                url_entry.configure(placeholder_text="PDS URL (既定: https://bsky.social)")
                url_entry.pack(fill="x", pady=2)
                handle_entry.configure(placeholder_text="Handle (例: user.bsky.social)")
                handle_entry.pack(fill="x", pady=2)
                pass_entry.configure(placeholder_text="App Password")
                pass_entry.pack(fill="x", pady=2)

        platform_var.trace_add("write", update_fields)
        update_fields()

        if data.get("url"): url_entry.insert(0, data.get("url"))
        if data.get("room"): room_entry.insert(0, data.get("room"))
        if data.get("token"): token_entry.insert(0, data.get("token"))
        if data.get("handle"): handle_entry.insert(0, data.get("handle"))
        if data.get("password"): pass_entry.insert(0, data.get("password"))

        card_data.update({
            "card": card,
            "platform_var": platform_var,
            "mode_var": mode_var,
            "url_entry": url_entry,
            "room_entry": room_entry,
            "token_entry": token_entry,
            "handle_entry": handle_entry,
            "pass_entry": pass_entry
        })
        self.destination_rows.append(card_data)

    def load_info_csv(self, csv_path, scroll_parent):
        etc_key = "[その他未分類] info/etc"
        etc_rel = "js_core/database/info/etc"
        self.csv_data_map[etc_key] = etc_rel
        etc_var = ctk.BooleanVar(value=False)
        etc_var.trace_add("write", self.update_duplicate_states)
        self.checkbox_vars[etc_key] = etc_var
        
        chk_etc = ctk.CTkCheckBox(scroll_parent, text="【その他未分類】 [info/etc]", variable=etc_var, font=("Yu Gothic", 10, "bold"), text_color="#ffcc00")
        chk_etc.pack(pady=2, padx=2, anchor="w")
        self.checkbox_widgets[etc_key] = chk_etc

        if not os.path.exists(csv_path):
            ctk.CTkLabel(scroll_parent, text="CSV未検出", text_color="orange").pack(anchor="w", padx=5, pady=2)
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
                        var.trace_add("write", self.update_duplicate_states)
                        self.checkbox_vars[kw] = var
                        
                        chk = ctk.CTkCheckBox(scroll_parent, text=f"{kw} [{tf}]", variable=var, font=("Yu Gothic", 10))
                        chk.pack(pady=2, padx=2, anchor="w")
                        self.checkbox_widgets[kw] = chk
        except Exception as e:
            print(f"Info CSV error: {e}")

    def load_quake_csv(self, csv_path, scroll_parent):
        etc_key = "[その他未分類] quake/etc"
        etc_rel = "js_core/database/quake/etc"
        self.csv_data_map[etc_key] = etc_rel
        etc_var = ctk.BooleanVar(value=False)
        etc_var.trace_add("write", self.update_duplicate_states)
        self.checkbox_vars[etc_key] = etc_var
        
        chk_etc = ctk.CTkCheckBox(scroll_parent, text="【その他未分類】 [quake/etc]", variable=etc_var, font=("Yu Gothic", 10, "bold"), text_color="#ffcc00")
        chk_etc.pack(pady=2, padx=2, anchor="w")
        self.checkbox_widgets[etc_key] = chk_etc

        if not os.path.exists(csv_path):
            ctk.CTkLabel(scroll_parent, text="CSV未検出", text_color="orange").pack(anchor="w", padx=5, pady=2)
            return
        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    cleaned = {k.strip().lower(): v for k, v in row.items() if k is not None}
                    kw, cat = cleaned.get("keyword"), cleaned.get("category")
                    if kw:
                        sub = f"quake/{cat}" if cat else "quake"
                        rel = os.path.join("js_core", "database", sub).replace("\\", "/")
                        self.csv_data_map[kw] = rel
                        var = ctk.BooleanVar(value=False)
                        var.trace_add("write", self.update_duplicate_states)
                        self.checkbox_vars[kw] = var
                        
                        chk = ctk.CTkCheckBox(scroll_parent, text=f"{kw} [{cat}]", variable=var, font=("Yu Gothic", 10))
                        chk.pack(pady=2, padx=2, anchor="w")
                        self.checkbox_widgets[kw] = chk
        except Exception as e:
            print(f"Quake CSV error: {e}")

    def load_volcano_csv(self, csv_path, scroll_parent):
        etc_key = "[その他未分類] volcano/etc"
        etc_rel = "js_core/database/volcano/etc"
        self.csv_data_map[etc_key] = etc_rel
        etc_var = ctk.BooleanVar(value=False)
        etc_var.trace_add("write", self.update_duplicate_states)
        self.checkbox_vars[etc_key] = etc_var
        
        chk_etc = ctk.CTkCheckBox(scroll_parent, text="【その他未分類】 [volcano/etc]", variable=etc_var, font=("Yu Gothic", 10, "bold"), text_color="#ffcc00")
        chk_etc.pack(pady=2, padx=2, anchor="w")
        self.checkbox_widgets[etc_key] = chk_etc

        if not os.path.exists(csv_path):
            ctk.CTkLabel(scroll_parent, text="CSV未検出", text_color="orange").pack(anchor="w", padx=5, pady=2)
            return
        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    cleaned = {k.strip().lower(): v for k, v in row.items() if k is not None}
                    kw = cleaned.get("keyword")
                    cat = cleaned.get("category") or cleaned.get("target folder")
                    
                    if kw:
                        sub = f"volcano/{cat}" if cat else "volcano"
                        rel = os.path.join("js_core", "database", sub).replace("\\", "/")
                        self.csv_data_map[kw] = rel
                        var = ctk.BooleanVar(value=False)
                        var.trace_add("write", self.update_duplicate_states)
                        self.checkbox_vars[kw] = var
                        
                        chk = ctk.CTkCheckBox(scroll_parent, text=f"{kw} [{cat if cat else 'volcano'}]", variable=var, font=("Yu Gothic", 10))
                        chk.pack(pady=2, padx=2, anchor="w")
                        self.checkbox_widgets[kw] = chk
        except Exception as e:
            print(f"Volcano CSV error: {e}")

    def load_all_csvs(self):
        self.load_info_csv(self.info_csv_path, self.scroll_info)
        self.load_quake_csv(self.quake_csv_path, self.scroll_quake)
        self.load_volcano_csv(self.volcano_csv_path, self.scroll_volcano)

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
                        "mode": dest.get("mode", "full"),
                        "url": dest.get("url", ""),
                        "room": dest.get("room", ""),
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
        try:
            if not os.path.exists(dest_dir):
                os.makedirs(dest_dir, exist_ok=True)
                
            path = os.path.join(dest_dir, f"{shortcut_name}.lnk")
            target_path = os.path.join(self.base_dir, target_script)
            python_path = sys.executable
            icon_file_path = os.path.join(self.base_dir, "icon.ico")

            # Windowsのパス表記（バックスラッシュ）に統一
            safe_path = path.replace("/", "\\")
            safe_target = target_path.replace("/", "\\")
            safe_workdir = self.base_dir.replace("/", "\\")
            safe_python = python_path.replace("/", "\\")
            safe_icon = icon_file_path.replace("/", "\\")

            vbs_path = os.path.join(self.base_dir, "temp_create_shortcut.vbs")
            
            # VBScript内で引数をダブルクォーテーションで囲むため、VBS側のエスケープ(" -> "")を正しく配置
            vbs_content = (
                'Set ws = CreateObject("WScript.Shell")\n'
                f'Set lnk = ws.CreateShortcut("{safe_path}")\n'
                f'lnk.TargetPath = "{safe_python}"\n'
                f'lnk.Arguments = """{safe_target}"""\n'
                f'lnk.WorkingDirectory = "{safe_workdir}"\n'
                f'lnk.IconLocation = "{safe_icon}, 0"\n'
                f'lnk.WindowStyle = 7\n'
                'lnk.Save\n'
            )

            with open(vbs_path, "w", encoding="cp932") as f:
                f.write(vbs_content)

            subprocess.run(["cscript", "//nologo", vbs_path], check=True)
            if os.path.exists(vbs_path):
                os.remove(vbs_path)
            return True
        except Exception as e:
            print(f"Shortcut creation error: {e}")
            if os.path.exists(vbs_path):
                try: os.remove(vbs_path)
                except Exception: pass
            return False

    def open_core_gui(self):
        core_gui_path = os.path.join(self.base_dir, "js_core", "js_gui_setup.py")
        if os.path.exists(core_gui_path):
            try:
                subprocess.Popen([sys.executable, core_gui_path])
            except Exception as e:
                messagebox.showerror("起動エラー", f"Core設定の起動に失敗しました:\n{e}")
        else:
            messagebox.showwarning("ファイル未検出", f"指定されたパスにファイルが見つかりません:\n{core_gui_path}")

    def save_config(self):
        raw_selected_dirs = [self.csv_data_map[kw] for kw, var in self.checkbox_vars.items() if var.get()]
        selected_dirs = []
        for p in raw_selected_dirs:
            if p not in selected_dirs:
                selected_dirs.append(p)

        destinations_list = []
        for row in self.destination_rows:
            display_platform = row["platform_var"].get()
            internal_platform = self.platform_map.get(display_platform, display_platform)

            display_mode = row["mode_var"].get()
            internal_mode = self.mode_map.get(display_mode, "full")

            destinations_list.append({
                "style": internal_platform,
                "mode": internal_mode,
                "url": row["url_entry"].get().strip(),
                "room": row["room_entry"].get().strip(),
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

            if self.var_create_desktop.get():
                desktop = os.path.join(os.path.expanduser("~"), "Desktop")
                if not os.path.exists(desktop):
                    desktop = os.path.join(os.environ.get("USERPROFILE", ""), "Desktop")
                sc_main = self.create_shortcut_file("J-Sentinel_main.py", "J-Sentinel_Alert", desktop)
                sc_bot = self.create_shortcut_file("bot.py", "J-Sentinel_CallBack", desktop)
                if sc_main and sc_bot:
                    created_actions.append("デスクトップショートカット作成完了")

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