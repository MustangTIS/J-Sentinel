======================================================================
 J-Sentinel ～ 高度防災システム (Full System Edition)
======================================================================

【概要】
J-Sentinel は、気象庁が公開する公式オープンデータ（地震、津波、気象警報、
防災情報など）を定期ポーリングによってローカルストレージへインジェストし、
Discord、Slack、Matrix、Bluesky などのマルチプラットフォームへ自動配信、
および Discord ボットによる対話型の気象・警報情報照会を行うための
スタンドアロン型コアシステムです。

【ディレクトリ構造 & 主要ファイル】
\J-Sentinel_FullSystem\
 ├─ config.json              # システム全体設定（Discordトークン・配信先・監視対象）
 ├─ setup-gui.bat            # 【Step 1】GUI設定管理ツール起動用バッチ
 ├─ J-Sentinel-Boot.bat      # 【Step 2】メインシステム (J-Sentinel_main.py) 起動用バッチ
 ├─ Bot-Boot.bat             # 【参考】Discordコールバックボット (bot.py) 単体起動用バッチ
 │
 ├─ J-Sentinel_main.py       # メイン・オーケストレーター（新着検知・ディスパッチ・更新確認）
 ├─ js_main_gui_setup.py     # GUI設定・マルチ配信先マネージャー (CustomTkinter製)
 ├─ config_manager.py        # 設定ファイル読み込み・環境検証モジュール
 ├─ log_monitor.py           # 監視ディレクトリの非同期ファイルウォッチャー
 ├─ senders.py               # マルチプラットフォーム配信司令塔（Discord / Slack / Matrix / Bluesky）
 ├─ bot.py                   # Discord インタラクティブ・コールバックボット
 ├─ warning_parser.py        # 気象警報・注意報JSON パーサ＆地域検索ロジック
 ├─ quake_parser.py          # 地震・津波・遠地地震情報 パーサ＆震度ソートロジック
 ├─ info_parser.py           # 気象情報・特別警報等の汎用パーサ
 │
 └─ js_core/                 # コア・インジェストモジュール群
     ├─ run_sentinel.py      # 気象庁データ定期ポーリング・インジェスト実行スクリプト
     ├─ codemaster/          # 振り分けルール・地域コード辞書 (CSV)
     └─ database/            # 取得データの保存先ルート
         ├─ info/            # 総合情報・気象警報系
         ├─ keiho/           # 警報変換データ (WarningRT.json 等)
         └─ quake/           # 地震系 (japan / tsunami / world / etc)


【クイックスタート手順】

1. 環境の準備
   - Python 3.x がインストールされていることを確認してください
     （インストーラー実行時は 'Add Python to PATH' にチェックを入れてください）。

2. 初期設定 (GUI)
   - `setup-gui.bat` を実行します。
   - 自動的に Python 環境の確認と、不足しているライブラリ
     （psutil, requests, Pillow, customtkinter）の導入が行われます。
   - GUI画面が起動したら、以下を設定してください：
     ・ Discord Bot 共通設定（Bot Token）
     ・ 1. 監視対象の選択（CSVに紐づくインジェストフォルダの有効化）
     ・ 2. 配信先・SNS連携設定（Discord Webhook、Matrix、Bluesky 等の追加）
   - 「設定を保存」ボタンを押すと `config.json` に反映されます。
   - 必要に応じて「Core設定」ボタンを押し、Coreシステム側の設定も行ってください。
   
3. システムの本格稼働
   - `J-Sentinel-Boot.bat` を実行します。
   - バッチが自動で Python 環境とライブラリを確認後、
     メインランナー (`J-Sentinel_main.py`) が起動し、裏で `run_sentinel.py` も連動します。
   - 新着防災イベントを検知次第、指定されたプラットフォームへ自動配信されます。

4. Discord Bot（情報照会機能）の併用
   - 地域ごとの警報・注意報をチャットから即座に引き出したい場合は、
     別途 `Bot-Boot.bat` を起動することで、Discord上で「帯広市の気象情報は」
     などのメンション・コマンド応答が利用可能になります。


【対応配信プラットフォーム】
- Discord (Embed形式 / Simple形式)
- Slack (Webhook連携)
- Matrix (マトリクスルーム送受信)
- Bluesky (AT Protocol)
======================================================================