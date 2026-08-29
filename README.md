<div align="center">
  <img src="Asset/icon.jpg" alt="J-Sentinel Logo" width="160" height="160">
  <h1>J-Sentinel (v0.9.5-beta)</h1>
  <p><strong>高度防災情報インジェスト・マルチプラットフォーム配信オーケストレーターシステム</strong></p>
</div>

---

## 📥 ダウンロード

最新のフルシステム版パッケージ（コアエンジン、マルチ配信モジュール、GUIマネージャー同梱）は、以下のリンクからダウンロードできます。

👉 **[J-Sentinel_FullSystem_v0.9.5.zip をダウンロード](https://github.com/MustangTIS/J-Sentinel/releases/download/v0.9.5/J-Sentinel_FullSyste_v0.9.5.zip)**

---

## 📋 概要

**J-Sentinel** は、気象庁が公開する公式オープンデータ（地震、津波、気象警報、各種防災情報など）を定期ポーリングによってローカルストレージへインジェスト（取得・蓄積）し、さらに **Discord、Slack、Matrix、Bluesky** などのマルチプラットフォームへ自動配信、対話型ボットによる情報照会を行うための高度防災システムです[cite: 22, 23]。

非公式APIに依存せず、気象庁の一次ソースからクリーンかつ安全にデータを取得する「コアエンジン」と、それを拡張・通知する「フルシステム（Discord連携等）」を一つに統合したパッケージとして提供しています[cite: 22, 23]。

---

## 📁 ディレクトリ構成

本パッケージには、コアエンジン単体と、マルチ通知・GUI設定マネージャーを含むフルシステム版が同梱されています。

```text
\GitHub\J-Sentinel\
 ┣ Asset/
 ┃  ┗ icon.jpg               # システムアイコン
 ┣ J-Sentinel-Core/          # コア・インジェストシステム単体
 ┃  ┣ codemaster/            # 振り分けルール・地域コード辞書 (CSV)
 ┃  ┣ database/              # 取得したJSONデータや同期時刻ファイル（※実行時に自動生成）
 ┃  ┣ config.json            # コア動作設定ファイル
 ┃  ┣ run_sentinel.py        # メイン・オーケストレーター（常駐ランナー）
 ┃  ┣ run_sentinel.bat       # ランナー起動用バッチ
 ┃  ┣ js_gui_setup.py        # GUI設定管理・マスター編集ツール
 ┃  ┗ setup-gui.bat          # コア用GUI設定起動バッチ
 ┗ J-Sentinel_FullSystem/    # フルシステム版（マルチ配信・GUI・Bot統合）
    ┣ config.json            # システム全体設定（トークン・配信先等）
    ┣ setup-gui.bat          # GUI設定・マルチ配信先マネージャー起動用バッチ
    ┣ J-Sentinel-Boot.bat    # メインシステム (J-Sentinel_main.py) 起動用バッチ
    ┣ Bot-Boot.bat           # Discordコールバックボット (bot.py) 起動用バッチ
    ┣ J-Sentinel_main.py     # メイン・オーケストレーター
    ┣ senders.py             # マルチプラットフォーム配信司令塔 (Discord/Slack/Matrix/Bluesky)
    ┣ bot.py                 # Discord インタラクティブ・コールバックボット
    └─ js_core/              # コアインジェストモジュール群