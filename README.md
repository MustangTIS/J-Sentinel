<div align="center">
  <img src="Asset/icon.jpg" alt="J-Sentinel Logo" width="160" height="160">
  <h1>J-Sentinel ～ 高度防災システム (v1.1.0)</h1>
  <p><strong>高度防災情報インジェスト・マルチプラットフォーム配信・対話型ボット統合オーケストレーターシステム</strong></p>
</div>

---

## 📥 ダウンロード

最新のフルシステム版パッケージ（コアエンジン、マルチ配信モジュール、対話型ボット、GUIマネージャー同梱）は、以下のリンクからダウンロードできます。

👉 **[J-Sentinel-FullSystem_v1.1.0.zip をダウンロード](https://github.com/MustangTIS/J-Sentinel/releases/download/v1.1.0/J-Sentinel-FullSystem_v1.1.0.zip)**

---

## 📋 概要

**J-Sentinel** は、気象庁が公開する公式オープンデータ（地震、津波、気象警報、各種防災情報など）を定期ポーリングによってローカルストレージへインジェスト（取得・蓄積）し、さらに **Discord、Slack、Matrix、Bluesky** などのマルチプラットフォームへ自動プッシュ通知配信、および **Discord / Matrix ボットによる対話型の気象・警報情報照会** を行うための高度防災システムです。

非公式APIに依存せず、気象庁の一次ソースからクリーンかつ安全にデータを取得する「コアエンジン」と、それを拡張・通知・対話化する「フルシステム」を一つに統合したパッケージとして提供しています。

---

## 📁 ディレクトリ構造

本パッケージには、コアエンジン単体と、マルチ通知・対話型ボット・GUI設定マネージャーを含むフルシステム版が同梱されています。

```text
\GitHub\J-Sentinel\
  ┣ Asset/
  ┃   ┗ icon.jpg              # システムアイコン
  ┣ J-Sentinel-Core/          # コア・インジェストシステム単体
  ┃   ┣ codemaster/           # 振り分けルール・地域コード辞書 (CSV)
  ┃   ┣ database/             # 取得したJSONデータや同期時刻ファイル（※実行時に自動生成）
  ┃   ┣ config.json           # コア動作設定ファイル
  ┃   ┣ run_sentinel.py       # メイン・オーケストレーター（常駐ランナー）
  ┃   ┣ core-runner.bat       # ランナー起動用バッチ
  ┃   ┣ js_gui_setup.py       # GUI設定管理・マスター編集ツール
  ┃   ┗ setup-gui.bat         # コア用GUI設定起動バッチ
  ┗ J-Sentinel-FullSystem/    # フルシステム版（マルチ配信・GUI・Bot統合）
      ┣ config.json           # システム全体設定（トークン・配信先等）
      ┣ setup-gui.bat         # GUI設定・マルチ配信先マネージャー起動用バッチ
      ┣ core-runner.bat       # システム全体の統合起動用バッチ
      ┣ J-sentinel.bat        # メイン・プッシュ通知システム起動用バッチ
      ┣ bot.bat               # 対話型チャットボット (Discord/Matrix) 起動用バッチ
      ┣ J-Sentinel_main.py    # メイン・オーケストレーター
      ├─ system/              # システム中核モジュール群
      │   ┣ config_manager.py # 設定ファイル読み込み・環境検証
      │   ┣ log_monitor.py    # 監視ディレクトリの非同期ファイルウォッチャー
      │   ┣ info_parser.py    # 気象情報・特別警報等の汎用パーサ
      │   ┣ quake_parser.py   # 地震・津波・遠地地震情報 パーサ＆震度ソート
      │   ┗ senders.py        # マルチプラットフォーム配信司令塔
      ├─ bot/                 # 対話型ボットモジュール群
      │   ┣ discord_bot.py    # Discord インタラクティブ・コールバックボット
      │   ┣ matrix_bot.py     # Matrix インタラクティブ・コールバックボット
      │   ┣ warning_parser.py # 気象警報・注意報JSON パーサ＆地域検索（レベル別グルーピング対応）
      │   ┣ weather_parser.py # 天気予報JSON パーサ (Discord Embed用)
      │   ┗ weather_parser_matrix.py # 天気予報JSON パーサ (Matrix用)
      └─ js_core/             # コアインジェストモジュール群

```

---

## ⚙️ 主な仕様・特徴

* **自動オーケストレーション**: 指定秒数ごとに各フェッチスクリプトを安全に順次実行し、データの取りこぼしを防止。
* **インテリジェントな差分同期**: 初回のみ全件取得を行い、2回目以降は前回同期時刻を基準にした高速な差分チェックへ自動移行。
* **堅牢なプロセス管理**: サブプロセス実行時のタイムアウト制御により、ネットワーク遅延や大量データ処理時のデッドロックを回避。
* **マルチプラットフォーム対応**: 検知した災害・気象情報を Discord (Embed/Simple・改行対応)、Slack、Matrix、Bluesky へシームレスにディスパッチ。
* **対話型チャットボット**: DiscordやMatrix上から「帯広市の気象情報は？」や「帯広の天気は？」などのメンション・問い合せて即座に情報を取得可能。
* **CustomTkinter製 GUIマネージャー**: `setup-gui.bat` により、巡回間隔、監視対象、各SNS配信先のトークンや表示名を直感的に設定可能。

---

## 🚀 クイックスタート (Full System Edition)

1. **環境の準備**
* Python 3.x がインストールされていることを確認してください（インストーラー実行時は `Add Python to PATH` にチェック）。


2. **初期設定 (GUI)**
* 展開したフォルダ内にある `\J-Sentinel-FullSystem\setup-gui.bat` を実行します。
* 自動で必要ライブラリ（`requests`, `psutil`, `Pillow`, `customtkinter`, `discord.py`, `nio`, `pandas` 等）が導入され、設定画面が起動します。
* トークンや各配信先、監視対象を設定して「設定を保存」してください。


3. **メイン・プッシュ通知システムの本格稼働**
* `core-runner.bat` または `J-sentinel.bat` を実行すると、メインランナーおよびインジェスト基盤が連動して常駐を開始し、新着情報を各プラットフォームへ自動プッシュ通知します。


4. **対話型チャットボットの利用**
* 必要に応じて `bot.bat` を起動することで、チャットからの対話型情報照会が利用可能になります。
* ※DiscordとMatrixのみ対応。
* **対応しているチャットの例**:
* 天気情報: `○○の天気は` または `天気/○○`
* 気象情報: `○○の気象情報は` または `気象/○○`







---

## 📄 仕様書・関連リンク

* [開発方針・仕様書 (GitHub)](https://github.com/MustangTIS/J-Sentinel/blob/main/%E9%96%8B%E7%99%BA%E6%96%B9%E9%87%9D%E4%BB%95%E6%A7%98%E6%9B%B8.md)

---

## 📝 履歴 / Version

* **v0.5 〜 v0.9.x**: コアシステム・オーケストレーターの安定稼働、マルチプラットフォーム配信およびGUI設定ツールの刷新。
* **v0.30.5**:
* モジュール構造の大幅な整理（`system/` および `bot/` 配下への機能分離）。
* Matrixチャットボット (`matrix_bot.py`) および天気予報パーサの統合。
* 監視ガードレールの最適化と通知・配信の安定化向上。
* 起動用バッチファイルの整理（`J-sentinel.bat` / `bot.bat`）。


* **v1.0.0**:
* 気象警報インジェスト・パーサの強化（お知らせ `notice` の取得対応、解除情報の厳密な除外）。
* マスターCSV（`keiho.csv`）からの危険レベル（`kikenlv`）動的連携と出力時のレベル別グルーピング（降順）対応。
* GUI設定マネージャーにおけるマルチプラットフォームの内部値・表示名マッピング機構の導入。
* 起動・運用バッチの `core-runner.bat` への集約とGUIショートカットの追従。

* **v1.1.0**:
* 気象庁の利用規約に基づき気象庁からのソースだという情報を語尾に記載するスクリプトを追加。